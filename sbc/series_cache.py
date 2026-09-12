"""On-disk cache for /api/prediction_series.

A day's prediction is a pure function of (date, anchor, school), so it is
safe to keep forever. The in-process dict in app.py stays as the L1 cache;
this SQLite file is L2, shared by every worker process and surviving
restarts. Without it the chart's first paint waited ~100 s after every boot,
once per gunicorn worker.
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


def _conn():
    global _ready
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    if not _ready:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS series ("
            " date TEXT NOT NULL, anchor TEXT NOT NULL, school TEXT NOT NULL,"
            " payload TEXT NOT NULL,"
            " PRIMARY KEY (date, anchor, school))"
        )
        conn.commit()
        _ready = True
    return conn


def get_many(dates, anchor, school):
    """Return {date: payload} for every cached date in *dates*."""
    if not dates:
        return {}
    placeholders = ",".join("?" * len(dates))
    with _lock, _conn() as conn:
        rows = conn.execute(
            "SELECT date, payload FROM series"
            " WHERE anchor=? AND school=? AND date IN (" + placeholders + ")",
            [anchor, school, *dates],
        ).fetchall()
    return {d: json.loads(p) for d, p in rows}


def put_many(items, anchor, school):
    """Persist {date: payload}. Entries carrying an 'error' key are skipped."""
    rows = [
        (d, anchor, school, json.dumps(p, separators=(",", ":")))
        for d, p in items.items()
        if isinstance(p, dict) and "error" not in p
    ]
    if not rows:
        return 0
    with _lock, _conn() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO series (date, anchor, school, payload)"
            " VALUES (?,?,?,?)",
            rows,
        )
        conn.commit()
    return len(rows)


def clear():
    """Drop every cached row (use after changing the prediction engine)."""
    with _lock, _conn() as conn:
        conn.execute("DELETE FROM series")
        conn.commit()
