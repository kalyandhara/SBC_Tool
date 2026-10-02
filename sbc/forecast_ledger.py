"""Forecast ledger: freeze each day's intraday forecast before the open, score it after.

The forecast is deterministic, so a forecast drawn after the fact equals one
drawn before, as long as the model has not changed. The ledger stores the
model_version with every row and separates three kinds of record:

  live        frozen before 09:15 IST on the day: the honest forward record
  late        frozen during/after the session (still same model, but not
              something you could have acted on at the open)
  backfill    explicitly generated for past days: a back-test, never mixed
              into the live figures

Scoring uses NIFTY 5-minute bars (yfinance ^NSEI, which serves ~60 days).
Per bucket: direction hit = sign(score) == sign(close - open of that bar).
The baseline is the majority-class rate over the same bars (the best
constant guess in hindsight), so a hit rate must beat it to mean anything.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import sqlite3
import threading
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
DB_PATH = Path(
    os.environ.get("SBC_FORECAST_DB")
    or Path(__file__).resolve().parent.parent / "data" / "forecast_ledger.db"
)
YF_INTRADAY_DAYS = 59
_lock = threading.Lock()


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS forecasts (
            date TEXT PRIMARY KEY, model_version TEXT NOT NULL,
            frozen_at TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS actuals (
            date TEXT PRIMARY KEY, fetched_at TEXT NOT NULL, bars TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS scores (
            date TEXT PRIMARY KEY, model_version TEXT NOT NULL,
            scored_at TEXT NOT NULL, metrics TEXT NOT NULL);
    """)
    return conn


def _now_ist(now=None):
    return (now or dt.datetime.now(IST)).astimezone(IST)


def _kind_for(day: dt.date, now: dt.datetime) -> str:
    open_dt = dt.datetime.combine(day, dt.time(9, 15), IST)
    return "live" if now < open_dt else "late"


# --------------------------------------------------------------------------
# freeze / read
# --------------------------------------------------------------------------

def freeze(day: dt.date, now: dt.datetime | None = None, backfill: bool = False,
           force: bool = False) -> dict:
    """Store the day's forecast once. Returns the stored row (existing wins)."""
    from sbc.intraday_forecast import build_forecast
    now = _now_ist(now)
    existing = get_frozen(day)
    if existing and not force:
        return existing
    payload = build_forecast(day)
    kind = "backfill" if backfill else _kind_for(day, now)
    with _lock, _conn() as c:
        c.execute("INSERT OR REPLACE INTO forecasts VALUES (?,?,?,?,?)",
                  (day.isoformat(), payload["model_version"],
                   now.isoformat(timespec="seconds"), kind, json.dumps(payload)))
        c.execute("DELETE FROM scores WHERE date=?", (day.isoformat(),))
    return get_frozen(day)


def get_frozen(day: dt.date) -> dict | None:
    with _lock, _conn() as c:
        row = c.execute("SELECT model_version, frozen_at, kind, payload FROM forecasts WHERE date=?",
                        (day.isoformat(),)).fetchone()
    if not row:
        return None
    return {"date": day.isoformat(), "model_version": row[0], "frozen_at": row[1],
            "kind": row[2], "forecast": json.loads(row[3])}


# --------------------------------------------------------------------------
# actual 5-minute bars
# --------------------------------------------------------------------------

def _download_5m(day: dt.date) -> list[dict]:
    import pandas as pd
    import yfinance as yf
    df = yf.download("^NSEI", start=day.isoformat(),
                     end=(day + dt.timedelta(days=1)).isoformat(),
                     interval="5m", progress=False, auto_adjust=False)
    if df is None or df.empty:
        return []
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    idx = df.index
    idx = idx.tz_localize("UTC") if idx.tz is None else idx
    df.index = idx.tz_convert(IST)
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    out = []
    for ts, r in df.iterrows():
        if ts.date() != day or not (dt.time(9, 15) <= ts.time() < dt.time(15, 30)):
            continue
        out.append({"time": ts.strftime("%H:%M"), "open": round(float(r["Open"]), 2),
                    "high": round(float(r["High"]), 2), "low": round(float(r["Low"]), 2),
                    "close": round(float(r["Close"]), 2)})
    return out


def actual_bars(day: dt.date, now: dt.datetime | None = None) -> dict:
    """5-minute NIFTY bars for a day. Settled days are cached; today is live."""
    from sbc.market_data import _settled_date
    now = _now_ist(now)
    with _lock, _conn() as c:
        row = c.execute("SELECT bars FROM actuals WHERE date=?", (day.isoformat(),)).fetchone()
    if row:
        return {"date": day.isoformat(), "bars": json.loads(row[0]), "settled": True, "source": "cache"}
    if day > now.date():
        return {"date": day.isoformat(), "bars": [], "settled": False, "source": "future"}
    if (now.date() - day).days > YF_INTRADAY_DAYS:
        return {"date": day.isoformat(), "bars": [], "settled": True,
                "source": "unavailable (yfinance keeps ~60 days of 5m bars)"}
    try:
        bars = _download_5m(day)
    except Exception as exc:  # network, rate limit
        return {"date": day.isoformat(), "bars": [], "settled": False, "source": f"error: {exc}"}
    settled = day <= _settled_date(now)
    if settled and bars:
        with _lock, _conn() as c:
            c.execute("INSERT OR REPLACE INTO actuals VALUES (?,?,?)",
                      (day.isoformat(), now.isoformat(timespec="seconds"), json.dumps(bars)))
    return {"date": day.isoformat(), "bars": bars, "settled": settled, "source": "yfinance"}


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------

