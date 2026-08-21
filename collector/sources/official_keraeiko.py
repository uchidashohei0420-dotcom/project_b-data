"""Scrapes けらえいこ公式サイト (keraeiko.com) news/events listing.

TODO before first real run: open https://keraeiko.com/ (news/works listing page) in a
browser, inspect the actual markup, and replace the selector constants below — they are
placeholders based on common WordPress/news-listing conventions, not verified against the
live site. Everything else (control flow, per-field extraction, graceful degradation on a
missing field) should not need to change when the selectors are corrected.
"""
from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .. import http_util
from ..models import FeedItemDraft, ItemType, SourceType
from .base import Source, SourceError

BASE_URL = "https://keraeiko.com/"
NEWS_URL = "https://keraeiko.com/news/"

# Selector constants — edit these first if the site's markup changes.
LISTING_ITEM_SELECTOR = "article.news-item, li.news-list__item"
TITLE_SELECTOR = ".news-item__title, h2, h3"
DATE_SELECTOR = "time, .news-item__date"
LINK_SELECTOR = "a"
IMAGE_SELECTOR = "img"


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


class OfficialKeraeikoSource(Source):
    name = "official_keraeiko"

    def collect(self) -> list[FeedItemDraft]:
        try:
            response = http_util.get(NEWS_URL)
        except Exception as exc:  # noqa: BLE001 - deliberately broad, isolated per-source
            raise SourceError(f"failed to fetch {NEWS_URL}: {exc}") from exc

        soup = BeautifulSoup(response.text, "lxml")
        items: list[FeedItemDraft] = []

        for node in soup.select(LISTING_ITEM_SELECTOR):
            title = _text(node, TITLE_SELECTOR)
            url = _href(node, LINK_SELECTOR)
            if not title or not url:
                continue  # a node we can't identify a title+link for isn't usable

            items.append(
                FeedItemDraft(
                    type=ItemType.NEWS,
                    source_type=SourceType.OFFICIAL,
                    source_name="けらえいこ公式サイト",
                    title=title,
                    url=url,
                    image_url=_image(node, IMAGE_SELECTOR),
                    description=_text(node, DATE_SELECTOR),
                )
            )

        return items
