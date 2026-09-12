"""
Cross-check daily astro events with precise timestamps
"""
import sys
sys.path.insert(0, r'D:\SBC_Tool')

import swisseph as swe
import datetime
from zoneinfo import ZoneInfo

# Set Lahiri ayanamsa
swe.set_sid_mode(swe.SIDM_LAHIRI)

# Nakshatra boundaries (Lahiri, 27 nakshatras)
NAKSHATRAS_27 = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "P.Phalguni", "U.Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "P.Ashadha", "U.Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "P.Bhadrapada", "U.Bhadrapada", "Revati",
]

NAKSHATRA_SPAN = 360.0 / 27.0  # 13°20'

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

# Check events for each day with precise timing
print("=" * 70)
print("CROSS-CHECK: AstroNaresh Events vs Tool Calculations")
print("=" * 70)

# 1. Mercury enters Leo - 22 Aug, 7:33 PM IST
print("\n1. MERCURY ENTERS LEO (AstroNaresh: 22 Aug, 7:33 PM IST)")
for hour in range(18, 21):
    for minute in [0, 15, 30, 45]:
        dt = datetime.datetime(2026, 8, 22, hour, minute, tzinfo=ZoneInfo('Asia/Kolkata'))
        utc = dt.astimezone(datetime.timezone.utc)
        jul = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)
        mer_lon, _ = get_planet_lon(jul, swe.MERCURY)
        sign, _ = sign_of(mer_lon)
        nak, _ = nakshatra_of(mer_lon)
        if sign == "Leo":
            print(f"   FIRST Leo entry: {dt.strftime('%b %d, %I:%M %p')} IST - {sign} {mer_lon:.2f}° ({nak})")
            break
    else:
        continue
    break

# 2. Mercury-Ketu-Sun Triangle - check daily positions
print("\n2. MERCURY-KETU-SUN TRIANGLE IN LEO (till Sep 7)")
for day in range(22, 30):
    dt = datetime.datetime(2026, 8, day, 12, 0, tzinfo=ZoneInfo('Asia/Kolkata'))
    utc = dt.astimezone(datetime.timezone.utc)
    jul = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)
    
    sun_lon, _ = get_planet_lon(jul, swe.SUN)
    mer_lon, _ = get_planet_lon(jul, swe.MERCURY)
    rahu_lon, _ = get_planet_lon(jul, swe.MEAN_NODE)
    ketu_lon = (rahu_lon + 180) % 360
    
    def angle(a, b):
        return abs((a - b + 180) % 360 - 180)
    
    sun_sign, _ = sign_of(sun_lon)
    mer_sign, _ = sign_of(mer_lon)
    ketu_sign, _ = sign_of(ketu_lon)
    
    sun_mer = angle(sun_lon, mer_lon)
    sun_ketu = angle(sun_lon, ketu_lon)
    mer_ketu = angle(mer_lon, ketu_lon)
    
    in_leo = "ALL IN LEO" if (sun_sign == mer_sign == ketu_sign == "Leo") else ""
    print(f"   Aug {day}: Sun {sun_lon:.2f}°({sun_sign}), Mer {mer_lon:.2f}°({mer_sign}), Ke {ketu_lon:.2f}°({ketu_sign}) | S-M:{sun_mer:.1f}° S-K:{sun_ketu:.1f}° M-K:{mer_ketu:.1f}° {in_leo}")

# 3. Venus enters Chitra - 25 Aug, 12:55 PM
print("\n3. VENUS ENTERS CHITRA (AstroNaresh: 25 Aug, 12:55 PM IST)")
for hour in range(11, 15):
    for minute in [0, 15, 30, 45]:
        dt = datetime.datetime(2026, 8, 25, hour, minute, tzinfo=ZoneInfo('Asia/Kolkata'))
        utc = dt.astimezone(datetime.timezone.utc)
        jul = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)
        ven_lon, _ = get_planet_lon(jul, swe.VENUS)
        nak, _ = nakshatra_of(ven_lon)
        if nak == "Chitra":
            print(f"   FIRST Chitra entry: {dt.strftime('%b %d, %I:%M %p')} IST - {nak} {ven_lon:.2f}°")
            break
    else:
        continue
    break

# 4. Sun-Mercury Conjunction at 0° - 27 Aug, 10:30 AM
print("\n4. SUN-MERCURY CONJUNCTION (AstroNaresh: 27 Aug, 10:30 AM IST)")
for hour in range(8, 13):
    for minute in [0, 15, 30, 45]:
        dt = datetime.datetime(2026, 8, 27, hour, minute, tzinfo=ZoneInfo('Asia/Kolkata'))
        utc = dt.astimezone(datetime.timezone.utc)
        jul = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)
        sun_lon, _ = get_planet_lon(jul, swe.SUN)
        mer_lon, _ = get_planet_lon(jul, swe.MERCURY)
        sep = angle(sun_lon, mer_lon)
        if sep < 1.0:
            print(f"   Exact conjunction: {dt.strftime('%b %d, %I:%M %p')} IST - Separation {sep:.2f}°")
            break
    else:
        continue
    break

# 5-9. Moon nakshatra entries
print("\n5-9. MOON NAKSHATRA TRANSITS")
moon_events = [
    ("Purva Ashada", "2026-08-23 17:44"),
    ("Uttara Ashada", "2026-08-24 20:27"),
    ("Shravana", "2026-08-25 22:50"),
    ("Dhanishta", "2026-08-27 00:47"),
    ("Shatabhisha", "2026-08-28 02:15"),
]

for nak_name, expected_str in moon_events:
    expected = datetime.datetime.fromisoformat(expected_str).replace(tzinfo=ZoneInfo('Asia/Kolkata'))
    print(f"\n   {nak_name} (Expected: {expected.strftime('%b %d, %I:%M %p')} IST)")
    
    # Search around expected time ±3 hours
    for offset_min in range(-180, 181, 15):
        dt = expected + datetime.timedelta(minutes=offset_min)
        utc = dt.astimezone(datetime.timezone.utc)
        jul = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)
        moon_lon, _ = get_planet_lon(jul, swe.MOON)
        nak, _ = nakshatra_of(moon_lon)
        if nak == nak_name:
            print(f"   TOOL: {dt.strftime('%b %d, %I:%M %p')} IST - {nak} {moon_lon:.2f}°")
            diff = (dt - expected).total_seconds() / 60
            print(f"   DIFF: {diff:+.0f} minutes")
            break

print("\n" + "=" * 70)
print("SUMMARY: Compare tool vs AstroNaresh timestamps")
print("=" * 70)