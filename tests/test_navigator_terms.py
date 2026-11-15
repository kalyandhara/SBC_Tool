import math
import re

import numpy as np
import pytest

from sbc import nakshatra as N
from sbc.navigator import terms as T
from sbc.navigator import weights as W
from sbc.navigator.ephemeris import SkyTable, build_sky
from sbc.navigator.profile import SAMPLE_PROFILE, natal_points
from sbc.yogas import vimshottari

NOTE = "partial: no Shadbala/Avastha yet"


def sky(jup, base=200.0):
    n = len(jup)
    b = W.TRANSIT_BODIES
    lon = {k: np.full(n, base) for k in b}
    lon["Jupiter"] = np.array(jup, float)
    return SkyTable([f"2020-01-{i+1:02d}" for i in range(n)], lon,
                    {k: np.zeros(n, bool) for k in b})


def one_day(retro=(), **lons):
    """A single-day sky: everything at 200 (Libra) unless named."""
    s = sky([200.0])
    for k, v in lons.items():
        s.lon[k] = np.array([float(v)])
    for k in retro:
        s.retro[k] = np.array([True])
    return s


def labels(term, i=0):
    return [f["label"] for f in term.factors(i)]


def by_label(term, text, i=0):
    hits = [f for f in term.factors(i) if text in f["label"]]
    assert len(hits) == 1, (text, labels(term, i))
    return hits[0]


@pytest.fixture(scope="module")
def real():
    days = [str(d)[:10] for d in
            np.arange(np.datetime64("2020-01-01"), np.datetime64("2020-07-01"), 3)]
    return build_sky(days), natal_points(SAMPLE_PROFILE)


# --- transit ---------------------------------------------------------------

def test_orb_taper_linear():
    t = T.transit_term(sky([120.0, 121.5, 123.0]), {"Jupiter": 0.0})
    assert t.raw[0] == pytest.approx(40)
    assert t.raw[1] == pytest.approx(20)
    assert t.raw[2] == pytest.approx(0)
    assert t.values[0] == pytest.approx(70)
    assert t.factors(2) == []


def test_transit_handles_wraparound_at_zero_aries():
    t = T.transit_term(sky([359.0]), {"Mars": 1.0})
    expected = W.ASPECT_WEIGHT("Jupiter", "Mars", "CONJ") * (1 - 2 / 3)
    assert t.raw[0] == pytest.approx(expected)


def test_transit_factor_names_the_aspect_and_keeps_full_precision():
    t = T.transit_term(sky([121.234567]), {"Jupiter": 0.0})
    f = by_label(t, "Jupiter trine natal Jupiter")
    assert f["term"] == "transit" and set(f) == {"term", "label", "raw"}
    assert f["raw"] == t.raw[0]


def test_transit_clips_value_but_raw_stays_reproducible():
    s = one_day(Jupiter=120.0, Venus=120.0)
    t = T.transit_term(s, {f"P{i}": 0.0 for i in range(6)})
    assert t.raw[0] > 100 and t.values[0] == 100
    assert sum(f["raw"] for f in t.factors(0)) == pytest.approx(t.raw[0])


# --- moon ------------------------------------------------------------------

def test_moon_raw_bounded_and_nakshatra_names_real():
    s = sky([0.0] * 360)
    s.lon["Moon"] = np.arange(360.0)
    r = T.moon_term(s).raw
    assert r.min() >= -100 and r.max() <= 100 and r.std() > 5
    names = {N.nakshatra_of(float(x))[0] for x in range(360)}
    assert names >= W.DRUVA | W.UGRA


def test_moon_druva_member_exact_score():
    # Rohini, Taurus, elongation 30 -> tithi 3: phase 15 + sign 25 + druva 25.
    t = T.moon_term(one_day(Moon=45.0, Sun=15.0))
    assert N.nakshatra_of(45.0)[0] == "Rohini"
    assert t.raw[0] == pytest.approx(65.0)
    assert by_label(t, "Rohini")["raw"] == 25.0
    assert t.values[0] == pytest.approx(82.5)


