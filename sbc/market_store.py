"""Market database for the prediction engine: daily bars and institutional flows.

One SQLite file (data/market.db, or SBC_MARKET_DB) holds:

  daily   symbol, date, open, high, low, close, volume, source
          NIFTY (^NSEI, 2007+), SENSEX (^BSESN, 1997+), INDIAVIX (^INDIAVIX, 2008+)
  flows   date, category (FII / DII), buy, sell, net  (INR crore)

Price history comes from yfinance and is backfilled in full. NSE publishes
FII/DII cash flows for the latest session only, so that history accumulates
one day at a time from the first refresh onwards.

The legacy per-asset CSV caches in sbc.market_data still serve the chart and
the older studies; this store is what the analog and statistics layers read.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import sqlite3
import threading
from collections.abc import Callable
from pathlib import Path
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")
DB_PATH = Path(
    os.environ.get("SBC_MARKET_DB")
    or Path(__file__).resolve().parent.parent / "data" / "market.db"
)

# symbol -> (yfinance ticker, earliest date worth asking for)
SYMBOLS = {
    "NIFTY": ("^NSEI", "1995-01-01"),
    "SENSEX": ("^BSESN", "1995-01-01"),
    "INDIAVIX": ("^INDIAVIX", "2008-01-01"),
    "BTC-USD": ("BTC-USD", "2010-07-17"),  # Bitcoin price data
    "^GSPC": ("^GSPC", "1950-01-03"),     # S&P 500 (NYSE proxy)
    "^DJI": ("^DJI", "1928-10-01"),       # Dow Jones Industrial Average
}

# Series for the sector-rule test (sbc.sector_validation): the instruments the
# sector scenarios in sbc.sector_signals were fitted on. Fetched on demand by
# scripts/refresh_market_data.py --research, not in the nightly refresh.
RESEARCH_SYMBOLS = {
    "HG": ("HG=F", "2000-01-01"), "KC": ("KC=F", "2000-01-01"), "FCX": ("FCX", "1995-01-01"),
    "HINDCOPPER": ("HINDCOPPER.NS", "2000-01-01"),
    "CHAMBLFERT": ("CHAMBLFERT.NS", "2000-01-01"), "COROMANDEL": ("COROMANDEL.NS", "2000-01-01"),
    "GNFC": ("GNFC.NS", "2000-01-01"), "RCF": ("RCF.NS", "2000-01-01"), "NFL": ("NFL.NS", "2000-01-01"),
    "DEEPAKFERT": ("DEEPAKFERT.NS", "2000-01-01"),
    "SB": ("SB=F", "2000-01-01"), "ZW": ("ZW=F", "2000-01-01"), "ZC": ("ZC=F", "2000-01-01"),
    "ZR": ("ZR=F", "2000-01-01"),
    "HINDUNILVR": ("HINDUNILVR.NS", "2000-01-01"), "ITC": ("ITC.NS", "2000-01-01"),
    "NESTLEIND": ("NESTLEIND.NS", "2000-01-01"), "BRITANNIA": ("BRITANNIA.NS", "2000-01-01"),
    "UPL": ("UPL.NS", "2000-01-01"), "PIIND": ("PIIND.NS", "2000-01-01"),
    "RALLIS": ("RALLIS.NS", "2000-01-01"), "DHANUKA": ("DHANUKA.NS", "2000-01-01"),
    "MCLEODRUSS": ("MCLEODRUSS.NS", "2000-01-01"),
}

# NSE sector indices for the sector-rotation study (docs/research/sector_rotation_preregistration_2026-10-29.md).
# Keys are ours; values are yfinance tickers. Ticker check 2026-10-29 (row counts and dates only):
# The 12 available indices registered in Addendum 2 of
# docs/research/sector_rotation_preregistration_2026-10-29.md. MEDIA, HEALTHCARE and
# OIL & GAS returned no rows under any ticker tried and are excluded from this study.
SECTOR_SYMBOLS = {
    "CNXBANK": "^NSEBANK", "CNXFIN": "NIFTY_FIN_SERVICE.NS", "CNXIT": "^CNXIT", "CNXPHARMA": "^CNXPHARMA",
    "CNXAUTO": "^CNXAUTO", "CNXFMCG": "^CNXFMCG", "CNXMETAL": "^CNXMETAL",
    "CNXENERGY": "^CNXENERGY", "CNXREALTY": "^CNXREALTY",
    "CNXPSUBANK": "^CNXPSUBANK", "CNXINFRA": "^CNXINFRA", "CNXCONSUM": "^CNXCONSUM",
}
RESEARCH_SYMBOLS.update({k: (t, "2005-01-01") for k, t in SECTOR_SYMBOLS.items()})

NSE_FIIDII_URL = "https://www.nseindia.com/api/fiidiiTradeReact"
_NSE_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126 Safari/537.36"),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/reports/fii-dii",
}
_lock = threading.Lock()


class MarketDataMissing(RuntimeError):
    """market.db has no bars for a symbol the caller needs."""


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS daily (
            symbol TEXT NOT NULL, date TEXT NOT NULL,
            open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL, close REAL NOT NULL,
            volume INTEGER NOT NULL DEFAULT 0, source TEXT NOT NULL,
            PRIMARY KEY (symbol, date));
        CREATE TABLE IF NOT EXISTS flows (
            date TEXT NOT NULL, category TEXT NOT NULL,
            buy REAL, sell REAL, net REAL NOT NULL, fetched_at TEXT NOT NULL,
            PRIMARY KEY (date, category));
    """)
    return conn


