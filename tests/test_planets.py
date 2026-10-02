"""Tests for planetary position calculations."""

from datetime import UTC

from sbc.nakshatra import paksha_of, tithi_of
from sbc.planets import all_planets_with_natures, positioned_planets, positions


class TestPlanetaryPositions:
    """Test planetary position calculations using Swiss Ephemeris."""

    def test_positions_returns_all_planets(self):
        """positions() should return all 9 grahas plus ayanamsa."""
        # Known date: 2026-09-11 09:15 Asia/Kolkata
        import zoneinfo
        from datetime import datetime

        import swisseph as swe

        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        local = datetime(2026, 9, 11, 9, 15, tzinfo=tz)
        utc = local.astimezone(UTC).replace(tzinfo=None)
        h = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
        jul = swe.julday(utc.year, utc.month, utc.day, h)

        planets, ayanamsa = positions(jul)

        assert isinstance(planets, list)
        assert len(planets) >= 9  # Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu
        assert isinstance(ayanamsa, float)
        assert 23.0 < ayanamsa < 25.0  # Lahiri ayanamsa ~24 deg

    def test_planet_structure(self):
        """Each planet should have required fields."""
        import zoneinfo
        from datetime import datetime

        import swisseph as swe

        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        local = datetime(2026, 9, 11, 9, 15, tzinfo=tz)
        utc = local.astimezone(UTC).replace(tzinfo=None)
        h = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
        jul = swe.julday(utc.year, utc.month, utc.day, h)

        planets, _ = positions(jul)

        # The actual fields returned by positions()
        required_fields = {"name", "symbol", "longitude", "sign", "degree", "nakshatra", "pada", "retrograde"}

        for p in planets:
            assert set(p.keys()) >= required_fields
            assert isinstance(p["longitude"], float)
            assert 0 <= p["longitude"] < 360
            assert isinstance(p["retrograde"], bool)
            assert p["pada"] in (1, 2, 3, 4)

    def test_all_planets_with_natures(self):
        """all_planets_with_natures should add nature and dignity fields."""
        import zoneinfo
        from datetime import datetime

        import swisseph as swe

        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        local = datetime(2026, 9, 11, 9, 15, tzinfo=tz)
        utc = local.astimezone(UTC).replace(tzinfo=None)
        h = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
        jul = swe.julday(utc.year, utc.month, utc.day, h)

        planets, _ = positions(jul)
        sun = next(p for p in planets if p["name"] == "Sun")
        moon = next(p for p in planets if p["name"] == "Moon")
        tithi = tithi_of(sun["longitude"], moon["longitude"])

        enriched = all_planets_with_natures(planets, tithi, sun["longitude"])

        for p in enriched:
            assert "nature" in p
            assert p["nature"] in ("benefic", "malefic")
            assert "dignity_reasons" in p
            assert isinstance(p["dignity_reasons"], list)


class TestTithiCalculations:
    """Test tithi and paksha calculations."""

    def test_tithi_range(self):
        """Tithi should be 1-30."""
        import zoneinfo
        from datetime import datetime

        import swisseph as swe

        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        local = datetime(2026, 9, 11, 9, 15, tzinfo=tz)
        utc = local.astimezone(UTC).replace(tzinfo=None)
        h = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
        jul = swe.julday(utc.year, utc.month, utc.day, h)

        planets, _ = positions(jul)
        sun = next(p for p in planets if p["name"] == "Sun")
        moon = next(p for p in planets if p["name"] == "Moon")
        tithi = tithi_of(sun["longitude"], moon["longitude"])

        assert 1 <= tithi <= 30

    def test_paksha_determination(self):
        """Paksha should be Shukla (1-15) or Krishna (16-30)."""
        import zoneinfo
        from datetime import datetime

        import swisseph as swe

        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        local = datetime(2026, 9, 11, 9, 15, tzinfo=tz)
        utc = local.astimezone(UTC).replace(tzinfo=None)
        h = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
        jul = swe.julday(utc.year, utc.month, utc.day, h)

        planets, _ = positions(jul)
        sun = next(p for p in planets if p["name"] == "Sun")
        moon = next(p for p in planets if p["name"] == "Moon")
        tithi = tithi_of(sun["longitude"], moon["longitude"])
        pk = paksha_of(tithi)

        assert pk in ("Shukla", "Krishna")
        if tithi <= 15:
            assert pk == "Shukla"
        else:
            assert pk == "Krishna"


class TestPositionedPlanets:
    """Test the positioned_planets convenience function."""

    def test_positioned_planets_returns_tuple(self):
        """positioned_planets should return (planets, ayanamsa, sun, moon, tithi)."""
        planets, ayanamsa, sun, moon, tithi = positioned_planets("2026-09-11")

        assert isinstance(planets, list)
        assert isinstance(ayanamsa, float)
        assert sun["name"] == "Sun"
        assert moon["name"] == "Moon"
        assert 1 <= tithi <= 30
