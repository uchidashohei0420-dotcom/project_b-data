from pathlib import Path
from unittest.mock import patch

from collector.sources import ec_loft

FIXTURE = Path(__file__).parent / "fixtures" / "loft_sample.html"


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


def test_parses_price_and_handles_missing_price():
    fixture_html = FIXTURE.read_text(encoding="utf-8")

    with patch.object(ec_loft.http_util, "get", return_value=_FakeResponse(fixture_html)):
        items = ec_loft.ECLoftSource().collect()

    assert len(items) == 2
    assert items[0].price_jpy == 2200
    assert items[0].purchase_url == items[0].url
    assert items[1].price_jpy is None  # missing price text must not crash the parser
