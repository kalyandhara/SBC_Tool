"""Phase 4: market controls, incremental test, forecast contract and daily ledger."""

import datetime as dt
import json

import numpy as np
import pytest

from sbc import analogs as an
from sbc import daily_ledger, market_store, research_reports
from sbc import fingerprint as fpm
from sbc import forecast as fc
from sbc import incremental as inc
from sbc import market_features as mf

IST = market_store.IST


# ── market controls ────────────────────────────────────────────────────────

def _sessions(n=400, start=dt.date(2019, 1, 1)):
    days = [start + dt.timedelta(days=i) for i in range(int(n * 1.5))]
    return [d.isoformat() for d in days if d.weekday() < 5][:n]


def test_controls_use_only_past_closes():
    dates = _sessions()
    closes = 1000 * np.exp(np.cumsum(np.random.default_rng(0).normal(0, 0.01, len(dates))))
    vix = {d: 15.0 + i % 7 for i, d in enumerate(dates)}
    base = mf.controls(dates, closes, vix)
    changed = closes.copy()
    changed[300:] *= 1.5  # rewrite the future from session 300 on
    vix2 = {d: (99.0 if i >= 300 else v) for i, (d, v) in enumerate(vix.items())}
    after = mf.controls(dates, changed, vix2)
    np.testing.assert_array_equal(base[:301], after[:301])  # session 300 sees closes up to 299
    assert base.shape == (len(dates), len(mf.CONTROL_NAMES))


def test_turn_of_month_flags():
    days = [dt.date(2026, 9, d) for d in (1, 2, 3, 4, 28, 29, 30)] + [dt.date(2026, 10, 1)]
    flags = [mf._turn_of_month(days, i) for i in range(len(days))]
    assert flags == [True, True, True, False, False, True, True, True]


# ── incremental test ───────────────────────────────────────────────────────

def test_partial_effect_separates_echo_from_information():
    rng = np.random.default_rng(0)
    n = 3000
    x = rng.normal(size=(n, 3))
    y = 0.003 * x[:, 0] + rng.normal(0, 0.01, n)
    echo = np.sign(x[:, 0] + rng.normal(0, 0.5, n))
    real = rng.choice([-1, 1], n)
    echo_res = inc.partial_effect(echo, y, x, n_perm=300)
    assert abs(echo_res["beta_raw"]) > 10 * abs(echo_res["beta"]) and echo_res["p"] > 0.05
    real_res = inc.partial_effect(real, y + 0.002 * real, x, n_perm=300)
    assert real_res["p"] < 0.01 and real_res["beta"] == pytest.approx(0.002, abs=0.0005)


def test_controls_walk_forward_has_no_skill_on_noise():
    rng = np.random.default_rng(1)
    dates = _sessions(3000, dt.date(2008, 1, 1))
    res = inc.controls_walk_forward(dates, rng.normal(0, 0.01, 3000), rng.normal(size=(3000, 4)), 1)
    assert res["status"] == "ok" and res["oos_r2"] < 0.01


# ── forecast contract ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def history():
    dates = _sessions(700, dt.date(2023, 1, 2))
    closes = 1000 * np.exp(np.cumsum(np.random.default_rng(2).normal(0.0003, 0.01, len(dates))))
    return an.History.build(dates, closes, [fpm.fingerprint(d) for d in dates])


def _next_session(history):
    from sbc.market_holidays import next_trading_day
    return next_trading_day(dt.date.fromisoformat(history.dates[-1]), inclusive=False).isoformat()


def test_forecast_is_the_base_rate_without_validated_components(history):
    f = fc.forecast(_next_session(history), 5, history=history)
    assert f["validated"] == [] and f["probability_up"] == pytest.approx(f["base"]["up_share"], abs=1e-4)
    assert f["entry_date"] == history.dates[-1]
    assert {c["name"] for c in f["components"]} >= {"sbc_allthree", "bradley_sign", "analog_medium"}
    assert not any(c["name"].startswith("placebo") for c in f["components"])
    assert f["status"] == "research" and "not investment advice" in f["caveat"]
    q = f["expected_range"]["historical_quantiles"]
    assert q["5"] < q["50"] < q["95"]
    assert "band_68" not in f["expected_range"]  # the test market.db has no VIX


def test_vix_band():
    r = fc._range(20000.0, 5, 16.0, np.array([0.01, -0.01]))
    sigma = 0.16 / np.sqrt(252) * np.sqrt(5)
    assert r["band_68"] == [round(20000 * (1 - sigma), 1), round(20000 * (1 + sigma), 1)]
    assert r["band_95"][0] < r["band_68"][0] < r["band_68"][1] < r["band_95"][1]


