import datetime
import pandas as pd
import yfinance as yf
import swisseph as swe
from sbc.planets import positions
from zoneinfo import ZoneInfo

# Set sidereal mode
swe.set_sid_mode(swe.SIDM_LAHIRI)

# Rashi trend mapping from table
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

# Map sign names to SBC sign_of output
# sign_of returns sign name in English capitalised
SIGN_MAP = {
    "Aries": "Aries",
    "Taurus": "Taurus",
    "Gemini": "Gemini",
    "Cancer": "Cancer",
    "Leo": "Leo",
    "Virgo": "Virgo",
    "Libra": "Libra",
    "Scorpio": "Scorpio",
    "Sagittarius": "Sagittarius",
    "Capricorn": "Capricorn",
    "Aquarius": "Aquarius",
    "Pisces": "Pisces"
}

def get_moon_sign(dt_ist):
    # Convert IST datetime to Julian Day UT
    # dt_ist is timezone-aware or naive IST
    if dt_ist.tzinfo is None:
        ist_tz = ZoneInfo("Asia/Kolkata")
        dt_ist = dt_ist.replace(tzinfo=ist_tz)
    dt_utc = dt_ist.astimezone(ZoneInfo("UTC"))
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600)
    planets, _ = positions(jd)
    moon = next(p for p in planets if p['name'] == 'Moon')
    return moon['sign']

def backtest(start_date, end_date):
    ticker = "^NSEI"
    df = yf.download(ticker, start=start_date, end=end_date, interval='1d', auto_adjust=True, progress=False)
    if df.empty:
        raise ValueError("No price data")
    # Ensure index is date
    df = df[['Open','High','Low','Close']].dropna()
    results = []
    correct = 0
    total = 0
    ist_tz = ZoneInfo("Asia/Kolkata")
    # Ensure column names are simple
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    for idx, row in df.iterrows():
        date = pd.to_datetime(idx).date()
        # Use market open 9:15 IST
        dt_ist = datetime.datetime.combine(date, datetime.time(9,15), tzinfo=ist_tz)
        moon_sign = get_moon_sign(dt_ist)
        expected = RASHI_TREND.get(moon_sign, "neutral")
        # Actual movement: close vs open for intraday
        open_price = float(row['Open'])
        close_price = float(row['Close'])
        actual_price_change_intraday = close_price - open_price
        actual_direction_intraday = "bullish" if actual_price_change_intraday > 0 else ("bearish" if actual_price_change_intraday < 0 else "neutral")
        # Day-over-day change using previous close
        # We'll compute later with shift, for now placeholder
        actual_price_change = actual_price_change_intraday
        actual_direction = actual_direction_intraday
        # For day-over-day
        # If it's first row, skip
        match = None
        if expected != "neutral" and actual_direction != "neutral":
            match = expected == actual_direction
            if match:
                correct += 1
            total += 1
        results.append({
            "date": date.isoformat(),
            "moon_sign": moon_sign,
            "expected": expected,
            "open": open_price,
            "close": close_price,
            "change": float(actual_price_change),
            "actual_direction": actual_direction,
            "match": match
        })
    accuracy = correct/total if total else 0
    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "results": results
    }

if __name__ == "__main__":
    end = datetime.date.today()
    start = end - datetime.timedelta(days=365*2)
    res = backtest(start, end)
    print(f"Backtest NIFTY 50 Moon Rashi {start} to {end}")
    print(f"Samples: {res['total']}, Correct: {res['correct']}, Accuracy: {res['accuracy']:.2%}")
    # Save to file
    pd.DataFrame(res['results']).to_csv("D:/SBC_Tool/moon_rashi_backtest.csv", index=False)
    print("Saved to moon_rashi_backtest.csv")
