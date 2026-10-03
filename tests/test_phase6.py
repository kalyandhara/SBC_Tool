"""Phase 6: candidate factors, their forecast wiring, and the sector out-of-sample test."""

import copy
import datetime as dt

import numpy as np
import pytest

from sbc import analogs as an
from sbc import factors as fx
from sbc import fingerprint as fpm
from sbc import forecast as fc
from sbc import market_store, research_reports
from sbc import sector_signals as ss
from sbc import sector_validation as sv

# ── factors ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def fp():
    return fpm.fingerprint("2026-10-05")


def test_declinations_are_physical():
    dec = fx.declinations("2026-10-05")
    assert set(dec) == {"Moon", "Mercury", "Venus", "Mars"}
    assert all(abs(v) < 29.0 for v in dec.values())


def test_graha_yuddha_and_node(fp):
    war = copy.deepcopy(fp)
    war["planets"]["Venus"]["longitude"] = war["planets"]["Mars"]["longitude"] + 0.4
    assert fx._graha_yuddha(war)
    near = copy.deepcopy(fp)
    near["planets"]["Moon"]["longitude"] = (near["planets"]["Ketu"]["longitude"] + 5) % 360
    assert fx._moon_with_node(near) == -1


def test_ingress_window_uses_calendar_neighbours(fp):
    nxt = copy.deepcopy(fp)
    nxt["planets"]["Mars"]["sign"] = (fp["planets"]["Mars"]["sign"] + 1) % 12
    days = {"2026-10-04": fp, "2026-10-06": nxt}
    signals = fx.signals_for([fp], days.get)
    assert signals["ingress_window"] == [True]
    assert fx.signals_for([fp], lambda d: fp)["ingress_window"] == [False]
    assert set(signals) == {f.name for f in fx.FACTORS}


# ── forecast wiring ────────────────────────────────────────────────────────

def _sessions(n, start):
    days = [start + dt.timedelta(days=i) for i in range(int(n * 1.6))]
    return [d.isoformat() for d in days if d.weekday() < 5][:n]


@pytest.fixture(scope="module")
def history():
    dates = _sessions(500, dt.date(2024, 9, 2))
    closes = 1000 * np.exp(np.cumsum(np.random.default_rng(5).normal(0.0003, 0.01, len(dates))))
    return an.History.build(dates, closes, [fpm.fingerprint(d) for d in dates])


def _next(history):
    from sbc.market_holidays import next_trading_day
    return next_trading_day(dt.date.fromisoformat(history.dates[-1]), inclusive=False).isoformat()


def test_factors_appear_as_unvalidated_components(history):
    f = fc.forecast(_next(history), 5, history=history)
    names = {c["name"] for c in f["components"] if c.get("source") == "factor"}
    assert names == {x.name for x in fx.FACTORS}
    assert f["validated"] == []


def test_a_factor_passing_both_tests_is_validated(history, monkeypatch):
    real = research_reports.result

    def fake(prefix, rule, horizon):
        if prefix == "factor_validation" and rule == "mercury_combust":
            return {"verdict": "edge", "_file": "x.json",
                    "beyond_market": {"verdict": "adds information", "beta": 0.001, "q": 0.01}}
        return real(prefix, rule, horizon)
    monkeypatch.setattr(research_reports, "result", fake)
    f = fc.forecast(_next(history), 5, history=history)
    comp = next(c for c in f["components"] if c["name"] == "mercury_combust")
    assert comp["validated"] and "mercury_combust" in f["validated"]
    assert comp["beyond_market"]["verdict"] == "adds information"


# ── sector out-of-sample test ──────────────────────────────────────────────

def test_findings_cover_the_catalogue_with_claimed_direction():
    rows = sv.findings()
    assert len(rows) == sum(1 for s in ss.SCENARIOS for f in s["findings"] if f["target"] in sv.TARGETS)
    assert all(r["direction"] == (1 if r["claimed_avg"] > 0 else -1) for r in rows)


def test_claim_returns_convention():
    level = np.array([100.0, 110.0, 121.0, 133.1])
    r = sv.claim_returns(level, 2)
    assert r[0] == pytest.approx(0.21) and np.isnan(r[2]) and np.isnan(r[3])


def test_series_baskets_and_neutralizes_splits(tmp_path, monkeypatch):
    monkeypatch.setattr(market_store, "DB_PATH", tmp_path / "m.db")
    monkeypatch.setitem(sv.TARGETS, "Test basket", ["AAA", "BBB"])
    bar = lambda d, c: {"date": d, "open": c, "high": c, "low": c, "close": c}  # noqa: E731
    market_store.upsert_daily("AAA", [bar("2020-01-01", 100), bar("2020-01-02", 110), bar("2020-01-03", 55)], "t")
    market_store.upsert_daily("BBB", [bar("2020-01-01", 50), bar("2020-01-02", 50), bar("2020-01-03", 50)], "t")
    dates, level, jumps = sv.series("Test basket")
    assert dates == ["2020-01-02", "2020-01-03"] and jumps == 1  # the 50% drop is a split
    assert level[0] == pytest.approx(1.05) and level[1] == pytest.approx(1.05)


def test_planted_effect_is_found_out_of_sample(monkeypatch):
    days = _sessions(4500, dt.date(2008, 1, 1))  # runs past FIT_START
    rng = np.random.default_rng(7)
    active_days = set(rng.choice(days, size=600, replace=False))
    rets = rng.normal(0, 0.01, len(days))
    for i, d in enumerate(days[:-1]):
        if d in active_days:
            rets[i + 1] += 0.01  # the day after an active day tends to rise
    level = np.cumprod(1 + rets)
    pair = ("Mars", "Jupiter")
    monkeypatch.setattr(sv, "findings", lambda: [
        {"pair": pair, "group": "g", "sector": "s", "target": "T", "h": 1, "claimed_avg": 0.01,
         "claimed_win": 0.6, "claimed_n": 50, "direction": 1}])
    monkeypatch.setattr(sv, "series", lambda t: (days, level, 0))
    monkeypatch.setattr(ss, "_active_pairs", lambda d: {pair} if d in active_days else set())
    monkeypatch.setitem(sv.TARGETS, "T", ["X"])
    report = sv.run(n_perm=200)
    r = report["results"][0]
    assert r["verdict"] == "edge" and r["replicates"]
