"""Tests for AstroCycle Pro Mercury/Moon cycle time bars."""

from unittest import mock

import pytest

from sbc import astro_cycles
from sbc.astro_cycles import CYCLE_PLANETS, cycle_bars, moon_ingress_bars


class TestCycleBars:
    """Test Mercury/Moon hora cycle bar generation."""

    def test_sl_points_positive_required(self):
        with pytest.raises(ValueError):
            cycle_bars("2026-09-11", ref_price=24000.0, sl_points=0)
        with pytest.raises(ValueError):
            cycle_bars("2026-09-11", ref_price=24000.0, sl_points=-5)
        with pytest.raises(ValueError):
            cycle_bars("2026-09-11", ref_price=-1.0)

    def test_bars_cover_session_and_have_entry_rules(self):
        """Bars align to hour boundaries clipped to 09:15..15:30 with entry geometry."""
        with mock.patch.object(astro_cycles, "_hour_hora_lord", return_value="Mercury"):
            bars = cycle_bars("2026-09-11", ref_price=24000.0, sl_points=15.0)

        # Market hours 09:15-15:30 -> 7 hourly slots (09:15-10:00 .. 15:00-15:30)
        assert len(bars) == 7
        assert bars[0]["time"] == "09:15"
        assert bars[0]["end"] == "10:00"
        assert bars[-1]["time"] == "15:00"
        assert bars[-1]["end"] == "15:30"
        for bar in bars:
            assert bar["type"] == "mercury"
            assert bar["ref_price"] == 24000.0
            assert bar["entry_above"] == 24015.0
            assert bar["entry_below"] == 23985.0
            assert bar["stop_loss"] == 24000.0
            assert bar["target_above"] == 24030.0
            assert bar["target_below"] == 23970.0
            assert "Buy above 24015.00" in bar["entry_rule"]
            assert "Sell below 23985.00" in bar["entry_rule"]

    def test_only_mercury_and_moon_lords_emit_bars(self):
        """Other hora lords produce no bars."""
        with mock.patch.object(astro_cycles, "_hour_hora_lord", return_value="Mars"):
            assert cycle_bars("2026-09-11", ref_price=24000.0) == []

    def test_alternating_lords(self):
        """Lords sequence alternates Mercury/Moon/others; only cycle planets emit."""
        lords = ["Mars", "Mercury", "Moon", "Saturn", "Jupiter", "Venus", "Sun"]
        with mock.patch.object(astro_cycles, "_hour_hora_lord", side_effect=lords):
            bars = cycle_bars("2026-09-11", ref_price=100.0, sl_points=10.0)
        assert [b["type"] for b in bars] == ["mercury", "moon"]
        assert bars[0]["time"] == "10:00"
        assert bars[1]["time"] == "11:00"

    def test_cycle_planets_constant(self):
        assert set(CYCLE_PLANETS) == {"Mercury", "Moon"}


class TestMoonIngressBars:
    """Test Moon nakshatra ingress detection."""

    def test_invalid_step_minutes_raises(self):
        with pytest.raises(ValueError):
            moon_ingress_bars("2026-09-11", step_minutes=0)

    def test_ingress_detected_on_nakshatra_change(self):
        """A nakshatra boundary crossing inside market hours emits a bar."""
        # Session scan makes 76 calls (09:15..15:30, step 5); ingress at step 50
        naks = ["Rohini"] * 10 + ["Mrigashira"] * 66
        with mock.patch("sbc.planets.positions", return_value=(
            [{"name": "Moon", "nakshatra": None}],
            24.0,
        )) as pos:
            # first call returns nakshatra None; use side_effect list instead
            pos.side_effect = [
                ([{"name": "Moon", "nakshatra": n}], 24.0) for n in naks
            ]
            bars = moon_ingress_bars("2026-09-11", step_minutes=5)

        assert len(bars) == 1
        assert bars[0]["type"] == "moon_ingress"
        assert bars[0]["into_nakshatra"] == "Mrigashira"
        assert bars[0]["from_nakshatra"] == "Rohini"
        assert "Mrigashira" in bars[0]["entry_rule"]
        # First scan at 09:15; ingress at 10th call: 09:15 + 50min = 10:05
        assert bars[0]["time"] == "10:05"
    def test_no_ingress_when_nakshatra_constant(self):
        with mock.patch("sbc.planets.positions", side_effect=(
            [([{"name": "Moon", "nakshatra": "Rohini"}], 24.0)] * 80
        )):
            assert moon_ingress_bars("2026-09-11", step_minutes=5) == []

    def test_moon_missing_is_ignored(self):
        """Sessions where Moon is absent from positions produce no crash."""
        with mock.patch("sbc.planets.positions", side_effect=(
            [([{"name": "Sun"}], 24.0)] * 80
        )):
            assert moon_ingress_bars("2026-09-11", step_minutes=5) == []
