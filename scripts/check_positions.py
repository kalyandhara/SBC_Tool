import datetime
from zoneinfo import ZoneInfo

import swisseph as swe

from sbc.planets import positions

date = datetime.date(2026, 8, 23)
local = datetime.datetime.combine(date, datetime.time(12, 0), tzinfo=ZoneInfo('Asia/Kolkata'))
utc = local.astimezone(datetime.UTC)
jul = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)

planets, ayanamsa = positions(jul)
for p in planets:
    print(f'{p["name"]:8s} | {p["sign"]:10s} | {p["degree"]:6.2f} | {p["nakshatra"]:15s} | retro={p["retrograde"]} | speed={p["speed"]:.4f}')
