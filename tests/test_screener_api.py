"""Tests for /api/screener endpoints — offline, pipeline monkeypatched."""

import numpy as np
import pandas as pd
import pytest

from sbc.screener import data as sdata
from sbc.screener import universes


def _frame(days=140, base=100.0, drift=0.8):
    rng = np.random.default_rng(11)
    idx = pd.date_range("2026-01-01", periods=days, freq="D")
    rows, price = [], base
    for _ in range(days):
        o = price
        c = price + drift + rng.uniform(-0.3, 0.3)
        rows.append([o, max(o, c) + 0.5, min(o, c) - 0.5, c, 50_000])
        price = c
    return pd.DataFrame(rows, columns=["open", "high", "low", "close",
                                       "volume"], index=idx)


@pytest.fixture
def offline_scan(monkeypatch):
    monkeypatch.setattr(universes, "load",
                        lambda name, **kw: ["A.NS", "B.NS"])
    monkeypatch.setattr(sdata, "batch",
                        lambda symbols, timeframe, end=None,
                        lookback_days=None, as_ha=False:
                        ({s: _frame() for s in symbols}, {}))


def test_universes_endpoint(client):
    resp = client.get("/api/screener/universes")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "NIFTY 50" in body["universes"]
    assert "IT" in body["sectors"]
    assert "1d" in body["timeframes"] and "full" in body["modes"]


def test_scan_json_preview(client, offline_scan):
    resp = client.get(
        "/api/screener/scan?universe=NIFTY%2050&mode=full&timeframe=1d"
        "&end=2026-04-30&format=json")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["signals_total"] >= 1
    assert body["meta"]["universe"] == "NIFTY 50"
    assert body["meta"]["scan_date"] == "2026-04-30"
    first = body["signals"][0]
    assert {"symbol", "side", "entry", "status"} <= set(first)


def test_scan_xlsx_download(client, offline_scan):
    resp = client.get(
        "/api/screener/scan?universe=NIFTY%2050&mode=full&timeframe=1d"
        "&format=xlsx")
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.content_type
    assert resp.data[:2] == b"PK"


def test_scan_rejects_bad_mode(client, offline_scan):
    resp = client.get("/api/screener/scan?mode=wat")
    assert resp.status_code == 400
    assert "mode" in resp.get_json()["error"]


def test_scan_rejects_bad_date(client):
    resp = client.get("/api/screener/scan?universe=NIFTY%2050&end=nope")
    assert resp.status_code == 400


def test_scan_enforces_symbol_cap(client, offline_scan, monkeypatch):
    monkeypatch.setattr(universes, "load",
                        lambda name, **kw: [f"S{i}.NS"
                                            for i in range(150)])
    resp = client.get(
        "/api/screener/scan?universe=NIFTY%2050&timeframe=5m")
    assert resp.status_code == 400
    assert "cap" in resp.get_json()["error"]
