"""Orchestrates a single collection run: gather from every Source (fault-isolated),
dedupe against history, write history + trimmed feed.json atomically, validate against
the schema, and commit+push only if everything succeeds.

Exits non-zero (failing the GitHub Actions job, which triggers the standard failure
email) if: a source that previously returned items now returns zero (silent-degradation
guard), too many sources errored, or the freshly-written feed fails schema validation.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .dedupe import merge
from .models import FeedItem, FeedItemDraft, ItemType, SourceType
from .sources.base import Source, SourceError
from .sources.ec_rakuten import ECRakutenSource
from .sources.official_keraeiko import OfficialKeraeikoSource
from .sources.sns_x import SnsXSource

# ec_animate.ECAnimateSource and ec_loft.ECLoftSource are deliberately NOT imported/wired
# in here — verified against the live sites (2026-08-21) to be unreachable via plain
# `requests` (CDN bot-protection blocks), see each module's docstring for specifics and
# what re-enabling would need (Playwright, most likely). official_30th.py was deleted
# outright (the site has no real news section at all, not a scraping problem). ec_amazon
# was dropped in favor of ec_rakuten.py — same reasoning: highest ToS/bot-detection risk
# of any source, replaced by a legitimate free JSON API that doesn't need scraping at all.

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("collector")

ALL_SOURCES: list[type[Source]] = [
    OfficialKeraeikoSource,
    ECRakutenSource,
    SnsXSource,
]


def _atomic_write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)  # atomic on POSIX: a crash mid-write can't leave a torn file


def _load_previous_status() -> dict:
    if not config.STATUS_PATH.exists():
        return {}
    try:
        return json.loads(config.STATUS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _load_all_history() -> list[FeedItem]:
    items: list[FeedItem] = []
    if not config.HISTORY_DIR.exists():
        return items
    for path in sorted(config.HISTORY_DIR.glob("*.json")):
        try:
            raw_items = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log.warning("skipping unreadable history file %s", path)
            continue
        for raw in raw_items:
            items.append(
                FeedItem(
                    **{**raw, "type": ItemType(raw["type"]), "source_type": SourceType(raw["source_type"])}
                )
            )
    return items


def _write_history(all_items: list[FeedItem]) -> None:
    by_month: dict[str, list[FeedItem]] = defaultdict(list)
    for item in all_items:
        month_key = item.collected_at[:7]  # "YYYY-MM" prefix of an ISO8601 timestamp
        by_month[month_key].append(item)

    for month_key, items in by_month.items():
        path = config.HISTORY_DIR / f"{month_key}.json"
        _atomic_write_json(path, [item.to_json_dict() for item in items])


def _write_feed(all_items: list[FeedItem], *, generated_at: datetime) -> None:
    latest = sorted(all_items, key=lambda i: i.collected_at, reverse=True)[: config.FEED_ITEM_LIMIT]
    envelope = {
        "generated_at": generated_at.isoformat(),
        "schema_version": 1,
        "items": [item.to_json_dict() for item in latest],
    }
    _atomic_write_json(config.FEED_PATH, envelope)


def _validate_feed() -> None:
    import jsonschema

    schema = json.loads(config.SCHEMA_PATH.read_text(encoding="utf-8"))
    feed = json.loads(config.FEED_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(instance=feed, schema=schema)


def _check_for_silent_regressions(status: dict[str, dict], previous_status: dict) -> list[str]:
    """A source that previously succeeded with >0 items but now returns 0 is treated as a
    likely selector break, not "nothing new today" — flag it rather than silently
    shrinking the feed forever."""
    regressions = []
    previous_sources = previous_status.get("sources", {})
    for name, result in status.items():
        prev = previous_sources.get(name)
        if prev and prev.get("ok") and prev.get("count", 0) > 0 and result["count"] == 0 and result["ok"]:
            regressions.append(name)
    return regressions


def run() -> int:
    now = datetime.now(timezone.utc).astimezone()
    previous_status = _load_previous_status()

    status: dict[str, dict] = {}
    drafts: list[FeedItemDraft] = []
    error_count = 0

    for source_cls in ALL_SOURCES:
        source = source_cls()
        try:
            collected = source.collect()
            drafts.extend(collected)
            status[source.name] = {"count": len(collected), "ok": True, "error": None}
        except SourceError as exc:
            log.warning("%s failed: %s", source.name, exc)
            status[source.name] = {"count": 0, "ok": False, "error": str(exc)}
            error_count += 1
        except Exception as exc:  # noqa: BLE001 - fault isolation: one source must not abort the run
            log.exception("%s raised an unexpected error", source.name)
            status[source.name] = {"count": 0, "ok": False, "error": repr(exc)}
            error_count += 1

    regressions = _check_for_silent_regressions(status, previous_status)
    if regressions:
        log.error("sources that previously had data now returned zero: %s", regressions)

    if error_count > len(ALL_SOURCES) * config.SOURCE_FAILURE_THRESHOLD:
        log.error("too many sources failed (%d/%d); aborting without committing", error_count, len(ALL_SOURCES))
        return 1

    history = _load_all_history()
    merged = merge(history, drafts, now=now)

    _write_history(merged)
    _write_feed(merged, generated_at=now)
    _atomic_write_json(config.STATUS_PATH, {"checked_at": now.isoformat(), "sources": status})

    try:
        _validate_feed()
    except Exception as exc:  # noqa: BLE001
        log.error("feed.json failed schema validation, refusing to commit: %s", exc)
        return 1

    if regressions:
        # Data was written and is schema-valid, but a likely-broken source means the feed
        # is silently smaller than it should be. Fail the job (triggers the GH Actions
        # failure email) without skipping the commit — partial data is still better than
        # none, but the maintainer needs to know a selector probably broke.
        from .git_commit import commit_and_push

        commit_and_push(f"chore: update feed ({now.isoformat()}) [source regression: {regressions}]")
        return 1

    from .git_commit import commit_and_push

    committed = commit_and_push(f"chore: update feed ({now.isoformat()})")
    log.info("run complete: %d total items, committed=%s", len(merged), committed)
    return 0


if __name__ == "__main__":
    sys.exit(run())
