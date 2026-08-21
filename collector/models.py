"""Dataclasses mirroring data/schema/feed.schema.json. Keep the two in lockstep."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum


class ItemType(str, Enum):
    EVENT = "event"
    GOODS = "goods"
    NEWS = "news"


class SourceType(str, Enum):
    OFFICIAL = "official"
    EC = "ec"
    SNS = "sns"


@dataclass
class FeedItemDraft:
    """What a Source.collect() returns: everything except `id` and `collected_at`, which
    are stamped centrally (in dedupe.py) so collection time is uniform and ID derivation
    logic lives in exactly one place."""

    type: ItemType
    source_type: SourceType
    source_name: str
    title: str
    url: str
    description: str | None = None
    image_url: str | None = None
    event_datetime: str | None = None
    location: str | None = None
    price_jpy: int | None = None
    release_date: str | None = None
    purchase_url: str | None = None
    raw_snippet: str | None = None


@dataclass
class FeedItem:
    """A finalized, schema-conformant item ready to be written to feed.json/history."""

    id: str
    type: ItemType
    source_type: SourceType
    source_name: str
    title: str
    url: str
    collected_at: str
    description: str | None = None
    image_url: str | None = None
    event_datetime: str | None = None
    location: str | None = None
    price_jpy: int | None = None
    release_date: str | None = None
    purchase_url: str | None = None
    raw_snippet: str | None = None

    @classmethod
    def from_draft(cls, draft: FeedItemDraft, *, item_id: str, collected_at: datetime) -> "FeedItem":
        data = asdict(draft)
        return cls(id=item_id, collected_at=collected_at.isoformat(), **data)

    def to_json_dict(self) -> dict:
        data = asdict(self)
        data["type"] = self.type.value if isinstance(self.type, ItemType) else self.type
        data["source_type"] = (
            self.source_type.value if isinstance(self.source_type, SourceType) else self.source_type
        )
        return data
