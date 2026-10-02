import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import swisseph as swe
import yfinance as yf

from sbc.nakshatra import nakshatra_of
from sbc.planets import positions

swe.set_sid_mode(swe.SIDM_LAHIRI)

RASHI_TREND = {
    "Aries": "bullish","Taurus": "bullish","Gemini": "bearish","Cancer": "bearish",
    "Leo": "bullish","Virgo": "bearish","Libra": "bearish","Scorpio": "bullish",
    "Sagittarius": "bullish","Capricorn": "bullish","Aquarius": "bearish","Pisces": "bearish"
}
BENEFIC = {"Jupiter","Venus","Mercury","Moon"}
MALEFIC = {"Sun","Mars","Saturn","Rahu","Ketu"}
nakshatra_ruler_map = {
    'Ashwini':'Ketu','Bharani':'Venus','Krittika':'Sun','Rohini':'Moon','Mrigashira':'Mars','Ardra':'Rahu','Punarvasu':'Jupiter','Pushya':'Saturn','Ashlesha':'Mercury','Magha':'Ketu','Purva Phalguni':'Venus','Uttara Phalguni':'Sun','Hasta':'Moon','Chitra':'Mars','Swati':'Rahu','Vishakha':'Jupiter','Anuradha':'Saturn','Jyeshtha':'Mercury','Mula':'Ketu','Purva Ashadha':'Venus','Uttara Ashadha':'Sun','Shravana':'Moon','Dhanishta':'Mars','Shatabhisha':'Rahu','Purva Bhadrapada':'Jupiter','Uttara Bhadrapada':'Saturn','Revati':'Mercury'
}

def get_moon_data(dt_ist):
    if dt_ist.tzinfo is None:
        dt_ist = dt_ist.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
    dt_utc = dt_ist.astimezone(ZoneInfo("UTC"))
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60)
    planets, _ = positions(jd)
    moon = next(p for p in planets if p['name']=='Moon')
    rashi = moon['sign']
    nakshatra, _ = nakshatra_of(moon['longitude'])
    ruler = nakshatra_ruler_map.get(nakshatra)
    rashi_expected = RASHI_TREND.get(rashi)
    nakshatra_expected = "bullish" if ruler in BENEFIC else "bearish" if ruler in MALEFIC else "neutral"
    return rashi, rashi_expected, nakshatra, ruler, nakshatra_expected

def backtest(start, end):
    ticker = "^NSEI"
    df = yf.download(ticker, start=start, end=end, interval='1d', auto_adjust=True, progress=False)
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df[['Close']].dropna()
    ist_tz = ZoneInfo("Asia/Kolkata")
    results = []
    correct = 0
    total = 0
    prev_close = None
    for idx in df.index:
        date = pd.to_datetime(idx).date()
        dt_ist = datetime.datetime.combine(date, datetime.time(9,15), tzinfo=ist_tz)
        rashi, rashi_exp, nakshatra, ruler, nak_exp = get_moon_data(dt_ist)
        close = float(df.loc[idx,'Close'])
        if prev_close is None:
            prev_close = close
            continue
        actual = "bullish" if close > prev_close else "bearish" if close < prev_close else "neutral"
        # Confluence
        if rashi_exp == nak_exp and rashi_exp != "neutral":
            expected = rashi_exp
            confidence = "high"
        elif rashi_exp == "neutral" or nak_exp == "neutral":
            expected = "neutral"
            confidence = "low"
        else:
            expected = "neutral"
            confidence = "conflict"
        match = None
        if expected != "neutral" and actual != "neutral":
            total += 1
            match = expected == actual
            if match:
                correct += 1
        results.append({
            "date": date.isoformat(),
            "rashi": rashi,
            "rashi_expected": rashi_exp,
            "nakshatra": nakshatra,
            "ruler": ruler,
            "nak_expected": nak_exp,
            "expected": expected,
            "confidence": confidence,
            "actual": actual,
            "match": match
        })
        prev_close = close
    acc = correct/total if total else 0
    return total, correct, acc, results

if __name__ == "__main__":
    end = datetime.date.today()
    start = end - datetime.timedelta(days=365*2)
    total, correct, acc, results = backtest(start, end)
    print("Confluence Moon Rashi + Nakshatra Ruler NIFTY50")
    print(f"Samples: {total}, Correct: {correct}, Accuracy: {acc:.2%}")
    pd.DataFrame(results).to_csv("D:/SBC_Tool/confluence_moon_rashi_nakshatra.csv", index=False)
