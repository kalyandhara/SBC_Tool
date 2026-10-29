"""Price data for the momentum screener: yfinance batch download with
timeframe windows and past-date back-scans.

Yahoo intraday limits are enforced up front: 5m/10m/15m bars only
exist for the last ~60 days, 1h for ~730.  `end` back-scans the scan
date (bars are clipped to it); `lookback_days` controls how much
history each scan sees.  Output DataFrames carry lowercase
open/high/low/close/volume, chronological order, no NaN rows.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

# timeframe -> (yfinance interval, max calendar days Yahoo serves)
TIMEFRAMES = {
    "5m": ("5m", 60),
    "10m": ("10m", 60),
    "15m": ("15m", 60),
    "1h": ("1h", 730),
    "1d": ("1d", None),
    "1wk": ("1wk", None),
}

DEFAULT_LOOKBACK = {"5m": 30, "10m": 30, "15m": 30, "1h": 120,
                    "1d": 400, "1wk": 700}


class TimeframeError(ValueError):
    pass


def clamp_window(timeframe: str, end: dt.date,
                 lookback_days: int | None) -> tuple[dt.date, dt.date, int]:
    """Return (start, clipped_end, effective_lookback) honouring Yahoo's
    intraday history limits."""
    if timeframe not in TIMEFRAMES:
        raise TimeframeError(
            f"unknown timeframe {timeframe!r}; one of {sorted(TIMEFRAMES)}")
    interval, max_days = TIMEFRAMES[timeframe]
    lookback = lookback_days or DEFAULT_LOOKBACK[timeframe]
    if max_days is not None:
        hard_end = dt.date.today()
        end = min(end, hard_end)
        earliest = end - dt.timedelta(days=max_days - 1)
        lookback = min(lookback, max_days - 1)
        start = max(end - dt.timedelta(days=lookback), earliest)
    else:
        start = end - dt.timedelta(days=lookback)
    return start, end, lookback


def history(symbol: str, timeframe: str = "1d", end: dt.date | None = None,
            lookback_days: int | None = None) -> pd.DataFrame:
    """One symbol's OHLCV bars ending at `end` (inclusive)."""
    end = end or dt.date.today()
    start, end, _ = clamp_window(timeframe, end, lookback_days)
    interval, _ = TIMEFRAMES[timeframe]
    df = _download(symbol, interval, start, end + dt.timedelta(days=1))
    if df.empty:
        return df
    cutoff = pd.Timestamp(end) + pd.Timedelta(days=1)
    if timeframe in ("1d", "1wk"):
        df = df[df.index <= cutoff]
    return df


def batch(symbols: list[str], timeframe: str = "1d",
          end: dt.date | None = None, lookback_days: int | None = None,
          as_ha: bool = False) -> tuple[dict[str, pd.DataFrame],
                                        dict[str, str]]:
    """Download many symbols at once.

    Returns ({symbol: OHLCV df}, {symbol: error}) — symbols with an
    error are simply absent from the first dict (empty universe lists
    raise ValueError before any download).
    """
    if not symbols:
        raise ValueError("empty symbol list")
    end = end or dt.date.today()
    start, end, _ = clamp_window(timeframe, end, lookback_days)
    interval, _ = TIMEFRAMES[timeframe]
    raw = _download_many(symbols, interval, start,
                         end + dt.timedelta(days=1))
    out: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}
    cutoff = pd.Timestamp(end) + pd.Timedelta(days=1)
    for symbol in symbols:
        df = raw.get(symbol)
        if df is None or df.empty:
            errors[symbol] = "no data returned"
            continue
        df = _clean(df)
        if df.empty:
            errors[symbol] = "no usable columns"
            continue
        if timeframe in ("1d", "1wk"):
            df = df[df.index <= cutoff]
        df = df.dropna(subset=["open", "high", "low", "close"])
        if df.empty:
            errors[symbol] = "no bars after filters"
            continue
        if as_ha:
            from .indicators import heikin_ashi
            ha = heikin_ashi(df)
            df = df.assign(open=ha["open"], high=ha["high"],
                           low=ha["low"], close=ha["close"])
        out[symbol] = df
    return out, errors


def _download(symbol: str, interval: str, start: dt.date,
              end_exclusive: dt.date) -> pd.DataFrame:
    frames = _download_many([symbol], interval, start, end_exclusive)
    return frames.get(symbol, pd.DataFrame())


def _download_many(symbols: list[str], interval: str, start: dt.date,
                   end_exclusive: dt.date) -> dict[str, pd.DataFrame]:
    import yfinance as yf
    try:
        raw = yf.download(symbols, start=start.isoformat(),
                          end=end_exclusive.isoformat(), interval=interval,
                          group_by="ticker", auto_adjust=False,
                          progress=False, threads=True)
    except Exception:  # noqa: BLE001 - yfinance can raise on odd tickers
        raw = None
    out: dict[str, pd.DataFrame] = {}
    if raw is None or raw.empty:
        return out
    if isinstance(raw.columns, pd.MultiIndex):
        for symbol in symbols:
            if symbol in raw.columns.get_level_values(0):
                out[symbol] = _clean(raw[symbol])
    else:
        out[symbols[0]] = _clean(raw)
    return {k: v for k, v in out.items() if v is not None and not v.empty}


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=str.lower)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.sort_index()
    cols = [c for c in ("open", "high", "low", "close", "volume")
            if c in df.columns]
    return df[cols]
