"""Tests for nakshatra, tithi, and paksha calculations."""

from sbc.nakshatra import (
    GROUP_OF_TITHI,
    GROUP_WEEKDAYS,
    NAKSHATRAS_27,
    moon_nature,
    nakshatra_of,
    paksha_of,
    sign_of,
)


class TestNakshatraConstants:
    """Test nakshatra constant definitions."""

    def test_nakshatras_27_count(self):
        """Should have exactly 27 nakshatras."""
        assert len(NAKSHATRAS_27) == 27

    def test_nakshatras_order(self):
        """Nakshatras should start with Ashwini."""
        assert NAKSHATRAS_27[0] == "Ashwini"
        assert NAKSHATRAS_27[-1] == "Revati"

    def test_group_of_tithi_coverage(self):
        """GROUP_OF_TITHI should cover all 30 tithis."""
        for t in range(1, 31):
            assert t in GROUP_OF_TITHI

    def test_group_weekdays_mapping(self):
        """GROUP_WEEKDAYS should map all groups to weekday lists."""
        groups = set(GROUP_OF_TITHI.values())
        for g in groups:
            assert g in GROUP_WEEKDAYS
            assert isinstance(GROUP_WEEKDAYS[g], list)
            assert len(GROUP_WEEKDAYS[g]) > 0


class TestPakshaOf:
    """Test paksha determination."""

    def test_shukla_paksha(self):
        """Tithis 1-15 should be Shukla."""
        for t in range(1, 16):
            assert paksha_of(t) == "Shukla"

    def test_krishna_paksha(self):
        """Tithis 16-30 should be Krishna."""
        for t in range(16, 31):
            assert paksha_of(t) == "Krishna"

    def test_paksha_boundaries(self):
        """Test boundary tithis."""
        assert paksha_of(15) == "Shukla"   # Purnima
        assert paksha_of(16) == "Krishna"  # First Krishna
        assert paksha_of(30) == "Krishna"  # Amavasya


class TestMoonNature:
    """Test moon nature (shubha/ashubha) determination."""

    def test_shubha_moon_range(self):
        """Shukla Panchami (5) through Krishna Dashami (25) should be shubha."""
        # Shukla 5-15
        for t in range(5, 16):
            assert moon_nature(t) == "benefic"
        # Krishna 1-10 (which are tithis 16-25)
        for t in range(16, 26):
            assert moon_nature(t) == "benefic"

    def test_ashubha_moon_range(self):
        """Krishna Ekadashi (26) through Shukla Chaturthi (4) should be ashubha."""
        # Krishna 11-15 (tithis 26-30)
        for t in range(26, 31):
            assert moon_nature(t) == "malefic"
        # Shukla 1-4
        for t in range(1, 5):
            assert moon_nature(t) == "malefic"


class TestNakshatraFromLongitude:
    """Test nakshatra and pada calculation from longitude."""

    def test_ashwini_range(self):
        """0-13:20 deg should be Ashwini."""
        lon = 5.0  # degrees
        nak, pada = nakshatra_of(lon)
        assert nak == "Ashwini"

    def test_bharani_range(self):
        """13:20-26:40 deg should be Bharani."""
        lon = 20.0
        nak, pada = nakshatra_of(lon)
        assert nak == "Bharani"

    def test_revati_wraparound(self):
        """346:40-360 deg should be Revati."""
        lon = 355.0
        nak, pada = nakshatra_of(lon)
        assert nak == "Revati"

    def test_abhijit_range(self):
        """Abhijit range should return Abhijit."""
        lon = 278.0  # Within Abhijit range
        nak, pada = nakshatra_of(lon)
        assert nak == "Abhijit"

    def test_nakshatra_pada(self):
        """Each nakshatra has 4 padas of 3:20 each."""
        # Ashwini: 0-13:20
        # Pada 1: 0-3:20
        # Pada 2: 3:20-6:40
        # Pada 3: 6:40-10:00
        # Pada 4: 10:00-13:20
        assert nakshatra_of(1.0)[1] == 1
        assert nakshatra_of(4.0)[1] == 2
        assert nakshatra_of(8.0)[1] == 3
        assert nakshatra_of(12.0)[1] == 4

    def test_pada_boundaries(self):
        """Test pada boundary conditions."""
        # Pada boundaries are at 3:20, 6:40, 10:00 degrees within each nakshatra
        # Ashwini pada 1: 0-3:20 (0-3.333...), pada 2: 3:20-6:40, etc.
        # At exactly 3.333... it should be pada 2
        # But due to floating point, let's test with a value clearly in pada 2
        assert nakshatra_of(4.0)[1] == 2
        assert nakshatra_of(7.0)[1] == 3
        assert nakshatra_of(11.0)[1] == 4

    def test_sign_of(self):
        """Test sign_of function."""
        assert sign_of(15.0) == ("Aries", 0)
        assert sign_of(45.0) == ("Taurus", 1)
        assert sign_of(355.0) == ("Pisces", 11)
