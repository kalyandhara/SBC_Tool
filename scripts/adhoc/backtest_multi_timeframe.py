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
def backtest(start,end):
    df=yf.download("^NSEI",start=start,end=end,interval='1d',auto_adjust=True,progress=False)
    df.columns=[c[0] if isinstance(c,tuple) else c for c in df.columns]
    df=df[['Close']].dropna()
    ist=ZoneInfo("Asia/Kolkata")
    correct=total=0
    prev=None
    for idx in df.index:
        d=pd.to_datetime(idx).date()
        dt=datetime.datetime.combine(d,datetime.time(9,15),tzinfo=ist)
        # weekly check: Monday of this week
        monday=dt-datetime.timedelta(days=dt.weekday())
        weekly_rashi=moon_rashi(datetime.datetime.combine(monday.date(),datetime.time(9,15),tzinfo=ist))
        daily_rashi=moon_rashi(dt)
        if RASHI_TREND.get(daily_rashi)==RASHI_TREND.get(weekly_rashi):
            close=float(df.loc[idx,'Close'])
            if prev is not None:
                actual="bullish" if close>prev else "bearish" if close<prev else "neutral"
                expected=RASHI_TREND[daily_rashi]
                if actual!="neutral":
                    total+=1
                    if expected==actual:
                        correct+=1
            prev=close
        else:
            prev=float(df.loc[idx,'Close'])
    print("Multi-timeframe accuracy:",correct/total if total else 0)
backtest(datetime.date.today()-datetime.timedelta(days=730),datetime.date.today())
