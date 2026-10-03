"""sbc.stats on synthetic data: finds a planted effect, ignores noise and drift."""

import numpy as np
import pytest

from sbc import stats as st


def test_forward_returns_align_with_prior_close():
    r = st.forward_returns([100, 110, 121, 133.1], 1)
    assert np.isnan(r[0])
    assert r[1:] == pytest.approx([0.10, 0.10, 0.10])
    r2 = st.forward_returns([100, 110, 121, 133.1], 2)
    assert r2[1] == pytest.approx(0.21) and np.isnan(r2[3])


def _market(n=3000, drift=0.0004, seed=1):
    rng = np.random.default_rng(seed)
    return rng.normal(drift, 0.01, n)


def test_detects_a_planted_effect():
    rng = np.random.default_rng(2)
    signal = rng.choice([-1, 1], size=3000)
    returns = _market() + 0.002 * signal
    res = st.evaluate_directional(signal, returns, n_perm=300)
    assert res["status"] == "ok"
    assert res["excess"] > 0.0015
    assert res["p"] < 0.01
    assert res["hit_rate"] > res["baseline"] + 0.05


def test_noise_is_not_significant():
    rng = np.random.default_rng(3)
    signal = rng.choice([-1, 1], size=3000)
    res = st.evaluate_directional(signal, _market(), n_perm=300)
    assert res["p"] > 0.05


def test_always_bullish_in_a_rising_market_is_not_an_edge():
    # A permanent bullish call earns the drift, not an edge: excess is ~0.
    res = st.evaluate_directional(np.ones(3000), _market(drift=0.001), n_perm=50)
    assert abs(res["excess"]) < 1e-12
    assert res["hit_rate"] == pytest.approx(res["baseline"])


def test_persistent_regime_signal_is_not_overstated():
    # Long +1/-1 blocks against a market with its own (independent) regimes.
    # An iid shuffle calls ~37% of these significant; circular shifts must stay
    # near the nominal 5%.
    rng = np.random.default_rng(7)
    trials, false_positives = 60, 0
    for trial in range(trials):
        signal = np.repeat(rng.choice([-1, 1], size=30), 100)
        offset = rng.integers(0, 137)
        trend = np.repeat(rng.normal(0, 0.002, 25), 137)[offset:offset + 3000]
        returns = rng.normal(0, 0.01, 3000) + trend
        if st.evaluate_directional(signal, returns, n_perm=200, seed=trial)["p"] < 0.05:
            false_positives += 1
    assert false_positives / trials <= 0.12


def test_insufficient_sample():
    signal = np.zeros(500)
    signal[:10] = 1
    assert st.evaluate_directional(signal, _market(500))["status"] == "insufficient"


def test_event_volatility():
    rng = np.random.default_rng(5)
    flag = rng.random(3000) < 0.15
    returns = rng.normal(0, 0.01, 3000) * np.where(flag, 1.8, 1.0)
    res = st.evaluate_event(flag, returns, n_perm=300)
    assert res["vol_ratio"] > 1.5 and res["p"] < 0.01
    calm = st.evaluate_event(flag, rng.normal(0, 0.01, 3000), n_perm=300)
    assert calm["p"] > 0.05


def test_bh_adjust_matches_reference():
    q = st.bh_adjust([0.01, 0.04, 0.03, 0.2, float("nan")])
    assert q[:4] == pytest.approx([0.04, 0.16 / 3, 0.16 / 3, 0.2])
    assert np.isnan(q[4])


def test_by_period_splits():
    signal = np.array([1, 1, 1, -1])
    fwd = np.array([0.01, 0.03, 0.02, -0.02])
    out = st.by_period(signal, fwd, ["a", "a", "b", "b"])
    assert out["a"] == pytest.approx(0.0)  # same call every day = the period's drift, no excess
    assert out["b"] == pytest.approx(0.02)
