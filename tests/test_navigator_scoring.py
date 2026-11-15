import re
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sbc.navigator import scoring as S
from sbc.navigator import terms as T
from sbc.navigator import weights as W
from sbc.navigator.ephemeris import SkyTable, build_sky
from sbc.navigator.profile import SAMPLE_PROFILE

FIXTURES = Path(__file__).parent / "fixtures"


def exact_sum(rows):
    return sum(Decimal(str(r["contribution"])) for r in rows)


def assert_sums_exactly(out):
    assert exact_sum(out["contributions"]) == out["score"]
    for line in out["contributions"]:
        if line["factors"]:
            total = Decimal(str(line["baseline"])) + exact_sum(line["factors"])
            assert total == Decimal(str(line["contribution"])), line["term"]


def flat_sky(n=40, start="2021-01-01"):
    days = [str(d) for d in np.arange(np.datetime64(start), np.datetime64(start) + n)]
    moving = (np.arange(n) * 13.0) % 360
    lon = {b: (moving + 30.0 * i) % 360 for i, b in enumerate(W.TRANSIT_BODIES)}
    return SkyTable(days, lon, {b: np.zeros(n, bool) for b in W.TRANSIT_BODIES})


def series(sky, vix=None, **kw):
    n = len(sky.days)
    rng = np.random.default_rng(5)
    opens = 100 * np.exp(np.cumsum(rng.normal(0, .01, n)))
    closes = opens * np.exp(rng.normal(0, .01, n))
    return S.score_series(sky, SAMPLE_PROFILE, opens, closes, vix or {}, **kw)


# --- bands ------------------------------------------------------------------

@pytest.mark.parametrize("v,b", [
    (0, "No Trading"), (20, "No Trading"), (21, "Very Defensive"), (40, "Very Defensive"),
    (41, "Normal"), (60, "Normal"), (61, "High Probability"), (80, "High Probability"),
    (81, "Exceptional Setup"), (100, "Exceptional Setup")])
def test_bands(v, b):
    assert S.band_of(v) == b


@pytest.mark.parametrize("band,action", [
    ("Exceptional Setup", "Trade Aggressively"), ("High Probability", "Trade Normally"),
    ("Normal", "Reduce Position Size"), ("Very Defensive", "Stay Cash"),
    ("No Trading", "Avoid Market Entirely")])
def test_actions(band, action):
    assert S.action_of(band) == action


# --- combine ----------------------------------------------------------------

def test_combine_uses_the_spec_weights():
    terms = {k: np.array([0.0]) for k in W.TERM_WEIGHTS}
    terms["transit"] = np.array([100.0])
    assert S.combine(terms)[0] == pytest.approx(25)


def test_combine_renormalises_without_histval():
    terms = {k: np.array([v]) for k, v in
             {"transit": 80.0, "moon": 40.0, "dasha": 60.0, "strength": 20.0, "vol": 100.0}.items()}
    expected = (.25 * 80 + .2 * 40 + .2 * 60 + .15 * 20 + .1 * 100) / .9
    assert S.combine(terms)[0] == pytest.approx(expected)


def test_combine_rejects_an_unknown_term():
    with pytest.raises(ValueError):
        S.combine({"transit": np.array([1.0]), "astro": np.array([1.0])})


# --- hist_val ---------------------------------------------------------------

def noise(n=1200):
    return np.random.default_rng(0).uniform(30, 70, n), np.random.default_rng(1).normal(0, .01, n)


def brute_hist(base, r, horizon, min_sessions):
    """The plan's definition written the slow way, with the t'+horizon<=t rule."""
    rounded = np.rint(base).astype(int)
    bands = np.array([S.band_of(int(v)) for v in rounded])
    out = np.full(len(base), 50.0)
    for t in range(min_sessions, len(base)):
        usable = t - horizon + 1
        same = r[:usable][bands[:usable] == bands[t]]
        if same.size >= 30:
            out[t] = 100.0 * (r[:usable] < same.mean()).mean()
    return out


def test_hist_val_warmup_is_neutral_and_later_days_vary():
    base, r = noise()
    h = S.hist_val(base, r, horizon=5, min_sessions=756)
    assert (h[:756] == 50).all()
    assert np.ptp(h[756:]) > 5


def test_hist_val_matches_slow_definition():
    base, r = noise()
    fast = S.hist_val(base, r, 5, 100)
    assert fast == pytest.approx(brute_hist(base, r, 5, 100))


