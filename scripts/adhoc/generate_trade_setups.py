import pandas as pd
df = pd.read_csv("D:/SBC_Tool/confluence_moon_rashi_nakshatra.csv")
high = df[df['confidence']=='high'].copy()
high['signal'] = high['expected']
# Create simple setup: entry next day open, target 1% , stop 0.5%
# We need price data for next day
import yfinance as yf
import datetime
ticker = "^NSEI"
end = datetime.date.today()
start = end - datetime.timedelta(days=365*2)
price = yf.download(ticker, start=start, end=end, interval='1d', auto_adjust=True, progress=False)
price.columns = [c[0] if isinstance(c, tuple) else c for c in price.columns]
price = price[['Close','Open']].dropna()
price.index = pd.to_datetime(price.index).date
# Build setup list
setups = []
for _, row in high.iterrows():
    d = row['date']
    try:
        entry_date = (pd.to_datetime(d) + pd.Timedelta(days=1)).date()
        if entry_date in price.index:
            entry_price = float(price.loc[entry_date, 'Open'])
            target = entry_price * (1.01 if row['expected']=='bullish' else 0.99)
            stop = entry_price * (0.995 if row['expected']=='bullish' else 1.005)
            # Actual outcome next day
            exit_date = entry_date + datetime.timedelta(days=1)
            if exit_date in price.index:
                exit_price = float(price.loc[exit_date, 'Close'])
                pnl = (exit_price - entry_price)/entry_price
            else:
                exit_price = None
                pnl = None
            setups.append({
                "signal_date": d,
                "entry_date": str(entry_date),
                "direction": row['expected'],
                "rashi": row['rashi'],
                "nakshatra": row['nakshatra'],
                "ruler": row['ruler'],
                "entry_price": entry_price,
                "target": target,
                "stop": stop,
                "exit_price": exit_price,
                "pnl_pct": pnl*100 if pnl is not None else None
            })
    except Exception as e:
        continue
pd.DataFrame(setups).to_csv("D:/SBC_Tool/moon_nakshatra_trade_setups.csv", index=False)
print(f"Generated {len(setups)} setups, saved")
