"""Integration-style test for collector.main.run()'s failure-threshold logic.

Regression test for a real bug found in production (2026-08-21): sources raising
SourceNotConfigured (missing API key/cookies — expected, not broken) were counted the
same as genuine failures, so with only 3 total sources, 2 unconfigured-but-optional
sources tripped the 50% failure threshold and blocked every run from committing, even
though the one configured source succeeded.
"""
from __future__ import annotations

from unittest.mock import patch

from collector import config, main
from collector.models import FeedItemDraft, ItemType, SourceType
from collector.sources.base import Source, SourceError, SourceNotConfigured


class _WorkingSource(Source):
    name = "working"

    def collect(self) -> list[FeedItemDraft]:
        return [
            FeedItemDraft(
                type=ItemType.NEWS,
                source_type=SourceType.OFFICIAL,
                source_name="test",
                title="test item",
                url="https://example.com/a",
            )
        ]


class _NotConfiguredSource(Source):
    name = "not_configured"

    def collect(self) -> list[FeedItemDraft]:
        raise SourceNotConfigured("API key not set")


class _BrokenSource(Source):
    name = "broken"

    def collect(self) -> list[FeedItemDraft]:
        raise SourceError("selector broke")


def _isolate_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    monkeypatch.setattr(config, "FEED_PATH", data_dir / "feed.json")
    monkeypatch.setattr(config, "STATUS_PATH", data_dir / "status.json")
    monkeypatch.setattr(config, "HISTORY_DIR", data_dir / "history")
    # Schema doesn't change between test runs — point at the real committed one.
    monkeypatch.setattr(config, "SCHEMA_PATH", config.REPO_ROOT / "data" / "schema" / "feed.schema.json")


def test_run_succeeds_when_only_unconfigured_sources_are_missing(tmp_path, monkeypatch):
    """2 of 3 sources being SourceNotConfigured must NOT abort the run — this is the
    exact scenario that broke in production."""
    _isolate_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "ALL_SOURCES", [_WorkingSource, _NotConfiguredSource, _NotConfiguredSource])

    with patch("collector.git_commit.commit_and_push", return_value=True) as mock_commit:
        exit_code = main.run()

    assert exit_code == 0
    mock_commit.assert_called_once()


def test_run_aborts_when_a_real_source_actually_breaks(tmp_path, monkeypatch):
    """A genuine SourceError (not SourceNotConfigured) still counts toward the
    threshold — this must keep failing loudly, or a real regression would go unnoticed."""
    _isolate_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "ALL_SOURCES", [_BrokenSource, _BrokenSource, _WorkingSource])

    with patch("collector.git_commit.commit_and_push") as mock_commit:
        exit_code = main.run()

    assert exit_code == 1
    mock_commit.assert_not_called()
