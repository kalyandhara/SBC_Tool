import datetime, pandas as pd, yfinance as yf, swisseph as swe
from sbc.planets import positions
from sbc.monthly_heatmap import monthly_heatmap
from zoneinfo import ZoneInfo
swe.set_sid_mode(swe.SIDM_LAHIRI)
RASHI_TREND={"Aries":"bullish","Taurus":"bullish","Gemini":"bearish","Cancer":"bearish","Leo":"bullish","Virgo":"bearish","Libra":"bearish","Scorpio":"bullish","Sagittarius":"bullish","Capricorn":"bullish","Aquarius":"bearish","Pisces":"bearish"}

def moon_rashi(dt):
    if dt.tzinfo is None: dt=dt.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
    dt_utc=dt.astimezone(ZoneInfo("UTC"))
    jd=swe.julday(dt_utc.year,dt_utc.month,dt_utc.day,dt_utc.hour+dt_utc.minute/60)
    planets,_=positions(jd)
    return next(p for p in planets if p['name']=='Moon')['sign']

def lunar_phase(dt):
    # compute sun-moon elongation
    if dt.tzinfo is None: dt=dt.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
    dt_utc=dt.astimezone(ZoneInfo("UTC"))
    jd=swe.julday(dt_utc.year,dt_utc.month,dt_utc.day,dt_utc.hour+dt_utc.minute/60)
    flags=swe.FLG_MOSEPH|swe.FLG_SIDEREAL
    sun,_=swe.calc_ut(jd,swe.SUN,flags)
    moon,_=swe.calc_ut(jd,swe.MOON,flags)
    diff=(moon[0]-sun[0])%360
    # tithi approx diff/12
    return diff

def is_high_mutation(dt):
    d=lunar_phase(dt)
    # Amavasya ~0 deg, Purnima ~180 deg within 10 deg
    return d<10 or d>170 or abs(d-180)<10

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
        # multi timeframe
        monday=dt-datetime.timedelta(days=dt.weekday())
        if RASHI_TREND.get(moon_rashi(dt))!=RASHI_TREND.get(moon_rashi(datetime.datetime.combine(monday.date(),datetime.time(9,15),tzinfo=ist))):
            prev=float(df.loc[idx,'Close'])
            continue
        if is_high_mutation(dt):
            prev=float(df.loc[idx,'Close'])
            continue
        close=float(df.loc[idx,'Close'])
        if prev is not None:
            expected=RASHI_TREND[moon_rashi(dt)]
            actual="bullish" if close>prev else "bearish" if close<prev else "neutral"
            if actual!="neutral":
                total+=1
                if expected==actual:
                    correct+=1
        prev=close
    print("Regime filtered accuracy:", correct/total if total else 0, "samples", total)

if __name__=="__main__":
    end=datetime.date.today()
    start=end-datetime.timedelta(days=730)
    backtest(start,end)
