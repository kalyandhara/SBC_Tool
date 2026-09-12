import sys
sys.path.insert(0, '.')
from sbc.market_calendar import reversal_alert
from sbc.planets import positions
import swisseph as swe
import datetime

# Test multiple dates to see bullish events
dates_to_test = [
    '2026-08-21',  # Current
    '2026-10-15',  # Jupiter might be in Cancer
    '2026-11-15',  # Mercury/Venus direct
    '2026-12-20',  # Saturn direct?
    '2026-09-15',  # Random
]

for d in dates_to_test:
    jul = swe.julday(*map(int, d.split('-')), 3.75)
    planets, _ = positions(jul)
    sun = next(p for p in planets if p['name'] == 'Sun')
    moon = next(p for p in planets if p['name'] == 'Moon')
    from sbc.nakshatra import tithi_of
    tithi = tithi_of(sun['longitude'], moon['longitude'])
    
    alert = reversal_alert(d, planets=planets, tithi=tithi)
    
    bullish = [w for w in alert['windows'] if 'BULLISH' in w['bias'] and 'BEARISH' not in w['bias']]
    bearish = [w for w in alert['windows'] if 'BEARISH' in w['bias'] and 'BULLISH' not in w['bias']]
    neutral = [w for w in alert['windows'] if w not in bullish and w not in bearish]
    
    print(d + ': ' + str(len(bullish)) + ' bullish, ' + str(len(bearish)) + ' bearish, ' + str(len(neutral)) + ' neutral/volatile')
    for w in bullish[:5]:
        print('   BULL: ' + w['title'][:70] + ' | ' + w['level'])
    for w in bearish[:3]:
        print('   BEAR: ' + w['title'][:70] + ' | ' + w['level'])
    print()