"""Conservative date/time/location extraction, shared by official_keraeiko.py and sns_x.py
for items already classified as `event`.

Deliberately narrow: a wrong date/location is worse than a missing one — FeedRowView already
falls back to "日時未定" / omits the location line when these are None — so every extraction
here only fires on unambiguous patterns and leaves everything else as None rather than
guessing. See docs/PLAN.md §16 Phase 6.
"""
from __future__ import annotations

import re
from datetime import datetime

_DATE_RE = re.compile(r"(\d{1,2})月(\d{1,2})日")
_TIME_RE = re.compile(r"(\d{1,2})[:時](\d{2})分?")

# Explicit labels only — no free-form place-name recognition (far too easy to produce a
# false positive for little value in a personal feed app). Deliberately excludes bare "@"
# as a location marker despite it reading like an event-flyer convention: on X, "@" almost
# always introduces an account mention instead, which would make this extract nonsense
# handles as locations.
_LOCATION_LABEL_RE = re.compile(r"会場[:：]\s*([^\s、。\n]+)")
_LOCATION_SUFFIX_RE = re.compile(r"([^\s、。\n]+?)にて開催")

_JST_SUFFIX = "+09:00"


def extract_event_datetime(text: str, *, reference_year: int) -> str | None:
    """Returns an ISO8601 JST timestamp, or None unless *both* an unambiguous date and time
    are found — a date with no time is deliberately left unset rather than defaulted to
    00:00, since that would silently invent information the source never stated.

    Doesn't reason about a date implying a different year than `reference_year` (e.g. a
    "1月" post found in December, referring to next year) — a known, accepted limitation
    rather than a guess.
    """
    date_match = _DATE_RE.search(text)
    time_match = _TIME_RE.search(text)
    if not date_match or not time_match:
        return None

    month, day = int(date_match.group(1)), int(date_match.group(2))
    hour, minute = int(time_match.group(1)), int(time_match.group(2))
    try:
        dt = datetime(reference_year, month, day, hour, minute)
    except ValueError:
        return None  # e.g. "13月45日" or "25時" garbage — not a real date, don't guess
    return dt.strftime("%Y-%m-%dT%H:%M:00") + _JST_SUFFIX


def extract_location(text: str) -> str | None:
    if match := _LOCATION_LABEL_RE.search(text):
        return match.group(1)
    if match := _LOCATION_SUFFIX_RE.search(text):
        return match.group(1)
    return None
