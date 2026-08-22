"""Collects from X (Twitter) via twitter-cli (pip install twitter-cli,
https://github.com/jackwener/twitter-cli — a standalone package, NOT something
`agent-reach install` sets up despite earlier assumptions): (1) the official account's
recent timeline, (2) a keyword search for "あたしンち".

Ambiguous posts (neither a clear event announcement nor a clear goods announcement) are
classified as `news` rather than forced into event/goods — see docs/PLAN.md's schema
notes. Both sub-collections are treated as source_type=sns (low confidence).

Verified against a real run (2026-08-22, via a disposable diagnostic GitHub Actions
workflow) using real throwaway-account cookies:
- `pip install twitter-cli` alone provides the `twitter` binary; auth env vars are
  `TWITTER_AUTH_TOKEN` + `TWITTER_CT0` as already assumed.
- `twitter user-posts <handle> --json` succeeds and returns
  `{"ok": true, "schema_version": "1", "data": [<post>, ...]}`. Each post has no
  `url`/`permalink` field — the permalink must be built from `author.screenName` + `id`
  (for a retweet, `author` is the ORIGINAL tweet's author, which is what we want to link
  to; `retweetedBy` names the account whose timeline surfaced it).
- `twitter search "<keyword>" --json` reproducibly 404s (confirmed with both a Japanese
  and an ASCII-only keyword) — root-caused to twitter-cli 0.8.5's hardcoded
  `SearchTimeline` GraphQL query ID having gone stale server-side, not anything wrong
  with our call. Because this is an upstream library bug outside our control and could
  resolve itself on a future twitter-cli release, `collect()` below fault-isolates the
  search sub-collection from the timeline one: a broken search must not discard a
  successfully-collected timeline.
"""
from __future__ import annotations

import json
import subprocess

from .. import config
from ..models import FeedItemDraft, ItemType, SourceType
from .base import Source, SourceError, SourceNotConfigured

OFFICIAL_HANDLE = "atashinchi_new"
SEARCH_KEYWORD = "あたしンち"

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

    # Real shape (verified 2026-08-22): {"ok": true, "data": [...]} on success, or
    # {"ok": false, "error": {...}} on failure — the latter has no "data" key, so it
    # naturally falls through to [] here rather than raising.
    if isinstance(parsed, dict):
        parsed = parsed.get("data") or []
    if not isinstance(parsed, list):
        raise SourceError("unexpected twitter-cli output shape")
    return parsed


def _draft_from_post(post: dict, *, source_name: str) -> FeedItemDraft | None:
    text = post.get("text")
    author = post.get("author") or {}
    screen_name = author.get("screenName")
    post_id = post.get("id")
    if not text or not screen_name or not post_id:
        return None
    url = f"https://x.com/{screen_name}/status/{post_id}"

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
            # Not configured yet, not broken — doesn't count toward the run failure
            # threshold (see SourceNotConfigured).
            raise SourceNotConfigured(
                f"{config.TWITTER_AUTH_TOKEN_ENV}/{config.TWITTER_CT0_ENV} not set; skipping SNS collection"
            )
        auth_token, ct0 = credentials

        items: list[FeedItemDraft] = []

        timeline_posts = _run_twitter_cli(_TIMELINE_ARGS, auth_token=auth_token, ct0=ct0)
        for post in timeline_posts:
            draft = _draft_from_post(post, source_name=f"@{OFFICIAL_HANDLE}")
            if draft:
                items.append(draft)

        # Fault-isolated from the timeline call above: twitter-cli's search subcommand is
        # known (2026-08) to be unreliable upstream (see module docstring), and a broken
        # search must not discard a successfully-collected timeline.
        try:
            search_posts = _run_twitter_cli(_SEARCH_ARGS, auth_token=auth_token, ct0=ct0)
        except SourceError:
            search_posts = []
        for post in search_posts:
            draft = _draft_from_post(post, source_name=f"X検索: {SEARCH_KEYWORD}")
            if draft:
                items.append(draft)

        return items
