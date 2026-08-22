"""Queries Rakuten Ichiba's Item Search API for "あたしンち" goods.

Public JSON API (https://webservice.rakuten.co.jp/), endpoint:
https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701

Chosen to replace ec_amazon/ec_loft/ec_animate: no HTML scraping, no CSS selectors to
maintain, and no bot-detection surface — the API is meant to be called programmatically.
Requires a free application ID + access key (self-service signup at the URL above),
supplied via the RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY environment variables / GitHub
Actions secrets.

Verified against a live call via Rakuten's own "APIテストフォーム" test tool on
webservice.rakuten.co.jp (2026-08-22), after the endpoint originally used here
(https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601, applicationId only)
returned {"error": "wrong_parameter", "error_description": "specify valid applicationId"}
for a freshly-issued applicationId. The domain, path, API version, and required params
all changed:
- domain: openapi.rakuten.co.jp (not app.rakuten.co.jp)
- path/version: /ichibams/api/IchibaItem/Search/20260701 (not /services/api/.../20220601)
- both applicationId (UUID-shaped now, not the old numeric form) AND accessKey are
  required together — applicationId alone is rejected
- format=json (not formatVersion=2); the response nests each item under "Item", the
  same shape formatVersion=1 used to produce, which _draft_from_item already unwraps
"""
from __future__ import annotations

from .. import config, http_util
from ..models import FeedItemDraft, ItemType, SourceType
from .base import Source, SourceError, SourceNotConfigured

SEARCH_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
KEYWORD = "あたしンち"
HITS = 30


def _extract_image_url(item: dict) -> str | None:
    image_urls = item.get("mediumImageUrls") or []
    if not image_urls:
        return None
    first = image_urls[0]
    return first.get("imageUrl") if isinstance(first, dict) else first


def _draft_from_item(raw: dict) -> FeedItemDraft | None:
    # The live API nests each item under "Item" (confirmed 2026-08-22); handle a flat
    # dict too in case a future formatVersion=2-style response is ever returned instead.
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
        credentials = config.rakuten_credentials()
        if not credentials:
            # Not configured yet, not broken — doesn't count toward the run failure
            # threshold (see SourceNotConfigured).
            raise SourceNotConfigured(
                f"{config.RAKUTEN_APP_ID_ENV}/{config.RAKUTEN_ACCESS_KEY_ENV} not set; skipping Rakuten collection"
            )
        app_id, access_key = credentials

        params = {
            "format": "json",
            "applicationId": app_id,
            "accessKey": access_key,
            "keyword": KEYWORD,
            "genreId": 0,
            "hits": HITS,
        }
        try:
            # The app is registered on webservice.rakuten.co.jp with "github.com" as its
            # allowed website (アプリケーションタイプ: Webアプリケーション). A
            # server-to-server call sends neither Origin nor Referer by default, which
            # the live API rejected with 403 {"errorMessage":
            # "REQUEST_CONTEXT_BODY_HTTP_REFERRER_MISSING"} — and, confirmed via a real
            # diagnostic run (2026-08-22), adding a Referer header did NOT satisfy this
            # check, but an Origin header matching the registered domain did (200, real
            # data). Despite the error message saying "REFERRER", Origin is what's
            # actually checked.
            response = http_util.get(
                SEARCH_URL, params=params, extra_headers={"Origin": "https://github.com"}
            )
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
