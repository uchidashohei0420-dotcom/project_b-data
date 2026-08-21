"""Scrapes あたしンち30周年特設サイト (atashinchi30th-anime.shin-ei-animation.jp) news/events.

**DISABLED — not wired into main.ALL_SOURCES.** Verified against the live site
(2026-08-21, via GitHub Actions): the root page is a near-static single-page landing
site (~20KB, one `div.particles-js` background effect, no `<nav>`, essentially no
internal links beyond one external link to publications.asahi.com). There is no
discoverable news/events listing on this domain to scrape — `/news/` 404s, and the
homepage itself has no repeating "article" structure. Re-enable only if the site adds a
real news section, or replace this source with something else entirely (e.g. the site's
own social links, if any are added later).
"""
from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .. import http_util
from ..models import FeedItemDraft, ItemType, SourceType
from .base import Source, SourceError

BASE_URL = "https://atashinchi30th-anime.shin-ei-animation.jp/"
NEWS_URL = "https://atashinchi30th-anime.shin-ei-animation.jp/news/"

LISTING_ITEM_SELECTOR = ".news-list li, article.news"
TITLE_SELECTOR = ".news-list__title, h2, h3"
LINK_SELECTOR = "a"
IMAGE_SELECTOR = "img"
DATE_SELECTOR = "time, .news-list__date"


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


class Official30thSource(Source):
    name = "official_30th"

    def collect(self) -> list[FeedItemDraft]:
        try:
            response = http_util.get(NEWS_URL)
        except Exception as exc:  # noqa: BLE001
            raise SourceError(f"failed to fetch {NEWS_URL}: {exc}") from exc

        soup = BeautifulSoup(response.text, "lxml")
        items: list[FeedItemDraft] = []

        for node in soup.select(LISTING_ITEM_SELECTOR):
            title = _text(node, TITLE_SELECTOR)
            url = _href(node, LINK_SELECTOR)
            if not title or not url:
                continue

            items.append(
                FeedItemDraft(
                    type=ItemType.NEWS,
                    source_type=SourceType.OFFICIAL,
                    source_name="あたしンち30周年特設サイト",
                    title=title,
                    url=url,
                    image_url=_image(node, IMAGE_SELECTOR),
                    description=_text(node, DATE_SELECTOR),
                )
            )

        return items
