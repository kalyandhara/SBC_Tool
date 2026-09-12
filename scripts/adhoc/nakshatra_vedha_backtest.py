import yfinance as yf
import datetime
import pandas as pd
from sbc.monthly_heatmap import _day_planets, _anchor_nakshatra
from sbc.prediction import analyze, compute_vedhas

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

nakshatra_map = {
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
    'P.Bhadrapada': ['Speculative'],
    'Pushya': ['Banks'],
    'Anuradha': ['Pharma'],
    'U.Bhadrapada': ['IT'],
    'Bharani': ['FMCG'],
    'P.Phalguni': ['Auto'],
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
    'Speculative': 'Nifty Bank',
}

end_date = datetime.date.today()
start_date = end_date - datetime.timedelta(days=365)

data = {}
for sector, ticker in SECTOR_TICKERS.items():
    df = yf.download(ticker, start=start_date, end=end_date, interval='1d', auto_adjust=True, progress=False)
    if not df.empty:
        close = df['Close']
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:,0]
        data[sector] = close

price_df = pd.DataFrame(data).dropna(how='all')
returns_df = price_df.pct_change().dropna()

anchor_nakshatra = _anchor_nakshatra('nse')

hits_long = 0
hits_short = 0
total_long = 0
total_short = 0
returns_long = []
returns_short = []

for d in returns_df.index.date:
    date_obj = datetime.date(d.year,d.month,d.day)
    if date_obj.weekday() >=5:
        continue
    planets, tithi = _day_planets(date_obj)
    # Moon nakshatra
    moon = next(p for p in planets if p['name']=='Moon')
    nak = moon.get('nakshatra')
    keywords = nakshatra_map.get(nak, [])
    pred_sectors = set(keyword_to_sector.get(k) for k in keywords if keyword_to_sector.get(k))
    if not pred_sectors:
        continue
    # SBC vedha net for day
    vedha_map,_ = compute_vedhas(planets, school='classical')
    analysis = analyze(planets, vedha_map, anchor_nakshatra, school='classical')
    vedha_net = analysis.get('net',0)
    # Choose one predicted sector, pick the one with highest return? We'll use first
    # For simplicity, pick best predicted sector return
    day_returns = returns_df.loc[pd.Timestamp(date_obj)]
    # Determine direction
    if vedha_net > 0:
        # long
        total_long +=1
        # evaluate best return among predicted sectors
        pred_returns = day_returns[list(pred_sectors)]
        best_pred_return = pred_returns.max()
        market_avg = day_returns.mean()
        returns_long.append(best_pred_return)
        if best_pred_return > market_avg:
            hits_long +=1
    elif vedha_net < 0:
        total_short +=1
        pred_returns = day_returns[list(pred_sectors)]
        best_pred_return = pred_returns.min()  # we want negative
        market_avg = day_returns.mean()
        returns_short.append(best_pred_return)
        if best_pred_return < market_avg:
            hits_short +=1

print(f"Long signal hit rate: {hits_long}/{total_long} = {hits_long/total_long:.2%}" if total_long else "No long")
if total_long:
    print(f"Avg long predicted sector return: {sum(returns_long)/len(returns_long):.4%}")
print(f"Short signal hit rate: {hits_short}/{total_short} = {hits_short/total_short:.2%}" if total_short else "No short")
if total_short:
    print(f"Avg short predicted sector return: {sum(returns_short)/len(returns_short):.4%}")
