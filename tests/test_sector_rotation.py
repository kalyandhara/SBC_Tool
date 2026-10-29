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


def test_core_events_spans_the_full_market_history():
    """The report covers 2007-2026; station lookups must stay within stations.between's limit."""
    events = sr.core_events(2007, 2026)
    mercury = [e for e in events if e["event"] == "MERCURY_RETROGRADE_START"]
    assert any(e["date"].startswith("2007") for e in mercury)
    assert any(e["date"].startswith("2026") for e in mercury)


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
    label, top5 = sr.rotation_pattern(["CNXFMCG", "CNXPHARMA", "CNXCONSUM", "CNXIT", "CNXAUTO"])
    assert label == "Defensive" and top5 == ["CNXFMCG", "CNXPHARMA", "CNXCONSUM", "CNXIT", "CNXAUTO"]


def test_rotation_pattern_tie_is_mixed():
    label, _ = sr.rotation_pattern(["CNXFMCG", "CNXIT"])
    assert label == "Mixed"


def test_rotation_pattern_uses_registered_sector_keys():
    # Every registered sector must have a rotation group; unavailable indices are excluded.
    from sbc import market_store as ms
    expected = {
        "CNXBANK", "CNXFIN", "CNXIT", "CNXPHARMA", "CNXAUTO", "CNXFMCG",
        "CNXMETAL", "CNXENERGY", "CNXREALTY", "CNXPSUBANK", "CNXINFRA", "CNXCONSUM",
    }
    assert set(ms.SECTOR_SYMBOLS) == expected
    assert set(ms.SECTOR_SYMBOLS) == set(sr.GROUPS)
    assert not set(ms.SECTOR_SYMBOLS) & {"CNXMEDIA", "CNXHEALTH", "CNXOILGAS"}


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


def test_upcoming_events_window_is_inclusive_and_sorted():
    events = [{"date": "2026-11-30", "event": "B"}, {"date": "2026-10-29", "event": "C"},
              {"date": "2026-11-01", "event": "A"}, {"date": "2026-10-28", "event": "PAST"},
              {"date": "2027-01-01", "event": "LATE"}]
    got = sr.upcoming_events(events, "2026-10-29", 33)  # window ends 2026-12-01
    assert [e["event"] for e in got] == ["C", "A", "B"]


def test_event_outlook_orders_strongest_then_weakest_and_trims():
    rows = [{"sector": s, "n_raw": 5, "n_clusters": 3, "mean_relative": v, "beat_rate": 0.5,
             "heat": "yellow", "volatility": 0.0, "sharpe": 0.0, "top5_rate": 0.0}
            for s, v in [("A", 0.03), ("B", 0.02), ("C", 0.01), ("D", -0.01)]]
    out = sr.event_outlook({"EV": {"5": rows}}, "EV", n=2)["5"]
    assert [r["sector"] for r in out["strongest"]] == ["A", "B"]
    assert [r["sector"] for r in out["weakest"]] == ["D", "C"]
    assert set(out["strongest"][0]) == {"sector", "n_raw", "n_clusters", "mean_relative", "beat_rate", "heat",
                                        "scorecard"}


def test_co_clusters_pairs_events_that_share_a_cluster():
    # Session indices (anchors) deliberately do not equal list positions.
    anchored = [{"event": "MERCURY_RETROGRADE_START", "anchor": 100}, {"event": "SOLAR_ECLIPSE", "anchor": 110},
                {"event": "SOLAR_ECLIPSE", "anchor": 140}, {"event": "LUNAR_ECLIPSE", "anchor": 300}]
    clusters = [[100, 110], [140], [300]]  # Mercury and the first eclipse share a cluster
    got = sr.co_clusters(anchored, clusters)
    assert got == {("MERCURY_RETROGRADE_START", "SOLAR_ECLIPSE"): [[100, 110]]}


def test_co_clusters_ignores_same_event_repeats():
    anchored = [{"event": "SOLAR_ECLIPSE", "anchor": 5}, {"event": "SOLAR_ECLIPSE", "anchor": 7}]
    assert sr.co_clusters(anchored, [[5, 7]]) == {}


def test_co_clusters_pair_key_is_sorted_and_stable():
    anchored = [{"event": "SOLAR_ECLIPSE", "anchor": 5}, {"event": "JUPITER_INGRESS", "anchor": 9}]
    assert list(sr.co_clusters(anchored, [[5, 9]])) == [("JUPITER_INGRESS", "SOLAR_ECLIPSE")]


def _event(**over):
    base = {"label": "Solar eclipse", "raw": 9, "clusters": 6, "window_end": None, "forecast": {"5": "No call"},
            "outlook": {"5": {
                "strongest": [{"sector": "CNXPHARMA", "mean_relative": 0.02, "n_clusters": 8}],
                "weakest": [{"sector": "CNXIT", "mean_relative": -0.01, "n_clusters": 7}]}}}
    return {**base, **over}


