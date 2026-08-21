"""Stable ID generation and history-based merge.

Dedup is always evaluated against the full history (data/history/*.json), never against
the trimmed feed.json — otherwise an item that scrolled out of the "latest 200" window
would look new again the next time a source resurfaces it (e.g. the same tweet showing
up in a fresh keyword search).
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from .models import FeedItem, FeedItemDraft

# Whitelist (not blacklist) of query params worth keeping per host — everything else is
# stripped. A blacklist of `utm_*` etc. is fragile against new tracking param names; a
# whitelist degrades safely (worst case: two URLs that differ only in an unknown param
# collide, which is the desired outcome for dedup anyway).
_QUERY_PARAM_WHITELIST_BY_HOST = {
    # (host substring) -> set of params to keep
    "loft.co.jp": {"pid"},
    "animate-onlineshop.jp": {"id"},
}

_AMAZON_HOST_HINTS = ("amazon.co.jp", "amazon.com")
_AMAZON_ASIN_RE = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})", re.IGNORECASE)


def _normalize_generic_url(url: str) -> str:
    parts = urlsplit(url)
    host = parts.netloc.lower()
    path = parts.path.rstrip("/") or "/"

    keep = _QUERY_PARAM_WHITELIST_BY_HOST.get(
        next((h for h in _QUERY_PARAM_WHITELIST_BY_HOST if h in host), ""), set()
    )
    query_pairs = [(k, v) for k, v in parse_qsl(parts.query) if k in keep]
    query = urlencode(sorted(query_pairs))

    normalized = urlunsplit(("https", host, path, query, ""))
    return normalized


def make_id(url: str) -> str:
    """Per-source-aware stable ID. Amazon gets its ASIN extracted (surviving query-string
    churn like `?ref=...`/`?th=1`/locale prefixes); everything else falls back to a
    normalized-URL hash."""
    parts = urlsplit(url)
    host = parts.netloc.lower()

    if any(hint in host for hint in _AMAZON_HOST_HINTS):
        match = _AMAZON_ASIN_RE.search(parts.path)
        if match:
            return f"amazon:{match.group(1).upper()}"

    normalized = _normalize_generic_url(url)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"sha256:{digest}"


def merge(existing: list[FeedItem], incoming: list[FeedItemDraft], *, now: datetime) -> list[FeedItem]:
    """Returns existing + only the genuinely-new items from incoming. Never mutates or
    drops existing history entries."""
    existing_ids = {item.id for item in existing}
    new_items: list[FeedItem] = []

    for draft in incoming:
        item_id = make_id(draft.url)
        if item_id in existing_ids:
            continue
        new_items.append(FeedItem.from_draft(draft, item_id=item_id, collected_at=now))
        existing_ids.add(item_id)  # guards against duplicates within the same batch too

    return existing + new_items
