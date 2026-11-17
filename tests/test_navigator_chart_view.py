"""Chart view: dignity, combustion, houses. Pure; no Postgres."""
import pytest

from sbc.navigator import chart_view as CV
from sbc.navigator.profile import SAMPLE_PROFILE, Profile

RAMAN = Profile("reference", False, "1912-08-08", "19:35:00", "Asia/Kolkata", 12.9716, 77.5946)


@pytest.mark.parametrize("planet,sign,expected", [
    ("Sun", 0, "exalted"), ("Sun", 6, "debilitated"), ("Sun", 4, "own"), ("Sun", 1, None),
    ("Moon", 1, "exalted"), ("Moon", 7, "debilitated"), ("Moon", 3, "own"),
    ("Mars", 9, "exalted"), ("Mars", 3, "debilitated"), ("Mars", 0, "own"), ("Mars", 7, "own"),
    ("Mercury", 5, "exalted"), ("Mercury", 11, "debilitated"), ("Mercury", 2, "own"),
    ("Jupiter", 3, "exalted"), ("Jupiter", 9, "debilitated"), ("Jupiter", 8, "own"), ("Jupiter", 11, "own"),
    ("Venus", 11, "exalted"), ("Venus", 5, "debilitated"), ("Venus", 1, "own"), ("Venus", 6, "own"),
    ("Saturn", 6, "exalted"), ("Saturn", 0, "debilitated"), ("Saturn", 9, "own"), ("Saturn", 10, "own"),
    ("Rahu", 1, None), ("Ketu", 7, None)])
def test_dignity_table(planet, sign, expected):
    assert CV.dignity(planet, sign) == expected


@pytest.mark.parametrize("planet,orb,retro", [
    ("Moon", 12, False), ("Mars", 17, False), ("Mercury", 14, False), ("Mercury", 12, True),
    ("Jupiter", 11, False), ("Venus", 10, False), ("Venus", 8, True), ("Saturn", 15, False)])
def test_combust_is_inclusive_at_the_orb(planet, orb, retro):
    sun = 100.0
    assert CV.is_combust(planet, sun + orb, sun, retro)
    assert CV.is_combust(planet, sun - orb + 0.5, sun, retro)
    assert not CV.is_combust(planet, sun + orb + 0.01, sun, retro)


@pytest.mark.parametrize("planet", ["Sun", "Rahu", "Ketu"])
def test_never_combust(planet):
    assert not CV.is_combust(planet, 100.0, 100.0, False)


def test_separation_wraps():
    assert CV.separation(359.0, 5.0) == pytest.approx(6.0)


def test_bhava_counts_from_lagna():
    assert CV.bhava(9, 9) == 1 and CV.bhava(10, 9) == 2 and CV.bhava(8, 9) == 12


def test_reference_chart_lagna_and_sun_house():
    view = CV.chart_view(RAMAN)
    assert view["lagna"]["sign"] == "Aquarius"
    sun = next(p for p in view["points"] if p["name"] == "Sun")
    assert sun["sign"] == "Cancer" and sun["bhava"] == 6


def test_sample_houses_hold_every_graha():
    view = CV.chart_view(SAMPLE_PROFILE)
    assert len(view["houses"]) == 12
    assert sorted(c for h in view["houses"] for c in h["points"]) == sorted(CV.CODES.values())
    assert view["houses"][0]["sign_number"] == view["lagna"]["sign_number"]
    for p in view["points"]:
        assert view["houses"][p["bhava"] - 1]["sign_number"] == p["sign_number"]


def test_nodes_always_retrograde_without_dignity():
    view = CV.chart_view(SAMPLE_PROFILE)
    for p in view["points"]:
        if p["name"] in ("Rahu", "Ketu"):
            assert p["retro"] is True and p["dignity"] is None and p["combust"] is False
