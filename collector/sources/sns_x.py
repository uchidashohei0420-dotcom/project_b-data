"""Collects from X (Twitter) via twitter-cli (https://github.com/public-clis/twitter-cli),
the backend that `agent-reach install` sets up: (1) the official account's recent
timeline, (2) a keyword search for "あたしンチ".

Ambiguous posts (neither a clear event announcement nor a clear goods announcement) are
classified as `news` rather than forced into event/goods — see docs/PLAN.md's schema
notes. Both sub-collections are treated as source_type=sns (low confidence).

Verified against twitter-cli's public README (2026-08): the binary is invoked directly
as `twitter` (not `agent-reach twitter ...` — agent-reach is only the installer/doctor
tool), subcommands are `user-posts <handle> --json` and `search "<keyword>" --json`, and
auth is two cookie values (`TWITTER_AUTH_TOKEN` + `TWITTER_CT0`), not a single token.

TODO before first real run:
- The README doesn't document the exact JSON field names per post. `_draft_from_post`
  below tries a few plausible key names (`text`/`full_text`, `url`/`permalink`) — run
  `twitter user-posts <handle> --json` once locally with real credentials and adjust to
  match the actual output.
- Use a dedicated throwaway X account's cookies — never the maintainer's main account.
"""
from __future__ import annotations

import json
import subprocess

from .. import config
from ..models import FeedItemDraft, ItemType, SourceType
from .base import Source, SourceError

OFFICIAL_HANDLE = "atashinchi_new"
SEARCH_KEYWORD = "あたしンチ"

_TIMELINE_ARGS = ["twitter", "user-posts", OFFICIAL_HANDLE, "--json"]
_SEARCH_ARGS = ["twitter", "search", SEARCH_KEYWORD, "--json"]

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


def _run_twitter_cli(args: list[str], *, auth_token: str, ct0: str) -> list[dict]:
    try:
        result = subprocess.run(
            args,
            env={"TWITTER_AUTH_TOKEN": auth_token, "TWITTER_CT0": ct0},
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise SourceError(f"twitter-cli exited {exc.returncode}: {exc.stderr[:500]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise SourceError(f"twitter-cli timed out: {' '.join(args)}") from exc
    except FileNotFoundError as exc:
        raise SourceError("twitter CLI is not installed on PATH (run `agent-reach install`)") from exc

    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SourceError(f"twitter-cli returned non-JSON output: {exc}") from exc

    # Expected shape: a list of post objects, or {"posts": [...]} / {"tweets": [...]}.
    # Accept any of these until the real output is verified (see module TODO).
    if isinstance(parsed, dict):
        parsed = parsed.get("posts") or parsed.get("tweets") or parsed.get("data") or []
    if not isinstance(parsed, list):
        raise SourceError("unexpected twitter-cli output shape")
    return parsed


def _draft_from_post(post: dict, *, source_name: str) -> FeedItemDraft | None:
    text = post.get("text") or post.get("full_text") or post.get("content")
    url = post.get("url") or post.get("permalink") or post.get("link")
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
        credentials = config.twitter_credentials()
        if not credentials:
            # Not a hard failure: SNS is one of three source categories, and missing
            # credentials (not yet configured, or expired) shouldn't fail the whole run.
            raise SourceError(
                f"{config.TWITTER_AUTH_TOKEN_ENV}/{config.TWITTER_CT0_ENV} not set; skipping SNS collection"
            )
        auth_token, ct0 = credentials

        items: list[FeedItemDraft] = []

        timeline_posts = _run_twitter_cli(_TIMELINE_ARGS, auth_token=auth_token, ct0=ct0)
        for post in timeline_posts:
            draft = _draft_from_post(post, source_name=f"@{OFFICIAL_HANDLE}")
            if draft:
                items.append(draft)

        search_posts = _run_twitter_cli(_SEARCH_ARGS, auth_token=auth_token, ct0=ct0)
        for post in search_posts:
            draft = _draft_from_post(post, source_name=f"X検索: {SEARCH_KEYWORD}")
            if draft:
                items.append(draft)

        return items
