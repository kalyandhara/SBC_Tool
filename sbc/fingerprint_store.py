"""Precomputed astro fingerprints (sbc.fingerprint) for every calendar day.

data/fingerprints.db (or SBC_FINGERPRINT_DB) holds one row per date with the
fingerprint JSON and the version of the code that produced it
(engine_version.module_version("sbc.fingerprint"): the module plus every
first-party module it imports). Rows from another version are treated as
missing, so editing the astro code invalidates the store by itself.

Every calendar day is stored, not just trading days: holidays and weekends
are cheap (~1 ms each), and the analog search decides which dates count.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
import threading
from functools import lru_cache
from pathlib import Path

from sbc import fingerprint as fpmod

DB_PATH = Path(
    os.environ.get("SBC_FINGERPRINT_DB")
    or Path(__file__).resolve().parent.parent / "data" / "fingerprints.db"
)
DEFAULT_RANGE = ("1990-01-01", "2035-12-31")
_lock = threading.Lock()


@lru_cache(maxsize=1)
def current_version() -> str:
    from sbc.engine_version import module_version
    return module_version("sbc.fingerprint")


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS fingerprints ("
        " date TEXT PRIMARY KEY, version TEXT NOT NULL, payload TEXT NOT NULL)")
    return conn


def _dates(start: str, end: str) -> list[str]:
    d0, d1 = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    if d1 < d0:
        raise ValueError("end before start")
    return [(d0 + dt.timedelta(days=i)).isoformat() for i in range((d1 - d0).days + 1)]


def missing(start: str, end: str, version: str | None = None) -> list[str]:
    """Dates in [start, end] with no row from the current version."""
    version = version or current_version()
    with _conn() as conn:
        have = {r[0] for r in conn.execute(
            "SELECT date FROM fingerprints WHERE version = ? AND date BETWEEN ? AND ?",
            (version, start, end))}
    return [d for d in _dates(start, end) if d not in have]


def build(start: str = DEFAULT_RANGE[0], end: str = DEFAULT_RANGE[1],
          batch: int = 500, progress=None) -> dict:
    """Compute and store every missing or stale date in [start, end]."""
    version = current_version()
    todo = missing(start, end, version)
    done = 0
    for i in range(0, len(todo), batch):
        rows = [(d, version, json.dumps(fpmod.fingerprint(d), separators=(",", ":")))
                for d in todo[i:i + batch]]
        with _lock, _conn() as conn:
            conn.executemany("INSERT OR REPLACE INTO fingerprints VALUES (?,?,?)", rows)
        done += len(rows)
        if progress:
            progress(done, len(todo))
    return {"version": version, "computed": done, "range": [start, end]}


def get(day: str) -> dict:
    """Fingerprint for one date: from the store when current, else computed and stored."""
    version = current_version()
    with _conn() as conn:
        row = conn.execute("SELECT payload FROM fingerprints WHERE date = ? AND version = ?",
                           (day, version)).fetchone()
    if row:
        return json.loads(row[0])
    fp = fpmod.fingerprint(day)
    with _lock, _conn() as conn:
        conn.execute("INSERT OR REPLACE INTO fingerprints VALUES (?,?,?)",
                     (fp["date"], version, json.dumps(fp, separators=(",", ":"))))
    return fp


def get_range(start: str, end: str) -> list[dict]:
    """Current-version fingerprints in [start, end], oldest first (missing dates skipped)."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT payload FROM fingerprints WHERE version = ? AND date BETWEEN ? AND ? ORDER BY date",
            (current_version(), start, end)).fetchall()
    return [json.loads(r[0]) for r in rows]


def purge_stale() -> int:
    """Delete rows written by another version; returns how many."""
    with _lock, _conn() as conn:
        return conn.execute("DELETE FROM fingerprints WHERE version != ?",
                            (current_version(),)).rowcount


def status() -> dict:
    version = current_version()
    with _conn() as conn:
        first, last, count = conn.execute(
            "SELECT MIN(date), MAX(date), COUNT(*) FROM fingerprints WHERE version = ?",
            (version,)).fetchone()
        stale = conn.execute("SELECT COUNT(*) FROM fingerprints WHERE version != ?",
                             (version,)).fetchone()[0]
    return {"version": version, "first": first, "last": last, "rows": count, "stale_rows": stale}
