"""Multi-timeframe EMA 9/21 trend matrix on Heikin-Ashi candles.

Frozen definitions (2026-10-27, pre-registered before any validation
run - see reports/mtf_ema_matrix_gap_analysis_2026-10-27.md):

- Candles: Heikin-Ashi (sbc.screener.indicators.heikin_ashi) computed
  on CLOSED bars only.  A running bar is reported separately as a
  provisional reading (see `provisional_state`) and never enters the
  state, age or bias.
- State: Bullish when EMA(9) > EMA(21) of the HA closes, else Bearish.
- Age: closed candles since the cross candle, the cross candle being
  candle 0.  A cell whose cross is the latest closed candle is a fresh
  cross (`fresh` = "up"/"down").  `age` None with a defined state means
  no cross inside the loaded window.
- Strong/Weak: a bullish state is Strong when the latest HA close is
  above BOTH EMAs, otherwise Weak; mirrored for bearish ("HA close not
  beyond both EMAs" -> Weak, per the source legend).
- n/a: fewer than 22 closed candles on a timeframe (EMA(21) warm-up).
- Bias (frozen rule): computed over the timeframes that carry data.
  With bull_ratio = bullish / available: >= 6/7 -> "Strong Bullish";
  > 1/2 -> "Bullish"; == 1/2 -> "Mixed"; mirrored for bearish
  (1 - bull_ratio >= 6/7 -> "Strong Bearish", else "Bearish"); no data
  -> "n/a".

Inputs are DataFrames of HA bars (lowercase OHLC, chronological).
"""

from __future__ import annotations

import pandas as pd

from .indicators import ema

__all__ = ["MATRIX_TIMEFRAMES", "MIN_BARS", "bias_label", "timeframe_state",
           "provisional_state", "symbol_matrix", "compute_matrix",
           "to_markdown"]

MATRIX_TIMEFRAMES = ("5m", "10m", "15m", "30m", "1h", "1d", "1wk")
MIN_BARS = 22  # EMA(21) warm-up on HA closes


def bias_label(bull: int, available: int) -> str:
    """Frozen count -> Bias rule (module docstring)."""
    if available <= 0:
        return "n/a"
    ratio = bull / available
    if ratio >= 6 / 7:
        return "Strong Bullish"
    if ratio > 0.5:
        return "Bullish"
    if ratio == 0.5:
        return "Mixed"
    if 1 - ratio >= 6 / 7:
        return "Strong Bearish"
    return "Bearish"


def _state_from_diff(diff: pd.Series) -> dict:
    """Shared state logic on a boolean EMA9>EMA21 series of CLOSED bars.

    Seed rule (frozen): both EMAs start equal at the series' first
    value, so bar 1 would always register as a cross; the walk ignores
    that warm-up artifact and looks for crosses from bar 2 onward.
    """
    n = len(diff)
    if n < MIN_BARS:
        return {"state": None, "age": None, "strong": None, "fresh": None,
                "bars": n}
    bull = bool(diff.iloc[-1])
    age = None
    for i in range(n - 1, 1, -1):
        if bool(diff.iloc[i]) != bool(diff.iloc[i - 1]):
            age = (n - 1) - i
            break
    return {"state": "bullish" if bull else "bearish", "age": age,
            "strong": None, "fresh": None, "bars": n}


def timeframe_state(df_ha: pd.DataFrame, fast: int = 9,
                    slow: int = 21) -> dict:
    """State of one closed-candle HA frame.

    Returns {state, age, strong, fresh, bars}; state None = n/a.
    """
    st = _state_from_diff(ema(df_ha["close"], fast)
                          > ema(df_ha["close"], slow))
    if st["state"] is None:
        return st
    close = float(df_ha["close"].iloc[-1])
    f = float(ema(df_ha["close"], fast).iloc[-1])
    s = float(ema(df_ha["close"], slow).iloc[-1])
    if st["state"] == "bullish":
        st["strong"] = close > f and close > s
        st["fresh"] = "up" if st["age"] == 0 else None
    else:
        st["strong"] = close < f and close < s
        st["fresh"] = "down" if st["age"] == 0 else None
    return st