def test_plain_summary_names_strongest_and_weakest_with_signed_returns():
    lines = sr.plain_summary(_event(), 5)
    body = " ".join(lines)
    assert "strongest sector relative to NIFTY was Pharma (+2.00%" in body
    assert "weakest was IT (-1.00%" in body


def test_plain_summary_opens_with_counts_and_names_the_event():
    assert sr.plain_summary(_event(), 5)[0] == ("Solar eclipse: 9 past occurrences in 6 independent clusters. "
                                                "The pattern covers all past dates for this event.")


def test_plain_summary_flags_sectors_under_the_cluster_floor():
    lines = sr.plain_summary(_event(), 5)
    assert any(l.startswith("Thin samples") and "IT" in l for l in lines)
    assert not any("Pharma" in l for l in lines if l.startswith("Thin samples"))


def test_plain_summary_says_pattern_is_pooled_not_date_specific():
    # Two upcoming dates for one event share the same pooled statistics; the text must not imply otherwise.
    assert "pattern covers all past dates for this event" in sr.plain_summary(_event(), 5)[0]


def test_plain_summary_states_descriptive_limit_last():
    last = sr.plain_summary(_event(), 5)[-1]
    assert "Descriptive only" in last and "no pre-registered edge" in last and "Not trading advice" in last


def test_plain_summary_avoids_directional_or_advice_language():
    text = " ".join(sr.plain_summary(_event(), 5)).lower()
    for word in ("will ", "expect", "likely", "should", "buy", "sell", "outperform next", "recommend"):
        assert word not in text


def test_plain_summary_reports_forecast_from_report_not_hardcoded():
    lines = sr.plain_summary(_event(forecast={"5": "High"}), 5)
    assert "forecast set by the report" in lines[-1]


def test_plain_summary_mentions_mercury_window_end():
    lines = sr.plain_summary(_event(label="Mercury retrograde start", window_end="2027-03-03"), 5)
    assert "Window ends 2027-03-03." in lines[0]


def test_plain_summary_without_sector_data_says_so():
    lines = sr.plain_summary(_event(outlook={}), 5)
    assert lines[1] == "No sector data at T+5."


def test_event_outlook_empty_for_unknown_event():
    assert sr.event_outlook({}, "MISSING") == {}


def _row(heat, n_clusters=12, beat=0.6):
    return {"sector": "CNXIT", "n_raw": 30, "n_clusters": n_clusters, "mean_relative": 0.01,
            "beat_rate": beat, "heat": heat}


def test_scorecard_direction_follows_heat_bucket():
    got = {h: sr.edge_scorecard(_row(h))["direction"] for h in
           ("dark_green", "light_green", "yellow", "orange", "dark_red", None)}
    assert got == {"dark_green": "outperform", "light_green": "outperform", "yellow": "neutral",
                   "orange": "underperform", "dark_red": "underperform", None: "neutral"}


def test_scorecard_sample_is_thin_below_the_registered_cluster_floor():
    assert sr.edge_scorecard(_row("yellow", n_clusters=sr.MIN_CLUSTERS - 1))["sample"] == "thin"
    assert sr.edge_scorecard(_row("yellow", n_clusters=sr.MIN_CLUSTERS))["sample"] == "adequate"


def test_scorecard_validity_is_descriptive_unless_confirmed():
    card = sr.edge_scorecard(_row("dark_green"))
    assert card["validity"] == "Descriptive" and card["forecast"] == "No call"


def test_scorecard_high_only_when_confirmed():
    card = sr.edge_scorecard(_row("dark_green"), confirmed=True)
    assert card["validity"] == "Confirmed" and card["forecast"] == "High"


def test_scorecard_carries_counts_and_beat_rate_for_display():
    card = sr.edge_scorecard(_row("light_green", n_clusters=9, beat=0.58))
    assert card["clusters"] == 9 and card["beat_rate"] == pytest.approx(0.58)


def test_scorecard_has_no_medium_level():
    outputs = {sr.edge_scorecard(_row(h), confirmed=c)["forecast"]
               for h in ("dark_green", "yellow", None) for c in (True, False)}
    assert outputs == {"High", "No call"}


def test_event_outlook_rows_carry_a_scorecard():
    rows = [dict(_row("dark_green"), sector="CNXIT")]
    out = sr.event_outlook({"EV": {"5": rows}}, "EV", n=1)["5"]
    assert out["strongest"][0]["scorecard"]["validity"] == "Descriptive"


def test_heat_bucket_five_levels_from_z():
    assert [sr.heat_bucket(z) for z in (1.2, 0.5, 0.0, -0.5, -1.2)] == [
        "dark_green", "light_green", "yellow", "orange", "dark_red"]
    assert sr.heat_bucket(float("nan")) is None