def test_moon_ugra_member_exact_score():
    # Bharani, Aries, tithi 3: phase 15 + sign 15 - ugra 25.
    t = T.moon_term(one_day(Moon=20.0, Sun=350.0))
    assert N.nakshatra_of(20.0)[0] == "Bharani"
    assert t.raw[0] == pytest.approx(5.0)
    assert by_label(t, "Bharani")["raw"] == -25.0


def test_abhijit_slice_of_u_ashadha_gets_no_nakshatra_points():
    # sbc.nakshatra carves Abhijit out of U.Ashadha; match it rather than the
    # plain 27-division. Capricorn scores 0, so only phase remains.
    assert N.nakshatra_of(278.0)[0] == "Abhijit"
    assert T.moon_term(one_day(Moon=278.0, Sun=248.0)).raw[0] == pytest.approx(15.0)
    assert T.moon_term(one_day(Moon=270.0, Sun=240.0)).raw[0] == pytest.approx(40.0)


@pytest.mark.parametrize("elong,points,label", [(40.0, -20.0, "rikta"),   # tithi 4
                                                (220.0, -20.0, "rikta"),  # tithi 19
                                                (64.0, 20.0, "nanda"),    # tithi 6
                                                (304.0, 20.0, "nanda")])  # tithi 26
def test_tithi_groups_either_paksha(elong, points, label):
    t = T.moon_term(one_day(Moon=(150.0 + elong) % 360, Sun=150.0))
    assert by_label(t, label)["raw"] == points


def test_moon_vector_matches_scalar_helpers_on_boundaries():
    span = N.NAKSHATRA_SPAN
    moon = np.concatenate([np.arange(0, 360, .37), span * np.arange(27.0),
                           [N.ABHIJIT_START, N.ABHIJIT_END, 359.9999999]])
    s = sky([0.0] * len(moon))
    s.lon["Moon"] = moon
    s.lon["Sun"] = np.full(len(moon), 17.0)
    got = T.moon_term(s).raw
    for i, m in enumerate(moon):
        m = float(m)
        name = N.nakshatra_of(m)[0]
        tithi = N.tithi_of(17.0, m)
        exp = W.MOON_PHASE * math.cos(math.radians((m - 17.0) % 360 - 90))
        exp += W.MOON_SIGN[N.sign_of(m)[1]]
        exp += W.MOON_NAKSHATRA_DRUVA if name in W.DRUVA else 0
        exp += W.MOON_NAKSHATRA_UGRA if name in W.UGRA else 0
        group = N.GROUP_OF_TITHI[tithi]
        exp += {"Rikta": W.MOON_TITHI_RIKTA, "Nanda": W.MOON_TITHI_NANDA}.get(group, 0)
        assert got[i] == pytest.approx(exp), m


# --- dasha -----------------------------------------------------------------

DASHA_DAYS = [str(d)[:10] for d in
              np.arange(np.datetime64("2007-01-01"), np.datetime64("2026-01-01"), 97)]


def test_dasha_matches_vimshottari_on_every_day():
    s = SkyTable(DASHA_DAYS, {}, {})
    moon, birth = 100.0, "1980-05-05"
    t = T.dasha_term(s, moon, birth)
    for i, day in enumerate(DASHA_DAYS):
        at = vimshottari(moon, birth, day)["at"]
        exp = (.5 * W.DASHA_LORD[at["maha"]] + .3 * W.DASHA_LORD[at["antar"]]
               + .2 * W.DASHA_LORD[at["pratyantar"]])
        assert t.raw[i] == pytest.approx(exp), day
        assert by_label(t, "main period", i)["raw"] == .5 * W.DASHA_LORD[at["maha"]]
    assert len(set(t.raw)) > 5


