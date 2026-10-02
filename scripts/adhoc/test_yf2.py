import yfinance as yf
for t in ['^CNXAUTO','^NSEAUTO','^CNXMETAL','^NSEMETAL','^CNXFMCG','^NSEFMCG','^CNXPHARMA','^NSEPHARMA','^CNXREALTY','^NSEREALTY']:
    try:
        df = yf.download(t, period='5d', auto_adjust=True, progress=False)
        print(t, 'rows' if not df.empty else 'empty')
    except Exception as e:
        print(t, 'error', e)
