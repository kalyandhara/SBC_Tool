"""Backlog fixes: B-11 vedha_daily, B-24 no fake bars, B-26 rate-limiter sweep, B-38 nakshatra names."""

import re
import time
from pathlib import Path

import app as app_module
from sbc import backtest as bt
from sbc import fingerprint as fpm
from sbc import market_ohlc
from sbc.api.blueprints import signals_bp
from sbc.nakshatra import NAKSHATRAS_27

ROOT = Path(__file__).resolve().parent.parent


# ── B-11 ───────────────────────────────────────────────────────────────────

def test_vedha_daily_uses_the_real_moon_nakshatra(client, monkeypatch):
    monkeypatch.setattr(signals_bp, "_heatmap_month_row", lambda month, row: {"2026-09-02": 1.5})
    rows = client.get("/api/vedha_daily?sector=Nifty%20Bank&start=2026-09-01&end=2026-09-03").get_json()
    assert [r["date"] for r in rows] == ["2026-09-01", "2026-09-02", "2026-09-03"]
    for r in rows:
        assert r["nakshatra_idx"] == fpm.fingerprint(r["date"])["planets"]["Moon"]["nakshatra"]
    assert rows[1]["score"] == 1.5 and rows[1]["source"] == "real"
    assert rows[0]["score"] is None and rows[0]["source"] == "missing"  # a gap is not a neutral 0


def test_vedha_daily_computes_only_the_months_in_range(client, monkeypatch):
    seen = []
    monkeypatch.setattr(signals_bp, "_heatmap_month_row", lambda month, row: seen.append(month) or {})
    client.get("/api/vedha_daily?sector=Nifty%20Bank&start=2026-08-20&end=2026-10-05")
    assert seen == ["2026-08-01", "2026-09-01", "2026-10-01"]
    assert client.get("/api/vedha_daily?start=2020-01-01&end=2026-01-01").status_code == 400


# ── B-24 ───────────────────────────────────────────────────────────────────

def test_no_fake_bar_generator():
    assert not hasattr(market_ohlc, "generate_sample_ohlc")
    assert not hasattr(market_ohlc, "ensure_week_cache")
    assert market_ohlc.DATA_DIR.is_absolute()


# ── B-26 ───────────────────────────────────────────────────────────────────

def test_rate_limiter_sweeps_idle_clients(client, monkeypatch):
    stale = time.time() - 120
    from sbc import app_factory
    table = app_factory._request_times
    table.clear()
    for i in range(app_factory._RATE_LIMIT_MAX_CLIENTS + 5):
        table[f"10.0.{i // 256}.{i % 256}"] = [stale]
    monkeypatch.setitem(app_module.app.config, "TESTING", False)
    client.get("/healthz")
    assert len(table) == 1  # only the live client remains
    table.clear()


# ── B-38 ───────────────────────────────────────────────────────────────────

def test_nakshatra_bullish_matches_engine_spelling():
    assert bt._nakshatra_bullish({"nakshatra": "U.Phalguni"})
    assert not bt._nakshatra_bullish({"nakshatra": "Uttara Phalguni"})  # the engine never emits this


def test_nadi_map_covers_every_engine_nakshatra():
    src = (ROOT / "sbc" / "api" / "engine_bp.py").read_text(encoding="utf-8")
    keys = set(re.findall(r'"([A-Za-z.]+)":"(?:Aadi|Madhya|Antya)"', src))
    assert keys == set(NAKSHATRAS_27)
