"""Queries Rakuten Ichiba's Item Search API for "あたしンチ" goods.

Public JSON API (https://webservice.rakuten.co.jp/), endpoint:
https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601

Chosen to replace ec_amazon/ec_loft/ec_animate: no HTML scraping, no CSS selectors to
maintain, and no bot-detection surface — the API is meant to be called programmatically.
Requires a free application ID (self-service signup at the URL above), supplied via the
RAKUTEN_APP_ID environment variable / GitHub Actions secret.

TODO before first real run: this dev sandbox has no general internet egress
(webservice.rakuten.co.jp is not reachable from here — same constraint documented in
official_keraeiko.py etc.), so the request/response shape below is written from
documented API behavior (formatVersion=2 response shape), not verified against a live
call. Verify via a throwaway GitHub Actions run once RAKUTEN_APP_ID is available, and
adjust field names here if the real response differs.
"""
from __future__ import annotations

from .. import config, http_util
from ..models import FeedItemDraft, ItemType, SourceType
from .base import Source, SourceError

SEARCH_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"
KEYWORD = "あたしンチ"
HITS = 30


def _extract_image_url(item: dict) -> str | None:
    image_urls = item.get("mediumImageUrls") or []
    if not image_urls:
        return None
    first = image_urls[0]
    return first.get("imageUrl") if isinstance(first, dict) else first


def _draft_from_item(raw: dict) -> FeedItemDraft | None:
    # formatVersion=2 gives flat item dicts; formatVersion=1 wraps each under "Item".
    item = raw.get("Item", raw) if "Item" in raw else raw
    title = item.get("itemName")
    url = item.get("itemUrl")
    if not title or not url:
        return None

    price = item.get("itemPrice")
    try:
        price_jpy = int(price) if price is not None else None
    except (TypeError, ValueError):
        price_jpy = None

    return FeedItemDraft(
        type=ItemType.GOODS,
        source_type=SourceType.EC,
        source_name=item.get("shopName") or "楽天市場",
        title=title,
        url=url,
        purchase_url=url,
        image_url=_extract_image_url(item),
        price_jpy=price_jpy,
    )


class ECRakutenSource(Source):
    name = "ec_rakuten"

    def collect(self) -> list[FeedItemDraft]:
        app_id = config.rakuten_app_id()
        if not app_id:
            # Not a hard failure: like the other optional sources, an unconfigured key
            # shouldn't fail the whole run.
            raise SourceError(f"{config.RAKUTEN_APP_ID_ENV} is not set; skipping Rakuten collection")

        params = {
            "applicationId": app_id,
            "keyword": KEYWORD,
            "hits": HITS,
            "formatVersion": 2,
        }
        try:
            response = http_util.get(SEARCH_URL, params=params)
        except Exception as exc:  # noqa: BLE001 - deliberately broad, isolated per-source
            raise SourceError(f"failed to fetch Rakuten search: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise SourceError(f"Rakuten API returned non-JSON response: {exc}") from exc

        if isinstance(payload, dict) and "error" in payload:
            raise SourceError(f"Rakuten API error: {payload.get('error_description', payload['error'])}")

        raw_items = payload.get("Items", []) if isinstance(payload, dict) else []
        items: list[FeedItemDraft] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            draft = _draft_from_item(raw)
            if draft:
                items.append(draft)

        return items
