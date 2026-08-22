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
# twitter-cli (the backend agent-reach installs) authenticates via these two cookie
# values, not a single token — see https://github.com/public-clis/twitter-cli.
TWITTER_AUTH_TOKEN_ENV = "TWITTER_AUTH_TOKEN"
TWITTER_CT0_ENV = "TWITTER_CT0"


def twitter_credentials() -> tuple[str, str] | None:
    """Returns (auth_token, ct0) if both are set, else None. Both-or-nothing: a partial
    credential pair would fail auth anyway and is easier to diagnose as "not configured"."""
    auth_token = os.environ.get(TWITTER_AUTH_TOKEN_ENV)
    ct0 = os.environ.get(TWITTER_CT0_ENV)
    if auth_token and ct0:
        return auth_token, ct0
    return None


# Rakuten Web Service credentials (free, self-service at https://webservice.rakuten.co.jp/).
# Not high-sensitivity secrets, but rate-limited per key, so kept out of the repo anyway.
# As of the 2026-08-22 API generation, both are required together — applicationId alone
# (the old, pre-2026 behavior) now fails with "wrong_parameter" / "specify valid
# applicationId", confirmed via the live API test form on webservice.rakuten.co.jp.
RAKUTEN_APP_ID_ENV = "RAKUTEN_APP_ID"
RAKUTEN_ACCESS_KEY_ENV = "RAKUTEN_ACCESS_KEY"


def rakuten_credentials() -> tuple[str, str] | None:
    """Returns (application_id, access_key) if both are set, else None. Both-or-nothing,
    same reasoning as twitter_credentials(): a partial pair fails auth anyway."""
    app_id = os.environ.get(RAKUTEN_APP_ID_ENV)
    access_key = os.environ.get(RAKUTEN_ACCESS_KEY_ENV)
    if app_id and access_key:
        return app_id, access_key
    return None
