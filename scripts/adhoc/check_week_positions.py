import datetime
from zoneinfo import ZoneInfo

import swisseph as swe

from sbc.planets import positions

# Check positions for each day this week (Aug 23 - Aug 29)
for day_offset in range(7):
    date = datetime.date(2026, 8, 23) + datetime.timedelta(days=day_offset)
    local = datetime.datetime.combine(date, datetime.time(12, 0), tzinfo=ZoneInfo('Asia/Kolkata'))
    utc = local.astimezone(datetime.UTC)
    jul = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)

    planets, _ = positions(jul)
    sun = next(p for p in planets if p["name"] == "Sun")
    mercury = next(p for p in planets if p["name"] == "Mercury")
    ketu = next(p for p in planets if p["name"] == "Ketu")

    # Calculate separations
    def angle(lon1, lon2):
        return abs((lon1 - lon2 + 180) % 360 - 180)

    sun_mercury = angle(sun["longitude"], mercury["longitude"])
    sun_ketu = angle(sun["longitude"], ketu["longitude"])
    mercury_ketu = angle(mercury["longitude"], ketu["longitude"])

    print(f"\n{date} ({date.strftime('%A')}):")
    print(f"  Sun:      {sun['sign']} {sun['degree']:.2f}° ({sun['nakshatra']})")
    print(f"  Mercury:  {mercury['sign']} {mercury['degree']:.2f}° ({mercury['nakshatra']})")
    print(f"  Ketu:     {ketu['sign']} {ketu['degree']:.2f}° ({ketu['nakshatra']})")
    print(f"  Sun-Mercury: {sun_mercury:.2f}° | Sun-Ketu: {sun_ketu:.2f}° | Mercury-Ketu: {mercury_ketu:.2f}°")
