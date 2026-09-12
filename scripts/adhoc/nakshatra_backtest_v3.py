import datetime
from sbc.monthly_heatmap import monthly_heatmap, _day_planets

nakshatra_sector_map = {
    'Ashwini': ['Auto','logistics','EV'],
    'Bharani': ['Midcaps','retail'],
    'Krittika': ['Metals','oil','energy'],
    'Rohini': ['Gold','silver','FMCG'],
    'Mrigashira': ['IT','telecom','media'],
    'Ardra': ['Telecom','cable','IT'],
    'Punarvasu': ['FMCG','housing'],
    'Pushya': ['Banks','large caps'],
    'Magha': ['PSU banks','govt','infra'],
    'P.Phalguni': ['Hotels','travel','consumption'],
    'U.Phalguni': ['Banks','insurance'],
    'Hasta': ['Banks','NBFC'],
    'Chitra': ['Cement','infra','construction'],
    'Swati': ['FMCG','retail'],
    'Vishakha': ['Banks','NBFC'],
    'Anuradha': ['Pharma','chemicals'],
    'Mula': ['Metals','mining'],
    'P.Ashadha': ['Financials','insurance'],
    'U.Ashadha': ['PSU','defence'],
    'Shravana': ['Large caps','blue chips'],
    'Dhanishta': ['Metals','steel','energy'],
    'Shatabhisha': ['Pharma','diagnostics'],
    'P.Bhadrapada': ['Crypto','speculative'],
    'U.Bhadrapada': ['IT','telecom'],
}

# Keyword to Nifty row mapping
keyword_to_row = {
    'auto': 'Nifty Auto',
    'logistics': 'Nifty Shipping',
    'ev': 'Nifty Auto',
    'midcaps': 'Nifty Large Caps',
    'retail': 'Nifty FMCG',
    'metals': 'Nifty Metal',
    'oil': 'Nifty Energy',
    'energy': 'Nifty Energy',
    'gold': 'Nifty Gold',
    'silver': 'Nifty Gold',
    'fmcg': 'Nifty FMCG',
    'it': 'Nifty IT',
    'telecom': 'Nifty Telecom/Cable',
    'cable': 'Nifty Telecom/Cable',
    'housing': 'Nifty Realty',
    'banks': 'Nifty Bank',
    'large caps': 'Nifty Large Caps',
    'blue chips': 'Nifty Large Caps',
    'psu': 'Nifty PSU',
    'govt': 'Nifty PSU',
    'infra': 'Nifty Infra',
    'hotels': 'Nifty Travel',
    'travel': 'Nifty Travel',
    'consumption': 'Nifty FMCG',
    'insurance': 'Nifty Bank',
    'nbfc': 'Nifty Bank',
    'cement': 'Nifty Infra',
    'construction': 'Nifty Infra',
    'pharma': 'Nifty Pharma',
    'chemicals': 'Nifty Pharma',
    'financials': 'Nifty Bank',
    'defence': 'Nifty Defense',
    'steel': 'Nifty Metal',
    'diagnostics': 'Nifty Pharma',
    'speculative': 'Nifty Large Caps',
    'crypto': 'Nifty Other',
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

correct = 0
total = 0
log = []
for d_str in dates:
    d = datetime.date.fromisoformat(d_str)
    planets,_ = _day_planets(d)
    nak = get_nakshatra(planets)
    # predicted rows
    pred_keywords = nakshatra_sector_map.get(nak, [])
    pred_rows = set()
    for kw in pred_keywords:
        row = keyword_to_row.get(kw.lower())
        if row:
            pred_rows.add(row)
    # actual top sector by net magnitude
    best_sector = None
    best_net = -1e9
    for s in sectors:
        v = matrix[s].get(d_str,0)
        if abs(v) > abs(best_net):
            best_net = v
            best_sector = s
    # check if best sector in predicted set
    hit = best_sector in pred_rows if pred_rows else False
    total+=1
    if hit:
        correct+=1
    log.append((d_str, nak, best_sector, best_net, pred_rows, hit))

print(f"Predicted match rate: {correct}/{total} = {correct/total:.2%}")
# Show mismatches
print("\nSample hits:")
for row in log:
    if row[-1]:
        print(row)
