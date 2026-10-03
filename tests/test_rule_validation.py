"""Rule catalog (sbc.rule_signals) and the validation runner (sbc.rule_validation)."""

import datetime as dt

import numpy as np
import pytest

from sbc import fingerprint as fpm
from sbc import rule_signals as rs
from sbc import rule_validation as rv


@pytest.fixture(scope="module")
def week():
    days = [dt.date(2026, 9, 28) + dt.timedelta(days=i) for i in range(5)]
    return [fpm.fingerprint(d) for d in days]


def test_every_rule_returns_a_valid_signal(week):
    signals = rs.signals_for(week)
    assert set(signals) == {r.name for r in rs.RULES}
    for rule in rs.RULES:
        values = signals[rule.name]
        assert len(values) == len(week)
        allowed = {-1, 0, 1} if rule.kind == "directional" else {True, False}
        assert set(values) <= allowed, rule.name


def test_rule_names_are_unique():
    names = [r.name for r in rs.RULES]
    assert len(names) == len(set(names))


def test_placebos_are_deterministic(week):
    assert rs.signals_for(week)["placebo_daily"] == rs.signals_for(week)["placebo_daily"]


def test_run_grades_every_rule_and_horizon(monkeypatch):
    # Synthetic history: 800 sessions of fingerprints and a random-walk index.
    days = [dt.date(2019, 1, 1) + dt.timedelta(days=i) for i in range(800)]
    fps = [fpm.fingerprint(d) for d in days]
    closes = list(1000 * np.exp(np.cumsum(np.random.default_rng(0).normal(0, 0.01, 800))))
    monkeypatch.setattr(rv, "load_history",
                        lambda start=None, end=None: ([d.isoformat() for d in days], closes, fps))
    report = rv.run(horizons=(1, 5), n_perm=50)
    assert len(report["results"]) == 2 * len(rs.RULES)
    for r in report["results"]:
        assert r["verdict"] in {"edge", "inconsistent", "no edge", "insufficient"}
        assert set(r["eras"]) <= {"2007-2020", "2021-2026"}
    placebo = [r for r in report["results"] if r["rule"].startswith("placebo")]
    assert all(r["verdict"] != "edge" for r in placebo)


def test_verdict_needs_both_eras_to_agree():
    ok = {"status": "ok", "q": 0.01, "excess": 0.002}
    assert rv._verdict(ok, {"2007-2020": 0.003, "2021-2026": 0.001}) == "edge"
    assert rv._verdict(ok, {"2007-2020": 0.003, "2021-2026": -0.001}) == "inconsistent"
    assert rv._verdict({**ok, "q": 0.2}, {"2007-2020": 0.003}) == "no edge"
    assert rv._verdict({"status": "insufficient"}, {}) == "insufficient"
