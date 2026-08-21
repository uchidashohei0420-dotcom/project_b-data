"""Shared HTTP helper: every outbound request goes through here so User-Agent and
timeout are never accidentally omitted (requests' default timeout is None/infinite)."""
from __future__ import annotations

import requests

from . import config


def get(url: str, *, timeout: int = config.REQUEST_TIMEOUT_SECONDS) -> requests.Response:
    response = requests.get(
        url,
        headers={"User-Agent": config.USER_AGENT},
        timeout=timeout,
    )
    response.raise_for_status()
    return response
