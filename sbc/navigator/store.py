"""The only Navigator module that touches Postgres."""
from __future__ import annotations

import os
from pathlib import Path

import psycopg

MIGRATIONS = Path(__file__).parent / "migrations"


class StoreUnavailable(RuntimeError):
    """Postgres is not configured or not reachable."""


def connect() -> psycopg.Connection:
    url = os.environ.get("NAV_DATABASE_URL", "").strip()
    if not url:
        raise StoreUnavailable("NAV_DATABASE_URL is not set")
    try:
        return psycopg.connect(url, connect_timeout=3)
    except psycopg.ProgrammingError:
        message = "NAV_DATABASE_URL is invalid"
    except psycopg.Error:
        message = "Postgres is unreachable"
    # Raise outside the except block. The psycopg error can echo the URL and
    # password, and `from None` would still keep it on __context__.
    raise StoreUnavailable(message)


def migrate() -> None:
    with connect() as conn:
        for path in sorted(MIGRATIONS.glob("*.sql")):
            conn.execute(path.read_text(encoding="utf8"))
