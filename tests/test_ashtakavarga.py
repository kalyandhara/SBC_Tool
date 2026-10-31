"""Ashtakavarga (spec .internal/specs/2026-10-31-ashtakavarga-design.md).

Sign pins (ambiguous contributors, the Raman fixture) were measured 2026-10-31
with Lahiri + Moshier via sbc.planets. A failure here after an ephemeris or
ayanamsa change is expected: re-measure and understand it, don't loosen the test.
"""

import datetime as dt

import pytest

from sbc import ashtakavarga as av
from sbc import natal
from sbc.engine import ANCHORS
from sbc.helio_aspects import IST, _jd
from sbc.nakshatra import RASHIS

# Hand count, all planets and the Lagna in Aries: for each house 1-12, how many
# of the Sun's 8 contributor lists contain it (Sun/Mars/Saturn 1,2,4,7,8,9,10,11;
# Jupiter 5,6,9,11; Moon 3,6,10,11; Mercury 3,5,6,9,10,11,12; Lagna 3,4,6,10,11,12;
# Venus 6,7,12).
SUN_FROM_ARIES = [3, 3, 3, 4, 2, 5, 4, 3, 5, 6, 7, 3]
MIXED = {"Sun": 3, "Moon": 1, "Mars": 4, "Mercury": 4, "Jupiter": 7, "Venus": 4, "Saturn": 1}


def _all_in(sign):
    return dict.fromkeys(av.PLANETS, sign)


def test_tables_cover_every_planet_and_contributor():
    assert set(av.BENEFIC_PLACES) == set(av.PLANETS)
    for planet in av.PLANETS:
        assert set(av.BENEFIC_PLACES[planet]) == set(av.CONTRIBUTORS)
        for houses in av.BENEFIC_PLACES[planet].values():
            assert all(1 <= h <= 12 for h in houses)
            assert len(set(houses)) == len(houses)


@pytest.mark.parametrize("planet,total", [
    ("Sun", 48), ("Moon", 49), ("Mars", 39), ("Mercury", 54),
    ("Jupiter", 56), ("Venus", 52), ("Saturn", 39)])
def test_classical_totals(planet, total):
    assert sum(len(h) for h in av.BENEFIC_PLACES[planet].values()) == total


def test_sun_bav_all_in_aries_matches_hand_count():
    assert av.bav(_all_in(0), 0)["Sun"] == SUN_FROM_ARIES


def test_all_in_taurus_shifts_the_row_one_sign():
    assert av.bav(_all_in(1), 1)["Sun"] == SUN_FROM_ARIES[-1:] + SUN_FROM_ARIES[:-1]


def test_classical_sav_total_is_337():
    assert sum(av.sav(av.bav(MIXED, 10))) == av.SAV_CLASSICAL_TOTAL == 337


def test_seven_sav_total_is_292():
    # 337 minus the Lagna's 6+4+5+7+9+8+6 = 45 places
    assert sum(av.sav(av.bav(MIXED, None))) == 292


def test_classical_minus_seven_is_the_lagna_contribution():
    lagna = 10
    full, seven = av.bav(MIXED, lagna), av.bav(MIXED, None)
    for planet in av.PLANETS:
        lagna_row = [0] * 12
        for house in av.BENEFIC_PLACES[planet]["Lagna"]:
            lagna_row[(lagna + house - 1) % 12] += 1
        assert [a - b for a, b in zip(full[planet], seven[planet])] == lagna_row


def test_cell_bounds():
    for lagna, top in ((10, 8), (None, 7)):
        for row in av.bav(MIXED, lagna).values():
            assert len(row) == 12 and all(0 <= c <= top for c in row)


@pytest.mark.parametrize("signs,lagna", [
    ({p: 0 for p in av.PLANETS if p != "Moon"}, 0),
    ({**MIXED, "Sun": 12}, 0),
    (MIXED, -1),
])
def test_bav_rejects_bad_input(signs, lagna):
    with pytest.raises(ValueError):
        av.bav(signs, lagna)


@pytest.mark.parametrize("anchor,expected", [
    ("india", ("classical", True, "exact official time, Indian place")),
    ("nifty", ("seven", False, "birth time approximate")),
    ("nse", ("seven", False, "birth time approximate")),
    ("bse", ("seven", False, "birth time approximate")),
    ("sensex", ("seven", False, "birth time approximate")),
    ("nyse", ("seven", False, "birth time approximate")),
    ("bitcoin", ("seven", False, "no birth place")),
])
def test_auto_mode_per_anchor(anchor, expected):
    assert av.resolve_mode(anchor, "auto") == expected


def test_every_anchor_resolves():
    for anchor in ANCHORS:
        mode, reliable, reason = av.resolve_mode(anchor)
        assert mode in ("classical", "seven") and isinstance(reliable, bool) and reason


def test_forced_modes_are_honoured():
    assert av.resolve_mode("nifty", "classical")[:2] == ("classical", False)
    assert av.resolve_mode("india", "seven")[:2] == ("seven", True)


