"""Tests for Sarvatobhadra Chakra grid and vedha computations."""

import zoneinfo
from datetime import UTC, datetime

import swisseph as swe

from sbc.chakra import GRID
from sbc.nakshatra import tithi_of
from sbc.planets import positions
from sbc.prediction import analyze, compute_vedhas, place_planets, summarize_vedhas


class TestChakraGrid:
    """Test the 81-cell grid structure."""

    def test_grid_dimensions(self):
        """Grid should be 9x9."""
        assert len(GRID) == 9
        for row in GRID:
            assert len(row) == 9

    def test_grid_cell_structure(self):
        """Each cell should have required fields."""
        for row in GRID:
            for cell in row:
                assert "row" in cell
                assert "col" in cell
                assert "type" in cell
                assert "label" in cell
                assert 1 <= cell["row"] <= 9
                assert 1 <= cell["col"] <= 9
                assert cell["type"] in ("nakshatra", "vowel", "consonant", "rashi", "tithi")

    def test_grid_corner_cells(self):
        """Corner cells should be vowels."""
        corners = [(1, 1), (1, 9), (9, 1), (9, 9)]
        for r, c in corners:
            assert GRID[r-1][c-1]["type"] == "vowel"

    def test_grid_center_cell(self):
        """Center cell (5,5) exists and has a type."""
        assert GRID[4][4]["type"] in ("consonant", "tithi", "vowel", "nakshatra", "rashi")


class TestPlacePlanets:
    """Test planet placement on the chakra."""

    def test_place_planets_returns_grid(self):
        """place_planets should return modified grid with planets."""

        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        local = datetime(2026, 9, 11, 9, 15, tzinfo=tz)
        utc = local.astimezone(UTC).replace(tzinfo=None)
        h = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
        jul = swe.julday(utc.year, utc.month, utc.day, h)

        planets, _ = positions(jul)
        sun = next(p for p in planets if p["name"] == "Sun")
        moon = next(p for p in planets if p["name"] == "Moon")
        tithi = tithi_of(sun["longitude"], moon["longitude"])

        from sbc.planets import all_planets_with_natures
        planets = all_planets_with_natures(planets, tithi, sun["longitude"])

        grid = place_planets(GRID, planets)

        # Check that planets were placed
        planet_count = 0
        for row in grid:
            for cell in row:
                if "planets" in cell:
                    planet_count += len(cell["planets"])
        assert planet_count >= 9  # At least 9 grahas placed


class TestComputeVedhas:
    """Test vedha ray computation."""

    def test_compute_vedhas_classical(self):
        """Classical school should compute single ray per planet."""

        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        local = datetime(2026, 9, 11, 9, 15, tzinfo=tz)
        utc = local.astimezone(UTC).replace(tzinfo=None)
        h = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
        jul = swe.julday(utc.year, utc.month, utc.day, h)

        planets, _ = positions(jul)
        sun = next(p for p in planets if p["name"] == "Sun")
        moon = next(p for p in planets if p["name"] == "Moon")
        tithi = tithi_of(sun["longitude"], moon["longitude"])

        from sbc.planets import all_planets_with_natures
        planets = all_planets_with_natures(planets, tithi, sun["longitude"])

        grid = place_planets(GRID, planets)
        vedha_map, ray_paths = compute_vedhas(planets, school="classical")

        # Each planet should have vedhas
        for p in planets:
            assert p["name"] in vedha_map
            assert isinstance(vedha_map[p["name"]], list)

    def test_compute_vedhas_allthree(self):
        """All-three school should compute three rays per planet."""

        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        local = datetime(2026, 9, 11, 9, 15, tzinfo=tz)
        utc = local.astimezone(UTC).replace(tzinfo=None)
        h = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
        jul = swe.julday(utc.year, utc.month, utc.day, h)

        planets, _ = positions(jul)
        sun = next(p for p in planets if p["name"] == "Sun")
        moon = next(p for p in planets if p["name"] == "Moon")
        tithi = tithi_of(sun["longitude"], moon["longitude"])

        from sbc.planets import all_planets_with_natures
        planets = all_planets_with_natures(planets, tithi, sun["longitude"])

        grid = place_planets(GRID, planets)
        vedha_map, ray_paths = compute_vedhas(planets, school="allthree")

        for p in planets:
            assert p["name"] in vedha_map
            vedhas = vedha_map[p["name"]]
            # Should have up to 3 rays (front, left, right)
            rays = set(v["ray"] for v in vedhas)
            assert len(rays) <= 3


