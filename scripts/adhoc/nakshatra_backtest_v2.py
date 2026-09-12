import datetime
from sbc.monthly_heatmap import monthly_heatmap, _day_planets

# Mapping with abbreviations used by swisseph library in this codebase
nakshatra_sector_map = {
    'Ashwini': ['Auto','logistics','EV','quick-delivery'],
    'Bharani': ['Midcaps','retail'],
    'Krittika': ['Metals','oil','energy'],
    'Rohini': ['Gold','silver','FMCG'],
    'Mrigashira': ['IT','telecom','media'],
    'Ardra': ['Telecom','cable','IT','cloud','AI'],
    'Punarvasu': ['FMCG','housing'],
    'Pushya': ['Banks','large caps'],
    'Ashlesha': [], # not in table
    'Magha': ['PSU banks','govt companies','infra'],
    'P.Phalguni': ['Hotels','travel','consumption'],
    'U.Phalguni': ['Banks','insurance'],
    'Hasta': ['Banks','NBFC'],
    'Chitra': ['Cement','infra','construction'],
    'Swati': ['FMCG','retail','midcaps'],
    'Vishakha': ['Banks','NBFC'],
    'Anuradha': ['Pharma','chemicals'],
    'Jyeshtha': [],
    'Mula': ['Metals','mining','midcap volatility'],
    'P.Ashadha': ['Financials','insurance'],
    'U.Ashadha': ['PSU','defence','govt stocks'],
    'Shravana': ['Large caps','blue chips'],
    'Dhanishta': ['Metals','steel','energy'],
    'Shatabhisha': ['Pharma','diagnostics','biotech'],
    'P.Bhadrapada': ['Crypto','speculative stocks'],
    'U.Bhadrapada': ['IT','telecom','utilities'],
    'Revati': [],
}

def get_nakshatra(planets):
    moon = next(p for p in planets if p['name']=='Moon')
    return moon.get('nakshatra','Unknown')

start = datetime.date(2025,9,1)
days = 30
data = monthly_heatmap(start_date=start, days=days)
sectors = data['sectors']
dates = data['dates']
matrix = data['matrix']

matches = 0
total = 0
hits = []
for d_str in dates:
    d = datetime.date.fromisoformat(d_str)
    planets,_ = _day_planets(d)
    nak = get_nakshatra(planets)
    best_sector = None
    best_net = 0
    for s in sectors:
        v = matrix[s].get(d_str,0)
        if abs(v) > abs(best_net):
            best_net = v
            best_sector = s
    pred_sectors = nakshatra_sector_map.get(nak, [])
    # check if any keyword matches sector name
    hit = False
    sector_lower = best_sector.lower()
    for kw in pred_sectors:
        if kw.lower() in sector_lower:
            hit = True
            break
    # Also allow partial mapping e.g., Metals -> Nifty Metal
    # Create a quick synonym map
    synonym_map = {
        'metal': 'metal',
        'gold': 'gold',
        'bank': 'bank',
        'it': 'it',
        'telecom': 'telecom',
        'fmcg': 'fmcg',
        'pharma': 'pharma',
        'energy': 'energy',
        'large caps': 'large caps',
        'psu': 'psu',
        'infra': 'infra',
        'defence': 'defense',
        'shipping': 'shipping',
        'travel': 'travel',
        'agri': 'agri',
    }
    # Compare via keywords
    if not hit:
        # check if any predicted sector maps to sector
        # simplified
        pass
    total+=1
    if hit:
        matches+=1
    hits.append((d_str, nak, best_sector, best_net, pred_sectors, hit))

print(f"Match rate: {matches}/{total} = {matches/total:.2%}")
# Show examples
for h in hits[:15]:
    print(h)
