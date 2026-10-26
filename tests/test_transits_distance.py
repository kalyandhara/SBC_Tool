"""Tests for the mutual sign-distance (Shashtashtaka) scanner."""

import datetime

import pytest

from sbc.transits import same_sign_periods, sign_distance_periods


class TestSignDistancePeriods:
    """sign_distance_periods generalises same_sign_periods to 6/8 etc."""

    def test_jupiter_saturn_shashtashtaka_2026(self):
        """Jupiter (Leo) vs Saturn (Pisces): mutual 6/8 Nov 2026-Jan 2027.

        The AstroZ video's headline configuration: Jupiter enters Leo
        2026-10-31 and leaves it 2027-01-25, Saturn stays in Pisces.
        """
        periods = sign_distance_periods(
            "Jupiter", "Saturn",
            datetime.date(2026, 9, 1), datetime.date(2027, 6, 30))
        spans = [(p["start"], p["end"]) for p in periods]
        assert any(start <= "2026-11-01" and end >= "2027-01-24"
                   for start, end in spans)
        hit = next(p for p in periods if p["start"] <= "2026-11-01"
                   and p["end"] >= "2027-01-24")
        assert hit["distance"] == 5
        assert hit["relation"] == "mutual 6/8"
        assert hit["planet_a_sign"] == "Leo"
        assert hit["planet_b_sign"] == "Pisces"
        assert hit["days"] > 80

    def test_covers_1929_black_tuesday(self):
        """Oct 1929: Jupiter Taurus / Saturn Sagittarius is also a 6/8."""
        periods = sign_distance_periods(
            "Jupiter", "Saturn",
            datetime.date(1929, 1, 1), datetime.date(1930, 6, 30))
        assert any(p["start"] <= "1929-10-29" and p["end"] >= "1929-10-30"
                   and p["distance"] == 5 for p in periods)

    def test_distance_zero_matches_same_sign_periods(self):
        """distances=(0,) must reproduce same_sign_periods exactly."""
        start = datetime.date(2026, 1, 1)
        end = datetime.date(2027, 12, 31)
        base = [(p["start"], p["end"])
                for p in same_sign_periods("Jupiter", "Ketu", start, end)]
        zero = [(p["start"], p["end"]) for p in
                sign_distance_periods("Jupiter", "Ketu", start, end,
                                      distances=(0,))]
        assert base == zero
        assert len(base) >= 1  # Jupiter Rx dips back into Cancer (Ketu)

    def test_input_validation(self):
        with pytest.raises(ValueError):
            sign_distance_periods("Jupiter", "Saturn",
                                  datetime.date(2026, 1, 1),
                                  datetime.date(2026, 2, 1), distances=())
        with pytest.raises(ValueError):
            sign_distance_periods("Jupiter", "Saturn",
                                  datetime.date(2026, 1, 1),
                                  datetime.date(2026, 2, 1), distances=(12,))
