from datetime import datetime, timezone

from collector.dedupe import make_id, merge
from collector.models import FeedItemDraft, ItemType, SourceType


def _draft(url: str, title: str = "テスト") -> FeedItemDraft:
    return FeedItemDraft(
        type=ItemType.NEWS,
        source_type=SourceType.OFFICIAL,
        source_name="テストソース",
        title=title,
        url=url,
    )


def test_merging_same_drafts_twice_yields_no_new_items_second_time():
    now = datetime.now(timezone.utc)
    drafts = [_draft("https://example.com/a"), _draft("https://example.com/b")]

    first_pass = merge([], drafts, now=now)
    assert len(first_pass) == 2

    second_pass = merge(first_pass, drafts, now=now)
    assert len(second_pass) == 2  # no duplicates re-added


def test_duplicates_within_a_single_batch_are_also_collapsed():
    now = datetime.now(timezone.utc)
    drafts = [_draft("https://example.com/a"), _draft("https://example.com/a")]

    merged = merge([], drafts, now=now)
    assert len(merged) == 1


def test_amazon_id_survives_query_string_variants():
    id_a = make_id("https://www.amazon.co.jp/dp/B0ABCDEFGH?ref=sr_1_1")
    id_b = make_id("https://www.amazon.co.jp/gp/product/B0ABCDEFGH?th=1&psc=1")
    assert id_a == id_b == "amazon:B0ABCDEFGH"


def test_generic_url_normalization_ignores_trailing_slash_and_unknown_params():
    id_a = make_id("https://keraeiko.com/news/sample-1")
    id_b = make_id("https://keraeiko.com/news/sample-1/?utm_source=twitter")
    assert id_a == id_b