def provisional_state(df_raw_with_running: pd.DataFrame, fast: int = 9,
                      slow: int = 21) -> dict:
    """What the state WOULD be if the running bar closed now.

    The caller passes the RAW (non-HA) frame including the running bar;
    the transform runs here so the stored closed-candle state is never
    mixed with it.
    """
    from .indicators import heikin_ashi
    ha = heikin_ashi(df_raw_with_running)
    return timeframe_state(ha, fast, slow)


def _cell(st: dict) -> dict:
    if st["state"] is None:
        return {"state": None, "age": None, "strong": None, "fresh": None}
    return st


def symbol_matrix(frames: dict[str, pd.DataFrame],
                  provisional: dict[str, pd.DataFrame] | None = None,
                  fast: int = 9, slow: int = 21,
                  timeframes: tuple[str, ...] = MATRIX_TIMEFRAMES) -> dict:
    """One symbol's matrix row.

    frames: timeframe -> HA frame of CLOSED candles (missing/empty
    timeframe -> n/a cell).  provisional: timeframe -> RAW frame
    including the running bar, for the provisional reading.
    """
    cells: dict[str, dict] = {}
    bull = 0
    available = 0
    for tf in timeframes:
        df = frames.get(tf)
        st = timeframe_state(df, fast, slow) if df is not None and len(df) \
            else {"state": None, "age": None, "strong": None, "fresh": None,
                  "bars": 0}
        cells[tf] = _cell(st)
        if st["state"] is not None:
            available += 1
            if st["state"] == "bullish":
                bull += 1
    price = None
    daily = frames.get("1d")
    if daily is not None and len(daily):
        price = round(float(daily["close"].iloc[-1]), 2)
    row = {"cells": cells, "bull": bull, "available": available,
           "bias": bias_label(bull, available), "price": price}
    if provisional:
        row["provisional"] = {
            tf: provisional_state(df, fast, slow)["state"]
            for tf, df in provisional.items() if df is not None and len(df)
        }
    return row


def compute_matrix(data_by_tf: dict[str, dict[str, pd.DataFrame]],
                   fast: int = 9, slow: int = 21,
                   timeframes: tuple[str, ...] = MATRIX_TIMEFRAMES) -> list[dict]:
    """Rows for the whole universe.

    data_by_tf: timeframe -> {symbol: HA frame of CLOSED candles}.
    Returns one row per symbol (any symbol present in at least one
    timeframe), sorted by bull count desc then symbol.
    """
    symbols = sorted({s for per_tf in data_by_tf.values() for s in per_tf})
    rows = []
    for sym in symbols:
        frames = {tf: per_tf[sym] for tf, per_tf in data_by_tf.items()
                  if sym in per_tf and per_tf[sym] is not None
                  and len(per_tf[sym])}
        row = symbol_matrix(frames, fast=fast, slow=slow,
                            timeframes=timeframes)
        row["symbol"] = sym
        rows.append(row)
    rows.sort(key=lambda r: (-r["bull"], r["symbol"]))
    return rows


def _cell_text(cell: dict) -> str:
    if cell["state"] is None:
        return "n/a"
    word = "Bullish" if cell["state"] == "bullish" else "Bearish"
    if cell["fresh"]:
        return f"{word} {'▲' if cell['fresh'] == 'up' else '▼'}"
    label = f"{'Weak ' if not cell['strong'] else ''}{word}"
    if cell["age"] is None:
        return f"{label} (no cross)"
    return f"{label} ({cell['age']})"


def to_markdown(rows: list[dict],
                timeframes: tuple[str, ...] = MATRIX_TIMEFRAMES) -> str:
    """The matrix as a markdown table (the screenshot's layout)."""
    head = ("| Symbol | Price | " + " | ".join(timeframes)
            + " | Bull Count | Bias |")
    sep = "|" + "---|" * (len(timeframes) + 4)
    lines = [head, sep]
    for r in rows:
        cells = " | ".join(_cell_text(r["cells"][tf]) for tf in timeframes)
        bull_txt = f"{r['bull']}/{r['available']}" if r["available"] else "n/a"
        lines.append(f"| {r['symbol']} | {r['price'] if r['price'] else '-'} "
                     f"| {cells} | {bull_txt} | {r['bias']} |")
    return "\n".join(lines) + "\n"
