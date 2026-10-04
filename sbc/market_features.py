"""Market-side control variables for each NIFTY session (from data/market.db).

Every value for session t uses closes up to t-1 only: the same information
an astro signal for t competes with at entry (the previous close).

  ret5, ret20, ret60   trailing NIFTY returns
  rv20                 20-session realized volatility (daily stdev)
  ma200_gap            previous close / 200-session average - 1
  log_vix              log India VIX at the previous close
  dvix5                5-session change in log VIX
  weekday_*            Monday..Thursday dummies (Friday is the baseline)
  turn_of_month        first 3 / last 2 sessions of a calendar month (NSE holidays
                       are known from 2024; earlier years skip weekends only)

FII/DII flows are not a control yet: NSE's free feed has no history, so the
series only starts on 2026-10-01 (see sbc.market_store).
"""

from __future__ import annotations

import datetime as dt

import numpy as np
from numpy.typing import ArrayLike

from sbc import market_store
from sbc.market_holidays import next_trading_day

CONTROL_NAMES = ("ret5", "ret20", "ret60", "rv20", "ma200_gap", "log_vix", "dvix5",
                 "weekday_Mon", "weekday_Tue", "weekday_Wed", "weekday_Thu", "turn_of_month")


def _trailing_return(close: np.ndarray, n: int) -> np.ndarray:
    """Return over the n sessions ending at t-1: close[t-1] / close[t-1-n] - 1."""
    out = np.full(len(close), np.nan)
    out[n + 1:] = close[n:-1] / close[:-n - 1] - 1.0
    return out


def _turn_of_month(days: list[dt.date], i: int) -> bool:
    """First 3 or last 2 sessions of the month (the trading calendar is known in advance)."""
    month = (days[i].year, days[i].month)
    from_start = 0
    while i - from_start - 1 >= 0 and (days[i - from_start - 1].year, days[i - from_start - 1].month) == month:
        from_start += 1
    following, day = [], days[i]
    for _ in range(2):
        day = next_trading_day(day, inclusive=False)
        following.append(day)
    from_end = sum(1 for d in following if (d.year, d.month) == month)
    return from_start < 3 or from_end < 2


def controls(dates: list[str], closes: ArrayLike, vix_by_date: dict[str, float]) -> np.ndarray:
    """(N, len(CONTROL_NAMES)) matrix aligned with `dates`; NaN where history is too short."""
    close = np.asarray(closes, dtype=float)
    n = len(close)
    daily = np.full(n, np.nan)
    daily[1:] = close[1:] / close[:-1] - 1.0

    rv20 = np.full(n, np.nan)
    ma200 = np.full(n, np.nan)
    for t in range(1, n):
        if t >= 21:
            rv20[t] = np.std(daily[t - 20:t], ddof=1)
        if t >= 200:
            ma200[t] = close[t - 1] / close[t - 200:t].mean() - 1.0

    vix = np.array([vix_by_date.get(d, np.nan) for d in dates], dtype=float)
    log_vix_today = np.log(vix)
    log_vix = np.full(n, np.nan)
    log_vix[1:] = log_vix_today[:-1]
    dvix5 = np.full(n, np.nan)
    dvix5[6:] = log_vix_today[5:-1] - log_vix_today[:-6]

    days = [dt.date.fromisoformat(d) for d in dates]
    weekdays = np.array([d.weekday() for d in days])
    tom = np.array([float(_turn_of_month(days, i)) for i in range(n)])

    cols = [
        _trailing_return(close, 5), _trailing_return(close, 20), _trailing_return(close, 60),
        rv20, ma200, log_vix, dvix5,
        *(weekdays == k for k in range(4)),
        tom,
    ]
    return np.column_stack([np.asarray(c, dtype=float) for c in cols])


def nifty_controls(dates: list[str], closes: ArrayLike) -> np.ndarray:
    """controls() with India VIX read from market.db."""
    vix = {b["date"]: b["close"] for b in market_store.get_daily("INDIAVIX")}
    return controls(dates, closes, vix)