def settled_date(now: dt.datetime | None = None) -> dt.date:
    """Latest date whose daily bar is final: today after 16:00 IST, else yesterday."""
    now = (now or dt.datetime.now(IST)).astimezone(IST)
    return now.date() if now.time() >= dt.time(16, 0) else now.date() - dt.timedelta(days=1)


# ── daily bars ─────────────────────────────────────────────────────────────

def upsert_daily(symbol: str, rows: list[dict], source: str) -> int:
    """Insert or replace bars: rows of {date, open, high, low, close, volume}."""
    clean = [
        (symbol, r["date"], float(r["open"]), float(r["high"]), float(r["low"]),
         float(r["close"]), int(r.get("volume") or 0), source)
        for r in rows
        if all(r.get(k) is not None and r[k] == r[k] for k in ("open", "high", "low", "close"))
    ]
    if not clean:
        return 0
    with _lock, _conn() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO daily VALUES (?,?,?,?,?,?,?,?)", clean)
    return len(clean)


def get_daily(symbol: str, start: str | None = None, end: str | None = None) -> list[dict]:
    """Bars for a symbol in [start, end], oldest first."""
    sql = "SELECT date, open, high, low, close, volume FROM daily WHERE symbol = ?"
    args: list = [symbol]
    if start:
        sql += " AND date >= ?"
        args.append(start)
    if end:
        sql += " AND date <= ?"
        args.append(end)
    with _conn() as conn:
        rows = conn.execute(sql + " ORDER BY date", args).fetchall()
    keys = ("date", "open", "high", "low", "close", "volume")
    return [dict(zip(keys, r)) for r in rows]


def _span(symbol: str) -> tuple[str | None, str | None, int]:
    with _conn() as conn:
        first, last, count = conn.execute(
            "SELECT MIN(date), MAX(date), COUNT(*) FROM daily WHERE symbol = ?", (symbol,)
        ).fetchone()
    return first, last, int(count)


def _yf_download(ticker: str, start: dt.date, end: dt.date) -> list[dict]:
    """Daily bars from yfinance for [start, end]."""
    import pandas as pd
    import yfinance as yf

    df = yf.download(ticker, start=start.isoformat(),
                     end=(end + dt.timedelta(days=1)).isoformat(),
                     progress=False, auto_adjust=False)
    if df is None or df.empty:
        return []
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.reset_index()
    out = []
    for _, r in df.iterrows():
        out.append({
            "date": pd.Timestamp(r["Date"]).date().isoformat(),
            "open": r["Open"], "high": r["High"], "low": r["Low"], "close": r["Close"],
            "volume": 0 if r["Volume"] != r["Volume"] else r["Volume"],
        })
    return out


def refresh_daily(symbol: str, full: bool = False, now: dt.datetime | None = None,
                  fetch: Callable[[str, dt.date, dt.date], list[dict]] | None = None) -> dict:
    """Fetch what is missing for one symbol and store it.

    full=True re-downloads the whole history (fills gaps and the head);
    otherwise only the tail after the last stored date, re-fetching the last
    5 days so a revised bar replaces the provisional one.
    """
    ticker, earliest = SYMBOLS.get(symbol) or RESEARCH_SYMBOLS[symbol]
    last_settled = settled_date(now)
    first, last, _ = _span(symbol)
    if full or last is None:
        start = dt.date.fromisoformat(earliest)
    else:
        start = dt.date.fromisoformat(last) - dt.timedelta(days=5)
    if start > last_settled:
        return {"symbol": symbol, "stored": 0}
    fetch = fetch or _yf_download
    rows = [r for r in fetch(ticker, start, last_settled) if r["date"] <= last_settled.isoformat()]
    stored = upsert_daily(symbol, rows, source=f"yfinance:{ticker}")
    return {"symbol": symbol, "stored": stored}


