import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import swisseph as swe
import yfinance as yf

from sbc.planets import positions

swe.set_sid_mode(swe.SIDM_LAHIRI)
RASHI_TREND={"Aries":"bullish","Taurus":"bullish","Gemini":"bearish","Cancer":"bearish","Leo":"bullish","Virgo":"bearish","Libra":"bearish","Scorpio":"bullish","Sagittarius":"bullish","Capricorn":"bullish","Aquarius":"bearish","Pisces":"bearish"}
def moon_rashi(dt):
    if dt.tzinfo is None: dt=dt.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
    dt_utc=dt.astimezone(ZoneInfo("UTC"))
    jd=swe.julday(dt_utc.year,dt_utc.month,dt_utc.day,dt_utc.hour+dt_utc.minute/60)
    planets,_=positions(jd)
    return next(p for p in planets if p['name']=='Moon')['sign']
def atr(df, period=14):
    high=df['High']; low=df['Low']; close=df['Close']
    tr=[]
    for i in range(1,len(df)):
        tr.append(max(high.iloc[i]-low.iloc[i], abs(high.iloc[i]-close.iloc[i-1]), abs(low.iloc[i]-close.iloc[i-1])))
    tr=pd.Series(tr,index=df.index[1:])
    return tr.rolling(period).mean()
def backtest(start,end):
    df=yf.download("^NSEI",start=start,end=end,interval='1d',auto_adjust=True,progress=False)
    df.columns=[c[0] if isinstance(c,tuple) else c for c in df.columns]
    df=df[['Open','High','Low','Close']].dropna()
    df['ATR']=atr(df)
    ist=ZoneInfo("Asia/Kolkata")
    wins=0
    trades=0
    for i in range(1,len(df)-1):
        d=pd.to_datetime(df.index[i]).date()
        dt=datetime.datetime.combine(d,datetime.time(9,15),tzinfo=ist)
        monday=dt-datetime.timedelta(days=dt.weekday())
        daily=moon_rashi(dt)
        weekly=moon_rashi(datetime.datetime.combine(monday.date(),datetime.time(9,15),tzinfo=ist))
        if RASHI_TREND.get(daily)!=RASHI_TREND.get(weekly):
            continue
        expected=RASHI_TREND[daily]
        atr_val=df['ATR'].iloc[i]
        if pd.isna(atr_val): continue
        # entry next day open
        entry=df['Open'].iloc[i+1]
        stop=entry -0.5*atr_val if expected=="bullish" else entry +0.5*atr_val
        target=entry +1.5*atr_val if expected=="bullish" else entry -1.5*atr_val
        high=float(df['High'].iloc[i+1])
        low=float(df['Low'].iloc[i+1])
        hit_target=False
        hit_stop=False
        if expected=="bullish":
            if high>=target: hit_target=True
            if low<=stop: hit_stop=True
        else:
            if low<=target: hit_target=True
            if high>=stop: hit_stop=True
        if hit_target and not hit_stop:
            wins+=1
        trades+=1
    print("ATR trades:",trades,"win rate:",wins/trades if trades else 0)
if __name__=="__main__":
    end=datetime.date.today()
    start=end-datetime.timedelta(days=730)
    backtest(start,end)
