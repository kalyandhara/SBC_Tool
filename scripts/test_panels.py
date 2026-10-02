import sys

sys.path.insert(0, r'D:\SBC_Tool')
from app import app

with app.test_client() as client:
    # Test futurecast APIs
    resp = client.get('/api/futurecast?date=2026-08-24')
    print('Futurecast:', resp.status_code)
    import json
    data = json.loads(resp.data)
    print('  windows:', len(data.get('windows', [])))
    print('  timeline_windows:', len(data.get('timeline_windows', [])))

    resp = client.get('/api/bullish_futurecast?date=2026-08-24')
    print('\nBullish Futurecast:', resp.status_code)
    data = json.loads(resp.data)
    print('  clusters:', len(data.get('clusters', [])))

    resp = client.get('/api/bearish_futurecast?date=2026-08-24')
    print('\nBearish Futurecast:', resp.status_code)
    data = json.loads(resp.data)
    print('  clusters:', len(data.get('clusters', [])))

    # Test yoga alerts
    import datetime
    from zoneinfo import ZoneInfo

    import swisseph as swe

    from sbc.market_calendar import upcoming_yoga_alerts
    from sbc.nakshatra import tithi_of
    from sbc.planets import all_planets_with_natures, positions

    date = datetime.date(2026, 8, 24)
    local = datetime.datetime.combine(date, datetime.time(9, 15), tzinfo=ZoneInfo('Asia/Kolkata'))
    utc = local.astimezone(datetime.UTC)
    jul = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)

    planets, ayanamsa = positions(jul)
    sun = next(p for p in planets if p["name"] == "Sun")
    moon = next(p for p in planets if p["name"] == "Moon")
    tithi = tithi_of(sun["longitude"], moon["longitude"])
    planets = all_planets_with_natures(planets, tithi, sun["longitude"])

    yoga = upcoming_yoga_alerts("2026-08-24", "09:15", "Asia/Kolkata", days=7)
    print(f'\nYoga alerts: {len(yoga)}')
    for y in yoga[:5]:
        print(f'  {y["date"]}: {y["type"]}')
