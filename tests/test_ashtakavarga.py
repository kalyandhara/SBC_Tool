"""Ashtakavarga (spec .internal/specs/2026-10-31-ashtakavarga-design.md).

Sign pins (ambiguous contributors, the Raman fixture) were measured 2026-10-31
with Lahiri + Moshier via sbc.planets. A failure here after an ephemeris or
ayanamsa change is expected: re-measure and understand it, don't loosen the test.
"""

import pytest

from sbc import ashtakavarga as av

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
