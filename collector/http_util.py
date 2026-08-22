"""Shared HTTP helper: every outbound request goes through here so User-Agent and
timeout are never accidentally omitted (requests' default timeout is None/infinite)."""
from __future__ import annotations

import requests

from . import config


def get(
    url: str,
    *,
    params: dict | None = None,
    extra_headers: dict | None = None,
    timeout: int = config.REQUEST_TIMEOUT_SECONDS,
) -> requests.Response:
    headers = {"User-Agent": config.USER_AGENT}
    if extra_headers:
        headers.update(extra_headers)
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response
