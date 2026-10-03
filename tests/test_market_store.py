"""market.db: daily bars, FII/DII flows, refresh windows and freshness."""

import datetime as dt

import pytest

from sbc import market_store as ms

IST = ms.IST


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(ms, "DB_PATH", tmp_path / "market.db")
    return ms


def _bar(day, close=100.0):
    return {"date": day, "open": close, "high": close + 1, "low": close - 1,
            "close": close, "volume": 10}


def test_upsert_skips_nan_and_replaces(store):
    nan = float("nan")
    assert store.upsert_daily("NIFTY", [_bar("2026-09-29"),
                                        {**_bar("2026-09-30"), "close": nan}], "t") == 1
    store.upsert_daily("NIFTY", [_bar("2026-09-29", close=200.0)], "t")
    rows = store.get_daily("NIFTY")
    assert [(r["date"], r["close"]) for r in rows] == [("2026-09-29", 200.0)]


def test_refresh_full_then_tail(store):
    calls = []

    def fetch(ticker, start, end):
        calls.append((ticker, start, end))
        return [_bar("2026-09-25"), _bar("2026-09-30"), _bar("2026-10-01")]

    after_close = dt.datetime(2026, 9, 30, 17, 0, tzinfo=IST)
    out = store.refresh_daily("NIFTY", now=after_close, fetch=fetch)
    # Empty store: full history from the symbol's earliest date; unsettled bar dropped.
    assert calls[0] == ("^NSEI", dt.date(1995, 1, 1), dt.date(2026, 9, 30))
    assert out["stored"] == 2
    store.refresh_daily("NIFTY", now=after_close, fetch=fetch)
    # Tail refresh re-reads the last 5 days so revised bars replace provisional ones.
    assert calls[1][1] == dt.date(2026, 9, 25)


def test_refresh_flows_parses_nse_payload(store):
    payload = [
        {"buyValue": "25420.04", "category": "DII", "date": "01-Oct-2026",
         "netValue": "10041.84", "sellValue": "15378.2"},
        {"buyValue": "12260.26", "category": "FII/FPI", "date": "01-Oct-2026",
         "netValue": "-9484.22", "sellValue": "21744.48"},
        {"category": "FII/FPI", "date": "bad", "netValue": "1"},
    ]
    out = store.refresh_flows(fetch=lambda: payload)
    assert out == {"stored": 2, "dates": ["2026-10-01"]}
    assert store.get_flows() == [{"date": "2026-10-01", "fii_net": -9484.22, "dii_net": 10041.84}]


def test_freshness_skips_holidays(store):
    for symbol in store.SYMBOLS:
        store.upsert_daily(symbol, [_bar("2026-10-01")], "t")
    store.refresh_flows(fetch=lambda: [
        {"category": "FII/FPI", "date": "01-Oct-2026", "netValue": "1"},
        {"category": "DII", "date": "01-Oct-2026", "netValue": "2"}])
    # 2026-10-02 is Gandhi Jayanti; on Saturday 3 Oct the last session is 1 Oct.
    fresh = store.freshness(now=dt.datetime(2026, 10, 3, 10, 0, tzinfo=IST))
    assert fresh["expected_last_session"] == "2026-10-01"
    assert fresh["stale"] is False
    late = store.freshness(now=dt.datetime(2026, 10, 5, 17, 0, tzinfo=IST))
    assert late["stale"] is True and late["series"]["NIFTY"]["stale"] is True


def test_refresh_all_reports_errors_without_raising(store, monkeypatch):
    def boom(*a, **k):
        raise ConnectionError("offline")
    monkeypatch.setattr(store, "refresh_daily", boom)
    monkeypatch.setattr(store, "_nse_fiidii", boom)
    report = store.refresh_all()
    assert len(report["errors"]) == len(store.SYMBOLS) + 1
    assert all("offline" not in e for e in report["errors"])


def test_freshness_endpoint(client):
    resp = client.get("/api/engine/market/freshness")
    assert resp.status_code == 200
    assert set(resp.get_json()["series"]) == {"NIFTY", "SENSEX", "INDIAVIX", "FII_DII"}
