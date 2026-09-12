"""
Generate daily commentary for each day this week (Aug 23-29)
"""
import sys
sys.path.insert(0, r'D:\SBC_Tool')

import datetime
from sbc.weekly_commentary import generate_weekly_commentary, format_commentary_text

# Generate for each day
for day_offset in range(7):
    date = datetime.date(2026, 8, 23) + datetime.timedelta(days=day_offset)
    print(f"\n{'='*70}")
    print(f"DAILY COMMENTARY: {date.strftime('%A, %b %d, %Y')}")
    print(f"{'='*70}")
    
    # Get commentary for this specific date (using the week's Monday)
    start = date - datetime.timedelta(days=date.weekday())
    commentary = generate_weekly_commentary(start)
    
    # Extract just the relevant parts for this day
    print(f"Weekly Bias: {commentary['market_bias']}")
    print(f"Main Cycle: {commentary['main_cycle']['name']}")
    
    # Moon transit for this day
    for mt in commentary['moon_transits']:
        if mt['date'] == date:
            print(f"Moon: {mt['nakshatra']} ({mt['sign']} {mt['degree']:.1f}°) - {mt['meaning']} [Lord: {mt['lord']}]")
            break
    
    # Active windows for this day
    active_today = []
    for w in commentary['active_windows']:
        start_d = datetime.date.fromisoformat(w['start'])
        end_d = datetime.date.fromisoformat(w['end'])
        if start_d <= date <= end_d:
            active_today.append(w)
    
    if active_today:
        print("Active Windows:")
        for w in active_today:
            print(f"  - {w['title']} [{w['level']}] {w['bias']}")
    
    # Configurations relevant this week
    print("Key Configurations:")
    for c in commentary['all_configurations']:
        if c.get('intensity') in ('extreme', 'high', 'moderate-high'):
            print(f"  [{c.get('intensity','').upper()}] {c['name']}: {c.get('details','')}")

# Also run cross-check summary
print(f"\n{'='*70}")
print("GAP ANALYSIS SUMMARY: Tool vs AstroNaresh")
print(f"{'='*70}")

gaps = [
    ("Mercury enters Leo", "Aug 22, 7:45 PM", "Aug 22, 7:33 PM", "+12 min", "Minor - acceptable"),
    ("Mercury-Ketu-Sun Triangle", "Aug 23-29 (ALL in Leo)", "Till Sep 7", "Matches", "Confirmed - tight triangle Aug 23-29"),
    ("Venus enters Chitra", "Aug 25, ~2:00 PM", "Aug 25, 12:55 PM", "~65 min", "Moderate - diff ayanamsa/ephemeris"),
    ("Sun-Mercury Exact Conjunction", "Aug 27, 10:30 PM", "Aug 27, 10:30 AM", "12 HOURS", "MAJOR - AM/PM discrepancy"),
    ("Moon enters Purva Ashada", "Aug 23, 5:45 PM", "Aug 23, 5:44 PM", "+1 min", "Excellent match"),
    ("Moon enters Uttara Ashada", "Aug 24, 8:30 PM", "Aug 24, 8:27 PM", "+3 min", "Excellent match"),
    ("Moon enters Shravana", "Aug 26, 12:45 AM", "Aug 25, 10:50 PM", "~2 hrs", "Date boundary issue"),
    ("Moon enters Dhanishta", "Aug 27, 1:00 AM", "Aug 27, 12:47 AM", "+13 min", "Good match"),
    ("Moon enters Shatabhisha", "Aug 28, 2:30 AM", "Aug 28, 2:15 AM", "+15 min", "Good match"),
]

for event, tool, astro, diff, note in gaps:
    if "Excellent" in note or "Good" in note or "Matches" in note or "Minor" in note:
        status = "[OK]"
    elif "Moderate" in note:
        status = "[WARN]"
    else:
        status = "[GAP]"
    print(f"  {status} {event}")
    print(f"      Tool: {tool}")
    print(f"      AstroNaresh: {astro}")
    print(f"      Gap: {diff} - {note}")
    print()