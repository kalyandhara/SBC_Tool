import datetime
from zoneinfo import ZoneInfo

import swisseph as swe

from sbc.market_calendar import (
    get_all_bullish_reversal_windows,
    jupiter_market_analysis,
    lunar_phase_alert,
    reversal_alert,
    transit_alert,
)
from sbc.nakshatra import tithi_of
from sbc.planets import all_planets_with_natures, positions

date = datetime.date(2026, 8, 23)
local = datetime.datetime.combine(date, datetime.time(12, 0), tzinfo=ZoneInfo('Asia/Kolkata'))
utc = local.astimezone(datetime.UTC)
jul = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)

planets, ayanamsa = positions(jul)
sun = next(p for p in planets if p["name"] == "Sun")
moon = next(p for p in planets if p["name"] == "Moon")
tithi = tithi_of(sun["longitude"], moon["longitude"])
planets = all_planets_with_natures(planets, tithi, sun["longitude"])

# Get reversal alerts
alert = reversal_alert("2026-08-23", planets, tithi)

print("=== ACTIVE REVERSAL WINDOWS ===")
for w in alert.get("windows", []):
    print(f"\nTitle: {w['title']}")
    print(f"  Level: {w['level']}")
    print(f"  Bias: {w['bias']}")
    print(f"  Sectors: {w['sectors']}")
    print(f"  Date range: {w['start']} to {w['end']}")

print("\n=== UPCOMING REVERSAL WINDOWS (7 days) ===")
for w in alert.get("upcoming_windows", []):
    print(f"\nTitle: {w['title']}")
    print(f"  Level: {w['level']}")
    print(f"  Bias: {w['bias']}")
    print(f"  Sectors: {w['sectors']}")
    print(f"  Days ahead: {w.get('days_ahead', 'N/A')}")

# Also check the transit alerts
transits = transit_alert(planets)
print("\n=== TRANSIT ALERTS ===")
for t in transits:
    print(f"\n{t['planet']} in {t['sign']} @ {t['degree']:.2f}° {t['nakshatra']}")
    print(f"  Bias: {t['bias']}")
    print(f"  Explanation: {t['explanation']}")
    print(f"  Sectors: {t['sectors']}")

lunar = lunar_phase_alert(tithi)
print("\n=== LUNAR PHASE ===")
if lunar:
    print(f"Phase: {lunar['phase']}")
    print(f"Tithi: {lunar['tithi']}")
    print(f"Level: {lunar['level']}")
    print(f"Bias: {lunar['bias']}")
    print(f"Explanation: {lunar['explanation']}")
else:
    print("No major lunar phase")

# Check Jupiter analysis
jupiter_analysis = jupiter_market_analysis(planets)
print("\n=== JUPITER MARKET ANALYSIS ===")
print(f"Active: {jupiter_analysis['active']}")
print(f"Bias: {jupiter_analysis['bias']}")
print(f"Level: {jupiter_analysis['level']}")
print(f"Reasons: {jupiter_analysis['reasons']}")

# Check bullish futurecast
from sbc.backtest import run_bullish_futurecast

bullish = run_bullish_futurecast(center_date="2026-08-23", years=1)
print("\n=== BULLISH FUTURECAST (clusters near current date) ===")
for c in bullish.get("clusters", []):
    start = c["start"]
    end = c["end"]
    if start <= "2026-09-07" and end >= "2026-08-15":
        print(f"  Score: {c['score']}, Level: {c['level']}, {c['start']} to {c['end']}")
        print(f"  Triggers: {c['triggers']}")

# Check bearish futurecast
from sbc.backtest import run_bearish_futurecast

bearish = run_bearish_futurecast(center_date="2026-08-23", years=1)
print("\n=== BEARISH FUTURECAST (clusters near current date) ===")
for c in bearish.get("clusters", []):
    start = c["start"]
    end = c["end"]
    if start <= "2026-09-07" and end >= "2026-08-15":
        print(f"  Score: {c['score']}, Level: {c['level']}, {c['start']} to {c['end']}")
        print(f"  Triggers: {c['triggers']}")

# Check Pushya windows
pushya_windows = get_all_bullish_reversal_windows(date, planets, tithi)
print("\n=== ALL BULLISH REVERSAL WINDOWS (dynamic) ===")
for w in pushya_windows:
    print(f"\nTitle: {w['title']}")
    print(f"  Level: {w['level']}")
    print(f"  Bias: {w['bias']}")
    print(f"  Sectors: {w['sectors']}")

# Check confluence report
if alert.get("confluence"):
    conf = alert["confluence"]
    print("\n=== CONFLUENCE REPORT ===")
    print(f"Overall Signal: {conf['overall']['signal']}")
    print(f"Net: {conf['overall']['net']}")
    print(f"Bullish Weight: {conf['overall']['bullish_weight']}")
    print(f"Bearish Weight: {conf['overall']['bearish_weight']}")
    print("\nHighlights:")
    print(f"  Bullish Confluence Sectors: {conf['highlights']['bullish_confluence_sectors']}")
    print(f"  Bearish Confluence Sectors: {conf['highlights']['bearish_confluence_sectors']}")
    print(f"  Conflicted Sectors: {conf['highlights']['conflicted_sectors']}")

    print("\nComponent Breakdown:")
    for name, comp in conf['components'].items():
        print(f"  {name}: Bullish={comp['overall']['bullish_weight']}, Bearish={comp['overall']['bearish_weight']}, Signal={comp['overall']['signal']}")

# Print planetary positions again for reference
print("\n=== PLANETARY POSITIONS (for reference) ===")
for p in planets:
    print(f'{p["name"]:8s} | {p["sign"]:10s} | {p["degree"]:6.2f} | {p["nakshatra"]:15s} | retro={p["retrograde"]}')
