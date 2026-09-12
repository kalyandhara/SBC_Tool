"""Minimal unit tests for SBC core modules."""

import sys
sys.path.insert(0, "D:\\SBC_Tool - Copy")

def test_chakra_layout():
    from sbc.chakra import GRID, NAKSHATRA_CELL
    assert len(GRID) == 9
    assert all(len(row) == 9 for row in GRID)
    # At least 28 nakshatra cells
    assert len(NAKSHATRA_CELL) >= 28
    print("OK chakra layout")

def test_sensitive_stars():
    from sbc.nakshatra import sensitive_stars
    pts = sensitive_stars("Mula")
    assert len(pts) == 9
    assert pts[0]["name"] == "Janma"
    assert pts[0]["nakshatra"] == "Mula"
    print("OK sensitive stars")

def test_tithi_of():
    from sbc.nakshatra import tithi_of
    # Sun at 0°, Moon at 0° => tithi 1
    t = tithi_of(0.0, 0.0)
    assert t == 1
    # Moon 15° ahead => tithi ~2
    t2 = tithi_of(0.0, 15.0)
    assert t2 == 2
    print("OK tithi")

def test_analyze():
    from sbc.planets import positioned_planets
    from sbc.prediction import analyze, compute_vedhas
    planets, _, _, _, _ = positioned_planets("2026-08-15", "09:15", "Asia/Kolkata")
    vedha_map, _ = compute_vedhas(planets, school="classical")
    analysis = analyze(planets, vedha_map, "Mula", "classical")
    assert "net" in analysis
    assert "score" in analysis
    assert "point_hits" in analysis
    print("OK analyze")

if __name__ == "__main__":
    test_chakra_layout()
    test_sensitive_stars()
    test_tithi_of()
    test_analyze()
    print("All core tests passed")