def test_dasha_builds_the_period_list_once(monkeypatch):
    calls = []
    real_v = T.vimshottari
    monkeypatch.setattr(T, "vimshottari", lambda *a: calls.append(a) or real_v(*a))
    T.dasha_term(SkyTable(DASHA_DAYS, {}, {}), 100.0, "1980-05-05")
    assert len(calls) == 1


def test_dasha_period_starts_on_its_first_midnight_and_ends_exclusive(monkeypatch):
    def period(lord, start, end, child=None):
        d = {"lord": lord, "start": start, "end": end}
        if child:
            d.update(child)
        return d

    def fake(moon, birth, at):
        a, b, c = "2020-01-01T00:00:00", "2020-01-05T00:00:00", "2020-01-09T00:00:00"
        def maha(lord, s, e):
            leaf = {"pratyantars": [period(lord, s, e)]}
            return period(lord, s, e, {"antardashas": [period(lord, s, e, leaf)]})
        return {"mahadashas": [maha("Jupiter", a, b), maha("Saturn", b, c)]}

    monkeypatch.setattr(T, "vimshottari", fake)
    days = ["2020-01-04", "2020-01-05", "2020-01-08", "2020-01-09"]
    t = T.dasha_term(SkyTable(days, {}, {}), 0.0, "2000-01-01")
    assert list(t.raw) == [40, -30, -30, 0]
    assert t.factors(3)[0]["neutral"] is True


def test_dasha_outside_timeline_is_flagged_neutral():
    s = SkyTable(["1900-01-01", "2020-01-01"], {}, {})
    t = T.dasha_term(s, 100.0, "1980-05-05")
    assert t.raw[0] == 0 and t.values[0] == 50
    assert t.factors(0)[0]["neutral"] is True and t.factors(0)[0]["raw"] == 0
    assert t.raw[1] != 0 and "neutral" not in t.factors(1)[0]


# --- strength --------------------------------------------------------------

def test_known_real_exaltation_case():
    # Sun near 6 deg sidereal Aries on 2020-04-20.
    s = build_sky(["2020-04-20"])
    assert N.sign_of(float(s.lon["Sun"][0]))[1] == 0
    f = by_label(T.strength_term(s), "Sun exalted")
    assert f["raw"] == W.STRENGTH_EXALTED and f["note"] == NOTE


def test_known_real_combustion_case():
    # Jupiter's solar conjunction was 2021-01-29.
    s = build_sky(["2021-01-29"])
    assert abs((s.lon["Jupiter"][0] - s.lon["Sun"][0] + 180) % 360 - 180) < 2
    assert by_label(T.strength_term(s), "Jupiter combust")["raw"] == W.STRENGTH_COMBUST


def test_debilitated_and_retrograde_exact():
    t = T.strength_term(one_day(retro=["Saturn"], Saturn=10.0))  # Aries, far from Sun
    assert by_label(t, "Saturn debilitated")["raw"] == W.STRENGTH_DEBILITATED
    assert by_label(t, "Saturn retrograde")["raw"] == W.STRENGTH_RETRO


def test_sun_itself_is_never_combust():
    t = T.strength_term(one_day(Sun=100.0, Mars=100.0))
    assert not any("Sun" in x and "combust" in x for x in labels(t))
    assert "Mars combust" in labels(t)


def test_nodes_get_no_strength_points():
    # Rahu exalted in Taurus, Ketu debilitated there; both are outside the seven.
    t = T.strength_term(one_day(Rahu=45.0, Ketu=45.0, retro=["Rahu", "Ketu"]))
    assert not any("Rahu" in x or "Ketu" in x for x in labels(t))


def test_combustion_wraps_and_respects_each_planets_orb():
    assert "Venus combust" in labels(T.strength_term(one_day(Sun=359.0, Venus=5.0)))
    assert "Venus combust" not in labels(T.strength_term(one_day(Sun=100.0, Venus=110.5)))
    assert "Mars combust" in labels(T.strength_term(one_day(Sun=100.0, Mars=116.5)))


