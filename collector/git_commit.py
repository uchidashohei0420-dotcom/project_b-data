"""Commits and pushes data/ changes. Relies on `git` being configured with push
credentials already (GitHub Actions' actions/checkout persists GITHUB_TOKEN
credentials by default — no PAT needed here)."""
from __future__ import annotations

import subprocess

from . import config


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=config.REPO_ROOT, capture_output=True, text=True, check=True
    )


def _configure_bot_identity() -> None:
    _run("config", "user.name", "atashinchi-watch-bot")
    _run("config", "user.email", "atashinchi-watch-bot@users.noreply.github.com")


def _current_branch() -> str:
    # `git pull origin HEAD` is not valid — HEAD isn't a resolvable remote ref name.
    # Resolve the actual local branch name and pull/push that explicitly instead.
    result = _run("rev-parse", "--abbrev-ref", "HEAD")
    return result.stdout.strip()


def has_changes() -> bool:
    result = subprocess.run(
        ["git", "diff", "--quiet", "--", "data/"], cwd=config.REPO_ROOT
    )
    return result.returncode != 0


def commit_and_push(message: str) -> bool:
    """Returns True if a commit was made and pushed, False if there was nothing to commit
    (an empty-diff run is a no-op, not an error — avoids spamming empty commits)."""
    if not has_changes():
        return False

    _configure_bot_identity()
    _run("add", "data/")
    _run("commit", "-m", message)

    branch = _current_branch()

    # Guard against a push race if two runs somehow overlap: rebase onto the remote once
    # before pushing, retry once on failure.
    try:
        _run("pull", "--rebase", "--autostash", "origin", branch)
        _run("push", "origin", branch)
    except subprocess.CalledProcessError:
        _run("pull", "--rebase", "--autostash", "origin", branch)
        _run("push", "origin", branch)

    return True
