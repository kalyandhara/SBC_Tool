import sys
sys.path.insert(0, r'D:\SBC_Tool')

from sbc.planets import positions, all_planets_with_natures
from sbc.nakshatra import tithi_of, nakshatra_of, moon_nature, paksha_of
from sbc.cgsp_framework import is_pada_bullish

import datetime
import zoneinfo

def get_planets(date_str):
    local = datetime.datetime.strptime(date_str + ' 09:15', '%Y-%m-%d %H:%M')
    tz = zoneinfo.ZoneInfo('Asia/Kolkata')
    local = local.replace(tzinfo=tz)
    utc = local.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    
    base = datetime.datetime(2000, 1, 1, 12, 0, 0)
    diff = utc - base
    jul = 2451545.0 + diff.total_seconds() / 86400.0
    
    planets, _ = positions(jul)
    sun = next(p for p in planets if p['name'] == 'Sun')
    moon = next(p for p in planets if p['name'] == 'Moon')
    tithi = tithi_of(sun['longitude'], moon['longitude'])
    planets = all_planets_with_natures(planets, tithi, sun['longitude'])
    return planets, tithi, sun, moon

def angular_distance(lon1, lon2):
    return abs((lon1 - lon2 + 180) % 360 - 180)

# Check trigger 2: Jupiter-Sun conjunction in fire sign
print('=== TRIGGER 2 DEBUG: Jupiter-Sun in Fire Sign ===')
for date_str in ['2023-04-20', '2023-04-21', '2023-04-22', '2023-04-23']:
    planets, tithi, sun, moon = get_planets(date_str)
    jupiter = next(p for p in planets if p['name'] == 'Jupiter')
    dist = angular_distance(sun['longitude'], jupiter['longitude'])
    print('{}: Sun={:.2f} {} Jup={:.2f} {} Dist={:.2f} Fire={} Conj={}'.format(
        date_str, sun['longitude'], sun['sign'], jupiter['longitude'], jupiter['sign'],
        dist, sun['sign'] in {"Aries","Leo","Sagittarius"}, dist<10))

print()
print('=== TRIGGER 3 DEBUG: Mercury Direct in Friendly Sign + Bullish Pada ===')
for date_str in ['2023-05-15', '2023-05-16', '2023-05-17', '2023-09-15', '2023-09-16', '2023-09-17', '2024-01-01', '2024-01-02']:
    planets, tithi, sun, moon = get_planets(date_str)
    mercury = next(p for p in planets if p['name'] == 'Mercury')
    pada_bullish = is_pada_bullish(mercury['nakshatra'], mercury['pada'])
    friendly = mercury['sign'] in {'Gemini', 'Virgo', 'Libra'}
    print('{}: Merc={:.2f} {} Retro={} Pada={} Nak={} Friendly={} PadaBull={}'.format(
        date_str, mercury['longitude'], mercury['sign'], mercury['retrograde'],
        mercury['pada'], mercury['nakshatra'], friendly, pada_bullish))

print()
print('=== TRIGGER 4 DEBUG: Saturn in Capricorn + Moon in Krittika ===')
for date_str in ['2021-01-15', '2021-02-15', '2021-03-15']:
    planets, tithi, sun, moon = get_planets(date_str)
    saturn = next(p for p in planets if p['name'] == 'Saturn')
    print('{}: Saturn={:.2f} {} Moon={:.2f} {} Nak={} Krittika={}'.format(
        date_str, saturn['longitude'], saturn['sign'], moon['longitude'], moon['sign'],
        moon['nakshatra'], moon['nakshatra']=="Krittika"))

print()
print('=== TRIGGER 5 DEBUG: Rahu in Heavy Metal Nak + Moon in Water ===')
for date_str in ['2023-01-15', '2023-06-15', '2023-12-15', '2024-06-15']:
    planets, tithi, sun, moon = get_planets(date_str)
    rahu = next(p for p in planets if p['name'] == 'Rahu')
    water = moon['sign'] in {'Cancer', 'Scorpio', 'Pisces'}
    heavy = rahu['nakshatra'] in {'Ashwini', 'Mrigashira', 'Ardra'}
    print('{}: Rahu={:.2f} {} Nak={} Heavy={} Moon={} Water={}'.format(
        date_str, rahu['longitude'], rahu['sign'], rahu['nakshatra'], heavy, moon['sign'], water))

print()
print('=== TRIGGER 7 DEBUG: Sun-Ketu Square in Fixed Sign ===')
for date_str in ['2023-01-15', '2023-04-15', '2023-07-15', '2023-10-15']:
    planets, tithi, sun, moon = get_planets(date_str)
    ketu = next(p for p in planets if p['name'] == 'Ketu')
    dist = angular_distance(sun['longitude'], ketu['longitude'])
    square = abs(dist - 90) < 5
    fixed = sun['sign'] in {'Taurus', 'Leo', 'Scorpio', 'Aquarius'}
    print('{}: Sun={:.2f} {} Ketu={:.2f} {} Dist={:.2f} Square={} Fixed={}'.format(
        date_str, sun['longitude'], sun['sign'], ketu['longitude'], ketu['sign'],
        dist, square, fixed))

print()
print('=== TRIGGER 8 DEBUG: Mars in Benefic Sign Pada 1/2 ===')
for date_str in ['2023-01-15', '2023-03-15', '2023-06-15', '2023-09-15', '2023-12-15']:
    planets, tithi, sun, moon = get_planets(date_str)
    mars = next(p for p in planets if p['name'] == 'Mars')
    benefic = mars['sign'] in {'Cancer', 'Libra', 'Capricorn'}
    pada_ok = mars['pada'] in (1, 2)
    print('{}: Mars={:.2f} {} Pada={} Nak={} Benefic={} PadaOK={}'.format(
        date_str, mars['longitude'], mars['sign'], mars['pada'], mars['nakshatra'], benefic, pada_ok))