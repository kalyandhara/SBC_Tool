import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import swisseph as swe
import yfinance as yf

from sbc.planets import positions

swe.set_sid_mode(swe.SIDM_LAHIRI)

RASHI_TREND = {
    "Aries": "bullish",
    "Taurus": "bullish",
    "Gemini": "bearish",
    "Cancer": "bearish",
    "Leo": "bullish",
    "Virgo": "bearish",
    "Libra": "bearish",
    "Scorpio": "bullish",
    "Sagittarius": "bullish",
    "Capricorn": "bullish",
    "Aquarius": "bearish",
    "Pisces": "bearish"
}

SECTORS = {
    "Nifty Bank": "^NSEBANK",
    "Nifty IT": "^NSEIT",
    "Nifty Auto": "^NSEAUTO",
    "Nifty Metal": "^NSEMETAL",
    "Nifty FMCG": "^NSEFMCG",
    "Nifty Pharma": "^NSEPHARMA",
    "Nifty Energy": "^CNXENERGY",
    "Nifty Realty": "^NSEREALTY"
}

FALLBACK = {
    "^NSEIT": "^CNXIT",
    "^NSEAUTO": "^CNXAUTO",
    "^NSEMETAL": "^CNXMETAL",
    "^NSEFMCG": "^CNXFMCG",
    "^NSEPHARMA": "^CNXPHARMA",
    "^NSEREALTY": "^CNXREALTY"
}

def get_moon_sign(dt_ist):
    ist_tz = ZoneInfo("Asia/Kolkata")
    if dt_ist.tzinfo is None:
        dt_ist = dt_ist.replace(tzinfo=ist_tz)
    dt_utc = dt_ist.astimezone(ZoneInfo("UTC"))
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600)
    planets, _ = positions(jd)
    moon = next(p for p in planets if p['name'] == 'Moon')
    return moon['sign']

def backtest_sector(ticker, start, end):
    df = yf.download(ticker, start=start, end=end, interval='1d', auto_adjust=True, progress=False)
    if df.empty:
        fb = FALLBACK.get(ticker)
        if fb:
            df = yf.download(fb, start=start, end=end, interval='1d', auto_adjust=True, progress=False)
    if df.empty:
        return None
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df[['Open','High','Low','Close']].dropna()
    ist_tz = ZoneInfo("Asia/Kolkata")
    correct = 0
    total = 0
    for i in range(1, len(df)):
        date = pd.to_datetime(df.index[i]).date()
        dt_ist = datetime.datetime.combine(date, datetime.time(9,15), tzinfo=ist_tz)
        moon_sign = get_moon_sign(dt_ist)
        expected = RASHI_TREND.get(moon_sign)
        prev_close = float(df['Close'].iloc[i-1])
        close = float(df['Close'].iloc[i])
        actual = "bullish" if close > prev_close else "bearish" if close < prev_close else "neutral"
        if expected and actual != "neutral":
            total += 1
            if expected == actual:
                correct += 1
    acc = correct/total if total else 0
    return total, correct, acc

if __name__ == "__main__":
    end = datetime.date.today()
    start = end - datetime.timedelta(days=365*2)
    rows = []
    for name, ticker in SECTORS.items():
        res = backtest_sector(ticker, start, end)
        if res:
            total, correct, acc = res
            rows.append({"sector": name, "ticker": ticker, "samples": total, "correct": correct, "accuracy": acc})
            print(f"{name}: {total} samples, accuracy {acc:.2%}")
    pd.DataFrame(rows).to_csv("D:/SBC_Tool/moon_rashi_multi_sector.csv", index=False)
