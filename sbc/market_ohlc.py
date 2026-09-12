"""OHLC cache + fallback for NIFTY/BANK NIFTY backtesting."""
from pathlib import Path
from datetime import datetime, timedelta
import json
import csv
import random

DATA_DIR = Path("data/ohlc")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _file_path(symbol: str, date: datetime):
    return DATA_DIR / f"{symbol}_{date.strftime('%Y-%m-%d')}.csv"

def ensure_week_cache(symbol: str = "NIFTY", days: int = 7):
    files = []
    for i in range(days):
        d = datetime.utcnow().date() - timedelta(days=i+1)
        # skip weekends
        # simple check
        if d.weekday() >= 5:
            continue
        fp = _file_path(symbol, datetime.combine(d, datetime.min.time()))
        if not fp.exists():
            generate_sample_ohlc(fp, d)
        files.append(fp)
    return files

def generate_sample_ohlc(fp: Path, date):
    """Generate 3-min bars for a trading day 09:15-15:30."""
    start_price = 25000 + random.randint(-500, 500)
    price = start_price
    rows = []
    minutes = list(range(9*60+15, 15*60+30, 3))
    for m in minutes:
        open_p = price
        change = random.uniform(-10, 10)
        close_p = open_p + change
        high_p = max(open_p, close_p) + random.uniform(0, 5)
        low_p = min(open_p, close_p) - random.uniform(0, 5)
        price = close_p
        hh = m // 60
        mm = m % 60
        time_str = f"{hh:02d}:{mm:02d}"
        rows.append([date.isoformat(), time_str, round(open_p,2), round(high_p,2), round(low_p,2), round(close_p,2), random.randint(1000,10000)])
    with open(fp, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(["date","time","open","high","low","close","volume"])
        w.writerows(rows)

def load_week_ohlc(symbol: str = "NIFTY", days: int = 7):
    ensure_week_cache(symbol, days)
    data = []
    for i in range(days):
        d = datetime.utcnow().date() - timedelta(days=i+1)
        if d.weekday() >=5:
            continue
        fp = _file_path(symbol, datetime.combine(d, datetime.min.time()))
        if fp.exists():
            with open(fp) as f:
                r = csv.DictReader(f)
                for row in r:
                    data.append(row)
    return data
