"""Daily forecast ledger: freeze sbc.forecast before the open, score it when the outcome is in.

Like the intraday ledger (sbc.forecast_ledger), rows are kept by kind:

  live      frozen before 09:15 IST on the session: the honest forward record
  late      frozen on the session after the open
  backfill  generated for past sessions on request; never mixed into live figures

Scoring (once the h-session outcome is in data/market.db):
  brier        (probability_up - up)^2, against the base rate's Brier score
  components   for every component that leaned, whether the market went its way
So each component, validated or not, builds a live record, and a pre-registered
idea ("contrarian Bradley" is just bradley_sign read backwards) can be judged
on sessions it has never seen.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
import threading
from collections.abc import Callable
from pathlib import Path

from sbc import market_store
from sbc.market_holidays import is_trading_day

IST = market_store.IST
HORIZONS = (1, 5, 20)
DB_PATH = Path(
    os.environ.get("SBC_DAILY_LEDGER_DB")
    or Path(__file__).resolve().parent.parent / "data" / "daily_ledger.db"
)
_lock = threading.Lock()


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS forecasts (
            date TEXT NOT NULL, horizon INTEGER NOT NULL, model_version TEXT NOT NULL,
            frozen_at TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
            PRIMARY KEY (date, horizon));
        CREATE TABLE IF NOT EXISTS scores (
            date TEXT NOT NULL, horizon INTEGER NOT NULL, scored_at TEXT NOT NULL,
            actual REAL NOT NULL, metrics TEXT NOT NULL,
            PRIMARY KEY (date, horizon));
    """)
    return conn


def _now(now: dt.datetime | None = None) -> dt.datetime:
    return (now or dt.datetime.now(IST)).astimezone(IST)


def _kind(day: dt.date, now: dt.datetime, backfill: bool) -> str:
    if backfill:
        return "backfill"
    return "live" if now < dt.datetime.combine(day, dt.time(9, 15), IST) else "late"


def freeze(day: dt.date, now: dt.datetime | None = None, backfill: bool = False,
           horizons: tuple[int, ...] = HORIZONS,
           make: Callable[[str, int], dict] | None = None) -> list[int]:
    """Store today's forecast for each horizon not already frozen; returns the horizons stored."""
    from sbc import forecast as fc

    make = make or fc.forecast
    now = _now(now)
    if not is_trading_day(day):
        return []
    kind = _kind(day, now, backfill)
    stored = []
    with _conn() as conn:
        have = {h for (h,) in conn.execute("SELECT horizon FROM forecasts WHERE date = ?", (day.isoformat(),))}
    for h in horizons:
        if h in have:
            continue
        payload = make(day.isoformat(), h)
        with _lock, _conn() as conn:
            conn.execute("INSERT OR IGNORE INTO forecasts VALUES (?,?,?,?,?,?)",
                         (day.isoformat(), h, payload["model_version"], now.isoformat(timespec="seconds"),
                          kind, json.dumps(payload, separators=(",", ":"))))
        stored.append(h)
    return stored


def _outcome(day: str, horizon: int, bars: list[dict]) -> float | None:
    """close[t+h-1] / close[t-1] - 1 if every bar is in; None otherwise."""
    dates = [b["date"] for b in bars]
    if day not in dates:
        return None
    t = dates.index(day)
    if t == 0 or t + horizon - 1 >= len(bars):
        return None
    return float(bars[t + horizon - 1]["close"] / bars[t - 1]["close"] - 1.0)


def score_pending(now: dt.datetime | None = None) -> list[tuple[str, int]]:
    """Score every frozen forecast whose outcome is complete; returns (date, horizon) scored."""
    now = _now(now)
    with _conn() as conn:
        pending = conn.execute(
            "SELECT f.date, f.horizon, f.payload FROM forecasts f LEFT JOIN scores s "
            "ON f.date = s.date AND f.horizon = s.horizon WHERE s.date IS NULL").fetchall()
    if not pending:
        return []
    first = min(d for d, _, _ in pending)
    start = (dt.date.fromisoformat(first) - dt.timedelta(days=10)).isoformat()
    bars = market_store.get_daily("NIFTY", start=start)
    done = []
    for day, horizon, raw in pending:
        actual = _outcome(day, horizon, bars)
        if actual is None:
            continue
        payload = json.loads(raw)
        up = 1.0 if actual > 0 else 0.0
        components = {}
        for c in payload["components"]:
            lean = c.get("lean")
            if lean:
                components[c["name"]] = {"lean": lean, "hit": (actual > 0) == (lean > 0)}
        metrics = {
            "up": up,
            "brier": (payload["probability_up"] - up) ** 2,
            "base_brier": (payload["base"]["up_share"] - up) ** 2,
            "components": components,
        }
        with _lock, _conn() as conn:
            conn.execute("INSERT OR REPLACE INTO scores VALUES (?,?,?,?,?)",
                         (day, horizon, now.isoformat(timespec="seconds"), actual, json.dumps(metrics)))
        done.append((day, horizon))
    return done


def summary(horizon: int, kind: str = "live") -> dict:
    """Live (by default) record for one horizon: Brier vs base rate and each component's hit rate."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT s.metrics FROM scores s JOIN forecasts f ON f.date = s.date AND f.horizon = s.horizon "
            "WHERE f.horizon = ? AND f.kind = ?", (horizon, kind)).fetchall()
        frozen = conn.execute("SELECT COUNT(*) FROM forecasts WHERE horizon = ? AND kind = ?",
                              (horizon, kind)).fetchone()[0]
    metrics = [json.loads(r[0]) for r in rows]
    out: dict = {"kind": kind, "horizon": horizon, "frozen": frozen, "scored": len(metrics)}
    if not metrics:
        return out
    out["brier"] = sum(m["brier"] for m in metrics) / len(metrics)
    out["base_brier"] = sum(m["base_brier"] for m in metrics) / len(metrics)
    out["up_share"] = sum(m["up"] for m in metrics) / len(metrics)
    comps: dict[str, list[bool]] = {}
    for m in metrics:
        for name, c in m["components"].items():
            comps.setdefault(name, []).append(c["hit"])
    out["components"] = {name: {"n": len(h), "hit_rate": sum(h) / len(h)} for name, h in sorted(comps.items())}
    return out


def get(day: str, horizon: int) -> dict | None:
    """The frozen forecast for (day, horizon) with its kind and freeze time, or None."""
    with _conn() as conn:
        row = conn.execute("SELECT kind, frozen_at, payload FROM forecasts WHERE date = ? AND horizon = ?",
                           (day, horizon)).fetchone()
    if not row:
        return None
    return {**json.loads(row[2]), "ledger": {"kind": row[0], "frozen_at": row[1]}}


def recent(horizon: int, limit: int = 30) -> list[dict]:
    """Latest frozen forecasts for a horizon with their scores (if any)."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT f.date, f.kind, f.frozen_at, f.payload, s.actual, s.metrics FROM forecasts f "
            "LEFT JOIN scores s ON f.date = s.date AND f.horizon = s.horizon "
            "WHERE f.horizon = ? ORDER BY f.date DESC LIMIT ?", (horizon, limit)).fetchall()
    out = []
    for day, kind, frozen_at, payload, actual, metrics in rows:
        p = json.loads(payload)
        out.append({"date": day, "kind": kind, "frozen_at": frozen_at,
                    "probability_up": p["probability_up"], "validated": p["validated"],
                    "actual": actual, "brier": json.loads(metrics)["brier"] if metrics else None})
    return out
