import numpy as np
import pytest

from sbc import nakshatra
from sbc.engine import _julday, _utc_from_local
from sbc.navigator import weights as W
from sbc.navigator.ephemeris import SkyTable, build_sky
from sbc.planets import positions


@pytest.mark.parametrize("a,b", [(("Jupiter", "Jupiter", "TRI"), 40),
                                 (("Mars", "Mercury", "SQ"), -20),
                                 (("Saturn", "Moon", "OPP"), -35)])
def test_required_examples(a, b):
    assert W.ASPECT_WEIGHT(*a) == b


def test_term_weights_sum():
    assert sum(W.TERM_WEIGHTS.values()) == pytest.approx(1)


def test_weights_version_pinned():
    assert W.WEIGHTS_VERSION == "nav-2"


@pytest.mark.parametrize("args,expected", [
    (("Jupiter", "Sun", "SXT"), 24.0),     # 20*.6*(1+1)
    (("Saturn", "Sun", "SQ"), -37.5),      # 20*-1*(1+.875)
    (("Venus", "Sun", "OPP"), -5.0),       # 20*-1*(1-.75)
    (("Mars", "Sun", "CONJ"), -15.0),      # 30*-.5
    (("Mars", "Sun", "TRI"), 10.0),        # 20*(1-.5)
])
def test_non_explicit_values_pinned(args, expected):
    assert W.ASPECT_WEIGHT(*args) == pytest.approx(expected)


def test_node_factor_halves_rahu_and_ketu():
    assert W.NODE_FACTOR == 0.5
    # Unhalved TRI for BENEFIC -0.5 would be 20*(1-0.5)=10; nodes carry half.
    assert W.ASPECT_WEIGHT("Rahu", "Sun", "TRI") == pytest.approx(5.0)
    assert W.ASPECT_WEIGHT("Ketu", "Sun", "TRI") == pytest.approx(5.0)
    assert W.ASPECT_WEIGHT("Mars", "Sun", "TRI") == pytest.approx(10.0)  # same benefic, no node
    assert W.ASPECT_WEIGHT("Rahu", "Sun", "CONJ") == pytest.approx(-7.5)
    assert W.ASPECT_WEIGHT("Rahu", "Moon", "SQ") == W.ASPECT_WEIGHT("Ketu", "Moon", "SQ")


def test_every_body_aspect_defined():
    for p in W.TRANSIT_BODIES:
        for a in W.ASPECTS:
            assert isinstance(W.ASPECT_WEIGHT(p, "Moon", a), float)


def test_dasha_and_strength_tables():
    assert W.DASHA_LORD["Jupiter"] == 40 and W.DASHA_LORD["Saturn"] == -30
    assert set(W.DASHA_LORD) == {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}
    assert sum(W.DASHA_LEVELS.values()) == pytest.approx(1)
    assert (W.STRENGTH_EXALTED, W.STRENGTH_DEBILITATED, W.STRENGTH_COMBUST, W.STRENGTH_RETRO) == (20.0, -20.0, -15.0, 5.0)


def test_nakshatra_sets_use_real_names():
    names = set(nakshatra.NAKSHATRAS_27)
    assert names >= W.DRUVA and names >= W.UGRA


def test_sky_bodies_and_shape():
    sky = build_sky(["2020-06-15", "2020-06-16"])
    assert isinstance(sky, SkyTable)
    assert list(sky.lon) == ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    assert all(v.shape == (2,) for v in sky.lon.values())
    assert all(v.dtype == bool for v in sky.retro.values())
    assert np.all(sky.lon["Sun"] > 0)


@pytest.mark.parametrize("day", ["2020-06-15", "2008-01-02", "2023-11-30"])
def test_sky_matches_positions(day):
    sky = build_sky([day])
    ps, _ = positions(_julday(_utc_from_local(day, "09:15", "Asia/Kolkata")))
    seen = 0
    for p in ps:
        if p["name"] in sky.lon:
            seen += 1
            assert sky.lon[p["name"]][0] == pytest.approx(p["longitude"], abs=1e-3)
            assert bool(sky.retro[p["name"]][0]) == p["retrograde"]
    assert seen == 9
