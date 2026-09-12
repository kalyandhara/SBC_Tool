import sys
sys.path.insert(0, r'D:\SBC_Tool')

# Test the full rendering pipeline
from sbc.weekly_commentary import generate_weekly_commentary, format_commentary_text
import datetime

start = datetime.date(2026, 8, 24)
c = generate_weekly_commentary(start)

# Test text formatting
text = format_commentary_text(c)
print("TEXT FORMATTING WORKS")
print("Length:", len(text))

# Check for sector outlook section
if "SECTOR-WISE FINANCIAL ASTRO-TREND OUTLOOK" in text:
    print("SECTOR OUTLOOK SECTION: PRESENT")
else:
    print("SECTOR OUTLOOK SECTION: MISSING")

if "GENERAL MARKET STRATEGY FOR THE WEEK" in text:
    print("GENERAL STRATEGY SECTION: PRESENT")
else:
    print("GENERAL STRATEGY SECTION: MISSING")

if "NIFTY KEY LEVELS" in text:
    print("NIFTY LEVELS SECTION: PRESENT")
else:
    print("NIFTY LEVELS SECTION: MISSING")

# Check sector outlook data
print("\nSector Outlook Data:")
for s in c['sector_outlook']:
    print("  {}: {} | {}".format(s['sector'], s['trend_outlook'], s['astrological_influence'][:50]))

print("\nGeneral Strategy:")
print(c['general_strategy'][:200])

print("\nNifty Levels:")
print(c['nifty_levels'])