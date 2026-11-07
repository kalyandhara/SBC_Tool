"""Backtest mechanics. Prices here are synthetic or the frozen fixture, used for
structure and determinism only: no assertion depends on market outcomes."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sbc.navigator import backtest as B
from sbc.navigator import scoring as S
from sbc.navigator.ephemeris import build_sky
from sbc.navigator.profile import Profile, SAMPLE_PROFILE

FIXTURES = Path(__file__).parent / "fixtures"
HP = "High Probability"
FAST = {"n_placebo": 3, "seed": 7, "min_sessions": 120, "n_perm": 50}


def strip_seconds(placebo):
    return {k: v for k, v in placebo.items() if k != "seconds"}


def blocky_scores(n, rng):
    """Scores that sit in Normal or High Probability for runs of a few days."""
    states = np.repeat(rng.choice([50, 70], size=n // 3 + 1), 3)[:n]
    return states + rng.integers(-5, 6, n)


def planted(seed, lift=.005):
    rng = np.random.default_rng(seed)
    scores = blocky_scores(2500, rng)
    returns = rng.normal(0, .01, 2500)
    returns[(scores > 60) & (scores <= 80)] += lift
    return scores, returns


def noise(seed):
    rng = np.random.default_rng(seed)
    return blocky_scores(2500, rng), rng.normal(0, .01, 2500)


@pytest.fixture(scope="module")
def sample_inputs():
    ohlc = pd.read_csv(FIXTURES / "navigator_nifty_sample.csv", index_col="date")
    vix = pd.read_csv(FIXTURES / "navigator_vix_sample.csv", index_col="date")["close"].to_dict()
    return B.Inputs(SAMPLE_PROFILE, ohlc, vix, build_sky(list(ohlc.index)))


# --- forward_returns fix ----------------------------------------------------

@pytest.mark.parametrize("n,horizon", [(0, 1), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5)])
def test_short_series_forward_returns_are_all_nan(n, horizon):
    out = S.forward_returns(np.ones(n), np.ones(n), horizon)
    assert len(out) == n and np.isnan(out).all()


def test_forward_returns_exact_length_has_one_value():
    out = S.forward_returns([100, 1, 1, 1, 1], [1, 1, 1, 1, 110], 5)
    assert out[0] == pytest.approx(.10) and np.isnan(out[1:]).all()


# --- helpers ----------------------------------------------------------------

def test_events_collapse_runs():
    assert B.count_events(np.array([0, 1, 1, 0, 1, 1, 1, 0], bool)) == 2
    assert B.count_events(np.array([1, 1], bool)) == 1
    assert B.count_events(np.array([], bool)) == 0


def test_cost_applied():
    assert B.net(np.array([.01]), cost_bps=10)[0] == pytest.approx(.009)


def test_decile_control_matches_prior_return_decile():
    prior = np.arange(100.0)
    mask = np.zeros(100, bool)
    mask[95:] = True
    fwd = np.zeros(100)
    fwd[90:95] = 1
    assert B.matched_control_mean(mask, prior, fwd) == pytest.approx(1.0)


def test_control_ignores_nan_prior_and_nan_forward():
    """np.digitize puts NaN in the top decile, and one NaN would poison a mean."""
    prior = np.arange(100.0)
    prior[:5] = np.nan
    mask = np.zeros(100, bool)
    mask[95:] = True
    fwd = np.zeros(100)
    fwd[80:95] = 1
    fwd[:5] = 50.0      # would drag the mean if NaN priors joined the top decile
    fwd[93] = np.nan
    assert B.matched_control_mean(mask, prior, fwd) == pytest.approx(1.0)


def test_control_with_nothing_usable_is_nan():
    assert np.isnan(B.matched_control_mean(np.ones(5, bool), np.arange(5.0), np.zeros(5)))


GOOD = dict(q=.05, beats_control=True, natal_pct=96, events=40, fold_pos=.7, natal_band_days=40)


def test_verdict_rules():
    assert B.verdict(GOOD, is_sample=False) == "edge candidate"
    assert B.verdict(GOOD, is_sample=True) == "no demonstrated edge"
    for k, v in [("q", .2), ("beats_control", False), ("natal_pct", 90), ("events", 20),
                 ("fold_pos", .5), ("q", float("nan")), ("q", None), ("natal_pct", None),
                 ("fold_pos", None), ("natal_band_days", 29), ("natal_band_days", None)]:
        assert B.verdict({**GOOD, k: v}, False) == "no demonstrated edge", (k, v)


@pytest.mark.parametrize("k,v,want", [
    ("q", .0999, "edge candidate"), ("q", .10, "no demonstrated edge"),
    ("natal_pct", 95, "edge candidate"), ("natal_pct", 94.9, "no demonstrated edge"),
    ("events", 30, "edge candidate"), ("events", 29, "no demonstrated edge"),
    ("fold_pos", .60, "edge candidate"), ("fold_pos", .59, "no demonstrated edge"),
    ("natal_band_days", 30, "edge candidate"), ("natal_band_days", 29, "no demonstrated edge")])
def test_verdict_boundaries(k, v, want):
    assert B.verdict({**GOOD, k: v}, False) == want


def test_percentile_needs_enough_placebos():
    assert B.percentile(5.0, np.arange(100.0)) == 5.0
    assert B.percentile(5.0, np.arange(19.0)) is None
    assert B.percentile(float("nan"), np.arange(100.0)) is None
    assert B.percentile(5.0, np.full(100, np.nan)) is None


def test_open_returns_and_prior_timing():
    o = np.array([100.0, 110, 121, 133.1])
    c = np.array([105.0, 115.5, 127.05, 140.0])
    assert B.open_returns(o, 1)[0] == pytest.approx(.10)
    assert B.open_returns(o, 3)[0] == pytest.approx(.331)
    assert np.isnan(B.open_returns(o, 3)[1:]).all()
    assert np.isnan(B.open_returns(o, 9)).all()
    prior = B.prior_returns(c)
    assert np.isnan(prior[:2]).all()
    assert prior[2] == pytest.approx(.10)      # T-1 session vs T-2, nothing from T


# --- band_stats -------------------------------------------------------------

def test_events_counted_per_band():
    scores = np.array([50, 50, 70, 70, 50, 70, 10, 10])
    out = B.band_stats(scores, np.zeros(8), n_perm=10)
    assert out[HP]["days"] == 3 and out[HP]["events"] == 2
    assert out["Normal"]["days"] == 3 and out["Normal"]["events"] == 2
    assert out["No Trading"]["events"] == 1
    assert out["Exceptional Setup"]["days"] == 0
    assert all(out[b]["insufficient"] for b in out)


def test_band_stats_metrics_are_net_of_cost():
    scores = np.array([70] * 200 + [50] * 200)
    ret = np.array([.01, -.01] * 100 + [0.0] * 200)
    gross = B.band_stats(scores, ret, cost_bps=0, n_perm=10)[HP]
    costed = B.band_stats(scores, ret, cost_bps=10, n_perm=10)[HP]
    assert gross["mean"] - costed["mean"] == pytest.approx(.001)
    assert gross["excess"] - costed["excess"] == pytest.approx(.001)


def test_max_drawdown_on_cumulative_in_band_curve():
    scores = np.array([70, 70, 50, 70, 70])
    ret = np.array([.10, -.20, 5.0, -.10, .50])
    out = B.band_stats(scores, ret, cost_bps=0, n_perm=10)[HP]
    assert out["max_dd"] == pytest.approx(.8 * .9 - 1)
    in_band = ret[[0, 1, 3, 4]]
    assert out["sharpe"] == pytest.approx(in_band.mean() / in_band.std() * np.sqrt(252))
    assert out["hit"] == pytest.approx(.5)
    assert out["win"] == pytest.approx(.5)     # first run -.10 net, second +.40


def test_empty_band_has_nan_p_not_a_low_one():
    """shift_pvalue tests abs(s) >= nan, never true, so it would return 1/(n+1)."""
    scores = np.full(400, 50)
    ret = np.random.default_rng(1).normal(0, .01, 400)
    assert np.isnan(B.band_stats(scores, ret, n_perm=50)[HP]["p"])


def test_p_is_net_of_cost():
    """An edge exactly the size of the cost is no edge."""
    scores, ret = planted(11, lift=.002)
    free = B.band_stats(scores, ret, cost_bps=0)[HP]
    assert free["p"] < .05
    assert B.band_stats(scores, ret, cost_bps=free["excess"] * 10000)[HP]["p"] > .5


def test_cost_alone_is_not_significant():
    """Regression: a two-sided test called idle bands significant at minus the cost."""
    assert B.band_stats(*noise(3), cost_bps=10)["Normal"]["p"] > .5


def test_planted_signal_detected_noise_not():
    assert B.band_stats(*planted(3))[HP]["p"] < .05
    assert B.band_stats(*planted(3))[HP]["excess"] > .001
    assert B.band_stats(*noise(3))[HP]["p"] > .05


def test_detection_and_false_positive_rates_over_seeds():
    power = np.mean([B.band_stats(*planted(s), n_perm=200)[HP]["p"] < .05 for s in range(30)])
    false_pos = np.mean([B.band_stats(*noise(s), n_perm=200, cost_bps=0)[HP]["p"] < .05
                         for s in range(100)])
    assert power >= .9
    assert false_pos <= .12


def test_events_and_win_exclude_tail_sessions_without_a_forward_return():
    scores = np.array([50] * 5 + [70, 70, 50, 70, 70])
    ret = np.array([0.0] * 5 + [.02, .02, 0.0, np.nan, np.nan])
    out = B.band_stats(scores, ret, cost_bps=0, n_perm=10)[HP]
    assert out["days"] == 4 and out["events"] == 1
    assert out["win"] == pytest.approx(1.0)


def test_fold_pos_ignores_folds_with_under_five_band_sessions():
    k = B.BAND_NAMES.index(HP)
    index = np.array([k] * 4 + [0] * 20 + [k] * 10 + [0] * 20)
    years = np.array(["2020"] * 24 + ["2021"] * 30)
    ret = np.concatenate(([-.05] * 4, np.zeros(20), [.05] * 10, np.zeros(20)))
    _, pos = B._folds(index, years, [ret], [1], 0)
    assert pos[k, 0] == 1.0       # the 4-session fold is not counted
    index[:5] = k                 # now five band sessions: the fold counts and fails
    _, pos = B._folds(index, years, [ret], [1], 0)
    assert 0 < pos[k, 0] < 1


# --- score_for ---------------------------------------------------------------

ENTRY = 300


def test_every_price_after_entry_leaves_scores_identical(sample_inputs):
    a = B.score_for(sample_inputs, min_sessions=120)
    assert np.ptp(a.terms["histval"][:ENTRY]) > 0
    assert np.ptp(a.terms["vol"][:ENTRY]) > 0
    rng = np.random.default_rng(9)
    n = len(sample_inputs.ohlc) - ENTRY
    ohlc = sample_inputs.ohlc.copy()
    # From the entry open on, with a different factor per price so returns change.
    for col in ["open", "high", "low", "close"]:
        ohlc.iloc[ENTRY:, ohlc.columns.get_loc(col)] *= rng.uniform(.2, 3, n)
    b = B.score_for(sample_inputs._replace(ohlc=ohlc), min_sessions=120)
    assert (a.score[:ENTRY + 1] == b.score[:ENTRY + 1]).all()
    assert (a.terms["histval"][:ENTRY + 1] == b.terms["histval"][:ENTRY + 1]).all()
    assert (a.terms["histval"][ENTRY + 1:] != b.terms["histval"][ENTRY + 1:]).any()


def test_embargo_opens_exactly_when_the_return_closes(sample_inputs):
    """A close first reaches HistVal at the session after it, and not before."""
    a = B.score_for(sample_inputs, min_sessions=120)
    ohlc = sample_inputs.ohlc.copy()
    ohlc.iloc[ENTRY - 1, ohlc.columns.get_loc("close")] *= 50    # T-1 close of ENTRY
    b = B.score_for(sample_inputs._replace(ohlc=ohlc), min_sessions=120)
    assert (a.terms["histval"][:ENTRY] == b.terms["histval"][:ENTRY]).all()
    assert (a.terms["histval"][ENTRY:] != b.terms["histval"][ENTRY:]).any()


def test_vix_after_t_minus_1_does_not_reach_score(sample_inputs):
    a = B.score_for(sample_inputs, min_sessions=120)
    days = list(sample_inputs.ohlc.index)
    vix = {d: (v * 9 if d >= days[ENTRY] else v) for d, v in sample_inputs.vix.items()}
    b = B.score_for(sample_inputs._replace(vix=vix), min_sessions=120)
    assert (a.score[:ENTRY + 1] == b.score[:ENTRY + 1]).all()
    assert (a.terms["vol"][ENTRY + 1:] != b.terms["vol"][ENTRY + 1:]).any()


def lead_vix(days, n):
    end = pd.Timestamp(days[0]) - pd.Timedelta(days=1)
    lead = [str(d)[:10] for d in pd.bdate_range(end=end, periods=n)]
    rng = np.random.default_rng(2)
    return {d: float(v) for d, v in zip(lead + list(days), rng.uniform(10, 30, n + len(days)))}


def test_vix_lead_in_reaches_vol_term(sample_inputs):
    days = list(sample_inputs.ohlc.index)
    full = B.score_for(sample_inputs._replace(vix=lead_vix(days, 254)), min_sessions=120)
    assert full.terms["vol"][0] != 50.0
    assert not any(f.get("neutral") for f in full.factors(0) if f["term"] == "vol")


def test_days_before_vix_history_are_neutral_and_flagged(sample_inputs):
    days = list(sample_inputs.ohlc.index)
    short = B.score_for(sample_inputs._replace(vix=lead_vix(days, 100)), min_sessions=120)
    assert short.terms["vol"][0] == 50.0
    assert [f for f in short.factors(0) if f["term"] == "vol"][0]["neutral"]
    assert short.terms["vol"][-1] != 50.0


def test_sky_must_match_sessions(sample_inputs):
    with pytest.raises(ValueError):
        B.score_for(sample_inputs._replace(ohlc=sample_inputs.ohlc.iloc[:-1]))


# --- pipeline on the fixture: structure and determinism ----------------------

def test_result_structure_and_json_safe(sample_inputs):
    out = B.run_inputs(sample_inputs, FAST)
    assert set(out) >= {"bands", "folds", "placebo", "verdict", "is_sample"}
    assert set(out["bands"]) == {name for _, name in S.BANDS}
    needed = {"days", "events", "mean_oc", "mean_oo_1", "mean_oo_5", "vol", "max_dd", "hit",
              "win", "sharpe", "excess_vs_control", "p", "q", "insufficient", "verdict"}
    assert all(needed <= set(b) for b in out["bands"].values())
    assert all("natal_band_days" in b for b in out["bands"].values())
    assert out["research_grade"] is True
    notes = " ".join(out["notes"]).lower()
    assert "natal-band days" in notes and "diluted" in notes and "one-sided" in notes
    assert {"full_pct", "natal_pct", "n", "seconds"} <= set(out["placebo"])
    assert out["placebo"]["n"] == 3
    json.dumps(out, allow_nan=False)


def test_band_days_add_up_to_scored_sessions(sample_inputs):
    out = B.run_inputs(sample_inputs, FAST)
    scored = len(sample_inputs.ohlc) - 120
    assert sum(b["days"] for b in out["bands"].values()) == scored
    assert sum(f["sessions"] for f in out["folds"]) == scored


def test_same_seed_same_result(sample_inputs):
    a, b = B.run_inputs(sample_inputs, FAST), B.run_inputs(sample_inputs, FAST)
    assert strip_seconds(a["placebo"]) == strip_seconds(b["placebo"])
    assert a["bands"] == b["bands"] and a["folds"] == b["folds"]


def test_placebo_draws_follow_the_seed():
    assert B.draw_placebos(5, 1) == B.draw_placebos(5, 1)
    assert B.draw_placebos(5, 1) != B.draw_placebos(5, 2)
    assert B.draw_placebos(5, 1) == B.draw_placebos(9, 1)[:5]


def test_placebo_births_in_range():
    for p in B.draw_placebos(50, 3):
        assert "1950-01-01" <= p.birth_date < "2006-01-01"
        assert -60 <= p.lat <= 60 and -180 <= p.lon <= 180 and p.tz == "UTC"


def test_sample_is_labelled_pipeline_check_and_never_candidate(sample_inputs):
    out = B.run_inputs(sample_inputs, FAST)
    assert out["is_sample"] is True
    assert out["verdict"] == "no demonstrated edge" and out["candidate_bands"] == []
    assert all(b["verdict"] == "no demonstrated edge" for b in out["bands"].values())
    assert "pipeline check" in out["label"]


def test_default_warm_up_on_short_fixture_reports_nothing_scored(sample_inputs):
    out = B.run_inputs(sample_inputs, {"n_placebo": 1, "n_perm": 10})
    assert sum(b["days"] for b in out["bands"].values()) == 0
    assert out["folds"] == [] and out["verdict"] == "no demonstrated edge"
    assert out["candidate_bands"] == []
    assert all(b["events"] == 0 and b["p"] is None and b["verdict"] == "no demonstrated edge"
               for b in out["bands"].values())
    json.dumps(out, allow_nan=False)


def test_progress_called_per_chart(sample_inputs):
    seen = []
    B.run_inputs(sample_inputs, FAST, on_progress=lambda i, n: seen.append((i, n)))
    assert seen == [(1, 3), (2, 3), (3, 3)]


class Clock:
    """Advances `step` seconds on every read, so one read per chart is one chart's time."""
    def __init__(self, step):
        self.t, self.step = 0.0, step

    def __call__(self):
        self.t += self.step
        return self.t


