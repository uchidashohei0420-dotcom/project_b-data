"""Constants and environment-variable references. No secret VALUES live here — only
the names of the environment variables the collector reads at runtime."""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
FEED_PATH = DATA_DIR / "feed.json"
STATUS_PATH = DATA_DIR / "status.json"
SCHEMA_PATH = DATA_DIR / "schema" / "feed.schema.json"
HISTORY_DIR = DATA_DIR / "history"

FEED_ITEM_LIMIT = 200
REQUEST_TIMEOUT_SECONDS = 15
USER_AGENT = "AtashinchiWatchCollector/1.0 (+personal hobby project; contact via GitHub issues)"

# Fraction of previously-successful sources allowed to fail before the whole run is
# treated as failed (see main.py's zero-count regression check).
SOURCE_FAILURE_THRESHOLD = 0.5

# --- secrets: names only, values come from the environment at runtime ---
AGENT_REACH_X_COOKIE_ENV = "AGENT_REACH_X_COOKIE"


def agent_reach_cookie() -> str | None:
    return os.environ.get(AGENT_REACH_X_COOKIE_ENV) or None
