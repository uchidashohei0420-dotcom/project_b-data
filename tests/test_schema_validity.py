import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent


def test_committed_feed_json_is_schema_valid():
    schema = json.loads((ROOT / "data" / "schema" / "feed.schema.json").read_text(encoding="utf-8"))
    feed = json.loads((ROOT / "data" / "feed.json").read_text(encoding="utf-8"))
    jsonschema.validate(instance=feed, schema=schema)


def test_schema_rejects_unknown_type_value():
    schema = json.loads((ROOT / "data" / "schema" / "feed.schema.json").read_text(encoding="utf-8"))
    bad_feed = {
        "generated_at": "2026-08-21T15:00:00+09:00",
        "schema_version": 1,
        "items": [
            {
                "id": "x", "type": "not-a-real-type", "source_type": "official",
                "source_name": "s", "title": "t", "url": "https://example.com",
                "collected_at": "2026-08-21T09:00:00+09:00",
            }
        ],
    }
    try:
        jsonschema.validate(instance=bad_feed, schema=schema)
    except jsonschema.ValidationError:
        return
    raise AssertionError("expected ValidationError for an invalid `type` enum value")
