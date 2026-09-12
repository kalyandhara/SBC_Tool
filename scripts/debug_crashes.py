import sys
sys.path.insert(0, '.')
from sbc.planets import positions
from sbc.nakshatra import tithi_of, nakshatra_of, sign_of
from sbc.market_calendar import NAKSHATRA_LORDS
from sbc.market_calendar import jupiter_market_analysis, _pushya_reversal_windows
import swisseph as swe
import datetime

crashes = [
    ('1929-10-24', 'Black Thursday'),
    ('1987-10-19', 'Black Monday'), 
    ('2000-03-10', 'Dot-com Peak'),
    ('2008-09-15', 'Lehman'),
    ('2020-02-19', 'COVID Peak'),
    ('1992-04-28', 'Harshad Mehta'),
    ('2008-01-08', '2007 Peak'),
    ('2011-11-07', '2011 Correction'),
]

for date_str, name in crashes:
    y, m, d = map(int, date_str.split('-'))
    jul = swe.julday(y, m, d, 3.75)  # 09:15 IST
    planets, _ = positions(jul)
    sun = next(p for p in planets if p['name'] == 'Sun')
    moon = next(p for p in planets if p['name'] == 'Moon')
    jupiter = next(p for p in planets if p['name'] == 'Jupiter')
    saturn = next(p for p in planets if p['name'] == 'Saturn')
    mars = next(p for p in planets if p['name'] == 'Mars')
    rahu = next(p for p in planets if p['name'] == 'Rahu')
    ketu = next(p for p in planets if p['name'] == 'Ketu')
    
    tithi = tithi_of(sun['longitude'], moon['longitude'])
    jup_analysis = jupiter_market_analysis(planets)
    
    # Check Pushya
    pushya_planets = [p['name'] for p in planets if p['nakshatra'] == 'Pushya']
    malefics_in_pushya = [p for p in pushya_planets if p in ('Saturn', 'Mars', 'Rahu', 'Ketu', 'Sun')]
    
    # Jupiter-Ketu nakshatra
    jup_nak_lord = NAKSHATRA_LORDS.get(jupiter['nakshatra'])
    
    # Saturn sign
    sat_sign = saturn['sign']
    
    # Mars retro in Cap/Cancer
    mars_retro_cap_can = mars['retrograde'] and mars['sign'] in ('Capricorn', 'Cancer')
    
    print('{} ({}):'.format(name, date_str))
    print('  Jupiter: {} {:.1f} in {} (lord: {})'.format(jupiter['sign'], jupiter['degree'], jupiter['nakshatra'], jup_nak_lord))
    print('  Saturn:  {} {:.1f} (retro: {})'.format(saturn['sign'], saturn['degree'], saturn['retrograde']))
    print('  Mars:    {} {:.1f} (retro: {})'.format(mars['sign'], mars['degree'], mars['retrograde']))
    print('  Rahu:    {} {:.1f}'.format(rahu['sign'], rahu['degree']))
    print('  Pushya:  {} | Malefics: {}'.format(pushya_planets, malefics_in_pushya))
    print('  Jupiter bias: {} ({})'.format(jup_analysis['bias'], jup_analysis['level']))
    if jup_analysis['reasons']:
        for r in jup_analysis['reasons']:
            print('    -> {}'.format(r))
    print()