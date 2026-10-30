"""Sector rotation: event anchors, clusters, window returns, ranks, grading and labels."""

import pathlib

import numpy as np
import pytest

from sbc import sector_rotation as sr

SESSIONS = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-08"]  # 2024-01-06/07 weekend


def test_anchor_moves_weekend_to_next_session():
    assert sr.anchor_session(SESSIONS, "2024-01-06") == 3


def test_anchor_none_after_last_session():
    assert sr.anchor_session(SESSIONS, "2025-01-01") is None


def test_cluster_merges_within_gap():
    assert sr.cluster([0, 5, 30, 60], gap=20) == [[0, 5], [30], [60]]
    assert sr.cluster([0, 19], gap=20) == [[0, 19]]
    assert sr.cluster([0, 20], gap=20) == [[0], [20]]


def test_mercury_one_occurrence_per_retrograde_window():
    rows = [
        {"planet": "Mercury", "direction": "retrograde", "date": "2024-03-01"},
        {"planet": "Mercury", "direction": "direct", "date": "2024-03-25"},
        {"planet": "Venus", "direction": "retrograde", "date": "2024-04-01"},
    ]
    kept = sr.mercury_events(rows)
    assert [(e["event"], e["date"]) for e in kept] == [("MERCURY_RETROGRADE_START", "2024-03-01")]
    assert kept[0]["window_end"] == "2024-03-25"


def test_mercury_window_without_end_has_none():
    rows = [{"planet": "Mercury", "direction": "retrograde", "date": "2024-12-01"}]
    assert sr.mercury_events(rows)[0]["window_end"] is None


def test_core_events_2024_has_the_four_kinds():
    events = sr.core_events(2024, 2024)
    kinds = {e["event"] for e in events}
    assert {"MERCURY_RETROGRADE_START", "SOLAR_ECLIPSE", "LUNAR_ECLIPSE", "JUPITER_INGRESS"} <= kinds
    assert sum(e["event"] == "MERCURY_RETROGRADE_START" for e in events) == 3
    assert sum(e["event"] == "SOLAR_ECLIPSE" for e in events) == 2
    assert sum(e["event"] == "LUNAR_ECLIPSE" for e in events) == 2
    assert "NODES_INGRESS" not in kinds  # node ingresses are not a core event


def test_window_return_known_answer():
    c = np.array([100.0, 101.0, 102.0, 110.0])
    assert sr.window_return(c, anchor=0, h=3) == pytest.approx(0.10)


def test_window_return_out_of_range_is_nan():
    c = np.array([100.0, 101.0])
    assert np.isnan(sr.window_return(c, anchor=1, h=5))


def test_window_return_missing_bar_is_nan():
    c = np.array([100.0, np.nan, 102.0])
    assert np.isnan(sr.window_return(c, anchor=0, h=1))  # end bar missing
    assert sr.window_return(c, anchor=0, h=2) == pytest.approx(0.02)  # end bar present


def test_rank_excludes_nan_and_orders_descending():
    r = {"IT": 0.062, "PHARMA": 0.054, "AUTO": float("nan"), "BANK": 0.035}
    assert [s for s, _ in sr.rank_sectors(r)] == ["IT", "PHARMA", "BANK"]


def test_relative_strength_is_difference():
    assert sr.relative_strength(0.072, 0.023) == pytest.approx(0.049)


