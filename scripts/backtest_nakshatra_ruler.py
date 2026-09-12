import datetime
import pandas as pd
import yfinance as yf
import swisseph as swe
from sbc.planets import positions
from sbc.nakshatra import nakshatra_of
from zoneinfo import ZoneInfo

swe.set_sid_mode(swe.SIDM_LAHIRI)

# Planet nature
BENEFIC = {"Jupiter","Venus","Mercury","Moon"}
MALEFIC = {"Sun","Mars","Saturn","Rahu","Ketu"}

def get_moon_nakshatra_ruler(dt_ist):
    if dt_ist.tzinfo is None:
        dt_ist = dt_ist.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
    dt_utc = dt_ist.astimezone(ZoneInfo("UTC"))
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600)
    planets, _ = positions(jd)
    moon = next(p for p in planets if p['name'] == 'Moon')
    nakshatra, pada = nakshatra_of(moon['longitude'])
    # Get ruler from nakshatra mapping
    # Use sbc.nakshatra.nakshatra_ruler? Let's infer from known mapping
    # We'll use a static map
    nakshatra_ruler_map = {
        'Ashwini':'Ketu','Bharani':'Venus','Krittika':'Sun','Rohini':'Moon','Mrigashira':'Mars','Ardra':'Rahu','Punarvasu':'Jupiter','Pushya':'Saturn','Ashlesha':'Mercury','Magha':'Ketu','Purva Phalguni':'Venus','Uttara Phalguni':'Sun','Hasta':'Moon','Chitra':'Mars','Swati':'Rahu','Vishakha':'Jupiter','Anuradha':'Saturn','Jyeshtha':'Mercury','Mula':'Ketu','Purva Ashadha':'Venus','Uttara Ashadha':'Sun','Shravana':'Moon','Dhanishta':'Mars','Shatabhisha':'Rahu','Purva Bhadrapada':'Jupiter','Uttara Bhadrapada':'Saturn','Revati':'Mercury'
    }
    ruler = nakshatra_ruler_map.get(nakshatra, None)
    nature = "bullish" if ruler in BENEFIC else "bearish" if ruler in MALEFIC else "neutral"
    return nakshatra, ruler, nature

def backtest(start_date, end_date):
    ticker = "^NSEI"
    df = yf.download(ticker, start=start_date, end=end_date, interval='1d', auto_adjust=True, progress=False)
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df[['Open','Close']].dropna()
    ist_tz = ZoneInfo("Asia/Kolkata")
    correct = 0
    total = 0
    results = []
    for idx, row in df.iterrows():
        date = pd.to_datetime(idx).date()
        dt_ist = datetime.datetime.combine(date, datetime.time(9,15), tzinfo=ist_tz)
        nakshatra, ruler, expected = get_moon_nakshatra_ruler(dt_ist)
        prev_close = None
        # day-over-day
        # We'll compute in loop with previous
    # Use itertuples for previous
    data = []
    prev_close = None
    for idx in df.index:
        date = pd.to_datetime(idx).date()
        dt_ist = datetime.datetime.combine(date, datetime.time(9,15), tzinfo=ist_tz)
        nakshatra, ruler, expected = get_moon_nakshatra_ruler(dt_ist)
        close = float(df.loc[idx, 'Close'])
        if prev_close is None:
            prev_close = close
            continue
        actual = "bullish" if close > prev_close else "bearish" if close < prev_close else "neutral"
        match = None
        if expected != "neutral" and actual != "neutral":
            total += 1
            match = expected == actual
            if match:
                correct += 1
        results.append({
            "date": date.isoformat(),
            "nakshatra": nakshatra,
            "ruler": ruler,
            "expected": expected,
            "close": close,
            "prev_close": prev_close,
            "actual": actual,
            "match": match
        })
        prev_close = close
    accuracy = correct/total if total else 0
    return total, correct, accuracy, results

if __name__ == "__main__":
    end = datetime.date.today()
    start = end - datetime.timedelta(days=365*2)
    total, correct, acc, results = backtest(start, end)
    print(f"Nakshatra Ruler backtest NIFTY50 {start} to {end}")
    print(f"Samples: {total}, Correct: {correct}, Accuracy: {acc:.2%}")
    pd.DataFrame(results).to_csv("D:/SBC_Tool/nakshatra_ruler_backtest.csv", index=False)
    print("Saved")
