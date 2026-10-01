"""OHLC data via yfinance with local CSV cache.

Covers the study assets NIFTY (^NSEI), Gold (GC=F) and Silver (SI=F).
Falls back to the cached file when the network/yfinance is unavailable,
so the chart still works offline.
"""

import datetime
import os
from zoneinfo import ZoneInfo

import swisseph as swe

from .config import RASHI_TREND
from .planets import positions

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                         "data")
_CACHE_PATH = os.path.join(_DATA_DIR, "nifty_ohlc.csv")
_TICKER = "^NSEI"

# Study assets: key -> (yfinance ticker, cache filename).  Gold and
# Silver use the COMEX front-month futures (GC=F / SI=F), which have
# continuous daily history back to 2000 — deep enough for the
# 2002-2024 transit studies.  Weekend/holiday gaps are handled by the
# studies as "first available trading day on or after".
_ASSETS = {
    "nifty": ("^NSEI", "nifty_ohlc.csv"),
    "gold": ("GC=F", "gold_ohlc.csv"),
    "silver": ("SI=F", "silver_ohlc.csv"),
}


def moon_rashi(dt):
    """Return the Moon's sidereal rashi for a timezone-aware datetime."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
    dt_utc = dt.astimezone(ZoneInfo("UTC"))
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                    dt_utc.hour + dt_utc.minute / 60.0)
    planets, _ = positions(jd)
    return next(p for p in planets if p["name"] == "Moon")["sign"]


def _load_cache(cache_path):
    import pandas as pd
    if not os.path.exists(cache_path):
        return None
    df = pd.read_csv(cache_path, parse_dates=["Date"])
    return df


def _save_cache(df, cache_path):
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    df.to_csv(cache_path, index=False)


def _get_ohlc_cached(ticker, cache_path, start=None, end=None):
    """Return list of {time:'YYYY-MM-DD', open, high, low, close, volume}.

    start/end: 'YYYY-MM-DD' strings or None (defaults: last 3 years).
    Uses and extends the local CSV cache; falls back to whatever cache
    we have when the network is unavailable.
    """
    import pandas as pd

    today = datetime.date.today()
    start_d = datetime.date.fromisoformat(start) if start else today - datetime.timedelta(days=3 * 365)
    end_d = datetime.date.fromisoformat(end) if end else today

    df = _load_cache(cache_path)
    need_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]

    cache_ok = (
        df is not None and not df.empty
        and df["Date"].min().date() <= start_d
        and df["Date"].max().date() >= min(end_d, today)
    )

    if not cache_ok:
        try:
            import yfinance as yf
            # never try to download beyond today — future data doesn't exist
            # and yfinance just errors out ("Data doesn't exist for startDate...")
            dl_end = min(end_d, today)
            fetch_start = start_d
            if df is not None and not df.empty:
                # only fetch the missing tail
                fetch_start = df["Date"].max().date() + datetime.timedelta(days=1)
            if fetch_start <= dl_end:
                new = yf.download(ticker, start=fetch_start.isoformat(),
                                  end=(dl_end + datetime.timedelta(days=1)).isoformat(),
                                  progress=False, auto_adjust=False)
                if new is not None and not new.empty:
                    if isinstance(new.columns, pd.MultiIndex):
                        new.columns = [c[0] for c in new.columns]
                    new = new.reset_index()
                    new["Date"] = pd.to_datetime(new["Date"]).dt.tz_localize(None)
                    new = new[need_cols]
                    df = new if df is None or df.empty else (
                        pd.concat([df, new]).drop_duplicates("Date").sort_values("Date")
                    )
                    _save_cache(df, cache_path)
        except Exception:
            pass  # fall through to whatever cache we have

    if df is None or df.empty:
        return []

    mask = (df["Date"].dt.date >= start_d) & (df["Date"].dt.date <= end_d)
    df = df[mask]
    out = []
    for _, r in df.iterrows():
        out.append({
            "time": r["Date"].date().isoformat(),
            "open": round(float(r["Open"]), 2),
            "high": round(float(r["High"]), 2),
            "low": round(float(r["Low"]), 2),
            "close": round(float(r["Close"]), 2),
            "volume": int(r["Volume"]) if r["Volume"] == r["Volume"] else 0,
        })
    return out


def get_ohlc(asset="nifty", start=None, end=None):
    """Return cached OHLC rows for a study asset key (nifty/gold/silver)."""
    try:
        ticker, cache_path = _ASSETS[asset]
    except KeyError:
        raise ValueError(f"unknown asset {asset!r}; "
                         f"expected one of {sorted(_ASSETS)}") from None
    return _get_ohlc_cached(ticker, cache_path, start, end)


def get_nifty_ohlc(start=None, end=None):
    return get_ohlc("nifty", start, end)


def get_gold_ohlc(start=None, end=None):
    return get_ohlc("gold", start, end)


def get_silver_ohlc(start=None, end=None):
    return get_ohlc("silver", start, end)
