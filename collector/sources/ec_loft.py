"""Scrapes ロフトネットストア search results for "あたしンチ".

TODO before first real run: verify selectors against the live search results page.
"""
from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .. import http_util
from ..models import FeedItemDraft, ItemType, SourceType
from ..text_util import parse_jpy_price
from .base import Source, SourceError

BASE_URL = "https://www.loft.co.jp/"
SEARCH_URL = "https://www.loft.co.jp/products/search?q=%E3%81%82%E3%81%9F%E3%81%97%E3%83%B3%E3%83%81"

ITEM_SELECTOR = ".item-list__item, li.product"
TITLE_SELECTOR = ".item-name, .product-name"
PRICE_SELECTOR = ".item-price, .price"
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


class ECLoftSource(Source):
    name = "ec_loft"

    def collect(self) -> list[FeedItemDraft]:
        try:
            response = http_util.get(SEARCH_URL)
        except Exception as exc:  # noqa: BLE001
            raise SourceError(f"failed to fetch {SEARCH_URL}: {exc}") from exc

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
                    source_name="ロフトネットストア",
                    title=title,
                    url=url,
                    purchase_url=url,
                    image_url=_image(node, IMAGE_SELECTOR),
                    price_jpy=parse_jpy_price(_text(node, PRICE_SELECTOR)),
                )
            )

        return items