def test_strength_sign_boundaries_use_aries_zero():
    assert "Jupiter exalted" in labels(T.strength_term(one_day(Jupiter=90.0)))
    assert "Jupiter exalted" not in labels(T.strength_term(one_day(Jupiter=89.99)))


def test_strength_value_formula_and_notes():
    t = T.strength_term(one_day(Saturn=10.0))
    assert t.values[0] == pytest.approx(np.clip(50 + t.raw[0] / 2, 0, 100))
    assert all(f["note"] == NOTE and f["term"] == "strength" for f in t.factors(0))


# --- vol -------------------------------------------------------------------

VOL_DAYS = [str(d)[:10] for d in
            np.arange(np.datetime64("2021-01-01"), np.datetime64("2021-03-01"))]


def wavy():
    return {d: 20 + 5 * math.sin(i * 1.3) + i * .05 for i, d in enumerate(VOL_DAYS)}


def test_vol_ignores_same_day_value_and_is_not_vacuous():
    vix = wavy()
    base = T.vol_term(VOL_DAYS, vix, window=30)
    i = len(VOL_DAYS) - 1
    assert "neutral" not in base.factors(i)[0]
    changed = dict(vix)
    changed[VOL_DAYS[i]] = 9999.0
    assert T.vol_term(VOL_DAYS, changed, window=30).values[i] == base.values[i]


def test_vol_every_day_ignores_own_and_later_values():
    vix = wavy()
    base = T.vol_term(VOL_DAYS, vix, window=30).values
    for i in (25, 40, 58):
        c = dict(vix)
        for d in VOL_DAYS[i:]:
            c[d] = 1e6
        assert T.vol_term(VOL_DAYS, c, window=30).values[i] == base[i]


def test_vol_uses_t_minus_1_and_varies():
    vix = wavy()
    base = T.vol_term(VOL_DAYS, vix, window=30)
    assert base.values[25:].std() > 5
    c = dict(vix)
    c[VOL_DAYS[39]] = 1e6                 # T-1 for day 40 becomes the highest
    moved = T.vol_term(VOL_DAYS, c, window=30)
    assert moved.values[40] == 0 and base.values[40] != 0


def test_vol_percentile_exact_with_ties_half_counted():
    days = VOL_DAYS[:25]
    vix = {d: float(i) for i, d in enumerate(days)}
    # T=23: T-1 (22) sits above all 22 earlier values: pct 100, value 0.
    assert T.vol_term(days, vix, window=252).values[23] == 0
    vix[days[22]] = 10.5                  # above 11 of 22 -> pct 50
    t = T.vol_term(days, vix, window=252)
    assert t.values[23] == pytest.approx(50)
    assert "neutral" not in t.factors(23)[0]
    vix[days[22]] = 10.0                  # one tie: (10 + .5) / 22
    assert T.vol_term(days, vix).values[23] == pytest.approx(100 - 100 * 10.5 / 22)


def test_vol_window_limits_the_reference_set():
    days = VOL_DAYS[:32]
    vix = dict.fromkeys(days[:5], 100.0)    # old spikes fall outside window=20
    vix.update({d: float(i) for i, d in enumerate(days) if i >= 5})
    # T=31: T-1=30; window=20 holds 10..29, all lower, so pct is 100.
    assert T.vol_term(days, vix, window=20).values[31] == 0
    assert T.vol_term(days, vix, window=30).values[31] > 0


def test_missing_vix_is_flagged_neutral():
    t = T.vol_term(["2021-01-01"], {})
    assert t.values[0] == 50 and t.factors(0)[0]["neutral"] is True


def test_vol_neutral_with_too_little_history_or_missing_t_minus_1():
    vix = wavy()
    t = T.vol_term(VOL_DAYS, vix, window=30)
    assert t.values[20] == 50 and t.factors(20)[0]["neutral"] is True  # 19 prior values
    assert "neutral" not in t.factors(21)[0]                           # 20 prior values
    del vix[VOL_DAYS[39]]
    assert T.vol_term(VOL_DAYS, vix, window=30).factors(40)[0]["neutral"] is True
    vix[VOL_DAYS[39]] = float("nan")
    assert T.vol_term(VOL_DAYS, vix, window=30).factors(40)[0]["neutral"] is True


