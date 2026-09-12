import datetime
import pandas as pd
import yfinance as yf
import swisseph as swe
from sbc.planets import positions
from zoneinfo import ZoneInfo

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

def get_moon_sign(dt_ist):
    if dt_ist.tzinfo is None:
        ist_tz = ZoneInfo("Asia/Kolkata")
        dt_ist = dt_ist.replace(tzinfo=ist_tz)
    dt_utc = dt_ist.astimezone(ZoneInfo("UTC"))
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600)
    planets, _ = positions(jd)
    moon = next(p for p in planets if p['name'] == 'Moon')
    return moon['sign']

def backtest_dod(start_date, end_date):
    ticker = "^NSEI"
    df = yf.download(ticker, start=start_date, end=end_date, interval='1d', auto_adjust=True, progress=False)
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df[['Open','High','Low','Close']].dropna()
    df['prev_close'] = df['Close'].shift(1)
    df = df.dropna()
    results = []
    correct = 0
    total = 0
    ist_tz = ZoneInfo("Asia/Kolkata")
    for idx, row in df.iterrows():
        date = pd.to_datetime(idx).date()
        dt_ist = datetime.datetime.combine(date, datetime.time(9,15), tzinfo=ist_tz)
        moon_sign = get_moon_sign(dt_ist)
        expected = RASHI_TREND.get(moon_sign, "neutral")
        actual_change = float(row['Close']) - float(row['prev_close'])
        actual_direction = "bullish" if actual_change > 0 else ("bearish" if actual_change < 0 else "neutral")
        match = None
        if expected != "neutral" and actual_direction != "neutral":
            match = expected == actual_direction
            total += 1
            if match:
                correct += 1
        results.append({
            "date": date.isoformat(),
            "moon_sign": moon_sign,
            "expected": expected,
            "prev_close": float(row['prev_close']),
            "close": float(row['Close']),
            "change": actual_change,
            "actual_direction": actual_direction,
            "match": match
        })
    accuracy = correct/total if total else 0
    return total, correct, accuracy, results

if __name__ == "__main__":
    end = datetime.date.today()
    start = end - datetime.timedelta(days=365*2)
    total, correct, acc, results = backtest_dod(start, end)
    print(f"Day-over-day NIFTY50 Moon Rashi {start} to {end}")
    print(f"Samples: {total}, Correct: {correct}, Accuracy: {acc:.2%}")
    pd.DataFrame(results).to_csv("D:/SBC_Tool/moon_rashi_backtest_dod.csv", index=False)
    print("Saved")
