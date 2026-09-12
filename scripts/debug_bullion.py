import sys
sys.path.insert(0, r'D:\SBC_Tool')

from sbc.planets import positions, all_planets_with_natures
from sbc.nakshatra import tithi_of
from sbc.prediction import compute_vedhas
import swisseph as swe
import datetime
from zoneinfo import ZoneInfo

# Check planetary positions for Aug 24
date = datetime.date(2026, 8, 24)
local = datetime.datetime.combine(date, datetime.time(12, 0), tzinfo=ZoneInfo('Asia/Kolkata'))
utc = local.astimezone(datetime.timezone.utc)
jul = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)

planets, ayanamsa = positions(jul)
sun = next(p for p in planets if p["name"] == "Sun")
moon = next(p for p in planets if p["name"] == "Moon")
tithi = tithi_of(sun["longitude"], moon["longitude"])
planets = all_planets_with_natures(planets, tithi, sun["longitude"])

print("Planetary positions with natures:")
for p in planets:
    print(f"  {p['name']:8s} | {p['sign']:10s} {p['degree']:6.2f} | {p['nakshatra']:15s} | {p['nature']:8s} | retro={p['retrograde']}")

print("\nComputing vedha map...")
vedha_map, _ = compute_vedhas(planets, school="classical")

# Check for bullion nakshatra hits
from sbc.bullion_vedha import BULLION_NAKSHATRAS

for p in planets:
    hits = vedha_map.get(p["name"], [])
    bullion_hits = [h for h in hits if h.get("label") in BULLION_NAKSHATRAS]
    if bullion_hits:
        print(f"\n{p['name']} in {p['nakshatra']} hits bullion nakshatras:")
        for h in bullion_hits:
            print(f"   -> {h['label']} via {h['ray']} ray (row={h['row']}, col={h['col']})")

# Check specific detectors
print("\n=== Krittika check ===")
for p in planets:
    if p["nakshatra"] == "Krittika":
        print(f"  {p['name']} in Krittika!")
    hits = vedha_map.get(p["name"], [])
    k_hits = [h for h in hits if h.get("label") == "Krittika"]
    if k_hits:
        print(f"  {p['name']} casts vedha on Krittika: {len(k_hits)} hits")

print("\n=== Rohini check ===")
for p in planets:
    if p["nakshatra"] == "Rohini":
        print(f"  {p['name']} in Rohini!")
    hits = vedha_map.get(p["name"], [])
    r_hits = [h for h in hits if h.get("label") == "Rohini"]
    if r_hits:
        print(f"  {p['name']} casts vedha on Rohini: {len(r_hits)} hits")

print("\n=== Sun-Jupiter check ===")
sun = next(p for p in planets if p["name"] == "Sun")
jupiter = next(p for p in planets if p["name"] == "Jupiter")
print(f"  Sun: {sun['nakshatra']}, Jupiter: {jupiter['nakshatra']}")
print(f"  Separation: {abs((sun['longitude'] - jupiter['longitude'] + 180) % 360 - 180):.2f}°")

print("\n=== Venus-Moon check ===")
venus = next(p for p in planets if p["name"] == "Venus")
moon = next(p for p in planets if p["name"] == "Moon")
print(f"  Venus: {venus['nakshatra']} (nature={venus['nature']}), Moon: {moon['nakshatra']}")
venus_hits = vedha_map.get("Venus", [])
moon_hits = [h for h in venus_hits if h.get("label") == moon["nakshatra"]]
print(f"  Venus hits Moon nakshatra ({moon['nakshatra']}): {len(moon_hits)}")

print("\n=== Retrograde malefics in fire signs ===")
for p in planets:
    if p["name"] in ("Mars", "Saturn") and p["retrograde"] and p["sign"] in ("Aries", "Leo", "Sagittarius"):
        print(f"  {p['name']} R in {p['sign']} ({p['nakshatra']})!")