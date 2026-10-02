"""Tests for the canonical market event model (aspect + ingress types)."""

from datetime import date

from sbc.market_events import (
    applying_or_separating,
    lunar_phase_event,
    planetary_aspect_events,
    planetary_ingress_events,
    sign_of_longitude,
)


class TestApplyingOrSeparating:
    """Test aspect motion classification."""

    def test_unknown_previous_returns_none(self):
        assert applying_or_separating(120.0, None, 120.0) is None

    def test_applying(self):
        # Gap to 90 shrinking: 95 -> 92
        assert applying_or_separating(92.0, 95.0, 90.0) == "applying"

    def test_separating(self):
        # Gap to 0 growing: 5 -> 7
        assert applying_or_separating(7.0, 5.0, 0.0) == "separating"

    def test_stationary(self):
        assert applying_or_separating(90.0, 90.0, 90.0) == "stationary"

    def test_wraps_across_zero(self):
        # 359 -> 0.5: gap to 0 shrinks from 1 to 0.5 -> applying
        assert applying_or_separating(0.5, 359.0, 0.0) == "applying"


def _planet(name, longitude, sign=None, retrograde=False):
    return {"name": name, "longitude": longitude, "sign": sign, "retrograde": retrograde}


class TestPlanetaryAspectEvents:
    """Test canonical aspect events with applying/separating state."""

    def test_aspect_detected_with_state(self):
        # Sun at 0, Moon at 88 -> square (gap 2 <= 8)
        planets = [_planet("Sun", 0.0), _planet("Moon", 88.0)]
        prev = [_planet("Sun", 0.0), _planet("Moon", 94.0)]
        events = planetary_aspect_events(date(2026, 9, 11), planets, prev)

        squares = [e for e in events if e.metadata.get("aspect") == "square"]
        assert squares
        assert squares[0].event_type == "planetary_aspect"
        assert squares[0].planet_a == "Sun"
        assert squares[0].planet_b == "Moon"
        assert squares[0].metadata["state"] == "applying"

    def test_no_prev_planets_omits_state(self):
        planets = [_planet("Sun", 0.0), _planet("Moon", 88.0)]
        events = planetary_aspect_events(date(2026, 9, 11), planets)
        assert events
        for e in events:
            assert "state" not in e.metadata

    def test_separating_state(self):
        # Moon moved away from the square angle: 88 (gap 2) -> 84 (gap 6)
        planets = [_planet("Sun", 0.0), _planet("Moon", 84.0)]
        prev = [_planet("Sun", 0.0), _planet("Moon", 88.0)]
        events = planetary_aspect_events(date(2026, 9, 11), planets, prev)
        squares = [e for e in events if e.metadata.get("aspect") == "square"]
        assert squares[0].metadata["state"] == "separating"


class TestPlanetaryIngressEvents:
    """Test canonical sign-ingress events."""

    def test_ingress_detected(self):
        planets = [_planet("Mars", 35.0, sign="Taurus")]
        prev = [_planet("Mars", 29.5, sign="Aries")]
        events = planetary_ingress_events(date(2026, 9, 11), planets, prev)

        assert len(events) == 1
        assert events[0].event_type == "planetary_ingress"
        assert events[0].planet_a == "Mars"
        assert events[0].metadata["from_sign"] == "Aries"
        assert events[0].metadata["to_sign"] == "Taurus"

    def test_no_ingress_when_sign_unchanged(self):
        planets = [_planet("Mars", 35.0, sign="Taurus")]
        prev = [_planet("Mars", 31.0, sign="Taurus")]
        assert planetary_ingress_events(date(2026, 9, 11), planets, prev) == []

    def test_retrograde_reentry_flagged(self):
        planets = [_planet("Mercury", 29.0, sign="Aries", retrograde=True)]
        prev = [_planet("Mercury", 31.5, sign="Taurus")]
        events = planetary_ingress_events(date(2026, 9, 11), planets, prev)
        assert events[0].metadata["retrograde"] is True

    def test_sign_fallback_from_longitude(self):
        """Missing sign fields fall back to longitude-derived signs."""
        planets = [_planet("Jupiter", 125.0)]   # 125/30 = 4.16 -> Leo
        prev = [_planet("Jupiter", 115.0)]      # 115/30 = 3.83 -> Cancer
        events = planetary_ingress_events(date(2026, 9, 11), planets, prev)
        assert events[0].metadata["from_sign"] == "Cancer"
        assert events[0].metadata["to_sign"] == "Leo"

    def test_unknown_prev_planet_skipped(self):
        planets = [_planet("Mars", 35.0, sign="Taurus")]
        prev = [_planet("Venus", 35.0, sign="Taurus")]
        assert planetary_ingress_events(date(2026, 9, 11), planets, prev) == []


class TestSignOfLongitude:
    def test_sign_boundaries(self):
        assert sign_of_longitude(0.0) == "Aries"
        assert sign_of_longitude(29.9) == "Aries"
        assert sign_of_longitude(30.0) == "Taurus"
        assert sign_of_longitude(359.9) == "Pisces"

    def test_lunar_phase_event_still_works(self):
        # Tithi 30 -> new moon
        ev = lunar_phase_event(date(2026, 9, 11), 30, 170.0, 170.0)
        assert ev.event_type == "new_moon"