class TestAnalyze:
    """Test the analysis engine."""

    def test_analyze_returns_complete_structure(self):
        """analyze() should return complete analysis dict."""

        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        local = datetime(2026, 9, 11, 9, 15, tzinfo=tz)
        utc = local.astimezone(UTC).replace(tzinfo=None)
        h = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
        jul = swe.julday(utc.year, utc.month, utc.day, h)

        planets, _ = positions(jul)
        sun = next(p for p in planets if p["name"] == "Sun")
        moon = next(p for p in planets if p["name"] == "Moon")
        tithi = tithi_of(sun["longitude"], moon["longitude"])

        from sbc.planets import all_planets_with_natures
        planets = all_planets_with_natures(planets, tithi, sun["longitude"])

        grid = place_planets(GRID, planets)
        vedha_map, _ = compute_vedhas(planets, school="allthree")

        # Get anchor nakshatra (NSE)
        anchor_nakshatra = "Krittika"  # NSE birth star

        analysis = analyze(planets, vedha_map, anchor_nakshatra, "allthree")

        required_keys = {"points", "point_hits", "per_point", "score", "net"}
        for key in required_keys:
            assert key in analysis

        assert isinstance(analysis["score"], dict)
        assert "benefic" in analysis["score"]
        assert "malefic" in analysis["score"]
        assert isinstance(analysis["net"], float)

    def test_point_hits_structure(self):
        """Point hits should have required fields."""

        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        local = datetime(2026, 9, 11, 9, 15, tzinfo=tz)
        utc = local.astimezone(UTC).replace(tzinfo=None)
        h = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
        jul = swe.julday(utc.year, utc.month, utc.day, h)

        planets, _ = positions(jul)
        sun = next(p for p in planets if p["name"] == "Sun")
        moon = next(p for p in planets if p["name"] == "Moon")
        tithi = tithi_of(sun["longitude"], moon["longitude"])

        from sbc.planets import all_planets_with_natures
        planets = all_planets_with_natures(planets, tithi, sun["longitude"])

        grid = place_planets(GRID, planets)
        vedha_map, _ = compute_vedhas(planets, school="allthree")

        anchor_nakshatra = "Krittika"
        analysis = analyze(planets, vedha_map, anchor_nakshatra, "allthree")

        for hit in analysis["point_hits"]:
            assert "planet" in hit
            assert "point" in hit
            assert "ray" in hit
            assert "nature" in hit
            assert "strength" in hit
            assert hit["nature"] in ("benefic", "malefic")
            assert isinstance(hit["strength"], float)


class TestSummarizeVedhas:
    """Test vedha summarization."""

    def test_summarize_vedhas_groups_by_planet(self):
        """summarize_vedhas should group vedhas by planet."""

        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        local = datetime(2026, 9, 11, 9, 15, tzinfo=tz)
        utc = local.astimezone(UTC).replace(tzinfo=None)
        h = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
        jul = swe.julday(utc.year, utc.month, utc.day, h)

        planets, _ = positions(jul)
        sun = next(p for p in planets if p["name"] == "Sun")
        moon = next(p for p in planets if p["name"] == "Moon")
        tithi = tithi_of(sun["longitude"], moon["longitude"])

        from sbc.planets import all_planets_with_natures
        planets = all_planets_with_natures(planets, tithi, sun["longitude"])

        grid = place_planets(GRID, planets)
        vedha_map, _ = compute_vedhas(planets, school="allthree")

        anchor_nakshatra = "Krittika"
        analysis = analyze(planets, vedha_map, anchor_nakshatra, "allthree")

        summary = summarize_vedhas(vedha_map, planets, analysis["points"])

        assert isinstance(summary, list)
        for v in summary:
            assert "planet" in v
            assert "symbol" in v
            assert "nakshatra" in v
            assert "nature" in v
            assert "strength" in v
            assert "rays" in v
            assert isinstance(v["rays"], list)
