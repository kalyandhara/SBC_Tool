"""Tests for sbc.screener.data — offline, yfinance monkeypatched."""

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from sbc.screener import data


def _frame(days, base=100.0):
    idx = pd.DatetimeIndex([pd.Timestamp("2026-01-01") + pd.Timedelta(days=d)
                            for d in range(days)])
    close = base + np.arange(days, dtype=float)
    return pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1,
                         "Close": close, "Volume": [1000] * days}, index=idx)


def test_clamp_window_daily_unclamped():
    end = dt.date(2026, 3, 31)
    start, clipped, lookback = data.clamp_window("1d", end, 30)
    assert start == end - dt.timedelta(days=30)
    assert clipped == end and lookback == 30


def test_clamp_window_intraday_respects_60_day_limit():
    end = dt.date.today()
    start, clipped, lookback = data.clamp_window("5m", end, 400)
    assert lookback == 59  # max_days - 1
    assert (clipped - start).days == 59


def test_clamp_window_1h_seven_month_limit():
    end = dt.date.today()
    _, _, lookback = data.clamp_window("1h", end, 2000)
    assert lookback == 729


def test_clamp_window_rejects_unknown():
    with pytest.raises(data.TimeframeError):
        data.clamp_window("2m", dt.date(2026, 1, 1), 10)


def test_history_clips_bars_after_end(monkeypatch):
    captured = {}

    def fake_many(symbols, interval, start, end_exclusive):
        captured["end_exclusive"] = end_exclusive
        return {symbols[0]: _frame(40)}

    monkeypatch.setattr(data, "_download_many", fake_many)
    df = data.history("TCS.NS", "1d", end=dt.date(2026, 1, 15),
                      lookback_days=50)
    assert df.index.max() <= pd.Timestamp("2026-01-16")
    assert captured["end_exclusive"] == dt.date(2026, 1, 16)


def test_history_empty_when_vendor_returns_nothing(monkeypatch):
    monkeypatch.setattr(data, "_download_many",
                        lambda s, i, a, b: {})
    assert data.history("X.NS", "1d", end=dt.date(2026, 1, 15)).empty


def test_batch_collects_errors_and_clips(monkeypatch):
    def fake_many(symbols, interval, start, end_exclusive):
        return {symbols[0]: _frame(10), symbols[1]: pd.DataFrame()}

    monkeypatch.setattr(data, "_download_many", fake_many)
    out, errors = data.batch(["A.NS", "B.NS"], "1d",
                             end=dt.date(2026, 1, 10),
                             lookback_days=50)
    assert "A.NS" in out and "B.NS" not in out
    assert errors["B.NS"] == "no data returned"
    assert out["A.NS"].index.max() <= pd.Timestamp("2026-01-11")


def test_batch_empty_list_raises():
    with pytest.raises(ValueError, match="empty symbol list"):
        data.batch([], "1d")


def test_batch_heikin_ashi_transform(monkeypatch):
    monkeypatch.setattr(data, "_download_many",
                        lambda s, i, a, b: {s[0]: _frame(5)})
    out, _ = data.batch(["A.NS"], "1d", end=dt.date(2026, 1, 10),
                        as_ha=True)
    # HA close is the mean of the four original OHLC values
    raw = _frame(5)
    expected = raw[["Open", "High", "Low", "Close"]].mean(axis=1)
    assert np.allclose(out["A.NS"]["close"].values, expected.values)
