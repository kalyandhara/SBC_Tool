"""Tests for sbc.screener.engine — synthetic offline candles."""

import numpy as np
import pandas as pd
import pytest

from sbc.screener import engine


def _trend_df(base=100.0, drift=0.4, n=120, noise=0.0, seed=3,
              break_at=None, break_drift=-1.5):
    rng = np.random.default_rng(seed)
    rows, price = [], base
    for i in range(n):
        d = drift
        if break_at is not None and i >= break_at:
            d = break_drift
        o = price
        c = price + d + (rng.uniform(-noise, noise) if noise else 0.0)
        rows.append([o, max(o, c) + 0.5, min(o, c) - 0.5, c, 10_000])
        price = c
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close",
                                     "volume"])
    df.index = pd.date_range("2026-01-01", periods=n, freq="D")
    return df


def test_merge_params_filters_unknown_keys():
    p = engine.merge_params("full", {"rsi_long": 60, "bogus": 1})
    assert p["rsi_long"] == 60 and "bogus" not in p
    with pytest.raises(ValueError):
        engine.merge_params("nope", None)


def test_full_mode_longs_in_uptrend():
    df = _trend_df(drift=1.0, n=140, noise=0.5)
    out = engine.run_scan({"TCS.NS": df}, "full")
    longs = [s for s in out["signals"] if s["side"] == "long"]
    assert longs, "uptrend should produce at least one long signal"
    assert all(s["entry_ts"] for s in longs)
    assert all(s["stop_initial"] < s["entry"] for s in longs
               if s["stop_initial"])


def test_short_signal_in_downtrend():
    up = _trend_df(drift=0.6, n=60).values.tolist()
    price = up[-1][3]
    for _ in range(80):
        o = price
        c = price - 1.2
        up.append([o, max(o, c) + 0.5, min(o, c) - 0.5, c, 10_000])
        price = c
    df = pd.DataFrame(up, columns=["open", "high", "low", "close",
                                   "volume"])
    df.index = pd.date_range("2026-01-01", periods=len(up), freq="D")
    out = engine.run_scan({"INFY.NS": df}, "full")
    shorts = [s for s in out["signals"] if s["side"] == "short"]
    assert shorts, "downtrend should produce a short signal"


def test_ema_mode_cross_and_candles_held():
    df = _trend_df(drift=0.0, n=30).values.tolist()
    price = df[-1][3]
    for _ in range(60):
        o = price
        c = price + 1.0
        df.append([o, max(o, c) + 0.5, min(o, c) - 0.5, c, 10_000])
        price = c
    frame = pd.DataFrame(df, columns=["open", "high", "low", "close",
                                      "volume"])
    frame.index = pd.date_range("2026-01-01", periods=len(df), freq="D")
    out = engine.run_scan({"HDFC.NS": frame}, "ema")
    trades = [s for s in out["signals"] if s["side"] == "long"]
    assert trades, "cross above 30 must fire"
    t = trades[0]
    assert t["ema_fast"] > t["ema_slow"]
    assert t["candles_held"] >= 0


def test_rsi_mode_crosses():
    df = _trend_df(drift=-0.3, n=80)
    up = df.values.tolist()
    price = up[-1][3]
    for _ in range(40):
        o = price
        c = price + 1.0
        up.append([o, max(o, c) + 0.5, min(o, c) - 0.5, c, 10_000])
        price = c
    frame = pd.DataFrame(up, columns=["open", "high", "low", "close",
                                      "volume"])
    frame.index = pd.date_range("2026-01-01", periods=len(up), freq="D")
    out = engine.run_scan({"SBIN.NS": frame}, "rsi")
    assert out["signals"], "rsi 50-cross expected after the reversal"


def test_trailing_stop_exits_trade():
    # long uptrend then a violent drop must exit the trade
    rows = _trend_df(drift=1.0, n=90, noise=0.5).values.tolist()
    price = rows[-1][3]
    for _ in range(20):
        o = price
        c = price - 3.0
        rows.append([o, max(o, c) + 0.5, min(o, c) - 0.5, c, 10_000])
        price = c
    frame = pd.DataFrame(rows, columns=["open", "high", "low", "close",
                                        "volume"])
    frame.index = pd.date_range("2026-01-01", periods=len(rows), freq="D")
    trades = engine.scan_symbol("YES.NS", frame, "full")
    exited = [t for t in trades if t["status"] == "exited"]
    assert exited, "crash should stop out the long"
    assert all(t["exit_reason"] in ("trailing stop", "opposite cross")
               for t in exited)
    assert all(t["pnl_pct"] is not None for t in trades)


def test_run_scan_collects_failures_and_sorts():
    good = _trend_df(n=60)
    bad = pd.DataFrame({"open": [1], "high": [1]})  # no close -> raises
    bad.index = pd.date_range("2026-01-01", periods=1)
    out = engine.run_scan({"A.NS": good, "B.NS": bad}, "ema")
    assert out["scanned"] == 2 and "B.NS" in out["failed"]
    ts = [s["entry_ts"] for s in out["signals"]]
    assert ts == sorted(ts)
