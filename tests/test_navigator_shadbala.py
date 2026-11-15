"""Shadbala pinned against two published worked examples.

V.P. Jain, A Text Book on Shadbala: 1981-09-13 01:30 IST, 28N39 77E13 (Lahiri).
B.V. Raman, Graha and Bhava Balas: 1918-10-16 14:22:16 IST, 13N00 77E35 (Raman ayanamsa).
Our positions come from Swiss Ephemeris, not the books' tables, and Chesta uses modern mean
longitudes, so small differences are expected; tolerances are stated per component.
"""
import pytest
import swisseph as swe

from sbc.navigator import shadbala as SB
from sbc.navigator import terms as T

P = SB.PLANETS


def _jd(y, m, d, h, mi, s, tz=5.5):
    return swe.julday(y, m, d, h + mi / 60 + s / 3600 - tz)


VPJ = (_jd(1981, 9, 13, 1, 30, 0), 28 + 39 / 60, 77 + 13 / 60, swe.SIDM_LAHIRI)
RAMAN = (_jd(1918, 10, 16, 14, 22, 16), 13.0, 77 + 35 / 60, swe.SIDM_RAMAN)


def _sb(case):
    jd, lat, lon, ay = case
    return SB.shadbala(jd, lat, lon, 5.5, ay)


def _close(got, exp, tol):
    assert all(abs(g - e) <= tol for g, e in zip(got, exp, strict=True)), (got, exp)


@pytest.mark.parametrize("part,exp,tol", [
    ("sthana", [172.04, 77.17, 184.94, 238.16, 152.98, 198.08, 206.31], 0.5),
    ("dig", [6.59, 12.22, 20.99, 31.97, 31.99, 53.29, 26.67], 0.5),
    ("kala", [81.80, 205.85, 158.08, 210.68, 144.22, 135.89, 139.56], 3.5),
    ("chesta", [0, 0, 20.93, 28.76, 8.43, 28.18, 5.05], 4.5),
    ("drik", [11.24, -0.32, -5.10, 4.29, 4.32, -2.86, 5.82], 0.5),
    ("total", [331.67, 346.35, 396.98, 539.57, 376.23, 455.45, 391.98], 3.5),
])
def test_vp_jain_example(part, exp, tol):
    r = _sb(VPJ)
    _close([r[p][part] for p in P], exp, tol)


def test_raman_example_sthana_components():
    jd, _, _, ay = RAMAN
    pos = SB._sidereal(jd, ay)
    signs = {p: int(pos[p]["lon"] // 30) for p in P}
    _close([SB.uchcha(p, pos[p]["lon"]) for p in P], [3.0, 32.75, 37.06, 54.5, 56.33, 1.95, 34.08], 0.8)
    assert [SB.saptavargaja(p, pos[p]["lon"], signs) for p in P] == [90, 48.75, 90, 135, 71.25, 116.25, 97.5]
    assert [SB.ojayugma(p, pos[p]["lon"]) for p in P] == [30, 15, 15, 30, 15, 30, 15]
    _close([_sb(RAMAN)[p]["sthana"] for p in P], [198, 126.5, 172.06, 279.5, 157.58, 178.2, 177.3], 0.8)


def test_raman_example_kala_and_mercury_malefic():
    r = _sb(RAMAN)
    _close([r[p]["kala"] for p in P], [102.98, 202.04, 30.06, 192.79, 211.18, 115.53, 116.97], 6.5)
    jd, _, _, ay = RAMAN
    pos = SB._sidereal(jd, ay)
    assert SB.mercury_is_benefic(pos, True) is False     # Mercury shares Libra with the Sun


@pytest.mark.parametrize("deg,sign,name", [(2, 0, "Bala"), (14, 0, "Yuva"), (29, 0, "Mrita"),
                                           (2, 1, "Mrita"), (29, 1, "Bala")])
def test_baladi_avastha_reverses_in_even_signs(deg, sign, name):
    assert SB.avastha(sign * 30 + deg)[0] == name


@pytest.mark.parametrize("d,lon,sign", [(2, 5, 4), (2, 20, 3), (2, 35, 3), (2, 50, 4), (3, 15, 4), (9, 0, 0),
                                        (9, 30, 9), (30, 3, 0), (30, 33, 1), (12, 29.9, 11)])
def test_varga_signs(d, lon, sign):
    assert SB.varga_sign(lon, d) == sign


def test_planet_strength_score_scaling():
    assert T.planet_strength_score(1.0, 1.0) == 50.0
    assert T.planet_strength_score(2.5, 1.0) == 100.0
    assert T.planet_strength_score(1.0, 0.0) == 50.0
    assert T.planet_strength_score(2.0, 0.0) == 75.0
    assert T.planet_strength_score(0.0, 0.5) == pytest.approx(50 - 50 * 0.75)


def test_shadbala_term_factors_sum_to_raw():
    days = ["2026-11-10", "2026-11-11"]
    t = T.shadbala_term(days)
    for i in range(2):
        assert sum(f["raw"] for f in t.factors(i)) == pytest.approx(t.raw[i])
        assert 0 <= t.values[i] <= 100
        assert len(t.factors(i)) == 7


def test_nav2_strength_settings_pinned():
    """Signed off with nav-2; changing any of these needs a new WEIGHTS_VERSION."""
    assert SB.AVASTHA == [("Bala", 0.25), ("Kumara", 0.5), ("Yuva", 1.0), ("Vriddha", 0.125), ("Mrita", 0.0)]
    assert SB.REQUIRED == {"Sun": 390, "Moon": 360, "Mars": 300, "Mercury": 420, "Jupiter": 390,
                           "Venus": 330, "Saturn": 300}
