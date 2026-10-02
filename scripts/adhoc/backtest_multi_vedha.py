import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import swisseph as swe
import yfinance as yf

from sbc.monthly_heatmap import monthly_heatmap
from sbc.planets import positions

swe.set_sid_mode(swe.SIDM_LAHIRI)
RASHI_TREND={"Aries":"bullish","Taurus":"bullish","Gemini":"bearish","Cancer":"bearish","Leo":"bullish","Virgo":"bearish","Libra":"bearish","Scorpio":"bullish","Sagittarius":"bullish","Capricorn":"bullish","Aquarius":"bearish","Pisces":"bearish"}
def moon_rashi(dt):
    if dt.tzinfo is None: dt=dt.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
    dt_utc=dt.astimezone(ZoneInfo("UTC"))
    jd=swe.julday(dt_utc.year,dt_utc.month,dt_utc.day,dt_utc.hour+dt_utc.minute/60)
    planets,_=positions(jd)
    return next(p for p in planets if p['name']=='Moon')['sign']
def get_vedha_score(date, cache):
    # cache monthly heatmap
    year,month = date.year, date.month
    key=(year,month)
    if key not in cache:
        start=datetime.date(year,month,1)
        # get up to last day of month
        import calendar
        days_in_month=calendar.monthrange(year,month)[1]
        res=monthly_heatmap(start_date=start, days=days_in_month+5, tz_name='Asia/Kolkata', anchor_key='nse')
        mat=res['matrix']
        # use Nifty Large Caps as market proxy
        sector='Nifty Large Caps'
        scores={}
        if sector in mat:
            for d,s in mat[sector].items():
                try:
                    scores[d]=float(s)
                except: pass
        cache[key]=scores
    return cache[key].get(date.isoformat(), None)

def backtest(start,end):
    df=yf.download("^NSEI", start=start, end=end, interval='1d', auto_adjust=True, progress=False)
    df.columns=[c[0] if isinstance(c,tuple) else c for c in df.columns]
    df=df[['Close']].dropna()
    ist=ZoneInfo("Asia/Kolkata")
    cache={}
    correct=total=0
    prev=None
    for idx in df.index:
        d=pd.to_datetime(idx).date()
        dt=datetime.datetime.combine(d,datetime.time(9,15),tzinfo=ist)
        # multi timeframe
        monday=dt-datetime.timedelta(days=dt.weekday())
        weekly_rashi=moon_rashi(datetime.datetime.combine(monday.date(),datetime.time(9,15),tzinfo=ist))
        daily_rashi=moon_rashi(dt)
        if RASHI_TREND.get(daily_rashi)!=RASHI_TREND.get(weekly_rashi):
            prev=float(df.loc[idx,'Close'])
            continue
        # vedha filter
        vedha=get_vedha_score(d,cache)
        expected=RASHI_TREND[daily_rashi]
        if vedha is None:
            prev=float(df.loc[idx,'Close'])
            continue
        if (expected=="bullish" and vedha<=0) or (expected=="bearish" and vedha>=0):
            prev=float(df.loc[idx,'Close'])
            continue
        close=float(df.loc[idx,'Close'])
        if prev is not None:
            actual="bullish" if close>prev else "bearish" if close<prev else "neutral"
            if actual!="neutral":
                total+=1
                if expected==actual:
                    correct+=1
        prev=close
    print("Accuracy with multi-timeframe + vedha filter:", correct/total if total else 0, "samples", total)

if __name__=="__main__":
    end=datetime.date.today()
    start=end-datetime.timedelta(days=730)
    backtest(start,end)
