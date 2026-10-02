import sys

sys.path.insert(0, r'D:\SBC_Tool')

import datetime
from zoneinfo import ZoneInfo

import swisseph as swe

from sbc.nakshatra import tithi_of
from sbc.planets import all_planets_with_natures, positions

# Check planetary positions for Aug 24
date = datetime.date(2026, 8, 24)
local = datetime.datetime.combine(date, datetime.time(12, 0), tzinfo=ZoneInfo('Asia/Kolkata'))
utc = local.astimezone(datetime.UTC)
jul = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)

planets, ayanamsa = positions(jul)
sun = next(p for p in planets if p["name"] == "Sun")
moon = next(p for p in planets if p["name"] == "Moon")
tithi = tithi_of(sun["longitude"], moon["longitude"])
planets = all_planets_with_natures(planets, tithi, sun["longitude"])

print("Current planetary nakshatras:")
for p in planets:
    print(f"  {p['name']:8s} -> {p['nakshatra']:15s} ({p['sign']} {p['degree']:.2f})")

print("\nTrigger conditions check:")
triggers = {
    ("Sun", "Ashlesha"): "Ashlesha Heat",
    ("Mars", "Ashlesha"): "Ashlesha Heat",
    ("Mars", "Dhanishta"): "Dhanishta/Chitra Industrial",
    ("Mars", "Chitra"): "Dhanishta/Chitra Industrial",
    ("Saturn", "Rohini"): "Rohini Liquid",
    ("Rahu", "Rohini"): "Rohini Liquid",
    ("Sun", "Swati"): "Swati Air/Tech",
    ("Mercury", "Swati"): "Swati Air/Tech",
    ("Jupiter", "Pushya"): "Pushya/Punarvasu Financial",
    ("Jupiter", "Punarvasu"): "Pushya/Punarvasu Financial",
    ("Mars", "Krittika"): "Krittika Bullion",
    ("Sun", "Krittika"): "Krittika Bullion",
    ("Venus", "Magha"): "Magha/Purva Auto",
    ("Venus", "P.Phalguni"): "Magha/Purva Auto",
    ("Saturn", "U.Bhadrapada"): "Uttara Bhadrapada Realty",
}

for (planet_name, nakshatra), vedha_name in triggers.items():
    planet = next((p for p in planets if p["name"] == planet_name), None)
    if planet:
        match = " *** MATCH ***" if planet["nakshatra"] == nakshatra else ""
        print(f"  {vedha_name}: {planet_name} in {nakshatra} -> Actual: {planet['nakshatra']}{match}")
