import yfinance as yf
for t in ['NIFTYEN','^CNXENERGY']:
    df=yf.download(t, period='5d', auto_adjust=True, progress=False)
    print(t, 'rows' if not df.empty else 'empty')
