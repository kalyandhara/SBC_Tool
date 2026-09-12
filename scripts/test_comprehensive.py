import sys
sys.path.insert(0, r'D:\SBC_Tool')

from sbc.nakshatra import nakshatra_of, sign_of, tithi_of, paksha_of, moon_nature, gandanta_of, sensitive_stars
from sbc.chakra import GRID, NAKSHATRA_CELL, RASHI_CELL, vedha_cells
from sbc.planets import positions, refine_natures, dignity_multiplier, all_planets_with_natures, NATURAL_NATURE, EXALT, DEBIL, COMBUST_ORB
from sbc.prediction import place_planets, compute_vedhas, analyze, summarize_vedhas, sentiment_of, recommendation, sector_read, planet_sector_read
from sbc.backtest import run_backtest, _julian_at_noon, _future_score, _bullish_future_score, run_futurecast, run_bullish_futurecast
from sbc.market_calendar import jupiter_market_analysis, upcoming_yoga_alerts, reversal_alert, transit_alert, lunar_phase_alert

# Test nakshatra module
print("Testing nakshatra module...")
assert nakshatra_of(0) == ("Ashwini", 1)
assert nakshatra_of(30) == ("Krittika", 1)
print("  nakshatra_of OK")

assert sign_of(0) == ("Aries", 0)
assert sign_of(30) == ("Taurus", 1)
print("  sign_of OK")

assert tithi_of(0, 0) == 1
assert tithi_of(0, 180) == 16
print("  tithi_of OK")

assert paksha_of(1) == "Shukla"
assert paksha_of(16) == "Krishna"
print("  paksha_of OK")

assert moon_nature(1) == "malefic"  # Shukla Pratipada is ashubha
assert moon_nature(30) == "malefic"  # Amavasya is ashubha
assert moon_nature(10) == "benefic"  # Shukla Dashami is shubha
print("  moon_nature OK")

assert gandanta_of(0) == True
assert gandanta_of(10) == False
print("  gandanta_of OK")

stars = sensitive_stars("Ashwini")
assert len(stars) == 9
print("  sensitive_stars OK")

# Test chakra module
print("Testing chakra module...")
assert len(GRID) == 9
assert len(GRID[0]) == 9
assert "Ashwini" in NAKSHATRA_CELL
assert "Aries" in RASHI_CELL
print("  GRID and cell maps OK")

# Test planets module
print("Testing planets module...")
planets, ayanamsa = positions(2459800.5)  # Some date
assert len(planets) == 9
assert all("name" in p for p in planets)
print("  positions OK")

# Test prediction module
print("Testing prediction module...")
planets, _ = positions(2459800.5)
from sbc.nakshatra import tithi_of
sun = next(p for p in planets if p["name"] == "Sun")
moon = next(p for p in planets if p["name"] == "Moon")
tithi = tithi_of(sun["longitude"], moon["longitude"])
planets = all_planets_with_natures(planets, tithi, sun["longitude"])
grid = place_planets(GRID, planets)
vedha_map, ray_paths = compute_vedhas(planets, school="classical")
assert len(vedha_map) == 9
analysis = analyze(planets, vedha_map, "Mula", "classical")
assert "net" in analysis
print("  prediction module OK")

# Test backtest
print("Testing backtest module...")
result = run_backtest()
assert "accuracy" in result
assert result["total"] == 7
print("  run_backtest OK")

result = run_futurecast()
assert "windows" in result
print("  run_futurecast OK")

result = run_bullish_futurecast()
assert "clusters" in result
print("  run_bullish_futurecast OK")

# Test market_calendar
print("Testing market_calendar module...")
planets, _ = positions(2459800.5)
jupiter_analysis = jupiter_market_analysis(planets)
assert "active" in jupiter_analysis
print("  jupiter_market_analysis OK")

reversal = reversal_alert("2026-08-15")
assert "active" in reversal
print("  reversal_alert OK")

events = upcoming_yoga_alerts("2026-08-15", "09:15", "Asia/Kolkata")
assert len(events) > 0
print("  upcoming_yoga_alerts OK")

print("\nAll comprehensive tests passed!")