@pytest.mark.parametrize("anchor,mode", [("nope", "auto"), ("nifty", "both")])
def test_resolve_mode_rejects_unknown(anchor, mode):
    with pytest.raises(ValueError):
        av.resolve_mode(anchor, mode)


@pytest.mark.parametrize("anchor,expected", [
    ("nifty", {"Moon": ["Aquarius", "Pisces"]}),
    ("nyse", {"Moon": ["Pisces", "Aries"]}),
    ("nse", {"Mercury": ["Scorpio", "Libra"]}),
    ("bse", {}), ("sensex", {}), ("india", {}), ("bitcoin", {}),
])
def test_ambiguous_contributors(anchor, expected):
    assert av.ambiguous_contributors(anchor) == expected


def test_ambiguity_check_leaves_natal_cache_alone():
    av._ambiguous.cache_clear()
    before = natal._planets.cache_info()
    av.ambiguous_contributors("nifty")
    assert natal._planets.cache_info() == before


def test_ambiguous_contributors_rejects_unknown_anchor():
    with pytest.raises(ValueError):
        av.ambiguous_contributors("nope")


def test_raman_sun_has_six_bindus_in_cancer():
    """B.V. Raman, Ashtakavarga System of Prediction p. 39 (cited in VedAstro's
    SunAshtakavargaYoga10Test): Sun in Cancer, 6th from Lagna, 6 bindus."""
    r = av.chart_ashtakavarga("1912-08-08", "19:35", "Asia/Kolkata", "Bengaluru", "classical")
    assert r["planet_signs"]["Sun"] == "Cancer"
    assert r["lagna_sign"] == "Aquarius"  # Cancer is the 6th sign from Aquarius
    assert r["bav"]["Sun"][RASHIS.index("Cancer")] == 6


@pytest.mark.parametrize("city,mode", [("Bengaluru", "auto"), ("Nowhere-ville", "classical")])
def test_chart_ashtakavarga_rejects_bad_input(city, mode):
    with pytest.raises(ValueError):
        av.chart_ashtakavarga("1912-08-08", "19:35", "Asia/Kolkata", city, mode)


def test_natal_nifty_is_seven_planet_with_ambiguous_moon():
    r = av.natal_ashtakavarga("nifty")
    assert (r["mode"], r["lagna_reliable"], r["max_per_sign"]) == ("seven", False, 7)
    assert r["lagna_reason"] == "birth time approximate"
    assert r["ambiguous_contributors"] == {"Moon": ["Aquarius", "Pisces"]}
    assert sum(r["sav"]) == 292 and set(r["bav"]) == set(av.PLANETS)


@pytest.mark.parametrize("anchor", sorted(ANCHORS))
def test_classical_sav_is_337_for_every_anchor(anchor):
    assert sum(av.natal_ashtakavarga(anchor, "classical")["sav"]) == 337


def test_transit_scores_are_natal_lookups():
    r = av.transit_scores("nifty", dt.date(2026, 10, 30))
    assert r["date"] == "2026-10-30" and r["transit_time"] == "09:15 IST"
    assert set(r["transit"]) == set(av.PLANETS)  # no Rahu, no Ketu
    for planet, t in r["transit"].items():
        assert t["sign"] == RASHIS[t["sign_index"]]
        assert t["bav_points"] == r["natal"]["bav"][planet][t["sign_index"]]
        assert t["sav_points"] == r["natal"]["sav"][t["sign_index"]]


def test_transit_is_computed_at_0915_ist(monkeypatch):
    calls = []
    real = av.positions

    def spy(jd):
        calls.append(jd)
        return real(jd)

    monkeypatch.setattr(av, "positions", spy)
    expected = _jd(dt.datetime(2026, 10, 30, 9, 15, tzinfo=IST))
    av.transit_scores("india", dt.date(2026, 10, 30))
    assert calls == [expected]


def test_transit_scores_rejects_non_date():
    with pytest.raises(TypeError):
        av.transit_scores("nifty", "2026-10-30")


def test_transit_scores_raises_when_a_planet_is_missing(monkeypatch):
    real = av.positions

    def no_saturn(jd):
        planets, ayanamsa = real(jd)
        return [p for p in planets if p["name"] != "Saturn"], ayanamsa

    monkeypatch.setattr(av, "positions", no_saturn)
    with pytest.raises(RuntimeError, match="Saturn"):
        av.transit_scores("nifty", dt.date(2026, 10, 30))


def test_india_classical_lagna_is_taurus_from_new_delhi():
    r = av.natal_ashtakavarga("india")
    assert r["mode"] == "classical"
    assert r["lagna_sign"] == "Taurus"


def test_india_lagna_city_changes_the_bav():
    """A Mumbai Lagna (Aries) would give a different BAV from the pinned New Delhi one (Taurus)."""
    r = av.natal_ashtakavarga("india")
    signs = av._planet_signs(natal.chart_detail("india"))
    assert r["bav"] == av.bav(signs, RASHIS.index("Taurus"))
    assert r["bav"] != av.bav(signs, RASHIS.index("Aries"))


def test_seven_mode_has_no_lagna_sign():
    assert av.natal_ashtakavarga("nifty")["lagna_sign"] is None
