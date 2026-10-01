import yfinance as yf
for t in ['^NSEBANK','^NSEI','^NSEIT']:
    df=yf.download(t, period='5d', auto_adjust=True, progress=False)
    print(t, 'rows' if not df.empty else 'empty')