def test_hist_val_embargo_boundary_is_t_minus_horizon():
    n, t, h = 400, 300, 5
    base, r = np.full(n, 50.0), np.random.default_rng(1).normal(0, .01, n)
    ref = S.hist_val(base, r, h, 100)

    inside = r.copy()
    inside[t - h + 1:] = 9.0          # window not closed by T-1: may not count
    assert S.hist_val(base, inside, h, 100)[:t + 1].tolist() == ref[:t + 1].tolist()

    last_usable = r.copy()
    last_usable[t - h] = 9.0          # window closed exactly at T-1: must count
    changed = S.hist_val(base, last_usable, h, 100)
    assert changed[t] != ref[t]
    assert changed[:t].tolist() == ref[:t].tolist()


def test_hist_val_needs_thirty_same_band_sessions():
    n = 200
    base = np.full(n, 50.0)
    base[:29] = 90.0
    base[150] = 90.0
    r = np.random.default_rng(1).normal(0, .01, n)
    assert S.hist_val(base, r, 5, 100)[150] == 50.0
    base[29] = 90.0
    assert S.hist_val(base, r, 5, 100)[150] != 50.0


def test_hist_val_ignores_missing_returns():
    base, r = noise(300)
    gap = r.copy()
    gap[50:60] = np.nan
    h = S.hist_val(base, gap, 5, 100)
    assert np.isfinite(h).all() and np.ptp(h[100:]) > 0


def test_hist_val_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        S.hist_val(np.zeros(5), np.zeros(4), 5, 1)


# --- lineage ----------------------------------------------------------------

TERMS = {"transit": 61.37, "moon": 48.91, "dasha": 55.13, "strength": 47.77, "histval": 50.0, "vol": 62.5}


def test_contributions_sum_exactly():
    out = S.lineage(TERMS, [])
    assert round(sum(c["contribution"] for c in out["contributions"]), 2) == out["score"]
    assert exact_sum(out["contributions"]) == out["score"]
    assert out["raised"][0]["term"] == "transit"


def test_lineage_score_is_the_rounded_combination():
    combined = S.combine({k: np.array([v]) for k, v in TERMS.items()})[0]
    assert S.lineage(TERMS, [])["score"] == int(np.rint(combined))


def test_lineage_lines_carry_term_label_raw_weight_contribution():
    line = S.lineage(TERMS, [])["contributions"][0]
    assert {"term", "label", "raw", "weight", "contribution", "factors"} <= set(line)
    assert line["weight"] == W.TERM_WEIGHTS["transit"] and line["raw"] == TERMS["transit"]


def test_raised_and_lowered_split_on_neutral_fifty_and_sort_by_size():
    out = S.lineage(TERMS, [])
    assert [r["term"] for r in out["raised"]] == ["transit", "vol", "dasha"]
    assert [r["term"] for r in out["lowered"]] == ["strength", "moon"]
    assert out["lowered"][0]["delta"] == pytest.approx(.15 * (47.77 - 50), abs=.005)


def test_factor_points_scale_by_weight_and_rebuild_the_line():
    factors = [{"term": "moon", "label": "a", "raw": 20.0},
               {"term": "moon", "label": "b", "raw": -8.0}]
    out = S.lineage({**TERMS, "moon": 56.0}, factors)
    moon = next(c for c in out["contributions"] if c["term"] == "moon")
    assert moon["factors"][1]["contribution"] == pytest.approx(.2 * -8 / 2)
    assert moon["factors"][0]["weight"] == W.TERM_WEIGHTS["moon"]
    assert_sums_exactly(out)


def test_clipped_day_has_an_explicit_adjustment_line():
    factors = [{"term": "transit", "label": "x", "raw": 90.0},
               {"term": "transit", "label": "y", "raw": 50.0}]
    out = S.lineage({**TERMS, "transit": 100.0}, factors)
    adj = [c for c in out["contributions"] if c.get("adjustment")]
    assert len(adj) == 1
    assert adj[0]["term"] == "transit"
    assert "clip" in adj[0]["label"].lower()
    assert adj[0]["contribution"] == pytest.approx(.25 * (100 - 120), abs=.001)
    assert_sums_exactly(out)


def test_negative_clip_adds_points_back():
    factors = [{"term": "transit", "label": "x", "raw": -135.0}]
    out = S.lineage({**TERMS, "transit": 0.0}, factors)
    adj = next(c for c in out["contributions"] if c.get("adjustment"))
    assert adj["contribution"] == pytest.approx(.25 * 17.5, abs=.0051)
    assert_sums_exactly(out)


def test_exactly_at_the_limit_needs_no_adjustment():
    factors = [{"term": "transit", "label": "x", "raw": 100.0}]
    out = S.lineage({**TERMS, "transit": 100.0}, factors)
    assert not any(c.get("adjustment") for c in out["contributions"])


