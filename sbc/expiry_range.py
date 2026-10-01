"""Expiry Range Indicator - expiry-day support/resistance forecast.

Forecasts NIFTY/BANKNIFTY expiry-day support/resistance from the previous
trading day's OHLC (floor-trader pivots) with a false-breakout buffer zone
around the first support/resistance. Breakouts only count beyond the buffer,
which eliminates most intraday false breakouts that close back inside range.

Includes a backtest harness that measures containment, breakout rates, and
the false-breakout rate on historical expiry days.

Research output, not investment advice.
"""

import datetime
from datetime import date, timedelta
from typing import Any

# Weekly expiry weekday (Mon=0) per instrument.
# NIFTY weekly expires Tuesday; BANKNIFTY is monthly (last Thursday).
EXPIRY_WEEKDAY = {"NIFTY": 1, "BANKNIFTY": 3, "FINNIFTY": 1, "MIDCPNIFTY": 1}

DEFAULT_BUFFER_PCT = 0.0025  # 0.25% false-breakout buffer for indices


def last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    """Return the last given weekday (Mon=0) of a month."""
    last_day = date(year, 12, 31) if month == 12 else date(year, month + 1, 1) - timedelta(days=1)
    delta = (last_day.weekday() - weekday) % 7
    return last_day - timedelta(days=delta)


def next_expiry(instrument: str, from_date: date | None = None) -> date:
    """Return the next expiry on/after `from_date` for the instrument.

    NIFTY/FINNIFTY/MIDCPNIFTY: weekly expiry (Tuesday by default).
    BANKNIFTY: monthly expiry (last Thursday of the month).
    """
    instrument = (instrument or "NIFTY").upper().replace(" ", "")
    from_date = from_date or datetime.date.today()
    weekday = EXPIRY_WEEKDAY.get(instrument, 1)

    if instrument == "BANKNIFTY":
        last = last_weekday_of_month(from_date.year, from_date.month, weekday)
        if from_date > last:
            if from_date.month == 12:
                return last_weekday_of_month(from_date.year + 1, 1, weekday)
            return last_weekday_of_month(from_date.year, from_date.month + 1, weekday)
        return last

    delta = (weekday - from_date.weekday()) % 7
    return from_date + timedelta(days=delta)


def expiry_range_levels(
    ohlc: dict[str, float], buffer_pct: float = DEFAULT_BUFFER_PCT
) -> dict[str, Any]:
    """Forecast expiry-day S/R from a reference day OHLC.

    Floor-trader pivots with a false-breakout buffer: resistance breakouts
    are only valid above R1 * (1 + buffer), support breakouts below
    S1 * (1 - buffer).
    """
    high = float(ohlc["high"])
    low = float(ohlc["low"])
    close = float(ohlc["close"])
    if high <= 0 or low <= 0 or high < low:
        raise ValueError("invalid OHLC for range forecast")

    pp = (high + low + close) / 3.0
    r1 = 2 * pp - low
    s1 = 2 * pp - high
    r2 = pp + (high - low)
    s2 = pp - (high - low)
    r3 = high + 2 * (pp - low)
    s3 = low - 2 * (high - pp)

    def rnd(x):
        return round(x, 2)

    return {
        "pivot": rnd(pp),
        "resistances": [
            {"level": "R1", "price": rnd(r1), "valid_above": rnd(r1 * (1 + buffer_pct))},
            {"level": "R2", "price": rnd(r2), "valid_above": rnd(r2 * (1 + buffer_pct))},
            {"level": "R3", "price": rnd(r3), "valid_above": rnd(r3 * (1 + buffer_pct))},
        ],
        "supports": [
            {"level": "S1", "price": rnd(s1), "valid_below": rnd(s1 * (1 - buffer_pct))},
            {"level": "S2", "price": rnd(s2), "valid_below": rnd(s2 * (1 - buffer_pct))},
            {"level": "S3", "price": rnd(s3), "valid_below": rnd(s3 * (1 - buffer_pct))},
        ],
        "buffer_pct": buffer_pct,
        "reference": {"open": rnd(float(ohlc.get("open", close))), "high": rnd(high),
                      "low": rnd(low), "close": rnd(close)},
    }


