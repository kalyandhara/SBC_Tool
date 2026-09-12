import sys
sys.path.insert(0, '.')
from sbc.planets import positions
from sbc.nakshatra import tithi_of
from sbc.market_calendar import NAKSHATRA_LORDS
from sbc.market_calendar import jupiter_market_analysis
import swisseph as swe

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

def angle(lon1, lon2):
    diff = abs((lon1 - lon2 + 180) % 360 - 180)
    return diff

for date_str, name in crashes:
    y, m, d = map(int, date_str.split('-'))
    jul = swe.julday(y, m, d, 3.75)
    planets, _ = positions(jul)
    jupiter = next(p for p in planets if p['name'] == 'Jupiter')
    saturn = next(p for p in planets if p['name'] == 'Saturn')
    mars = next(p for p in planets if p['name'] == 'Mars')
    rahu = next(p for p in planets if p['name'] == 'Rahu')
    ketu = next(p for p in planets if p['name'] == 'Ketu')
    
    jup_nak_lord = NAKSHATRA_LORDS.get(jupiter['nakshatra'])
    jup_sat_angle = angle(jupiter['longitude'], saturn['longitude'])
    jup_rahu_angle = angle(jupiter['longitude'], rahu['longitude'])
    jup_ketu_angle = angle(jupiter['longitude'], ketu['longitude'])
    sat_rahu_angle = angle(saturn['longitude'], rahu['longitude'])
    sat_ketu_angle = angle(saturn['longitude'], ketu['longitude'])
    mars_rahu_angle = angle(mars['longitude'], rahu['longitude'])
    mars_ketu_angle = angle(mars['longitude'], ketu['longitude'])
    
    # Saturn-Jupiter cycle phase
    # Conjunction = 0, Opposition = 180, Square = 90, Trine = 120, Sextile = 60
    phase = "Unknown"
    for a, label in [(0, "Conj"), (180, "Opp"), (90, "Sq"), (120, "Tri"), (60, "Sex")]:
        if abs(jup_sat_angle - a) < 10:
            phase = label
            break
    
    print('{} ({}):'.format(name, date_str))
    print('  Jup-Sat angle: {:.1f} [{}]'.format(jup_sat_angle, phase))
    print('  Jup-Rahu: {:.1f}, Jup-Ketu: {:.1f}'.format(jup_rahu_angle, jup_ketu_angle))
    print('  Sat-Rahu: {:.1f}, Sat-Ketu: {:.1f}'.format(sat_rahu_angle, sat_ketu_angle))
    print('  Mar-Rahu: {:.1f}, Mar-Ketu: {:.1f}'.format(mars_rahu_angle, mars_ketu_angle))
    print('  Jupiter nak lord: {}'.format(jup_nak_lord))
    print()