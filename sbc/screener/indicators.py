"""Technical indicators for the NSE momentum screener.

Timeframe-agnostic pandas implementations: EMA, Wilder RSI, Bollinger
Bands, previous-period pivot levels (P/R1/S1 from the prior candle's
H/L/C), Supertrend (ATR with Wilder smoothing) and a Heikin-Ashi
transform.  Inputs are DataFrames with lowercase OHLC columns
(open, high, low, close) in chronological order.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["ema", "rsi", "bollinger", "pivots", "true_range", "atr",
           "supertrend", "heikin_ashi"]


def ema(close: pd.Series, span: int) -> pd.Series:
    """Exponential moving average (adjust=False, seeded with the first value)."""
    return close.ewm(span=span, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI.  Flat series -> 50; one-sided series -> 100/0."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False,
                        min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False,
                        min_periods=period).mean()
    out = pd.Series(np.where(
        (avg_loss == 0) & (avg_gain == 0), 50.0,
        np.where(avg_loss == 0, 100.0,
                 100.0 - 100.0 / (1.0 + avg_gain / avg_loss))),
        index=close.index)
    out[avg_gain.isna() | avg_loss.isna()] = np.nan
    return out


def bollinger(close: pd.Series, period: int = 20,
              num_std: float = 2.0) -> pd.DataFrame:
    mid = close.rolling(period).mean()
    sd = close.rolling(period).std(ddof=0)
    return pd.DataFrame({"bb_mid": mid, "bb_up": mid + num_std * sd,
                         "bb_low": mid - num_std * sd})


def pivots(high: pd.Series, low: pd.Series, close: pd.Series,
           shift: int = 1) -> pd.DataFrame:
    """Classic floor-trader pivots from the candle `shift` bars ago
    (shift=1 -> previous period): P=(H+L+C)/3, R1=2P-L, S1=2P-H."""
    p = ((high + low + close) / 3.0).shift(shift)
    r1 = 2.0 * p - low.shift(shift)
    s1 = 2.0 * p - high.shift(shift)
    return pd.DataFrame({"pivot_p": p, "pivot_r1": r1, "pivot_s1": s1})


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    ranges = pd.concat([df["high"] - df["low"],
                        (df["high"] - prev_close).abs(),
                        (df["low"] - prev_close).abs()], axis=1)
    return ranges.max(axis=1)


def atr(df: pd.DataFrame, period: int = 10) -> pd.Series:
    """Classic Wilder ATR: seed = SMA of the first `period` true ranges,
    then a[i] = (a[i-1]*(period-1) + TR[i]) / period."""
    tr = true_range(df)
    out = pd.Series(np.nan, index=df.index)
    tr_vals = tr.values
    for i in range(len(df)):
        if i == period - 1:
            out.iloc[i] = np.nanmean(tr_vals[:period])
        elif i >= period:
            out.iloc[i] = (out.iloc[i - 1] * (period - 1)
                           + tr_vals[i]) / period
    return out


def supertrend(df: pd.DataFrame, period: int = 10,
               multiplier: float = 3.0) -> pd.DataFrame:
    """Supertrend: columns `st` (line value) and `st_dir` (+1 up, -1 down).

    Canonical carry-forward bands (Pine reference): the lower band only
    ratchets up while close holds above it, the upper band only ratchets
    down while close holds below it; the trend flips when close crosses
    the previous bar's opposite final band.  The line rides below price
    in an uptrend and above it in a downtrend.
    """
    hl2 = (df["high"] + df["low"]) / 2.0
    atr_ = atr(df, period)
    lower_raw = hl2 - multiplier * atr_
    upper_raw = hl2 + multiplier * atr_
    close = df["close"]

    n = len(df)
    f_lb = pd.Series(np.nan, index=df.index)
    f_ub = pd.Series(np.nan, index=df.index)
    direction = pd.Series(np.nan, index=df.index)
    line = pd.Series(np.nan, index=df.index)
    trend = 1.0
    for i in range(n):
        if np.isnan(lower_raw.iloc[i]):
            continue
        if np.isnan(f_lb.iloc[i - 1]) if i > 0 else True:
            f_lb.iloc[i] = lower_raw.iloc[i]
            f_ub.iloc[i] = upper_raw.iloc[i]
        else:
            prev_close = close.iloc[i - 1]
            prev_lb = f_lb.iloc[i - 1]
            prev_ub = f_ub.iloc[i - 1]
            f_lb.iloc[i] = (lower_raw.iloc[i]
                            if lower_raw.iloc[i] > prev_lb
                            or prev_close < prev_lb else prev_lb)
            f_ub.iloc[i] = (upper_raw.iloc[i]
                            if upper_raw.iloc[i] < prev_ub
                            or prev_close > prev_ub else prev_ub)
            # Pine reference: trend flips on the CURRENT close vs the
            # PREVIOUS bar's final opposite band.
            if trend == 1 and close.iloc[i] < prev_lb:
                trend = -1
            elif trend == -1 and close.iloc[i] > prev_ub:
                trend = 1
        direction.iloc[i] = trend
        line.iloc[i] = f_lb.iloc[i] if trend == 1 else f_ub.iloc[i]
    return pd.DataFrame({"st": line, "st_dir": direction,
                         "st_lb": f_lb, "st_ub": f_ub})


def heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """Heikin-Ashi OHLC transform; keeps the original index."""
    ha_close = (df["open"] + df["high"] + df["low"] + df["close"]) / 4.0
    ha_open = ha_close.copy()
    if len(df):
        ha_open.iloc[0] = (df["open"].iloc[0] + df["close"].iloc[0]) / 2.0
    o = ha_open.to_numpy(copy=True)
    c = ha_close.to_numpy(copy=True)
    for i in range(1, len(df)):
        o[i] = (o[i - 1] + c[i - 1]) / 2.0
    ha_open = pd.Series(o, index=df.index)
    ha_high = pd.concat([df["high"], ha_open, ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([df["low"], ha_open, ha_close], axis=1).min(axis=1)
    return pd.DataFrame({"open": ha_open, "high": ha_high, "low": ha_low,
                         "close": ha_close})
