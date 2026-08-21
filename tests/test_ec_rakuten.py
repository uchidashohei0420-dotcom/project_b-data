"""Offline test: stubs http_util.get so this never calls the real Rakuten API."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from collector.sources import ec_rakuten
from collector.sources.base import SourceError

FIXTURE = Path(__file__).parent / "fixtures" / "rakuten_sample.json"


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_parses_items_coerces_string_price_and_skips_urlless_item(monkeypatch):
    monkeypatch.setenv("RAKUTEN_APP_ID", "dummy-app-id")

    with patch.object(ec_rakuten.http_util, "get", return_value=_FakeResponse(_load_fixture())):
        items = ec_rakuten.ECRakutenSource().collect()

    # 3 raw items in the fixture, 1 has no itemUrl and must be skipped.
    assert len(items) == 2
    assert items[0].price_jpy == 2200
    assert items[0].image_url is not None
    assert items[1].price_jpy == 4400  # "4400" string coerced to int
    assert items[1].image_url is None
    assert all(item.type.value == "goods" for item in items)
    assert all(item.source_type.value == "ec" for item in items)


def test_missing_app_id_raises_source_error_without_calling_http(monkeypatch):
    monkeypatch.delenv("RAKUTEN_APP_ID", raising=False)

    with patch.object(ec_rakuten.http_util, "get") as mock_get:
        with pytest.raises(SourceError):
            ec_rakuten.ECRakutenSource().collect()
        mock_get.assert_not_called()


def test_api_error_response_raises_source_error(monkeypatch):
    monkeypatch.setenv("RAKUTEN_APP_ID", "dummy-app-id")
    error_payload = {"error": "wrong_parameter", "error_description": "applicationId is invalid"}

    with patch.object(ec_rakuten.http_util, "get", return_value=_FakeResponse(error_payload)):
        with pytest.raises(SourceError):
            ec_rakuten.ECRakutenSource().collect()
