"""B-39: heliocentric aspect windows, swing exits, validation and endpoints."""

import datetime as dt

import numpy as np
import pytest
import swisseph as swe

from sbc import helio_aspects as ha
from sbc import swing_model as sm
from sbc import swing_validation as swv

# ── ENTRY layer ────────────────────────────────────────────────────────────

def test_earth_is_the_sun_plus_180():
    jd = swe.julday(2026, 10, 3, 0.0)
    sun = swe.calc_ut(jd, swe.SUN, swe.FLG_MOSEPH)[0][0]
    assert ha.helio_longitude(swe.EARTH, jd) == pytest.approx((sun + 180) % 360, abs=1e-3)


def test_jupiter_opposition_2026_is_a_helio_conjunction():
    # Jupiter's geocentric opposition fell on 10 Jan 2026: Earth and Jupiter in line with the Sun.
    w = ha.scan("2026-01-01", "2026-01-31", planets=["Jupiter"], aspects=["CONJ"])
    assert len(w) == 1
    win = w[0]
    assert win["exact_date"] == "2026-01-10" and win["min_orb"] < 0.05
    assert win["entry_date"] < win["exact_date"] < win["exit_date"]
    assert win["pair"] == "Earth-Jupiter" and win["aspect_name"] == "Conjunction"


def test_window_edges_sit_on_the_orb():
    w = ha.scan("2026-01-01", "2026-03-31", planets=["Mars"], aspects=["OPP"])[0]
    t = dt.datetime.fromisoformat(f"{w['entry_date']}T{w['entry_time']}").replace(tzinfo=ha.IST)
    assert abs(abs(ha.separation("Mars", ha._jd(t)) - 180) - ha.ORB) < 0.01


def test_tv_payload_and_filters():
    w = ha.scan("2026-01-01", "2026-12-31", planets=["Jupiter"], aspects=["SS"])
    p = ha.tv_payload(w)
    assert p == {"dates": sorted(p["dates"]), "label": "SS", "skip_holidays": False}
    assert len(p["dates"]) == len(w) and all(len(d) == 10 for d in p["dates"])
    with pytest.raises(ValueError):
        ha.scan("2026-01-01", "2026-02-01", planets=["Moon"])
    assert any(a["planet"] == "Jupiter" and a["aspect"] == "CONJ" for a in ha.active_on("2026-01-10"))


# ── EXIT layer ─────────────────────────────────────────────────────────────

def _bars(closes, start=dt.date(2020, 1, 1), volume=0):
    days = [start + dt.timedelta(days=i) for i in range(len(closes) * 2)]
    days = [d.isoformat() for d in days if d.weekday() < 5][:len(closes)]
    return sm.Bars([{"date": d, "open": c, "high": c * 1.005, "low": c * 0.995, "close": c, "volume": volume}
                    for d, c in zip(days, closes, strict=True)])


def test_indicators():
    up = np.linspace(100, 200, 50)
    assert sm.rsi(up)[-1] == pytest.approx(100.0)
    assert np.isnan(sm.rsi(up)[:14]).all()
    e = sm.ema(np.array([1.0, 1.0, 1.0, 4.0]), 3)
    assert e[-1] == pytest.approx(2.5)
    b = _bars(list(up))
    assert np.nanmin(b.atr) > 0


def test_direction_reverses_the_prior_trend():
    b = _bars(list(np.linspace(200, 100, 40)))
    assert sm.direction_at(b, 30) == 1 and sm.direction_at(b, 5) == 0


def test_confluence_needs_layers_together():
    events = {"gann": {11: ["x"]}, "fib": {12: ["y"]}, "indicator": {20: ["z"]}}
    assert sm.confluence_exit(events, 10, 30, need=3) is None
    assert sm.confluence_exit(events, 10, 30, need=2) == 12
    events["indicator"][13] = ["w"]
    assert sm.confluence_exit(events, 10, 30, need=3) == 13


def test_trade_exits_and_marks_open_trades():
    closes = list(np.linspace(200, 100, 30)) + list(np.linspace(100, 160, 70))
    b = _bars(closes)
    t = sm.trade(b, 29, 1, "hold", hold=10)
    assert t["bars"] == 10 and t["return"] > 0 and t["exit_reason"] == "hold"
    c = sm.trade(b, 29, 1, "confluence")
    assert c["exit_reason"] in ("confluence", "timeout") and c["bars"] <= sm.MAX_HOLD
    late = sm.trade(b, 90, 1, "confluence")
    assert late["exit_reason"] in ("open", "confluence")
    for rule in ("ema20", "atr_stop"):
        assert sm.trade(b, 29, 1, rule)["bars"] >= 1
    with pytest.raises(ValueError):
        sm.trade(b, 29, 1, "magic")


