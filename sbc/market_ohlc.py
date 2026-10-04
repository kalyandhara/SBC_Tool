"""Read cached 3-min NIFTY/BANK NIFTY bars from data/ohlc/ (never fabricated).

The random sample-bar generator that used to live here was removed (B-24).
"""
import csv
from datetime import UTC, datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "ohlc"  # read-only; not created here

def _file_path(symbol: str, date: datetime) -> Path:
    return DATA_DIR / f"{symbol}_{date.strftime('%Y-%m-%d')}.csv"

def load_week_ohlc(symbol: str = "NIFTY", days: int = 7) -> list[dict[str, str]]:
    """Read cached 3-min bars for the last `days` weekdays (read-only).

    Never fabricates data: days without a cached file are simply skipped.
    """
    data = []
    for i in range(days):
        d = datetime.now(UTC).date() - timedelta(days=i+1)
        if d.weekday() >=5:
            continue
        fp = _file_path(symbol, datetime.combine(d, datetime.min.time()))
        if fp.exists():
            with open(fp) as f:
                r = csv.DictReader(f)
                for row in r:
                    data.append(row)
    return data