def test_time_limit_reduces_and_discloses_n(sample_inputs, monkeypatch):
    monkeypatch.setattr(B, "_clock", Clock(30.0))
    p = B.run_inputs(sample_inputs, {**FAST, "n_placebo": 200})["placebo"]
    assert p["n"] == 20 and p["requested"] == 200 and p["reduced"] is True


def test_within_time_limit_runs_all(sample_inputs, monkeypatch):
    monkeypatch.setattr(B, "_clock", Clock(.001))
    p = B.run_inputs(sample_inputs, {**FAST, "n_placebo": 12})["placebo"]
    assert p["n"] == 12 and p["reduced"] is False


# --- end to end with a planted edge -----------------------------------------

def synthetic_market(days, lifted, lift, seed=4):
    rng = np.random.default_rng(seed)
    n = len(days)
    day_ret = rng.normal(0, .008, n) + np.where(lifted, lift, 0.0)
    gap = rng.normal(0, .002, n)
    opens, closes = np.empty(n), np.empty(n)
    level = 1000.0
    for i in range(n):
        opens[i] = level * (1 + gap[i])
        closes[i] = opens[i] * (1 + day_ret[i])
        level = closes[i]
    return pd.DataFrame({"open": opens, "close": closes}, index=days)


@pytest.fixture(scope="module")
def market_case():
    days = [str(d)[:10] for d in pd.bdate_range("2012-01-02", periods=1500)]
    chart = Profile("synthetic", False, SAMPLE_PROFILE.birth_date, SAMPLE_PROFILE.birth_time,
                    SAMPLE_PROFILE.tz, SAMPLE_PROFILE.lat, SAMPLE_PROFILE.lon)
    flat = synthetic_market(days, np.zeros(1500, bool), 0.0)
    base = B.Inputs(chart, flat, lead_vix(days, 260), build_sky(days))
    sub = B.natal_subscore(B.score_for(base, min_sessions=250))
    params = {"n_placebo": 25, "seed": 5, "min_sessions": 250, "n_perm": 300}
    return base, sub, params, days


def test_full_pipeline_noise_is_not_a_candidate(market_case):
    base, _, params, _ = market_case
    out = B.run_inputs(base, params)
    assert out["candidate_bands"] == [] and out["verdict"] == "no demonstrated edge"


def test_full_pipeline_finds_planted_edge_but_not_for_a_sample(market_case):
    base, sub, params, days = market_case
    ohlc = synthetic_market(days, (sub > 60) & (sub <= 80), .006)
    out = B.run_inputs(base._replace(ohlc=ohlc), params)
    assert HP in out["candidate_bands"], out["bands"][HP]
    assert out["verdict"] == "edge candidate" and out["research_grade"] is True
    assert out["bands"][HP]["natal_band_days"] >= 30
    sample = base._replace(ohlc=ohlc, profile=SAMPLE_PROFILE)
    s_out = B.run_inputs(sample, params)
    assert s_out["candidate_bands"] == [] and s_out["verdict"] == "no demonstrated edge"
