import sys
sys.path.insert(0, r'D:\SBC_Tool')
from sbc.weekly_commentary import generate_weekly_commentary
import datetime

start = datetime.date(2026, 8, 24)
c = generate_weekly_commentary(start)
print('Keys:', c.keys())
print('Has sector_outlook:', 'sector_outlook' in c)
print('Has general_strategy:', 'general_strategy' in c)
print('Has nifty_levels:', 'nifty_levels' in c)
if 'sector_outlook' in c:
    print('Sector outlook count:', len(c['sector_outlook']))
    for s in c['sector_outlook'][:3]:
        print('  {}: {}'.format(s['sector'], s['trend_outlook']))