def _synthetic(n=1000, effect=0.02, in_effect=None, seed=0):
    """Random 20% signal days; fwd carries `effect` (OOS, last half) and `in_effect` (in-era).

    The signal is random, not periodic: a periodic signal lines up with itself under circular
    shifts that are multiples of its period, which inflates the null and hides the effect.
    """
    rng = np.random.default_rng(seed)
    days = np.arange(n)
    signal = (rng.random(n) < 0.2).astype(float)
    in_effect = effect if in_effect is None else in_effect
    shift = np.where(days >= n // 2, effect, in_effect)
    fwd = rng.normal(0, 0.01, n) + shift * signal
    clusters = days // 50  # 20 clusters of 50 sessions; OOS (last half) = 10 clusters
    era = days >= n // 2
    controls = rng.normal(size=(n, 2))
    return signal, fwd, clusters, era, controls


HYP = [{"id": "T", "event": "X", "sector": "IT", "h": 5, "direction": 1}]


def test_pass_when_effect_is_consistent_in_both_eras():
    signal, fwd, clusters, era, controls = _synthetic()
    res = sr.grade_confirmatory(HYP, {"T": signal}, {5: fwd}, era, clusters, controls)
    assert res[0]["status"] == "ok" and res[0]["passed"] is True


def test_no_pass_when_in_era_direction_opposes_oos():
    signal, fwd, clusters, era, controls = _synthetic(in_effect=-0.02)
    res = sr.grade_confirmatory(HYP, {"T": signal}, {5: fwd}, era, clusters, controls)
    assert res[0]["passed"] is False


def test_insufficient_below_eight_oos_clusters():
    signal, fwd, clusters, era, controls = _synthetic()
    clusters = np.arange(len(fwd)) // 100  # OOS covers 5 clusters
    res = sr.grade_confirmatory(HYP, {"T": signal}, {5: fwd}, era, clusters, controls)
    assert res[0]["status"] == "insufficient" and res[0]["passed"] is False


def test_confirmatory_list_matches_preregistration():
    root = pathlib.Path(__file__).resolve().parents[1]
    doc = (root / "docs/research/sector_rotation_preregistration_2026-10-29.md").read_text(encoding="utf-8")
    assert "Confirmatory list: empty" in doc
    assert sr.CONFIRMATORY == []


def test_descriptive_summary_has_no_pass_fields():
    rows = [{"sector": "IT", "event": "SOLAR_ECLIPSE", "h": 5, "ret": 0.01, "nifty": 0.0,
             "cluster": 0, "rank": 1}]
    out = sr.descriptive_summary(rows)
    assert not ({"q", "p", "passed"} & set(out))
    assert out["n_raw"] == 1 and out["n_clusters"] == 1


def test_insufficient_below_minimum_signal_days():
    signal, fwd, clusters, era, controls = _synthetic()
    signal = np.zeros_like(signal)
    signal[:10] = 1.0  # 10 signal days, below MIN_SIGNAL_DAYS
    res = sr.grade_confirmatory(HYP, {"T": signal}, {5: fwd}, era, clusters, controls)
    assert res[0]["status"] == "insufficient"


def test_rotation_pattern_majority():
    label, top5 = sr.rotation_pattern(["CNXFMCG", "CNXPHARMA", "CNXHEALTH", "CNXIT", "CNXAUTO"])
    assert label == "Defensive" and top5 == ["CNXFMCG", "CNXPHARMA", "CNXHEALTH", "CNXIT", "CNXAUTO"]


def test_rotation_pattern_tie_is_mixed():
    label, _ = sr.rotation_pattern(["CNXFMCG", "CNXIT"])
    assert label == "Mixed"


def test_rotation_pattern_uses_sector_keys_from_preregistration():
    # Pre-registration section "Rotation pattern labels" names the sectors; every one must map.
    from sbc import market_store as ms
    assert set(ms.SECTOR_SYMBOLS) == set(sr.GROUPS)


def test_confidence_no_call_by_default():
    assert sr.forecast_confidence({"passed": False}) == "No call"


def test_confidence_high_only_on_confirmatory_pass():
    assert sr.forecast_confidence({"passed": True}) == "High"


def test_no_medium_level_anywhere():
    outputs = {sr.forecast_confidence(r) for r in ({"passed": True}, {"passed": False}, {}, {"passed": None})}
    assert outputs <= {"High", "No call"}


def test_daily_returns_within_window():
    c = np.array([100.0, 110.0, 99.0, 99.0])
    r = sr.daily_returns(c, anchor=0, h=3)
    assert r[0] == pytest.approx(0.10) and r[1] == pytest.approx(-0.1) and r[2] == pytest.approx(0.0)


def test_daily_returns_nan_past_end_and_on_missing():
    c = np.array([100.0, np.nan, 102.0])
    r = sr.daily_returns(c, anchor=0, h=3)
    assert np.isnan(r[0]) and np.isnan(r[1]) and np.isnan(r[2])


def test_volatility_and_sharpe_need_two_finite_values():
    assert np.isnan(sr.volatility(np.array([0.01, np.nan])))
    assert np.isnan(sr.sharpe(np.array([0.01])))
    assert np.isnan(sr.sharpe(np.array([0.02, 0.02, 0.02])))  # zero std


def test_sharpe_is_mean_over_std_not_annualised():
    x = np.array([0.01, 0.03])
    assert sr.sharpe(x) == pytest.approx(0.02 / np.std(x, ddof=1))


def test_participation_is_share_of_available_positive_returns():
    assert sr.participation({"A": 0.01, "B": -0.02, "C": float("nan"), "D": 0.0}) == pytest.approx(1 / 3)
    assert sr.participation({"A": float("nan")}) is None


def test_heat_bucket_five_levels_from_z():
    assert [sr.heat_bucket(z) for z in (1.2, 0.5, 0.0, -0.5, -1.2)] == [
        "dark_green", "light_green", "yellow", "orange", "dark_red"]
    assert sr.heat_bucket(float("nan")) is None
