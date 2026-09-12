import datetime, pandas as pd, yfinance as yf, swisseph as swe
from sbc.planets import positions
from zoneinfo import ZoneInfo
swe.set_sid_mode(swe.SIDM_LAHIRI)

RASHI_TREND={"Aries":"bullish","Taurus":"bullish","Gemini":"bearish","Cancer":"bearish","Leo":"bullish","Virgo":"bearish","Libra":"bearish","Scorpio":"bullish","Sagittarius":"bullish","Capricorn":"bullish","Aquarius":"bearish","Pisces":"bearish"}

def moon_rashi(dt):
    if dt.tzinfo is None: dt=dt.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
    dt_utc=dt.astimezone(ZoneInfo("UTC"))
    jd=swe.julday(dt_utc.year,dt_utc.month,dt_utc.day,dt_utc.hour+dt_utc.minute/60)
    planets,_=positions(jd)
    return next(p for p in planets if p['name']=='Moon')['sign']

def backtest(ticker="^NSEI", start=None, end=None, multi_tf=True, vedha=False, regime=False, volume=False):
    if start is None: start=datetime.date.today()-datetime.timedelta(days=730)
    if end is None: end=datetime.date.today()
    df=yf.download(ticker,start=start,end=end,interval='1d',auto_adjust=True,progress=False)
    df.columns=[c[0] if isinstance(c,tuple) else c for c in df.columns]
    df=df[['Open','High','Low','Close','Volume']].dropna()
    df['vol_ma']=df['Volume'].rolling(20).mean()
    ist=ZoneInfo("Asia/Kolkata")
    correct=total=0
    results=[]
    for i in range(1,len(df)-1):
        d=pd.to_datetime(df.index[i]).date()
        dt=datetime.datetime.combine(d,datetime.time(9,15),tzinfo=ist)
        daily_rashi=moon_rashi(dt)
        expected=RASHI_TREND.get(daily_rashi)
        if expected is None: 
            prev=float(df['Close'].iloc[i])
            continue
        # multi timeframe
        if multi_tf:
            monday=dt-datetime.timedelta(days=dt.weekday())
            weekly=moon_rashi(datetime.datetime.combine(monday.date(),datetime.time(9,15),tzinfo=ist))
            if RASHI_TREND.get(weekly)!=expected:
                prev=float(df['Close'].iloc[i])
                continue
        # regime filter placeholder
        if regime:
            # skip Amavasya/Purnima approx via lunar phase
            # simplified: skip if day of month ==1 or 15
            if d.day in [1,15]: 
                prev=float(df['Close'].iloc[i])
                continue
        # volume confirmation
        entry_i=i+1
        if volume:
            if df['Volume'].iloc[entry_i] < df['vol_ma'].iloc[entry_i]:
                prev=float(df['Close'].iloc[i])
                continue
            open_p=float(df['Open'].iloc[entry_i])
            prev_close=float(df['Close'].iloc[i])
            if expected=="bullish" and open_p<=prev_close: 
                prev=float(df['Close'].iloc[i]); continue
            if expected=="bearish" and open_p>=prev_close:
                prev=float(df['Close'].iloc[i]); continue
        # evaluate
        prev_close=float(df['Close'].iloc[i])
        close_next=float(df['Close'].iloc[entry_i])
        actual="bullish" if close_next>prev_close else "bearish" if close_next<prev_close else "neutral"
        if actual!="neutral":
            total+=1
            match=expected==actual
            if match: correct+=1
            results.append({"date":d.isoformat(),"expected":expected,"actual":actual,"match":match})
        # update prev
        # keep loop simple
    acc=correct/total if total else 0
    return {"samples":total,"correct":correct,"accuracy":acc,"results":results}

if __name__=="__main__":
    res=backtest(multi_tf=True, regime=True, volume=True)
    print(res)
