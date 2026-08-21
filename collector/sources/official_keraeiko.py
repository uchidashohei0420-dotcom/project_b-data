"""Scrapes けらえいこ公式サイト (keraeiko.com) news listing at /category/topics.

Verified against the live site (2026-08-21, via a throwaway GitHub Actions run — this
dev sandbox has no general internet egress, so real-site verification has to happen
inside Actions). Confirmed real structure (WordPress + UIkit theme):

    <div class="uk-card uk-grid-collapse" id="post-1688">
      <div class="uk-card-body uk-padding-remove">
        <div class="uk-card-media-top ..."><a href="..."><img class="wp-post-image" src="..."></a></div>
      </div>
      <div class="uk-card-body hentry ...">
        <div class="uk-card-text ... hentry">
          <a class="koz-medium uk-text-small" href="https://keraeiko.com/1688.html">『あたしンちSUPER』④巻、発売！</a>
          <div class="uk-card-text ...">
            <span class="entry-meta"><span class="meta-date">
              <time class="entry-date published updated" datetime="2026-03-16T00:03:07+09:00">2026.03.16</time>
            </span></span>
          </div>
        </div>
      </div>
    </div>

Note: the original guess (`/news/`) 404'd — the real listing lives at `/category/topics`.
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from .. import http_util
from ..models import FeedItemDraft, ItemType, SourceType
from .base import Source, SourceError

NEWS_URL = "https://keraeiko.com/category/topics"

LISTING_ITEM_SELECTOR = "div.uk-card.uk-grid-collapse"
TITLE_LINK_SELECTOR = "a.koz-medium"
DATE_SELECTOR = "time.entry-date"
IMAGE_SELECTOR = "img.wp-post-image"


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
            title_link = node.select_one(TITLE_LINK_SELECTOR)
            if not title_link:
                continue  # a card we can't identify a title+link for isn't usable
            title = title_link.get_text(strip=True)
            url = title_link.get("href")
            if not title or not url:
                continue

            image_el = node.select_one(IMAGE_SELECTOR)
            image_url = image_el.get("src") if image_el else None

            date_el = node.select_one(DATE_SELECTOR)
            posted_date = date_el.get("datetime") if date_el else None

            items.append(
                FeedItemDraft(
                    type=ItemType.NEWS,
                    source_type=SourceType.OFFICIAL,
                    source_name="けらえいこ公式サイト",
                    title=title,
                    url=url,
                    image_url=image_url,
                    description=posted_date,
                )
            )

        return items
