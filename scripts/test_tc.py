import sys
sys.stdout.reconfigure(encoding='utf-8')
from sbc.planets import positions, all_planets_with_natures
from sbc.nakshatra import tithi_of
from sbc.prediction import compute_vedhas, place_planets, planet_sector_read
from sbc.chakra import GRID
import swisseph as swe
jd = swe.julday(2026, 9, 3, 0)
planets, _ = positions(jd)
sun = next(p for p in planets if p['name']=='Sun')
moon = next(p for p in planets if p['name']=='Moon')
tithi = tithi_of(sun['longitude'], moon['longitude'])
planets = all_planets_with_natures(planets, tithi, sun['longitude'])
vmap, _ = compute_vedhas(planets, school='classical')
grid = place_planets(GRID, planets)
psr = planet_sector_read(planets)
tc = [p for p in psr if 'Telecom' in str(p.get('sectors',[])) or 'Cable' in str(p.get('sectors',[]))]
for p in tc:
    print(f"{p['planet']}: sectors={p['sectors']}, strength={p['strength']}, read={p['read']}")
