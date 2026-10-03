"""OHLC cache: correct path, no NaN bars, only settled bars persisted."""

import datetime
import math
import sys
import types

import pandas as pd
import pytest

from sbc import market_data as m


def _fake_yf(frame):
    mod = types.ModuleType("yfinance")
    mod.calls = []

    def download(ticker, start, end, **kw):
        mod.calls.append((ticker, start, end))
        return frame.copy()
    mod.download = download
    return mod


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(m, "_last_fetch", {})
    monkeypatch.setattr(m, "_vendor_first", {})
    return tmp_path


def _cache(path, rows):
    pd.DataFrame(rows, columns=["Date", "Open", "High", "Low", "Close", "Volume"]).to_csv(path, index=False)


def test_reads_cache_from_data_dir_without_network(data_dir, monkeypatch):
    today = datetime.date.today()
    rows = [((today - datetime.timedelta(days=i)).isoformat(), 10, 11, 9, 10.5, 100) for i in range(5, -1, -1)]
    _cache(data_dir / "nifty_ohlc.csv", rows)
    yf = _fake_yf(pd.DataFrame())
    monkeypatch.setitem(sys.modules, "yfinance", yf)
    out = m.get_nifty_ohlc((today - datetime.timedelta(days=5)).isoformat(), today.isoformat())
    assert len(out) == 6 and yf.calls == []


def test_running_session_nan_bar_dropped_and_not_cached(data_dir, monkeypatch):
    settled = datetime.date(2026, 9, 30)
    monkeypatch.setattr(m, "_settled_date", lambda now=None: settled)
    _cache(data_dir / "nifty_ohlc.csv", [("2026-09-28", 1, 2, 0.5, 1.5, 10)])
    idx = pd.to_datetime(["2026-09-29", "2026-09-30", "2026-10-01"])
    idx.name = "Date"
    frame = pd.DataFrame({"Open": [1, 2, 3], "High": [2, 3, 4], "Low": [0, 1, 2],
                          "Close": [1.5, 2.5, float("nan")], "Volume": [5, 6, 0]}, index=idx)
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf(frame))
    out = m.get_nifty_ohlc("2026-09-28", "2026-10-01")
    assert [r["time"] for r in out] == ["2026-09-28", "2026-09-29", "2026-09-30"]
    assert not any(isinstance(v, float) and math.isnan(v) for r in out for v in r.values())
    saved = pd.read_csv(data_dir / "nifty_ohlc.csv")
    assert saved["Date"].tolist() == ["2026-09-28", "2026-09-29", "2026-09-30"]


def test_unsettled_bar_with_values_not_persisted(data_dir, monkeypatch):
    monkeypatch.setattr(m, "_settled_date", lambda now=None: datetime.date(2026, 9, 30))
    _cache(data_dir / "nifty_ohlc.csv", [("2026-09-29", 1, 2, 0.5, 1.5, 10)])
    idx = pd.to_datetime(["2026-09-30", "2026-10-01"])
    idx.name = "Date"
    frame = pd.DataFrame({"Open": [1, 3], "High": [2, 4], "Low": [0, 2],
                          "Close": [1.5, 3.5], "Volume": [5, 1]}, index=idx)
    monkeypatch.setitem(sys.modules, "yfinance", _fake_yf(frame))
    m.get_nifty_ohlc("2026-09-29", "2026-10-01")
    saved = pd.read_csv(data_dir / "nifty_ohlc.csv")
    assert saved["Date"].max() == "2026-09-30"


def test_refetch_cooldown(data_dir, monkeypatch):
    # Friday bar cached, asked on Sunday: the "missing" weekend bar never comes.
    monkeypatch.setattr(m, "_settled_date", lambda now=None: datetime.date(2026, 9, 27))
    _cache(data_dir / "nifty_ohlc.csv", [("2026-09-25", 1, 2, 0.5, 1.5, 10)])
    yf = _fake_yf(pd.DataFrame())
    monkeypatch.setitem(sys.modules, "yfinance", yf)
    m.get_nifty_ohlc("2026-09-25", "2026-09-27")
    m.get_nifty_ohlc("2026-09-25", "2026-09-27")
    assert len(yf.calls) == 1


def _frame(dates):
    idx = pd.to_datetime(dates)
    idx.name = "Date"
    n = len(dates)
    return pd.DataFrame({"Open": [1] * n, "High": [2] * n, "Low": [0] * n,
                         "Close": [1.5] * n, "Volume": [5] * n}, index=idx)


def test_missing_head_is_backfilled(data_dir, monkeypatch):
    # Cache holds only recent bars; a request from earlier must fetch the head,
    # not just the tail (this is how nifty_ohlc.csv got stuck at 2 years).
    monkeypatch.setattr(m, "_settled_date", lambda now=None: datetime.date(2026, 9, 30))
    _cache(data_dir / "nifty_ohlc.csv", [("2026-09-29", 1, 2, 0.5, 1.5, 10),
                                         ("2026-09-30", 1, 2, 0.5, 1.5, 10)])
    yf = _fake_yf(_frame(["2026-09-24", "2026-09-25", "2026-09-29", "2026-09-30"]))
    monkeypatch.setitem(sys.modules, "yfinance", yf)
    out = m.get_nifty_ohlc("2026-09-24", "2026-09-30")
    assert yf.calls[0][1] == "2026-09-24"
    assert [r["time"] for r in out] == ["2026-09-24", "2026-09-25", "2026-09-29", "2026-09-30"]


def test_head_before_vendor_history_not_refetched(data_dir, monkeypatch):
    # ^NSEI starts in 2007; asking for 2000 must not re-download every time.
    monkeypatch.setattr(m, "_settled_date", lambda now=None: datetime.date(2026, 9, 30))
    monkeypatch.setattr(m, "_REFETCH_COOLDOWN_S", 0)
    yf = _fake_yf(_frame(["2007-09-17", "2026-09-30"]))
    monkeypatch.setitem(sys.modules, "yfinance", yf)
    m.get_nifty_ohlc("2000-01-01", "2026-09-30")
    m.get_nifty_ohlc("2000-01-01", "2026-09-30")
    assert len(yf.calls) == 1


def test_settled_date_cutoff():
    ist = m._IST
    assert m._settled_date(datetime.datetime(2026, 10, 1, 15, 0, tzinfo=ist)) == datetime.date(2026, 9, 30)
    assert m._settled_date(datetime.datetime(2026, 10, 1, 16, 5, tzinfo=ist)) == datetime.date(2026, 10, 1)


def test_nifty_chart_is_strict_json(client, monkeypatch):
    import json
    monkeypatch.setattr(m, "get_nifty_ohlc", lambda s=None, e=None: [
        {"time": "2026-09-30", "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 1}])
    text = client.get("/api/nifty_chart?start=2026-09-01&end=2026-10-01").get_data(as_text=True)
    json.loads(text, parse_constant=lambda c: pytest.fail(f"non-JSON constant {c}"))