def test_vol_future_days_neutral():
    days = VOL_DAYS + ["2021-03-01", "2021-03-02"]
    t = T.vol_term(days, wavy(), window=30)
    assert t.factors(len(days) - 1)[0]["neutral"] is True   # T-1 itself is future
    assert "neutral" not in t.factors(len(days) - 2)[0]     # T-1 is the last close


# --- every term ------------------------------------------------------------

def all_terms(s, natal):
    vix = {d: 15 + 4 * math.sin(i) for i, d in enumerate(s.days)}
    return {"transit": T.transit_term(s, natal), "moon": T.moon_term(s),
            "dasha": T.dasha_term(s, natal["Moon"], SAMPLE_PROFILE.birth_date),
            "strength": T.strength_term(s), "vol": T.vol_term(s.days, vix)}


def test_every_factor_list_reproduces_raw_on_real_sky(real):
    s, natal = real
    for name, t in all_terms(s, natal).items():
        assert t.raw.shape == t.values.shape == (len(s.days),)
        assert np.all((t.values >= 0) & (t.values <= 100)), name
        for i in range(len(s.days)):
            fs = t.factors(i)
            assert all(f["term"] == name for f in fs)
            assert sum(f["raw"] for f in fs) == pytest.approx(t.raw[i], abs=1e-9), (name, i)


@pytest.mark.parametrize("name", ["transit", "moon", "dasha", "strength", "vol"])
def test_terms_vary_on_real_sky(real, name):
    s, natal = real
    assert all_terms(s, natal)[name].values.std() > 0.5


def test_factor_text_uses_no_mystical_wording(real):
    s, natal = real
    bad = ("auspicious", "blessing", "divine", "destiny", "karma", "malefic",
           "benefic", "fate", "omen", "cosmic", "curse")
    for t in all_terms(s, natal).values():
        for i in range(len(s.days)):
            for f in t.factors(i):
                assert not any(b in f["label"].lower() for b in bad), f["label"]


# --- fix round 1 -------------------------------------------------------------

def test_natal_node_axis_counts_once():
    t = T.transit_term(one_day(Mars=200.0), {"Rahu": 200.0, "Ketu": 20.0})
    assert by_label(t, "Mars conjunct natal Rahu")["raw"] == pytest.approx(-7.5)
    assert by_label(t, "Mars opposite natal Ketu")["raw"] == pytest.approx(-15.0)


def test_node_factor_applies_to_transiting_and_natal_nodes():
    assert W.ASPECT_WEIGHT("Mars", "Rahu", "CONJ") == pytest.approx(-7.5)
    assert W.ASPECT_WEIGHT("Mars", "Ketu", "OPP") == pytest.approx(-15.0)
    assert W.ASPECT_WEIGHT("Rahu", "Mars", "CONJ") == pytest.approx(-7.5)
    both = 30.0 * W.BENEFIC["Rahu"] * .25
    assert W.ASPECT_WEIGHT("Rahu", "Ketu", "CONJ") == pytest.approx(both)
    assert W.WEIGHTS_VERSION == "nav-2"


def test_transit_factors_accept_negative_index():
    t = T.transit_term(sky([120.0, 121.5, 123.0]), {"Jupiter": 0.0})
    assert t.factors(-1) == t.factors(2)
    assert t.factors(-3) == t.factors(0) and t.factors(0)


def test_vol_label_says_percentile_number_not_ordinal():
    t = T.vol_term(VOL_DAYS, wavy(), window=30)
    label = t.factors(30)[0]["label"]
    assert re.fullmatch(r"India VIX prior close at percentile \d+", label), label
    assert not re.search(r"\d(st|nd|rd|th)\b", label)
