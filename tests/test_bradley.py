"""Tests for the simplified Bradley barometer (experimental)."""

from sbc.bradley import (
    bradley_score,
    forward_return_validation,
    turning_point_candidates,
)


def _planet(name, longitude):
    return {"name": name, "longitude": longitude}


class TestBradleyScore:
    def test_hard_aspect_negative(self):
        # Jupiter-Saturn square (90 apart, orb 0) -> negative contribution
        score = bradley_score([_planet("Jupiter", 0.0), _planet("Saturn", 90.0)])
        assert score < 0

    def test_soft_aspect_positive(self):
        # Jupiter-Saturn trine (120 apart, orb 0) -> positive contribution
        score = bradley_score([_planet("Jupiter", 0.0), _planet("Saturn", 120.0)])
        assert score > 0

    def test_zero_score_when_unweighted_only(self):
        # Planets without weights contribute nothing
        assert bradley_score([_planet("Vesta", 0.0), _planet("Chiron", 90.0)]) == 0.0

    def test_orb_scales_contribution(self):
        exact = bradley_score([_planet("Jupiter", 0.0), _planet("Saturn", 90.0)])
        wide = bradley_score([_planet("Jupiter", 0.0), _planet("Saturn", 90.0 + 4.0)])
        assert abs(wide) < abs(exact)

    def test_empty_snapshot(self):
        assert bradley_score([]) == 0.0


class TestTurningPointCandidates:
    def test_high_and_low_candidates(self):
        scores = [
            {"date": "2026-09-01", "bradley_score": 0.0},
            {"date": "2026-09-02", "bradley_score": 1.0},
            {"date": "2026-09-03", "bradley_score": 0.0},
            {"date": "2026-09-04", "bradley_score": -1.0},
            {"date": "2026-09-05", "bradley_score": 0.0},
        ]
        candidates = turning_point_candidates(scores)
        assert {"date": "2026-09-02", "kind": "high", "bradley_score": 1.0} in candidates
        assert {"date": "2026-09-04", "kind": "low", "bradley_score": -1.0} in candidates

    def test_min_swing_filters_noise(self):
        scores = [
            {"date": "2026-09-01", "bradley_score": 0.0},
            {"date": "2026-09-02", "bradley_score": 0.2},
            {"date": "2026-09-03", "bradley_score": 0.0},
        ]
        assert turning_point_candidates(scores, min_swing=0.5) == []

    def test_ends_are_not_candidates(self):
        scores = [
            {"date": "2026-09-01", "bradley_score": 1.0},
            {"date": "2026-09-02", "bradley_score": 0.0},
        ]
        assert turning_point_candidates(scores) == []


class TestForwardReturnValidation:
    def test_high_candidate_hit_when_price_falls(self):
        scores = [
            {"date": "2026-09-01", "bradley_score": 0.0},
            {"date": "2026-09-02", "bradley_score": 1.0},
            {"date": "2026-09-03", "bradley_score": 0.0},
        ]
        closes = {"2026-09-01": 100.0, "2026-09-02": 101.0, "2026-09-03": 100.5,
                  "2026-09-04": 100.0, "2026-09-05": 99.0, "2026-09-06": 98.5,
                  "2026-09-07": 98.0}
        result = forward_return_validation(scores, closes, horizon=5)
        assert result["candidates_evaluated"] == 1
        assert result["hits"] == 1
        assert result["hit_rate"] == 1.0
        assert result["details"][0]["forward_move_pct"] < 0

    def test_low_candidate_miss_when_price_falls(self):
        scores = [
            {"date": "2026-09-01", "bradley_score": 0.0},
            {"date": "2026-09-02", "bradley_score": -1.0},
            {"date": "2026-09-03", "bradley_score": 0.0},
        ]
        closes = {"2026-09-01": 100.0, "2026-09-02": 99.0, "2026-09-03": 98.5,
                  "2026-09-04": 98.0, "2026-09-05": 97.5, "2026-09-06": 97.0,
                  "2026-09-07": 96.5}
        result = forward_return_validation(scores, closes, horizon=5)
        assert result["candidates_evaluated"] == 1
        assert result["hits"] == 0
        assert result["hit_rate"] == 0.0

    def test_missing_future_dates_skipped(self):
        scores = [
            {"date": "2026-09-01", "bradley_score": 0.0},
            {"date": "2026-09-02", "bradley_score": 1.0},
            {"date": "2026-09-03", "bradley_score": 0.0},
        ]
        closes = {"2026-09-01": 100.0, "2026-09-02": 101.0}
        result = forward_return_validation(scores, closes, horizon=5)
        assert result["candidates_evaluated"] == 0
        assert result["hit_rate"] is None
