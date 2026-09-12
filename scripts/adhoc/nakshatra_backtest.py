import datetime
from sbc.monthly_heatmap import monthly_heatmap, _day_planets
from collections import defaultdict

# Mapping from the provided table
nakshatra_sector_map = {
    # Ketu group
    'Ashwini': ['Auto','logistics','EV','quick-delivery'],
    'Magha': ['PSU banks','govt companies','infra'],
    'Mula': ['Metals','mining','midcap volatility'],
    # Rahu group
    'Ardra': ['Telecom','cable','IT','cloud','AI'],
    'Swati': ['FMCG','retail','midcaps'],
    'Shatabhisha': ['Pharma','diagnostics','biotech'],
    # Moon group
    'Rohini': ['Gold','silver','FMCG'],
    'Hasta': ['Banks','NBFC'],
    'Shravana': ['Large caps','blue chips'],
    # Mars group
    'Mrigashira': ['IT','telecom','media'],
    'Chitra': ['Cement','infra','construction'],
    'Dhanishta': ['Metals','steel','energy'],
    # Sun group
    'Krittika': ['Metals','oil','energy'],
    'Uttara Phalguni': ['Banks','insurance'],
    'Uttara Ashadha': ['PSU','defence','govt stocks'],
    # Jupiter group
    'Punarvasu': ['FMCG','housing'],
    'Vishakha': ['Banks','NBFC'],
    'Purva Bhadrapada': ['Crypto','speculative stocks'],
    # Saturn group
    'Pushya': ['Banks','large caps'],
    'Anuradha': ['Pharma','chemicals'],
    'Uttara Bhadrapada': ['IT','telecom','utilities'],
    # Venus group
    'Bharani': ['Midcaps','retail'],
    'Purva Phalguni': ['Hotels','travel','consumption'],
    'Purva Ashadha': ['Financials','insurance'],
}

# Helper to get nakshatra name from planets
def get_nakshatra(planets):
    moon = next(p for p in planets if p['name']=='Moon')
    # nakshatra stored in planets dict? Let's assume planets have nakshatra field
    return moon.get('nakshatra','Unknown')

start = datetime.date(2025,9,1)
days = 30
data = monthly_heatmap(start_date=start, days=days)
sectors = data['sectors']
dates = data['dates']
matrix = data['matrix']

matches = 0
total = 0
details = []
for d_str in dates:
    d = datetime.date.fromisoformat(d_str)
    planets,_ = _day_planets(d)
    nak = get_nakshatra(planets)
    # Find top sector per day by max abs net
    best_sector = None
    best_net = 0
    for s in sectors:
        v = matrix[s].get(d_str,0)
        if abs(v) > abs(best_net):
            best_net = v
            best_sector = s
    # Map nakshatra to sector keywords
    pred_sectors = nakshatra_sector_map.get(nak, [])
    # Simple check if best sector name contains any keyword
    hit = False
    for kw in pred_sectors:
        if kw.lower() in best_sector.lower():
            hit = True
            break
    # Allow mapping via keywords to Nifty rows
    total +=1
    if hit:
        matches+=1
    details.append((d_str, nak, best_sector, best_net, pred_sectors, hit))

print(f"Match rate: {matches}/{total} = {matches/total:.2%}")
print("Sample:")
for row in details[:10]:
    print(row)