# ── FII / DII flows ────────────────────────────────────────────────────────

def _nse_fiidii() -> list[dict]:
    import requests

    session = requests.Session()
    resp = session.get(NSE_FIIDII_URL, headers=_NSE_HEADERS, timeout=20)
    resp.raise_for_status()
    data: list[dict] = resp.json()
    return data


def _num(value: object) -> float | None:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def refresh_flows(now: dt.datetime | None = None,
                  fetch: Callable[[], list[dict]] | None = None) -> dict:
    """Store NSE's latest FII/DII cash-market session (INR crore)."""
    fetched_at = (now or dt.datetime.now(IST)).astimezone(IST).isoformat(timespec="seconds")
    rows = []
    for item in (fetch or _nse_fiidii)():
        category = "FII" if str(item.get("category", "")).upper().startswith("FII") else "DII"
        net = _num(item.get("netValue"))
        try:
            day = dt.datetime.strptime(item["date"], "%d-%b-%Y").date().isoformat()
        except (KeyError, ValueError):
            continue
        if net is None:
            continue
        rows.append((day, category, _num(item.get("buyValue")), _num(item.get("sellValue")),
                     net, fetched_at))
    if rows:
        with _lock, _conn() as conn:
            conn.executemany("INSERT OR REPLACE INTO flows VALUES (?,?,?,?,?,?)", rows)
    return {"stored": len(rows), "dates": sorted({r[0] for r in rows})}


def get_flows(start: str | None = None, end: str | None = None) -> list[dict]:
    """One row per date: {date, fii_net, dii_net} (INR crore)."""
    sql = "SELECT date, category, net FROM flows WHERE 1=1"
    args: list = []
    if start:
        sql += " AND date >= ?"
        args.append(start)
    if end:
        sql += " AND date <= ?"
        args.append(end)
    with _conn() as conn:
        rows = conn.execute(sql + " ORDER BY date", args).fetchall()
    by_date: dict[str, dict] = {}
    for day, category, net in rows:
        rec = by_date.setdefault(day, {"date": day, "fii_net": None, "dii_net": None})
        rec["fii_net" if category == "FII" else "dii_net"] = net
    return list(by_date.values())


# ── refresh + freshness ────────────────────────────────────────────────────

def refresh_research(full: bool = False, now: dt.datetime | None = None) -> dict:
    """Refresh the sector-test series (RESEARCH_SYMBOLS); one failure doesn't stop the rest."""
    report: dict = {"daily": [], "errors": []}
    for symbol in RESEARCH_SYMBOLS:
        try:
            report["daily"].append(refresh_daily(symbol, full=full, now=now))
        except Exception as exc:
            log.exception("research refresh failed for %s", symbol)
            report["errors"].append(f"{symbol}: {type(exc).__name__}")
    return report


def refresh_all(full: bool = False, now: dt.datetime | None = None) -> dict:
    """Refresh every symbol and the flows; one failure doesn't stop the rest."""
    report: dict = {"daily": [], "flows": None, "errors": []}
    for symbol in SYMBOLS:
        try:
            report["daily"].append(refresh_daily(symbol, full=full, now=now))
        except Exception as exc:  # network/vendor errors are expected here
            log.exception("market refresh failed for %s", symbol)
            report["errors"].append(f"{symbol}: {type(exc).__name__}")
    try:
        report["flows"] = refresh_flows(now=now)
    except Exception as exc:
        log.exception("FII/DII refresh failed")
        report["errors"].append(f"flows: {type(exc).__name__}")
    return report


def freshness(now: dt.datetime | None = None) -> dict:
    """Coverage per series and whether its last row is behind the last trading day."""
    from sbc.market_holidays import is_trading_day

    expected = settled_date(now)
    while not is_trading_day(expected):
        expected -= dt.timedelta(days=1)

    series = {}
    for symbol in SYMBOLS:
        first, last, count = _span(symbol)
        series[symbol] = {"first": first, "last": last, "rows": count,
                          "stale": last is None or last < expected.isoformat()}
    with _conn() as conn:
        first, last, count = conn.execute(
            "SELECT MIN(date), MAX(date), COUNT(DISTINCT date) FROM flows").fetchone()
    series["FII_DII"] = {"first": first, "last": last, "rows": count,
                         "stale": last is None or last < expected.isoformat(),
                         "note": "NSE publishes the latest cash-session flows only; "
                                 "this series starts at the first refresh, so cumulative "
                                 "FII totals (e.g. 'FIIs withdrew ~4 lakh crore in 2026') "
                                 "cannot be audited from this store."}
    return {"expected_last_session": expected.isoformat(), "series": series,
            "stale": any(s["stale"] for s in series.values())}
