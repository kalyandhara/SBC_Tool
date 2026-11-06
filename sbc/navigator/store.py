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
    except psycopg.OperationalError as exc:
        # Do not chain the original message into the text: it can echo the URL.
        raise StoreUnavailable("Postgres is unreachable") from exc


def migrate() -> None:
    with connect() as conn:
        for path in sorted(MIGRATIONS.glob("*.sql")):
            conn.execute(path.read_text(encoding="utf8"))
