import yfinance as yf
import datetime
import pandas as pd
from sbc.monthly_heatmap import _day_planets

# Sector tickers mapping
SECTOR_TICKERS = {
    'Nifty Bank': '^NSEBANK',
    'Nifty IT': '^CNXIT',
    'Nifty Auto': '^CNXAUTO',
    'Nifty Metal': '^CNXMETAL',
    'Nifty FMCG': '^CNXFMCG',
    'Nifty Pharma': '^CNXPHARMA',
    'Nifty Energy': '^CNXENERGY',
    'Nifty Realty': '^CNXREALTY',
    'Nifty Gold': '^NSEBANK',  # placeholder, use Gold? We'll skip
}

# Nakshatra to sector keyword mapping from table
nakshatra_sector_keywords = {
    'Ashwini': ['Auto'],
    'Magha': ['PSU'],
    'Mula': ['Metals'],
    'Ardra': ['IT','Telecom'],
    'Swati': ['FMCG'],
    'Shatabhisha': ['Pharma'],
    'Rohini': ['Gold','FMCG'],
    'Hasta': ['Banks'],
    'Shravana': ['Large caps'],
    'Mrigashira': ['IT','Telecom'],
    'Chitra': ['Infra'],
    'Dhanishta': ['Metals','Energy'],
    'Krittika': ['Metals','Energy'],
    'U.Phalguni': ['Banks'],
    'U.Ashadha': ['PSU'],
    'Punarvasu': ['FMCG'],
    'Vishakha': ['Banks'],
    'Purva Bhadrapada': ['Speculative'],
    'Pushya': ['Banks'],
    'Anuradha': ['Pharma'],
    'U.Bhadrapada': ['IT','Telecom'],
    'Bharani': ['Retail'],
    'Purva Phalguni': ['Travel'],
    'Purva Ashadha': ['Financials'],
    'P.Ashadha': ['Financials'],
}

# Map keywords to sector names
keyword_to_sector = {
    'Auto': 'Nifty Auto',
    'Metals': 'Nifty Metal',
    'IT': 'Nifty IT',
    'Telecom': 'Nifty IT',  # approximate
    'FMCG': 'Nifty FMCG',
    'Pharma': 'Nifty Pharma',
    'Banks': 'Nifty Bank',
    'PSU': 'Nifty Bank',
    'Infra': 'Nifty Realty',
    'Energy': 'Nifty Energy',
    'Gold': 'Nifty Bank',
    'Large caps': 'Nifty Bank',
    'Travel': 'Nifty Auto',
    'Financials': 'Nifty Bank',
    'Retail': 'Nifty FMCG',
    'Speculative': 'Nifty Bank',
}

end_date = datetime.date.today()
start_date = end_date - datetime.timedelta(days=365)

# Download data
data = {}
for sector, ticker in SECTOR_TICKERS.items():
    try:
        df = yf.download(ticker, start=start_date, end=end_date, interval='1d', auto_adjust=True, progress=False)
        data[sector] = df['Close']
    except Exception as e:
        print(f"Failed {sector}: {e}")

price_df = pd.DataFrame(data).dropna()
returns_df = price_df.pct_change().dropna()

# Get Moon Nakshatra per date
dates = returns_df.index.date
nakshatras = []
for d in dates:
    if d.weekday() >=5: # weekend skip
        continue
    planets,_ = _day_planets(datetime.date(d.year,d.month,d.day))
    moon = next(p for p in planets if p['name']=='Moon')
    nak = moon.get('nakshatra')
    # Normalize names
    nak_map = {
        'P.Phalguni':'P.Phalguni',
        'U.Phalguni':'U.Phalguni',
        'P.Ashadha':'P.Ashadha',
        'U.Ashadha':'U.Ashadha',
        'P.Bhadrapada':'P.Bhadrapada',
        'U.Bhadrapada':'U.Bhadrapada',
    }
    nakshatras.append(nak)

# Compute hit rate
hits = 0
total = 0
for idx, d in enumerate(dates):
    if d.weekday()>=5:
        continue
    nak = nakshatras[idx]
    keywords = nakshatra_sector_keywords.get(nak, [])
    predicted_sectors = set()
    for kw in keywords:
        sec = keyword_to_sector.get(kw)
        if sec:
            predicted_sectors.add(sec)
    if not predicted_sectors:
        continue
    # actual best performing sector that day
    day_returns = returns_df.loc[d]
    best_sector = day_returns.idxmax()
    total +=1
    if best_sector in predicted_sectors:
        hits +=1

print(f"Nakshatra sector bias hit rate vs actual best sector: {hits}/{total} = {hits/total:.2%}")
print("Sample dates:")
# show first 10
for i in range(min(10,len(dates))):
    d = dates[i]
    if d.weekday()>=5:
        continue
    nak = nakshatras[i]
    print(d, nak, returns_df.loc[d].idxmax(), returns_df.loc[d].max())
