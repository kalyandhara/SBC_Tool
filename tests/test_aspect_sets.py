import pytest
from sbc.aspect_sets import angular_separation, evaluate_aspect, CLASSICAL_ASPECTS, normalize_angle


def test_angular_separation():
    assert angular_separation(10.0, 100.0) == 90.0
    assert angular_separation(350.0, 10.0) == 20.0


def test_normalize_angle():
    assert normalize_angle(370.0) == 10.0
    assert normalize_angle(-10.0) == 350.0
    assert normalize_angle("invalid") == 0.0


def test_evaluate_aspect_exact():
    res = evaluate_aspect(0.0, 90.0)
    assert res is not None
    assert res["aspect"] == "Square"
    assert res["orb_diff"] == 0.0
    assert res["angle"] == 90.0


def test_evaluate_aspect_within_orb():
    res = evaluate_aspect(10.0, 102.0)  # sep 92, target 90, orb 10
    assert res is not None
    assert res["aspect"] == "Square"
    assert res["orb_diff"] == 2.0


def test_evaluate_aspect_no_match():
    res = evaluate_aspect(10.0, 25.0)  # sep 15, no standard aspect within orb
    assert res is None


def test_evaluate_aspect_tie_breaking():
    # Construct a custom aspect set with overlapping orbs for testing tie-breaking
    custom_set = {
        60: {"angle": 60.0, "name": "SextileOverlap", "orb": 5.0, "energy": 1.0, "polarity": 1},
        62: {"angle": 62.0, "name": "CustomOverlap", "orb": 5.0, "energy": 1.2, "polarity": 1},
    }
    # separation = 61.0. orb_diff to 60 is 1.0; orb_diff to 62 is 1.0.
    # Tie break should pick the lower angle (60).
    res = evaluate_aspect(0.0, 61.0, aspect_set=custom_set)
    assert res is not None
    assert res["aspect"] == "SextileOverlap"
