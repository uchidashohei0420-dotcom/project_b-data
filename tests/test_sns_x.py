"""Offline test: stubs subprocess.run so this never invokes the real agent-reach CLI or
touches a real X cookie."""
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


def test_classifies_event_goods_and_news_correctly(monkeypatch):
    monkeypatch.setenv("AGENT_REACH_X_COOKIE", "dummy-cookie")
    fixture_json = FIXTURE.read_text(encoding="utf-8")

    with patch.object(sns_x.subprocess, "run", return_value=_fake_completed_process(fixture_json)):
        items = sns_x.SnsXSource().collect()

    # timeline + search both hit the same fixture in this test, so 3 posts x 2 calls = 6.
    assert len(items) == 6
    types = {item.title[:6]: item.type for item in items}
    assert any(item.type.value == "event" for item in items)  # "トークイベント" -> event
    assert any(item.type.value == "goods" for item in items)  # "グッズ" + "発売" -> goods
    assert any(item.type.value == "news" for item in items)  # ambiguous weather post -> news
    assert all(item.source_type.value == "sns" for item in items)
    assert all(item.raw_snippet for item in items)


def test_missing_cookie_raises_source_error_without_calling_subprocess(monkeypatch):
    monkeypatch.delenv("AGENT_REACH_X_COOKIE", raising=False)

    with patch.object(sns_x.subprocess, "run") as mock_run:
        with pytest.raises(SourceError):
            sns_x.SnsXSource().collect()
        mock_run.assert_not_called()


def test_cli_not_found_raises_source_error(monkeypatch):
    monkeypatch.setenv("AGENT_REACH_X_COOKIE", "dummy-cookie")

    with patch.object(sns_x.subprocess, "run", side_effect=FileNotFoundError()):
        with pytest.raises(SourceError):
            sns_x.SnsXSource().collect()
