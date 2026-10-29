"""Tests for exact conjunction/opposition crossing events."""

import datetime

from sbc.transits import conjunction_events


class TestConjunctionEvents:
    """conjunction_events locates exact 0/180-deg separation crossings."""

    def test_mars_ketu_2026_11_15(self):
        """The AstroZ video's 'Mars joins Ketu' event."""
        events = conjunction_events(
            "Mars", "Ketu", datetime.date(2026, 10, 1),
            datetime.date(2027, 1, 31))
        conj = [e for e in events if e["kind"] == "conjunction"]
        assert len(conj) == 1
        assert conj[0]["ist_date"] in ("2026-11-14", "2026-11-15",
                                       "2026-11-16")
        assert conj[0]["orb"] < 0.01

    def test_mars_rahu_2026_03_13(self):
        events = conjunction_events(
            "Mars", "Rahu", datetime.date(2026, 2, 1),
            datetime.date(2026, 5, 31))
        conj = [e for e in events if e["kind"] == "conjunction"]
        assert len(conj) == 1
        assert conj[0]["ist_date"] in ("2026-03-12", "2026-03-13",
                                       "2026-03-14")

    def test_mars_ketu_2025_07_23(self):
        events = conjunction_events(
            "Mars", "Ketu", datetime.date(2025, 6, 1),
            datetime.date(2025, 9, 30))
        conj = [e for e in events if e["kind"] == "conjunction"]
        assert len(conj) == 1
        assert conj[0]["ist_date"] in ("2025-07-22", "2025-07-23",
                                       "2025-07-24")

    def test_jupiter_saturn_great_conjunction_2020(self):
        """The Dec 2020 'Christmas star' conjunction."""
        events = conjunction_events(
            "Jupiter", "Saturn", datetime.date(2020, 1, 1),
            datetime.date(2020, 12, 31))
        conj = [e for e in events if e["kind"] == "conjunction"]
        assert len(conj) == 1
        assert conj[0]["ist_date"] in ("2020-12-20", "2020-12-21",
                                       "2020-12-22")

    def test_sun_moon_alternates_and_counts(self):
        """~12.4 lunations in 2026: 12-13 new moons, same full moons."""
        events = conjunction_events(
            "Sun", "Moon", datetime.date(2026, 1, 1),
            datetime.date(2026, 12, 31))
        conj = [e for e in events if e["kind"] == "conjunction"]
        opp = [e for e in events if e["kind"] == "opposition"]
        assert 11 <= len(conj) <= 14
        assert abs(len(conj) - len(opp)) <= 1
        kinds = [e["kind"] for e in events]
        assert all(kinds[i] != kinds[i + 1] for i in range(len(kinds) - 1))