def test_clipped_day_counts_as_raised_by_its_clipped_value():
    factors = [{"term": "transit", "label": "x", "raw": 140.0}]
    out = S.lineage({**TERMS, "transit": 100.0}, factors)
    # The clipped value, plus the score's rounding residual that lands on this line.
    shown = sum(c["contribution"] for c in out["contributions"] if c["term"] == "transit")
    assert out["raised"][0]["delta"] == pytest.approx(shown - 12.5, abs=.001)
    assert out["raised"][0]["delta"] == pytest.approx(12.5, abs=.5)


def test_rounding_residual_lands_on_the_largest_line_when_it_has_no_movers():
    out = S.lineage(dict.fromkeys(TERMS, 50.4), [])
    assert out["score"] == 50
    assert_sums_exactly(out)


def test_neutral_factor_stays_at_zero_points():
    factors = [{"term": "transit", "label": "active", "raw": 1.0},
               {"term": "vol", "label": "India VIX unavailable", "raw": 0.0, "neutral": True}]
    out = S.lineage({**TERMS, "transit": 50.5, "vol": 50.0}, factors)
    vol = next(c for c in out["contributions"] if c["term"] == "vol")
    assert next(f for f in vol["factors"] if f.get("neutral"))["contribution"] == 0
    assert_sums_exactly(out)


# --- vol lead-in ------------------------------------------------------------

def test_vol_min_history_keeps_short_history_neutral():
    days = [str(d) for d in np.arange(np.datetime64("2020-01-01"), np.datetime64("2020-02-20"))]
    vix = {d: 10.0 + (i * 7) % 11 for i, d in enumerate(days)}
    assert np.ptp(T.vol_term(days, vix).values) > 0
    t = T.vol_term(days, vix, min_history=252)
    assert (t.values == 50).all()
    assert t.factors(30)[0]["neutral"] is True


def vix_sessions(n, end="2021-01-01"):
    days = [str(d) for d in np.arange(np.datetime64(end) - n, np.datetime64(end))]
    rng = np.random.default_rng(2)
    return {d: float(v) for d, v in zip(days, rng.uniform(10, 30, n))}


def test_score_series_uses_253_lead_in_sessions_on_the_first_day():
    sky = flat_sky()
    vix = vix_sessions(300)
    vix.update(zip(sky.days, np.linspace(12, 28, len(sky.days))))
    s = series(sky, vix)
    assert s.terms["vol"][0] != 50.0
    prior = sorted(d for d in vix if d < sky.days[0])
    last, past = vix[prior[-1]], np.array([vix[d] for d in prior[-253:-1]])
    pct = 100 * (np.sum(past < last) + .5 * np.sum(past == last)) / 252
    assert s.terms["vol"][0] == pytest.approx(100 - pct)


def test_score_series_stays_neutral_and_flagged_with_only_252_lead_in():
    sky = flat_sky()
    s = series(sky, vix_sessions(252))
    assert s.terms["vol"][0] == 50.0
    assert [f for f in s.factors(0) if f["term"] == "vol"][0]["neutral"] is True


def test_full_lead_in_does_not_shift_vol_factors():
    sky = flat_sky()
    vix = vix_sessions(300)
    vix.update(zip(sky.days, np.linspace(12, 28, len(sky.days))))
    s = series(sky, vix)
    vol = [f for f in s.factors(10) if f["term"] == "vol"][0]
    assert vol["raw"] == pytest.approx(2 * s.terms["vol"][10] - 100)


# --- score_series -----------------------------------------------------------

def test_series_shape_and_base_excludes_histval():
    sky = flat_sky()
    s = series(sky, min_sessions=10)
    assert s.days == sky.days
    assert s.score.dtype.kind == "i"
    five = {k: v for k, v in s.terms.items() if k != "histval"}
    assert s.base == pytest.approx(S.combine(five))
    assert s.score.tolist() == np.rint(S.combine(s.terms)).astype(int).tolist()


def test_hist_returns_run_from_open_to_close_of_the_last_session():
    o = np.array([100., 110., 120., 130.])
    c = np.array([101., 111., 121., 131.])
    r = S.forward_returns(o, c, 2)
    assert r[:3] == pytest.approx([111 / 100 - 1, 121 / 110 - 1, 131 / 120 - 1])
    assert np.isnan(r[3])


def test_series_rejects_misaligned_prices():
    with pytest.raises(ValueError):
        S.score_series(flat_sky(), SAMPLE_PROFILE, np.ones(3), np.ones(3), {})


def test_histval_neutral_day_is_flagged_and_active_day_is_not():
    s = series(flat_sky(120), min_sessions=60)
    assert [f for f in s.factors(5) if f["term"] == "histval"][0]["neutral"] is True
    i = int(np.argmax(s.terms["histval"] != 50.0))
    assert i >= 60
    assert not [f for f in s.factors(i) if f["term"] == "histval"][0].get("neutral")


