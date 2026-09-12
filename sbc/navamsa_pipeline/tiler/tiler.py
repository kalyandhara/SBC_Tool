"""
Temporal tiler for minute/hour forward generation.
"""
from datetime import datetime, timedelta
import pytz

IST = pytz.timezone("Asia/Kolkata")

def generate_times(start_date, end_date, granularity):
    start = IST.localize(datetime.combine(start_date, datetime.min.time()))
    end = IST.localize(datetime.combine(end_date, datetime.max.time()))
    if granularity == "1m":
        step = timedelta(minutes=1)
    elif granularity == "5m":
        step = timedelta(minutes=5)
    elif granularity == "1h":
        step = timedelta(hours=1)
    else:
        raise ValueError("Unsupported granularity")
    cur = start
    while cur <= end:
        yield cur
        cur += step

def market_hours_times(start_date, end_date):
    # Generate only IST 09:15-15:30 each trading day
    for dt in generate_times(start_date, end_date, "1m"):
        if dt.weekday() >=5:
            continue
        t = dt.time()
        if datetime.min.time().replace(hour=9, minute=15) <= t <= datetime.min.time().replace(hour=15, minute=30):
            yield dt
