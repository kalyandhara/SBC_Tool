import yfinance as yf
import datetime
import pandas as pd
from sbc.monthly_heatmap import _day_planets

SECTOR_TICKERS = {
    'Nifty Bank': '^NSEBANK',
    'Nifty IT': '^CNXIT',
    'Nifty Auto': '^CNXAUTO',
    'Nifty Metal': '^CNXMETAL',
    'Nifty FMCG': '^CNXFMCG',
    'Nifty Pharma': '^CNXPHARMA',
    'Nifty Energy': '^CNXENERGY',
    'Nifty Realty': '^CNXREALTY',
}

nakshatra_sector_keywords = {
    'Ashwini': ['Auto'],
    'Magha': ['PSU'],
    'Mula': ['Metals'],
    'Ardra': ['IT'],
    'Swati': ['FMCG'],
    'Shatabhisha': ['Pharma'],
    'Rohini': ['FMCG'],
    'Hasta': ['Banks'],
    'Shravana': ['Bank'],
    'Mrigashira': ['IT'],
    'Chitra': ['Realty'],
    'Dhanishta': ['Metals','Energy'],
    'Krittika': ['Metals','Energy'],
    'U.Phalguni': ['Banks'],
    'U.Ashadha': ['PSU'],
    'Punarvasu': ['FMCG'],
    'Vishakha': ['Banks'],
    'Pushya': ['Banks'],
    'Anuradha': ['Pharma'],
    'U.Bhadrapada': ['IT'],
    'P.Ashadha': ['Bank'],
}

keyword_to_sector = {
    'Auto': 'Nifty Auto',
    'Metals': 'Nifty Metal',
    'IT': 'Nifty IT',
    'FMCG': 'Nifty FMCG',
    'Pharma': 'Nifty Pharma',
    'Banks': 'Nifty Bank',
    'Bank': 'Nifty Bank',
    'PSU': 'Nifty Bank',
    'Realty': 'Nifty Realty',
    'Energy': 'Nifty Energy',
}

end_date = datetime.date.today()
start_date = end_date - datetime.timedelta(days=180)

data = {}
for sector, ticker in SECTOR_TICKERS.items():
    df = yf.download(ticker, start=start_date, end=end_date, interval='1d', auto_adjust=True, progress=False)
    if not df.empty:
        data[sector] = df['Close']

price_df = pd.DataFrame(data).dropna(how='all')
returns_df = price_df.pct_change().dropna()

# map nakshatra
def get_nak(d):
    planets,_ = _day_planets(d)
    moon = next(p for p in planets if p['name']=='Moon')
    return moon.get('nakshatra')

hits = 0
total = 0
for d in returns_df.index.date:
    if datetime.date.weekday(datetime.date(d.year,d.month,d.day)) >=5:
        continue
    nak = get_nak(datetime.date(d.year,d.month,d.day))
    keywords = nakshatra_sector_keywords.get(nak, [])
    pred = set(keyword_to_sector.get(k) for k in keywords if keyword_to_sector.get(k))
    if not pred:
        continue
    row = returns_df.loc[pd.Timestamp(d)]
    best = row.idxmax()
    total +=1
    if best in pred:
        hits +=1

print(f"Hit rate {hits}/{total} = {hits/total:.2%}")
