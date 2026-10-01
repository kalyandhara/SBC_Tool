import yfinance as yf
for t in ['^NSEIT','^CNXIT','NIFTYIT.NS','^NIFTYIT']:
    try:
        df = yf.download(t, period='5d', auto_adjust=True, progress=False)
        print(t, 'rows' if not df.empty else 'empty', df.shape)
    except Exception as e:
        print(t, 'error', e)
