#!/usr/bin/env python3
"""Standalone: `python scripts/validate_feed.py` validates data/feed.json against
data/schema/feed.schema.json and exits non-zero on failure. main.py also calls this
logic inline as a commit gate; this script is for ad-hoc/manual checks."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    schema = json.loads((ROOT / "data" / "schema" / "feed.schema.json").read_text(encoding="utf-8"))
    feed = json.loads((ROOT / "data" / "feed.json").read_text(encoding="utf-8"))
    try:
        jsonschema.validate(instance=feed, schema=schema)
    except jsonschema.ValidationError as exc:
        print(f"INVALID: {exc.message} (path: {list(exc.absolute_path)})", file=sys.stderr)
        return 1
    print(f"OK: {len(feed['items'])} items valid against schema")
    return 0


if __name__ == "__main__":
    sys.exit(main())
