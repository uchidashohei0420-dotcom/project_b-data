"""Offline test: stubs subprocess.run so this never invokes the real twitter-cli or
touches real X credentials."""
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from collector.sources import sns_x
from collector.sources.base import SourceError

FIXTURE = Path(__file__).parent / "fixtures" / "agent_reach_sample_output.json"


def _fake_completed_process(stdout: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


def _set_credentials(monkeypatch):
    monkeypatch.setenv("TWITTER_AUTH_TOKEN", "dummy-token")
    monkeypatch.setenv("TWITTER_CT0", "dummy-ct0")


def test_classifies_event_goods_and_news_correctly(monkeypatch):
    _set_credentials(monkeypatch)
    fixture_json = FIXTURE.read_text(encoding="utf-8")

    with patch.object(sns_x.subprocess, "run", return_value=_fake_completed_process(fixture_json)):
        items = sns_x.SnsXSource().collect()

    # timeline + search both hit the same fixture in this test, so 3 posts x 2 calls = 6.
    assert len(items) == 6
    assert any(item.type.value == "event" for item in items)  # "トークイベント" -> event
    assert any(item.type.value == "goods" for item in items)  # "グッズ" + "発売" -> goods
    assert any(item.type.value == "news" for item in items)  # ambiguous weather post -> news
    assert all(item.source_type.value == "sns" for item in items)
    assert all(item.raw_snippet for item in items)


def test_missing_credentials_raises_source_error_without_calling_subprocess(monkeypatch):
    monkeypatch.delenv("TWITTER_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_CT0", raising=False)

    with patch.object(sns_x.subprocess, "run") as mock_run:
        with pytest.raises(SourceError):
            sns_x.SnsXSource().collect()
        mock_run.assert_not_called()


def test_partial_credentials_is_treated_as_not_configured(monkeypatch):
    monkeypatch.setenv("TWITTER_AUTH_TOKEN", "dummy-token")
    monkeypatch.delenv("TWITTER_CT0", raising=False)

    with patch.object(sns_x.subprocess, "run") as mock_run:
        with pytest.raises(SourceError):
            sns_x.SnsXSource().collect()
        mock_run.assert_not_called()


def test_cli_not_found_raises_source_error(monkeypatch):
    _set_credentials(monkeypatch)

    with patch.object(sns_x.subprocess, "run", side_effect=FileNotFoundError()):
        with pytest.raises(SourceError):
            sns_x.SnsXSource().collect()


def test_retweet_credits_original_author_not_official_handle(monkeypatch):
    """Regression test for a real bug found by the user: every timeline post used to get a
    hardcoded source_name of "@atashinchi_new", even for retweets of other accounts — so the
    footer misleadingly implied the official account wrote everything."""
    _set_credentials(monkeypatch)
    timeline_payload = json.dumps(
        {
            "ok": True,
            "schema_version": "1",
            "data": [
                {
                    "id": "9000000000000000001",
                    "text": "ファンの方の投稿です、ありがとうございます!",
                    "author": {"screenName": "a_fan_account", "name": "A Fan"},
                    "isRetweet": True,
                    "retweetedBy": sns_x.OFFICIAL_HANDLE,
                }
            ],
        }
    )
    empty_search_payload = json.dumps({"ok": False, "error": {"code": "not_found"}})

    with patch.object(
        sns_x.subprocess,
        "run",
        side_effect=[
            _fake_completed_process(timeline_payload),
            _fake_completed_process(empty_search_payload),
        ],
    ):
        items = sns_x.SnsXSource().collect()

    assert len(items) == 1
    assert items[0].source_name == f"@a_fan_account(@{sns_x.OFFICIAL_HANDLE}がRT)"
    assert items[0].url == "https://x.com/a_fan_account/status/9000000000000000001"
