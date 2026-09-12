import sys
sys.stdout.reconfigure(encoding='utf-8')
from sector_outlook import generate_sector_outlook
import datetime
o = generate_sector_outlook(datetime.date(2026, 9, 3))
for s in o['sectors']:
    infl = s['astrological_influence'][:55]
    trend = s['trend_outlook'][:26]
    conf = s['confluence_score']
    print(f"{s['sector']:<20} infl={infl} trend={trend} conf={conf}")
print()
print("Nifty PSU focus:", o['sectors'][8]['key_focus'] if len(o['sectors']) > 8 else 'N/A')
for s in o['sectors']:
    if 'PSU' in s['sector']:
        print(f"Nifty PSU focus: {s['key_focus']}")
        break
