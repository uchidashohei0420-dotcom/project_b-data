"""Scrapes Amazon.co.jp search results for "あたしンチ".

**DISABLED — not wired into main.ALL_SOURCES.** This was the highest-risk source (bot
detection / CAPTCHA, ToS considerations — see docs/PLAN.md Context section) and, in a
real GitHub Actions run (2026-08-21), returned 0 items without erroring — likely a
selector mismatch against Amazon's real search-result markup, though it's also
consistent with a soft bot-detection response that doesn't trip the explicit CAPTCHA
check below. Rather than keep chasing Amazon's markup/anti-bot changes, goods collection
was moved to `ec_rakuten.py` (a legitimate free JSON API, no scraping). Left in place in
case Amazon coverage is wanted later, but re-enabling needs the selectors below verified
against a live page first.
"""
from __future__ import annotations

import random
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .. import http_util
from ..models import FeedItemDraft, ItemType, SourceType
from ..text_util import parse_jpy_price
from .base import Source, SourceError

BASE_URL = "https://www.amazon.co.jp/"
SEARCH_URL = "https://www.amazon.co.jp/s?k=%E3%81%82%E3%81%9F%E3%81%97%E3%83%B3%E3%83%81"

ITEM_SELECTOR = "div[data-component-type='s-search-result']"
TITLE_SELECTOR = "h2 span"
PRICE_SELECTOR = ".a-price .a-offscreen"
LINK_SELECTOR = "h2 a"
IMAGE_SELECTOR = "img.s-image"

_CAPTCHA_MARKERS = ("automated access", "captcha", "robot check")


def _text(node, selector: str) -> str | None:
    found = node.select_one(selector)
    return found.get_text(strip=True) if found else None


def _href(node, selector: str) -> str | None:
    found = node.select_one(selector)
    href = found.get("href") if found else None
    return urljoin(BASE_URL, href) if href else None


def _image(node, selector: str) -> str | None:
    found = node.select_one(selector)
    src = found.get("src") if found else None
    return urljoin(BASE_URL, src) if src else None


class ECAmazonSource(Source):
    name = "ec_amazon"

    def collect(self) -> list[FeedItemDraft]:
        time.sleep(random.uniform(1.0, 3.0))  # small randomized delay, not a guarantee

        try:
            response = http_util.get(SEARCH_URL)
        except Exception as exc:  # noqa: BLE001
            raise SourceError(f"failed to fetch {SEARCH_URL}: {exc}") from exc

        lowered = response.text.lower()
        if any(marker in lowered for marker in _CAPTCHA_MARKERS):
            raise SourceError("Amazon returned a bot-detection/CAPTCHA page")

        soup = BeautifulSoup(response.text, "lxml")
        items: list[FeedItemDraft] = []

        for node in soup.select(ITEM_SELECTOR):
            title = _text(node, TITLE_SELECTOR)
            url = _href(node, LINK_SELECTOR)
            if not title or not url:
                continue

            items.append(
                FeedItemDraft(
                    type=ItemType.GOODS,
                    source_type=SourceType.EC,
                    source_name="Amazon",
                    title=title,
                    url=url,
                    purchase_url=url,
                    image_url=_image(node, IMAGE_SELECTOR),
                    price_jpy=parse_jpy_price(_text(node, PRICE_SELECTOR)),
                )
            )

        return items