def _sign(x):
    return 1 if x > 0 else -1 if x < 0 else 0


def _corr(a, b):
    if len(a) < 3:
        return None
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va == 0 or vb == 0:
        return None
    return round(sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb), 4)


def score_forecast(forecast: dict, bars: list[dict]) -> dict:
    """Pure scoring of one day's forecast against its 5-minute bars."""
    by_time = {b["time"]: b for b in bars}
    step = forecast.get("step_minutes", 5)
    scores, rets, cums, moves = [], [], [], []
    hits = n = up = down = 0
    day_open = bars[0]["open"] if bars else None
    for bk in forecast["buckets"]:
        t0 = dt.datetime.strptime(bk["time"], "%H:%M")
        window = [by_time[(t0 + dt.timedelta(minutes=k)).strftime("%H:%M")]
                  for k in range(0, step, 5)
                  if (t0 + dt.timedelta(minutes=k)).strftime("%H:%M") in by_time]
        if not window:
            continue
        ret = window[-1]["close"] - window[0]["open"]
        scores.append(bk["score"])
        rets.append(ret)
        cums.append(bk["cumulative"])
        moves.append(window[-1]["close"] - day_open)
        if bk["score"] != 0 and ret != 0:
            n += 1
            hits += _sign(bk["score"]) == _sign(ret)
            up += ret > 0
            down += ret < 0
    day_ret = (bars[-1]["close"] - day_open) if bars else None
    final = forecast["buckets"][-1]["cumulative"] if forecast["buckets"] else 0
    return {
        "buckets_scored": n, "hits": hits,
        "hit_rate": round(hits / n, 4) if n else None,
        "baseline": round(max(up, down) / n, 4) if n else None,
        "corr_score_return": _corr(scores, rets),
        "corr_path_price": _corr(cums, moves),
        "day_return": round(day_ret, 2) if day_ret is not None else None,
        "final_cumulative": final,
        "day_direction_hit": (_sign(final) == _sign(day_ret))
        if day_ret not in (None, 0) and final != 0 else None,
        "bars": len(bars),
    }


def score_day(day: dt.date, now: dt.datetime | None = None) -> dict | None:
    from sbc.market_data import _settled_date
    now = _now_ist(now)
    frozen = get_frozen(day)
    if not frozen or day > _settled_date(now):
        return None
    act = actual_bars(day, now)
    if not act["bars"]:
        return None
    metrics = score_forecast(frozen["forecast"], act["bars"])
    with _lock, _conn() as c:
        c.execute("INSERT OR REPLACE INTO scores VALUES (?,?,?,?)",
                  (day.isoformat(), frozen["model_version"],
                   now.isoformat(timespec="seconds"), json.dumps(metrics)))
    return metrics


def score_pending(now: dt.datetime | None = None, limit: int = 30) -> list[str]:
    """Score frozen, settled, unscored days (newest first). Returns dates scored."""
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT f.date FROM forecasts f LEFT JOIN scores s ON s.date=f.date "
            "WHERE s.date IS NULL ORDER BY f.date DESC LIMIT ?", (limit,)).fetchall()
    done = []
    for (d,) in rows:
        if score_day(dt.date.fromisoformat(d), now):
            done.append(d)
    return done


def summary(days: int = 60, now: dt.datetime | None = None) -> dict:
    """Rolling record, live/late separated from backfill."""
    now = _now_ist(now)
    since = (now.date() - dt.timedelta(days=days)).isoformat()
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT f.date, f.kind, f.model_version, s.metrics FROM forecasts f "
            "JOIN scores s ON s.date=f.date WHERE f.date>=? ORDER BY f.date", (since,)).fetchall()
    groups = {}
    per_day = []
    for d, kind, mv, m in rows:
        m = json.loads(m)
        per_day.append({"date": d, "kind": kind, "model_version": mv, **m})
        g = groups.setdefault("backfill" if kind == "backfill" else "forward", {
            "days": 0, "hits": 0, "buckets": 0, "baseline_hits": 0.0,
            "day_hits": 0, "day_called": 0, "corrs": []})
        g["days"] += 1
        g["hits"] += m["hits"]
        g["buckets"] += m["buckets_scored"]
        g["baseline_hits"] += (m["baseline"] or 0) * m["buckets_scored"]
        if m["day_direction_hit"] is not None:
            g["day_called"] += 1
            g["day_hits"] += bool(m["day_direction_hit"])
        if m["corr_score_return"] is not None:
            g["corrs"].append(m["corr_score_return"])
    out = {}
    for k, g in groups.items():
        out[k] = {
            "days": g["days"], "buckets": g["buckets"],
            "hit_rate": round(g["hits"] / g["buckets"], 4) if g["buckets"] else None,
            "baseline": round(g["baseline_hits"] / g["buckets"], 4) if g["buckets"] else None,
            "day_direction": f"{g['day_hits']}/{g['day_called']}",
            "mean_corr": round(sum(g["corrs"]) / len(g["corrs"]), 4) if g["corrs"] else None,
        }
    return {"window_days": days, "groups": out, "per_day": per_day}