def test_entry_after_the_close_counts_from_the_next_session():
    b = _bars(list(np.linspace(100, 120, 20)))
    w = {"entry_date": b.dates[3], "entry_time": "16:00"}
    assert sm.entry_session(b, w) == 4
    assert sm.entry_session(b, {**w, "entry_time": "10:00"}) == 3


def test_one_position_at_a_time():
    b = _bars(list(np.linspace(200, 100, 40)) + list(np.linspace(100, 150, 100)))
    win = lambda d: {"entry_date": d, "entry_time": "10:00", "exact_date": d, "exact_time": "12:00",  # noqa: E731
                     "exit_date": d, "exit_time": "14:00", "pair": "Earth-Mars", "aspect": "SQ",
                     "aspect_name": "Square", "starts_before_range": False}
    swings = sm.swing_windows([win(b.dates[39]), win(b.dates[41])], b, need=3)
    assert len(swings) == 1 or swings[1]["entry_session"] > swings[0]["exit_session"]


# ── validation ─────────────────────────────────────────────────────────────

def test_reversal_uses_only_past_closes():
    c = np.array([float(x) for x in range(1, 30)])
    r = swv.reversal(c)
    assert (r[:sm.TREND_BARS + 1] == 0).all() and (r[sm.TREND_BARS + 1:] == -1).all()
    c2 = c.copy()
    c2[20:] = 0.5  # rewriting the future must not change earlier signals
    assert (swv.reversal(c2)[:21] == r[:21]).all()


def test_part_b_compares_with_random_entries(monkeypatch):
    rng = np.random.default_rng(1)
    closes = list(1000 * np.exp(np.cumsum(rng.normal(0, 0.01, 900))))
    b = _bars(closes, start=dt.date(2008, 1, 1))
    picks = [b.dates[i] for i in range(40, 800, 15)]
    monkeypatch.setattr(ha, "scan", lambda *a, **k: [
        {"entry_date": d, "entry_time": "10:00", "exact_date": d, "exact_time": "11:00", "exit_date": d,
         "exit_time": "12:00", "pair": "Earth-Mars", "aspect": "SQ", "aspect_name": "Square",
         "starts_before_range": False} for d in picks])
    out = swv.part_b(b, n_sets=20)
    strict = out["models"]["strict (3 of 3)"]
    assert strict["model"]["n"] > 0 and set(strict["baselines"]) >= {"hold 10", "EMA20 break", "2xATR trailing stop"}
    assert 0 < strict["random"]["p_value"] <= 1 and strict["verdict"] in (
        "timing adds value", "no better than random entries", "insufficient")


# ── endpoints and forecast ─────────────────────────────────────────────────

def test_endpoints(client, monkeypatch):
    tv = client.get("/api/engine/aspect_windows?start=2026-01-01&end=2026-12-31&planet=Jupiter&aspect=SS&format=tv")
    assert tv.status_code == 200 and tv.get_json()["label"] == "SS"
    full = client.get("/api/engine/aspect_windows?start=2026-01-01&end=2026-02-01&planet=Jupiter").get_json()
    assert full["count"] == len(full["windows"])
    assert client.get("/api/engine/aspect_windows?planet=Moon").status_code == 400
    assert client.get("/api/engine/aspect_windows?start=2010-01-01&end=2026-01-01").status_code == 400

    rng = np.random.default_rng(2)
    bars = _bars(list(1000 * np.exp(np.cumsum(rng.normal(0, 0.01, 400)))), start=dt.date(2025, 1, 1))
    monkeypatch.setattr(sm.Bars, "nifty", classmethod(lambda cls, *a, **k: bars))
    body = client.get("/api/engine/swing_windows?start=2025-01-01&end=2026-06-30&confluence=2").get_json()
    assert body["need"] == 2 and body["entries"]["skip_holidays"] is False and body["bars"]
    assert client.get("/api/engine/swing_windows?confluence=4").status_code == 400


def test_forecast_carries_the_helio_component():
    from sbc import analogs as an
    from sbc import fingerprint as fpm
    from sbc import forecast as fc
    from sbc.market_holidays import next_trading_day
    days = [dt.date(2024, 9, 2) + dt.timedelta(days=i) for i in range(800)]
    dates = [d.isoformat() for d in days if d.weekday() < 5][:500]
    closes = 1000 * np.exp(np.cumsum(np.random.default_rng(3).normal(0, 0.01, len(dates))))
    history = an.History.build(dates, closes, [fpm.fingerprint(d) for d in dates])
    day = next_trading_day(dt.date.fromisoformat(dates[-1]), inclusive=False).isoformat()
    comp = next(c for c in fc.forecast(day, 5, history=history)["components"] if c["name"] == "helio_all_reversal")
    assert comp["source"] == "helio" and comp["lean"] in (-1, 0, 1) and not comp["validated"]
    assert (comp["lean"] == 0) == (not comp["windows"])
