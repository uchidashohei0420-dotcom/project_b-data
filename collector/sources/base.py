"""Every concrete Source is independently fault-isolated: main.py catches and logs
whatever a collect() call raises, so one broken source (a changed selector, a network
timeout, an expired cookie) never prevents the others from collecting."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import FeedItemDraft


class SourceError(Exception):
    """Raised by a Source to signal a recoverable collection failure (auth expired,
    selector returned nothing, upstream 4xx/5xx). main.py logs it and records it in
    status.json rather than letting it crash the whole run."""


class SourceNotConfigured(SourceError):
    """Raised when a source's required config (API key, cookies) simply isn't set yet.
    This is expected/intentional, not a fault — main.py records it in status.json like any
    other SourceError but does NOT count it toward the "too many sources failed" abort
    threshold, so an optional source awaiting setup can't perpetually block every run from
    committing the sources that *are* configured."""


class Source(ABC):
    #: Key used in data/status.json and for the zero-count regression check in main.py.
    name: str

    @abstractmethod
    def collect(self) -> list[FeedItemDraft]:
        """Returns freshly-collected drafts. May raise SourceError (or let network/parse
        exceptions propagate — main.py treats any exception from collect() the same way)."""
        raise NotImplementedError
