"""Offline parser test: reads a saved HTML fixture, never hits the live network."""
from pathlib import Path
from unittest.mock import patch

from collector.sources import official_keraeiko

FIXTURE = Path(__file__).parent / "fixtures" / "keraeiko_sample.html"


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


def test_parses_items_and_skips_linkless_card():
    fixture_html = FIXTURE.read_text(encoding="utf-8")

    with patch.object(official_keraeiko.http_util, "get", return_value=_FakeResponse(fixture_html)):
        items = official_keraeiko.OfficialKeraeikoSource().collect()

    # Three valid cards; the malformed one (no title link) must be skipped, not crash.
    assert len(items) == 3
    assert items[0].title == "『あたしンちSUPER』④巻、発売！"
    assert items[0].url == "https://keraeiko.com/1688.html"
    assert items[0].image_url is not None
    assert items[0].description == "2026-03-16T00:03:07+09:00"
    assert items[0].type.value == "goods"  # "発売" -> goods
    assert items[1].image_url is None
    assert items[1].type.value == "news"  # no event/goods keyword


def test_event_item_gets_datetime_and_location_extracted():
    fixture_html = FIXTURE.read_text(encoding="utf-8")

    with patch.object(official_keraeiko.http_util, "get", return_value=_FakeResponse(fixture_html)):
        items = official_keraeiko.OfficialKeraeikoSource().collect()

    event_item = next(item for item in items if item.url == "https://keraeiko.com/1702.html")
    assert event_item.type.value == "event"
    # reference year is taken from the card's own posted date (2026-08-20).
    assert event_item.event_datetime == "2026-09-15T18:30:00+09:00"
    assert event_item.location == "渋谷ロフト9"


def test_non_event_item_leaves_datetime_and_location_unset():
    fixture_html = FIXTURE.read_text(encoding="utf-8")

    with patch.object(official_keraeiko.http_util, "get", return_value=_FakeResponse(fixture_html)):
        items = official_keraeiko.OfficialKeraeikoSource().collect()

    goods_item = next(item for item in items if item.url == "https://keraeiko.com/1688.html")
    assert goods_item.event_datetime is None
    assert goods_item.location is None
