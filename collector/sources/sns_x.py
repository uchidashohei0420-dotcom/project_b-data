"""Collects from X (Twitter) via the Agent Reach CLI (https://github.com/Panniantong/agent-reach):
(1) the official account's recent timeline, (2) a keyword search for "あたしンチ".

Ambiguous posts (neither a clear event announcement nor a clear goods announcement) are
classified as `news` rather than forced into event/goods — see docs/PLAN.md's schema
notes. Both sub-collections are treated as source_type=sns (low confidence).

TODO before first real run:
- Run `agent-reach doctor` locally to confirm the installed CLI's exact subcommand names
  and output shape; the invocation below is written from the project's documented
  capabilities (cookie-auth, "read & search Twitter") but not yet verified against a real
  run. Adjust `_TIMELINE_ARGS`/`_SEARCH_ARGS` and `_parse_agent_reach_json` accordingly.
- Use a dedicated throwaway X account's cookie — never the maintainer's main account.
"""
from __future__ import annotations

import json
import subprocess

from .. import config
from ..models import FeedItemDraft, ItemType, SourceType
from .base import Source, SourceError

OFFICIAL_HANDLE = "atashinchi_new"
SEARCH_KEYWORD = "あたしンチ"

_TIMELINE_ARGS = ["agent-reach", "twitter", "timeline", OFFICIAL_HANDLE, "--json"]
_SEARCH_ARGS = ["agent-reach", "twitter", "search", SEARCH_KEYWORD, "--json"]

# A post is only classified as event/goods if it clearly signals one; keyword lists are
# intentionally narrow to keep false positives low (an over-eager classifier here would
# undermine the "SNS = low confidence, but classification should still be honest" design).
_EVENT_KEYWORDS = ("イベント", "開催", "トークショー", "サイン会", "フェア")
_GOODS_KEYWORDS = ("グッズ", "発売", "予約", "コラボ商品")


def _classify(text: str) -> ItemType:
    if any(keyword in text for keyword in _EVENT_KEYWORDS):
        return ItemType.EVENT
    if any(keyword in text for keyword in _GOODS_KEYWORDS):
        return ItemType.GOODS
    return ItemType.NEWS


def _run_agent_reach(args: list[str], *, cookie: str) -> list[dict]:
    try:
        result = subprocess.run(
            args,
            env={"AGENT_REACH_X_COOKIE": cookie},
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise SourceError(f"agent-reach exited {exc.returncode}: {exc.stderr[:500]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise SourceError(f"agent-reach timed out: {' '.join(args)}") from exc
    except FileNotFoundError as exc:
        raise SourceError("agent-reach CLI is not installed on PATH") from exc

    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SourceError(f"agent-reach returned non-JSON output: {exc}") from exc

    # Expected shape: a list of post objects, or {"posts": [...]}. Accept either until the
    # real CLI output is verified (see module TODO).
    if isinstance(parsed, dict):
        parsed = parsed.get("posts", [])
    if not isinstance(parsed, list):
        raise SourceError("unexpected agent-reach output shape")
    return parsed


def _draft_from_post(post: dict, *, source_name: str) -> FeedItemDraft | None:
    text = post.get("text") or post.get("content")
    url = post.get("url") or post.get("permalink")
    if not text or not url:
        return None

    return FeedItemDraft(
        type=_classify(text),
        source_type=SourceType.SNS,
        source_name=source_name,
        title=text[:80],
        url=url,
        raw_snippet=text,
    )


class SnsXSource(Source):
    name = "sns_x"

    def collect(self) -> list[FeedItemDraft]:
        cookie = config.agent_reach_cookie()
        if not cookie:
            # Not a hard failure: SNS is one of three source categories, and a missing
            # cookie (not yet configured, or expired) shouldn't fail the whole run.
            raise SourceError(f"{config.AGENT_REACH_X_COOKIE_ENV} is not set; skipping SNS collection")

        items: list[FeedItemDraft] = []

        timeline_posts = _run_agent_reach(_TIMELINE_ARGS, cookie=cookie)
        for post in timeline_posts:
            draft = _draft_from_post(post, source_name=f"@{OFFICIAL_HANDLE}")
            if draft:
                items.append(draft)

        search_posts = _run_agent_reach(_SEARCH_ARGS, cookie=cookie)
        for post in search_posts:
            draft = _draft_from_post(post, source_name=f"X検索: {SEARCH_KEYWORD}")
            if draft:
                items.append(draft)

        return items