def test_validated_component_moves_the_probability(history, monkeypatch):
    def fake(prefix, rule, horizon):
        if rule != "analog_fast":
            return None
        verdict = "edge" if prefix == "analog_validation" else "adds information"
        return {"verdict": verdict, "_file": "x.json", "_sample": {}}
    monkeypatch.setattr(research_reports, "result", fake)
    f = fc.forecast(_next_session(history), 5, history=history)
    comp = next(c for c in f["components"] if c["name"] == "analog_fast")
    assert f["validated"] == ["analog_fast"] and comp["validated"]
    expected = f["base"]["up_share"] + (comp["analog_up_share"] - comp["pool_up_share"]) if comp["lean"] else f["base"]["up_share"]
    assert f["probability_up"] == pytest.approx(expected, abs=1e-4)


def test_forecast_rejects_bad_input(history):
    with pytest.raises(ValueError):
        fc.forecast("2026-10-04", 5, history=history)  # Sunday
    with pytest.raises(ValueError):
        fc.forecast(_next_session(history), 3, history=history)


# ── daily ledger ───────────────────────────────────────────────────────────

@pytest.fixture
def ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(daily_ledger, "DB_PATH", tmp_path / "daily.db")
    monkeypatch.setattr(market_store, "DB_PATH", tmp_path / "market.db")
    return daily_ledger


def _fake_forecast(day, h):
    return {"model_version": "test", "probability_up": 0.6, "base": {"up_share": 0.55},
            "validated": [], "components": [{"name": "a", "lean": 1}, {"name": "b", "lean": -1},
                                             {"name": "c", "lean": 0}]}


def test_freeze_kinds_and_idempotence(ledger):
    day = dt.date(2026, 10, 5)
    early = dt.datetime(2026, 10, 5, 8, 0, tzinfo=IST)
    assert ledger.freeze(day, early, make=_fake_forecast) == [1, 5, 20]
    assert ledger.freeze(day, early, make=_fake_forecast) == []
    assert ledger.freeze(dt.date(2026, 10, 6), dt.datetime(2026, 10, 6, 10, 0, tzinfo=IST),
                         make=_fake_forecast) == [1, 5, 20]
    assert ledger.freeze(dt.date(2026, 10, 4), early, make=_fake_forecast) == []  # Sunday
    assert ledger.summary(1)["frozen"] == 1 and ledger.summary(1, "late")["frozen"] == 1


def test_scoring_waits_for_the_outcome_then_scores(ledger):
    day = dt.date(2026, 10, 5)
    ledger.freeze(day, dt.datetime(2026, 10, 5, 8, 0, tzinfo=IST), horizons=(1, 5), make=_fake_forecast)
    market_store.upsert_daily("NIFTY", [
        {"date": "2026-10-01", "open": 1, "high": 1, "low": 1, "close": 100.0},
        {"date": "2026-10-05", "open": 1, "high": 1, "low": 1, "close": 101.0}], "t")
    assert ledger.score_pending() == [("2026-10-05", 1)]  # the 5-session outcome isn't in yet
    s = ledger.summary(1)
    assert s["scored"] == 1 and s["brier"] == pytest.approx(0.16) and s["base_brier"] == pytest.approx(0.2025)
    assert s["components"] == {"a": {"n": 1, "hit_rate": 1.0}, "b": {"n": 1, "hit_rate": 0.0}}
    recent = ledger.recent(1)
    assert recent[0]["actual"] == pytest.approx(0.01)


# ── endpoints ──────────────────────────────────────────────────────────────

def test_forecast_endpoints(client, monkeypatch, history):
    monkeypatch.setattr(an, "load_nifty_history", lambda: history)
    body = client.get(f"/api/engine/forecast?date={_next_session(history)}&horizon=1").get_json()
    assert body["horizon"] == 1 and "probability_up" in body
    assert client.get("/api/engine/forecast?date=2026-10-04").status_code == 400
    assert client.get("/api/engine/forecast?horizon=x").status_code == 400
    ledger = client.get("/api/engine/forecast/ledger?horizon=5").get_json()
    assert ledger["summary"]["horizon"] == 5 and isinstance(ledger["recent"], list)
    assert client.get("/api/engine/forecast/ledger?horizon=7").status_code == 400
    json.dumps(body)  # strict-JSON serializable
