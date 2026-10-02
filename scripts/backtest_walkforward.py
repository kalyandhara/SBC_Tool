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
def walk_forward(ticker="^NSEI", start=None, end=None, window_days=365, step_days=90):
    if start is None: start=datetime.date.today()-datetime.timedelta(days=730)
    if end is None: end=datetime.date.today()
    df=yf.download(ticker,start=start,end=end,interval='1d',auto_adjust=True,progress=False)
    df.columns=[c[0] if isinstance(c,tuple) else c for c in df.columns]
    df=df[['Close']].dropna()
    ist=ZoneInfo("Asia/Kolkata")
    results=[]
    cur=start
    while cur<end:
        train_end=cur+datetime.timedelta(days=window_days)
        test_end=min(train_end+datetime.timedelta(days=step_days), end)
        # simple accuracy over test period using multi-tf
        correct=total=0
        # get slice
        prev=None
        for idx in df.index:
            d=pd.to_datetime(idx).date()
            if d<cur or d>=test_end:
                continue
            d=pd.to_datetime(idx).date()
            dt=datetime.datetime.combine(d,datetime.time(9,15),tzinfo=ist)
            monday=dt-datetime.timedelta(days=dt.weekday())
            daily=moon_rashi(dt)
            weekly=moon_rashi(datetime.datetime.combine(monday.date(),datetime.time(9,15),tzinfo=ist))
            if RASHI_TREND.get(daily)!=RASHI_TREND.get(weekly):
                prev=float(df.loc[idx,'Close']); continue
            close=float(df.loc[idx,'Close'])
            if prev is not None:
                expected=RASHI_TREND[daily]
                actual="bullish" if close>prev else "bearish" if close<prev else "neutral"
                if actual!="neutral":
                    total+=1
                    if expected==actual: correct+=1
            prev=close
        acc=correct/total if total else None
        results.append({"train_start":cur.isoformat(),"test_end":test_end.isoformat(),"samples":total,"accuracy":acc})
        cur=cur+datetime.timedelta(days=step_days)
    for r in results:
        print(r)
    return results
if __name__=="__main__":
    walk_forward()
