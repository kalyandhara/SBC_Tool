"""
Detailed Moon nakshatra transit check with finer granularity
"""
import sys
sys.path.insert(0, r'D:\SBC_Tool')

import swisseph as swe
import datetime
from zoneinfo import ZoneInfo

swe.set_sid_mode(swe.SIDM_LAHIRI)

NAKSHATRAS_27 = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "P.Phalguni", "U.Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "P.Ashadha", "U.Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "P.Bhadrapada", "U.Bhadrapada", "Revati",
]

NAKSHATRA_SPAN = 360.0 / 27.0
ABHIJIT_START = 276.0 + 40.0 / 60.0
ABHIJIT_END = 280.0 + 53.0 / 60.0 + 20.0 / 3600.0

def nakshatra_of(longitude):
    lon = longitude % 360.0
    if ABHIJIT_START <= lon < ABHIJIT_END:
        return "Abhijit", 1
    idx = int(lon // NAKSHATRA_SPAN)
    if idx >= 27:
        idx = 26
    pada = int((lon % NAKSHATRA_SPAN) // (NAKSHATRA_SPAN / 4.0)) + 1
    return NAKSHATRAS_27[idx], pada

def sign_of(longitude):
    RASHIS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
              "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    idx = int(longitude % 360.0) // 30
    return RASHIS[idx], idx

def get_planet_lon(julian_day, planet_id):
    flags = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    xx, _ = swe.calc_ut(julian_day, planet_id, flags)
    return xx[0] % 360.0, xx[3]

# Check Moon nakshatra transitions day by day with 15-min intervals
print("MOON NAKSHATRA TRANSITS (15-min intervals Aug 22-29)")
print("=" * 70)

prev_nak = None
for day in range(22, 30):
    for hour in range(0, 24):
        for minute in [0, 15, 30, 45]:
            dt = datetime.datetime(2026, 8, day, hour, minute, tzinfo=ZoneInfo('Asia/Kolkata'))
            utc = dt.astimezone(datetime.timezone.utc)
            jul = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)
            moon_lon, _ = get_planet_lon(jul, swe.MOON)
            nak, _ = nakshatra_of(moon_lon)
            sign, _ = sign_of(moon_lon)
            
            if nak != prev_nak:
                print(f"  {dt.strftime('%b %d, %I:%M %p')} IST: Moon enters {nak} ({sign} {moon_lon:.2f}°)")
                prev_nak = nak

print("\n" + "=" * 70)
print("SUN-MERCURY CONJUNCTION - precise timing")
print("=" * 70)

def angle(a, b):
    return abs((a - b + 180) % 360 - 180)

# Check every 15 mins on Aug 26-27
for day in [26, 27]:
    for hour in range(0, 24):
        for minute in [0, 15, 30, 45]:
            dt = datetime.datetime(2026, 8, day, hour, minute, tzinfo=ZoneInfo('Asia/Kolkata'))
            utc = dt.astimezone(datetime.timezone.utc)
            jul = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)
            sun_lon, _ = get_planet_lon(jul, swe.SUN)
            mer_lon, _ = get_planet_lon(jul, swe.MERCURY)
            sep = angle(sun_lon, mer_lon)
            if sep < 2.0:
                print(f"  {dt.strftime('%b %d, %I:%M %p')} IST: Sep={sep:.2f}° Sun={sun_lon:.2f}° Mer={mer_lon:.2f}°")

print("\n" + "=" * 70)
print("VENUS NAKSHATRA TRANSITS (Hasta -> Chitra -> Swati)")
print("=" * 70)

prev_nak = None
for day in range(22, 29):
    for hour in range(0, 24, 2):
        for minute in [0, 30]:
            dt = datetime.datetime(2026, 8, day, hour, minute, tzinfo=ZoneInfo('Asia/Kolkata'))
            utc = dt.astimezone(datetime.timezone.utc)
            jul = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)
            ven_lon, _ = get_planet_lon(jul, swe.VENUS)
            nak, _ = nakshatra_of(ven_lon)
            if nak != prev_nak:
                sign, _ = sign_of(ven_lon)
                print(f"  {dt.strftime('%b %d, %I:%M %p')} IST: Venus enters {nak} ({sign} {ven_lon:.2f}°)")
                prev_nak = nak