# --- real days --------------------------------------------------------------

@pytest.fixture(scope="module")
def real():
    bars = pd.read_csv(FIXTURES / "navigator_nifty_sample.csv")
    vix_rows = pd.read_csv(FIXTURES / "navigator_vix_sample.csv")
    vix = dict(zip(vix_rows["date"], vix_rows["close"]))
    days = bars["date"].tolist()
    opens, closes = bars["open"].to_numpy(float), bars["close"].to_numpy(float)
    sky = build_sky(days)
    return sky, opens, closes, vix, S.score_series(sky, SAMPLE_PROFILE, opens, closes, vix,
                                                   min_sessions=120)


def test_real_days_every_lineage_sums_exactly_to_its_series_score(real):
    s = real[-1]
    assert len(s.days) >= 50
    assert np.ptp(s.terms["histval"]) > 0
    for i in range(len(s.days)):
        out = S.day_lineage(s, i)
        assert out["score"] == s.score[i]
        assert_sums_exactly(out)


def test_real_clipped_days_show_the_adjustment(real):
    s = real[-1]
    clipped = np.nonzero((s.terms["transit"] == 0) | (s.terms["transit"] == 100))[0]
    assert clipped.size > 0
    for i in clipped:
        out = S.day_lineage(s, int(i))
        assert any(c.get("adjustment") for c in out["contributions"])
        assert_sums_exactly(out)


def test_real_factor_text_has_no_mystical_wording(real):
    s = real[-1]
    banned = re.compile(r"divine|cosmic|destin|fate|karma|auspicious|blessed|sacred|"
                        r"mystic|omen|magic|spirit|prophe|fortune", re.I)
    labels = set()
    for i in range(len(s.days)):
        out = S.day_lineage(s, i)
        labels |= {c["label"] for c in out["contributions"]}
        labels |= {f["label"] for c in out["contributions"] for f in c["factors"]}
    assert len(labels) > 50
    assert [x for x in labels if banned.search(x)] == []


def test_real_changing_everything_after_t_minus_1_close_leaves_scores_identical(real):
    sky, opens, closes, vix, a = real
    k = 300
    assert np.ptp(a.terms["histval"][:k]) > 0
    o2, c2 = opens.copy(), closes.copy()
    o2[k:] *= 3
    c2[k:] *= .2
    vix2 = {d: (v * 4 if d >= sky.days[k] else v) for d, v in vix.items()}
    b = S.score_series(sky, SAMPLE_PROFILE, o2, c2, vix2, min_sessions=120)
    assert a.score[:k + 1].tolist() == b.score[:k + 1].tolist()
    assert a.terms["histval"][:k + 1].tolist() == b.terms["histval"][:k + 1].tolist()
    assert a.terms["vol"][:k + 1].tolist() == b.terms["vol"][:k + 1].tolist()
    assert a.base[:k + 1].tolist() == b.base[:k + 1].tolist()
    assert a.terms["histval"].tolist() != b.terms["histval"].tolist()


def test_real_the_t_minus_1_close_does_reach_day_t(real):
    sky, opens, closes, vix, a = real
    reached = 0
    for k in range(300, 340, 5):
        c2 = closes.copy()
        c2[k - 1] *= 3                # closes the window that opened at k-5
        b = S.score_series(sky, SAMPLE_PROFILE, opens, c2, vix, min_sessions=120)
        assert a.terms["histval"][:k].tolist() == b.terms["histval"][:k].tolist()
        reached += a.terms["histval"][k] != b.terms["histval"][k]
    assert reached >= 1


@pytest.mark.parametrize("terms", [TERMS, dict.fromkeys(TERMS, 50.4),
                                   {**TERMS, "transit": 61.6, "vol": 50.0},
                                   {k: v + .37 for k, v in TERMS.items()}])
def test_raised_and_lowered_equal_displayed_points_minus_baseline(terms):
    out = S.lineage(terms, [])
    shown = {}
    for c in out["contributions"]:
        shown[c["term"]] = shown.get(c["term"], 0) + round(c["contribution"] * 100)
    expected = {k: shown[k] - round(W.TERM_WEIGHTS[k] * 50 * 100) for k in W.TERM_WEIGHTS}
    moves = {m["term"]: round(m["delta"] * 100) for m in out["raised"] + out["lowered"]}
    assert moves == {k: v for k, v in expected.items() if v}
    assert all(m["delta"] > 0 for m in out["raised"]) and all(m["delta"] < 0 for m in out["lowered"])
