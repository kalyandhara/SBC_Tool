"""NIFTY 50 OHLC data via yfinance with local CSV cache.

Falls back to the cached file when the network/yfinance is unavailable,
so the chart still works offline.
"""

import datetime
import os
import swisseph as swe
from zoneinfo import ZoneInfo

from .planets import positions
from .config import RASHI_TREND

_CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                          "data", "nifty_ohlc.csv")
_TICKER = "^NSEI"


def moon_rashi(dt):
    """Return the Moon's sidereal rashi for a timezone-aware datetime."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
    dt_utc = dt.astimezone(ZoneInfo("UTC"))
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                    dt_utc.hour + dt_utc.minute / 60.0)
    planets, _ = positions(jd)
    return next(p for p in planets if p["name"] == "Moon")["sign"]


def _load_cache():
    import pandas as pd
    if not os.path.exists(_CACHE_PATH):
        return None
    df = pd.read_csv(_CACHE_PATH, parse_dates=["Date"])
    return df


def _save_cache(df):
    os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
    df.to_csv(_CACHE_PATH, index=False)


def get_nifty_ohlc(start=None, end=None):
    """Return list of {time:'YYYY-MM-DD', open, high, low, close, volume}.

    start/end: 'YYYY-MM-DD' strings or None (defaults: last 3 years).
    """
    import pandas as pd

    today = datetime.date.today()
    start_d = datetime.date.fromisoformat(start) if start else today - datetime.timedelta(days=3 * 365)
    end_d = datetime.date.fromisoformat(end) if end else today

    df = _load_cache()
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
                new = yf.download(_TICKER, start=fetch_start.isoformat(),
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
                    _save_cache(df)
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
