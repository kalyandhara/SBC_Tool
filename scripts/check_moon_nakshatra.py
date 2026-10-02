import datetime
from zoneinfo import ZoneInfo

import swisseph as swe

from sbc.planets import positions

# Check Moon nakshatra for each day this week
for day_offset in range(7):
    date = datetime.date(2026, 8, 23) + datetime.timedelta(days=day_offset)
    local = datetime.datetime.combine(date, datetime.time(12, 0), tzinfo=ZoneInfo('Asia/Kolkata'))
    utc = local.astimezone(datetime.UTC)
    jul = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)

    planets, _ = positions(jul)
    moon = next(p for p in planets if p["name"] == "Moon")

    print(f"{date} ({date.strftime('%A')}): Moon in {moon['sign']} {moon['degree']:.2f}° - {moon['nakshatra']}")
