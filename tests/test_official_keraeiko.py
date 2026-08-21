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

    # Two valid cards; the third (no title link) must be skipped, not crash.
    assert len(items) == 2
    assert items[0].title == "『あたしンちSUPER』④巻、発売！"
    assert items[0].url == "https://keraeiko.com/1688.html"
    assert items[0].image_url is not None
    assert items[0].description == "2026-03-16T00:03:07+09:00"
    assert items[1].image_url is None
