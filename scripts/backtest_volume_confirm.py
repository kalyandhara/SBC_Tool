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
def backtest(start,end):
    df=yf.download("^NSEI",start=start,end=end,interval='1d',auto_adjust=True,progress=False)
    df.columns=[c[0] if isinstance(c,tuple) else c for c in df.columns]
    df=df[['Open','High','Low','Close','Volume']].dropna()
    df['vol_ma']=df['Volume'].rolling(20).mean()
    ist=ZoneInfo("Asia/Kolkata")
    correct=total=0
    for i in range(1,len(df)-1):
        d=pd.to_datetime(df.index[i]).date()
        dt=datetime.datetime.combine(d,datetime.time(9,15),tzinfo=ist)
        monday=dt-datetime.timedelta(days=dt.weekday())
        daily=moon_rashi(dt)
        weekly=moon_rashi(datetime.datetime.combine(monday.date(),datetime.time(9,15),tzinfo=ist))
        if RASHI_TREND.get(daily)!=RASHI_TREND.get(weekly):
            continue
        expected=RASHI_TREND[daily]
        # volume confirmation on entry day
        entry_day_i=i+1
        vol=df['Volume'].iloc[entry_day_i]
        vol_ma=df['vol_ma'].iloc[entry_day_i]
        open_p=float(df['Open'].iloc[entry_day_i])
        prev_close=float(df['Close'].iloc[i])
        if pd.isna(vol_ma): continue
        if vol<vol_ma: continue
        if expected=="bullish" and open_p<=prev_close: continue
        if expected=="bearish" and open_p>=prev_close: continue
        actual="bullish" if df['Close'].iloc[entry_day_i]>prev_close else "bearish" if df['Close'].iloc[entry_day_i]<prev_close else "neutral"
        if actual!="neutral":
            total+=1
            if expected==actual:
                correct+=1
    print("Volume confirmed accuracy:",correct/total if total else 0,"samples",total)
if __name__=="__main__":
    end=datetime.date.today()
    start=end-datetime.timedelta(days=730)
    backtest(start,end)
