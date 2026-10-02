"""Database bootstrap — ensures schema exists on first use."""

import os
import sqlite3
from pathlib import Path

_SCHEMA_PATH = Path(__file__).parent.parent / "data" / "schema.sql"
# SBC_PROFILES_DB overrides the location (tests point it at a temp file so
# they never write into the real profiles).
_DB_PATH = Path(
    os.environ.get("SBC_PROFILES_DB")
    or Path(__file__).parent.parent / "data" / "profiles.db"
)
_BOOTSTRAPPED = False


def _bootstrap():
    """Apply schema.sql if tables don't exist. Idempotent and thread-safe-ish."""
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    try:
        cur = conn.cursor()
        # Check if core tables exist
        cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='profiles'"
        )
        if cur.fetchone() is None:
            # Schema missing — apply it
            with open(_SCHEMA_PATH, encoding="utf-8") as f:
                conn.executescript(f.read())
            conn.commit()
    finally:
        conn.close()
    _BOOTSTRAPPED = True


def get_db():
    """Return a sqlite3 connection with row_factory, bootstrapping if needed."""
    _bootstrap()
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def connect():
    """Plain sqlite3 connection (tuple rows) to the profiles DB."""
    _bootstrap()
    return sqlite3.connect(str(_DB_PATH))


# For backwards compatibility with inline-connect code in app.py
PROFILES_DB_PATH = _DB_PATH
