"""On-disk cache for /api/prediction_series.

A day's prediction is a pure function of (date, anchor, school) *for a given
engine*. Each row records the engine version that produced it
(sbc.engine_version: a hash of the code behind build_response and the
payload builder), and only rows from the current version are served, so a
change to the prediction engine invalidates the cache by itself.

The in-process dict in chart_bp stays as the L1 cache; this SQLite file is
L2, shared by every worker process and surviving restarts. Without it the
chart's first paint waited ~100 s after every boot, once per gunicorn worker.
"""

import json
import os
import sqlite3
import threading
from pathlib import Path

DB_PATH = Path(
    os.environ.get("SBC_SERIES_CACHE_DB")
    or Path(__file__).resolve().parent.parent / "data" / "series_cache.db"
)
_lock = threading.Lock()
_ready = False


def _current_engine():
    from sbc.engine_version import engine_version
    return engine_version()


def _conn():
    global _ready
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    if not _ready:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS series ("
            " date TEXT NOT NULL, anchor TEXT NOT NULL, school TEXT NOT NULL,"
            " payload TEXT NOT NULL, engine TEXT,"
            " PRIMARY KEY (date, anchor, school))"
        )
        cols = {row[1] for row in conn.execute("PRAGMA table_info(series)")}
        if "engine" not in cols:
            # Databases from before engine versioning: rows keep engine NULL,
            # so they count as stale and are rebuilt on the next request.
            conn.execute("ALTER TABLE series ADD COLUMN engine TEXT")
        conn.commit()
        _ready = True
    return conn


def get_many(dates, anchor, school, engine=None):
    """Return {date: payload} for every date cached by the current engine."""
    if not dates:
        return {}
    engine = engine or _current_engine()
    placeholders = ",".join("?" * len(dates))
    with _lock, _conn() as conn:
        rows = conn.execute(
            "SELECT date, payload FROM series"
            " WHERE anchor=? AND school=? AND engine=? AND date IN (" + placeholders + ")",
            [anchor, school, engine, *dates],
        ).fetchall()
    return {d: json.loads(p) for d, p in rows}


def put_many(items, anchor, school, engine=None):
    """Persist {date: payload} under the current engine. Entries carrying an
    'error' key are skipped."""
    engine = engine or _current_engine()
    rows = [
        (d, anchor, school, json.dumps(p, separators=(",", ":")), engine)
        for d, p in items.items()
        if isinstance(p, dict) and "error" not in p
    ]
    if not rows:
        return 0
    with _lock, _conn() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO series (date, anchor, school, payload, engine)"
            " VALUES (?,?,?,?,?)",
            rows,
        )
        conn.commit()
    return len(rows)


def purge_stale(engine=None):
    """Delete rows written by any other engine version. Returns rows removed."""
    engine = engine or _current_engine()
    with _lock, _conn() as conn:
        n = conn.execute(
            "DELETE FROM series WHERE engine IS NULL OR engine != ?", (engine,)
        ).rowcount
        conn.commit()
    return n


def clear():
    """Drop every cached row."""
    with _lock, _conn() as conn:
        conn.execute("DELETE FROM series")
        conn.commit()
