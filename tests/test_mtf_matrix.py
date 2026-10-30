"""Tests for the multi-timeframe EMA 9/21 Heikin-Ashi matrix.

The fixtures build raw OHLC series with known crossover points, apply
the real heikin_ashi transform, and grade the frozen definitions in
sbc/screener/mtf_matrix.py.
"""

import numpy as np
import pandas as pd
import pytest

from sbc.screener.indicators import ema, heikin_ashi
from sbc.screener.mtf_matrix import (MIN_BARS, bias_label, compute_matrix,
                                     provisional_state, timeframe_state,
                                     to_markdown)


def raw_frame(closes, base=100.0):
    """Raw OHLCV frame whose CLOSES are `closes`; O/H/L stay near them."""
    closes = pd.Series(closes, dtype=float)
    n = len(closes)
    open_ = closes.shift(1).fillna(base)
    high = np.maximum(open_, closes) + 0.5
    low = np.minimum(open_, closes) - 0.5
    idx = pd.date_range("2026-01-01", periods=n, freq="h")
    return pd.DataFrame({"open": open_.values, "high": high.values,
                         "low": low.values, "close": closes.values,
                         "volume": np.ones(n)}, index=idx)


def ha(closes):
    return heikin_ashi(raw_frame(closes))


# ── state, age, fresh ──────────────────────────────────────────────────────

def test_bullish_state_with_age():
    # 10 falling then 30 rising closes: EMA9 crosses above EMA21 mid-series.
    closes = list(np.linspace(120, 100, 10)) + list(np.linspace(101, 140, 30))
    st = timeframe_state(ha(closes))
    assert st["state"] == "bullish"
    assert st["age"] is not None and st["age"] > 0
    assert st["fresh"] is None


def test_fresh_cross_on_latest_closed_candle():
    # A long flat run converges both EMAs exactly to 100; a single strong
    # bar then lifts EMA9 above EMA21 on that bar -> fresh up, age 0.
    closes = [100.0] * 40 + [130.0]
    st = timeframe_state(ha(closes))
    assert st["state"] == "bullish"
    assert st["age"] == 0 and st["fresh"] == "up"


def test_bearish_state_strong():
    closes = list(np.linspace(100, 140, 10)) + list(np.linspace(139, 60, 30))
    st = timeframe_state(ha(closes))
    assert st["state"] == "bearish"
    assert st["strong"] is True
    close, f, s = 60.0, None, None
    ha_df = ha(closes)
    close = float(ha_df["close"].iloc[-1])
    f = float(ema(ha_df["close"], 9).iloc[-1])
    s = float(ema(ha_df["close"], 21).iloc[-1])
    assert close < f and close < s


def test_weak_bullish_when_close_not_beyond_both_emas():
    # Rise establishes EMA9>EMA21; a pullback bar drops the HA close
    # between the two EMAs -> still bullish, but Weak.
    closes = list(np.linspace(100, 160, 30)) + [160.0] * 5 + [150.0]
    st = timeframe_state(ha(closes))
    assert st["state"] == "bullish"
    ha_df = ha(closes)
    close = float(ha_df["close"].iloc[-1])
    f = float(ema(ha_df["close"], 9).iloc[-1])
    s = float(ema(ha_df["close"], 21).iloc[-1])
    # fixture sanity: state bullish, close between the EMAs
    assert f > s
    assert s < close < f
    assert st["strong"] is False


def test_no_cross_in_window():
    closes = list(np.linspace(100, 200, 40))
    st = timeframe_state(ha(closes))
    assert st["state"] == "bullish" and st["age"] is None


def test_na_when_too_few_bars():
    st = timeframe_state(ha(list(np.linspace(100, 110, MIN_BARS - 1))))
    assert st["state"] is None and st["bars"] == MIN_BARS - 1


# ── provisional reading ────────────────────────────────────────────────────

def test_provisional_differs_from_closed_state():
    # Flat run (EMAs converge to 100), one rise bar: the closed frame is
    # freshly bullish.  A crash bar as the running candle drops EMA9 back
    # below EMA21 -> the provisional reading flips bearish.
    closes = [100.0] * 40 + [110.0]
    st_closed = timeframe_state(ha(closes))
    assert st_closed["state"] == "bullish" and st_closed["fresh"] == "up"
    running = raw_frame(closes + [60.0])
    st_prov = provisional_state(running)
    assert st_prov["state"] == "bearish"
    assert st_prov["fresh"] == "down"


# ── bias rule (frozen) ─────────────────────────────────────────────────────

@pytest.mark.parametrize("bull,available,want", [
    (7, 7, "Strong Bullish"), (6, 7, "Strong Bullish"),
    (5, 7, "Bullish"), (4, 7, "Bullish"),
    (3, 7, "Bearish"), (2, 7, "Bearish"),
    (1, 7, "Strong Bearish"), (0, 7, "Strong Bearish"),
    (2, 4, "Mixed"), (0, 0, "n/a"),
])
def test_bias_label(bull, available, want):
    assert bias_label(bull, available) == want


# ── whole-universe rows ────────────────────────────────────────────────────

def test_compute_matrix_rows_sorted_with_price():
    up = ha(list(np.linspace(100, 160, 40)))
    dn = ha(list(np.linspace(160, 100, 40)))
    rows = compute_matrix({"1d": {"AAA": up, "BBB": dn},
                           "1wk": {"AAA": up, "BBB": dn}})
    assert [r["symbol"] for r in rows] == ["AAA", "BBB"]
    assert rows[0]["bull"] == 2 and rows[0]["bias"] == "Strong Bullish"
    assert rows[1]["bull"] == 0 and rows[1]["bias"] == "Strong Bearish"
    assert rows[0]["price"] == round(float(up["close"].iloc[-1]), 2)
    # missing timeframe renders n/a and shrinks the denominator
    rows2 = compute_matrix({"1d": {"AAA": up}})
    assert rows2[0]["available"] == 1 and rows2[0]["bias"] == "Strong Bullish"


def test_to_markdown_renders_cells():
    up = ha(list(np.linspace(100, 160, 40)))
    rows = compute_matrix({"1d": {"AAA": up}, "1wk": {"AAA": up}})
    md = to_markdown(rows)
    assert "| Symbol | Price |" in md
    assert "Strong Bullish" in md
    assert "n/a" in md  # the five timeframes without data