def evaluate_expiry_day(
    levels: dict[str, Any], expiry_ohlc: dict[str, float]
) -> dict[str, Any]:
    """Evaluate forecast levels against an actual expiry-day OHLC.

    Returns containment, breakout direction, and whether the breakout was
    false (intraday break that closed back inside the S1/R1 range).
    """
    high = float(expiry_ohlc["high"])
    low = float(expiry_ohlc["low"])
    close = float(expiry_ohlc["close"])

    r1 = next(lvl for lvl in levels["resistances"] if lvl["level"] == "R1")
    s1 = next(lvl for lvl in levels["supports"] if lvl["level"] == "S1")

    breakout_up = high > r1["valid_above"]
    breakout_down = low < s1["valid_below"]
    contained = not breakout_up and not breakout_down

    false_breakout_up = breakout_up and close < r1["price"]
    false_breakout_down = breakout_down and close > s1["price"]

    return {
        "contained": contained,
        "breakout_up": breakout_up,
        "breakout_down": breakout_down,
        "false_breakout_up": false_breakout_up,
        "false_breakout_down": false_breakout_down,
        "close": round(close, 2),
    }


def backtest_expiry(
    instrument: str = "NIFTY",
    months: int = 3,
    buffer_pct: float = DEFAULT_BUFFER_PCT,
    bars: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Backtest the expiry range forecast on historical expiry days.

    `bars` is an optional list of {date, open, high, low, close} daily bars
    (newest last); when omitted, bars are fetched via yfinance. Each expiry
    day's forecast is built from the previous trading day's OHLC.
    """
    if months <= 0 or months > 24:
        raise ValueError("months must be between 1 and 24")

    if bars is None:
        import yfinance as yf
        ticker = "^NSEI" if instrument.upper().replace(" ", "") == "NIFTY" else "^NSEBANK"
        end = datetime.date.today()
        start = end - timedelta(days=months * 31 + 10)
        df = yf.download(ticker, start=start, end=end, interval="1d", auto_adjust=True, progress=False)
        if df.empty:
            raise ValueError("no price data for backtest")
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        bars = [{"date": (idx.isoformat() if hasattr(idx, "isoformat") else str(idx))[:10],
                 "open": float(r["Open"]), "high": float(r["High"]),
                 "low": float(r["Low"]), "close": float(r["Close"])}
                for idx, r in df.iterrows()]

    # Reconstruct expiry day list (weekly/monthly cadence) inside the bar range.
    instrument_key = (instrument or "NIFTY").upper().replace(" ", "")
    dates = [date.fromisoformat(b["date"]) for b in bars]
    first, last = min(dates), max(dates)
    expiry_days = []
    cursor = first
    while cursor <= last:
        exp = next_expiry(instrument_key, cursor)
        if exp > last:
            break
        expiry_days.append(exp)
        cursor = exp + timedelta(days=1)

    results = []
    false_up = false_down = breakouts = contained_days = 0
    for exp in expiry_days:
        ref_idx = next((i for i, d in enumerate(dates) if d >= exp), None)
        prev_idx = ref_idx - 1 if ref_idx is not None else None
        if prev_idx is None or ref_idx is None:
            continue
        # The reference day must be the trading day before the expiry.
        if (dates[ref_idx] - dates[prev_idx]).days > 5:
            continue
        try:
            levels = expiry_range_levels(bars[prev_idx], buffer_pct)
            ev = evaluate_expiry_day(levels, bars[ref_idx])
        except ValueError:
            continue
        false_up += 1 if ev["false_breakout_up"] else 0
        false_down += 1 if ev["false_breakout_down"] else 0
        breakouts += 1 if (ev["breakout_up"] or ev["breakout_down"]) else 0
        contained_days += 1 if ev["contained"] else 0
        results.append({"expiry": exp.isoformat(), **ev})

    evaluated = len(results)
    return {
        "instrument": instrument_key,
        "months": months,
        "buffer_pct": buffer_pct,
        "expiry_days_evaluated": evaluated,
        "contained_days": contained_days,
        "containment_rate": round(contained_days / evaluated, 4) if evaluated else None,
        "breakout_days": breakouts,
        "false_breakout_up": false_up,
        "false_breakout_down": false_down,
        "false_breakout_rate": round((false_up + false_down) / max(breakouts, 1), 4) if breakouts else None,
        "results": results,
    }


__all__ = [
    "next_expiry",
    "last_weekday_of_month",
    "expiry_range_levels",
    "evaluate_expiry_day",
    "backtest_expiry",
    "EXPIRY_WEEKDAY",
    "DEFAULT_BUFFER_PCT",
]
