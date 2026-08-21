"""Small text-parsing helpers shared by EC scrapers."""
from __future__ import annotations

import re

_PRICE_DIGITS_RE = re.compile(r"[\d,]+")


def parse_jpy_price(text: str | None) -> int | None:
    """"税込3,300円" / "¥3,300" -> 3300. Returns None if no digits are found."""
    if not text:
        return None
    match = _PRICE_DIGITS_RE.search(text)
    if not match:
        return None
    digits = match.group(0).replace(",", "")
    return int(digits) if digits else None
