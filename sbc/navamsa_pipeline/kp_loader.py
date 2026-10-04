"""
Load KP precomputed CSV data for a given date range.
"""
import csv
from datetime import datetime
from pathlib import Path

import pytz

IST = pytz.timezone("Asia/Kolkata")

def find_kp_file(month_date):
    base = Path(__file__).resolve().parents[2] / "data" / "kp"
    # Try file naming KP_Data_MMMYYYY.csv
    month_name = month_date.strftime("%b").capitalize()
    year = month_date.year
    candidates = [
        base / f"KP_Data_{month_name}{year}.csv",
        base / f"KP_Data_{month_date.strftime('%b%Y').capitalize()}.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    # fallback search
    for p in base.glob("KP_Data_*.csv"):
        if month_date.strftime("%Y-%m") in p.stem:
            return p
    return None

def load_kp_for_day(kp_path, target_date):
    rows: list[dict[str, str]] = []
    if not kp_path or not kp_path.exists():
        return rows
    with open(kp_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                ts = datetime.fromisoformat(r['timestamp'])
                if ts.date() == target_date:
                    rows.append(r)
            except Exception:
                continue
    return rows
