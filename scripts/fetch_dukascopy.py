"""Download Dukascopy hourly BID candles for XAUUSD and XAGUSD (B-57, amendment 1).

Run on a machine that can reach datafeed.dukascopy.com (the user's PC):

    python scripts/fetch_dukascopy.py                      # 2010-01 to 2026-09, both metals
    python scripts/fetch_dukascopy.py --symbols XAUUSD --start 2024-01 --end 2024-03

Writes data/intraday/<symbol>_1h.csv (time_utc, open, high, low, close, volume) and
data/intraday/<symbol>_1h.meta.json (first/last bar, bar count, months with no data).
Months are cached under data/intraday/cache/, so an interrupted run resumes.

Source format: one LZMA-compressed file per month,
  https://datafeed.dukascopy.com/datafeed/<SYM>/<YYYY>/<MM-1, 2 digits>/BID_candles_hour_1.bi5
holding 24-byte big-endian records (seconds from month start, open, close, low, high as
integer points, volume as float32). If a month's hourly file is missing, the script falls
back to that month's daily 1-minute files and aggregates them to hours.

Nothing is filled or synthesized: a month with no data is listed in the meta file.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import lzma
import struct
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "intraday"
BASE = "https://datafeed.dukascopy.com/datafeed"
REC = struct.Struct(">IIIIIf")
# Plausible price ranges since 2010, used to pick the point size and reject bad decodes.
RANGES = {"XAUUSD": (900.0, 10000.0), "XAGUSD": (8.0, 200.0)}
DIVISORS = (1000.0, 100.0, 100000.0, 10.0)


def _get(url: str, tries: int = 4) -> bytes | None:
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SBC-Tool research)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (k + 1))
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2 * (k + 1))
    raise RuntimeError(f"could not download {url}")


def _decode(raw: bytes, origin: dt.datetime, symbol: str) -> list[tuple]:
    if not raw:
        return []
    data = lzma.decompress(raw)
    recs = [REC.unpack_from(data, i) for i in range(0, len(data) - len(data) % REC.size, REC.size)]
    if not recs:
        return []
    lo, hi = RANGES[symbol]
    div = next((d for d in DIVISORS if lo <= recs[0][1] / d <= hi), None)
    if div is None:
        raise ValueError(f"{symbol}: cannot place price {recs[0][1]} in {RANGES[symbol]}")
    out = []
    for secs, o, c, low, high, vol in recs:
        t = origin + dt.timedelta(seconds=secs)
        out.append((t, o / div, high / div, low / div, c / div, float(vol)))
    return out


def _hours_from_minutes(rows: list[tuple]) -> list[tuple]:
    by_hour: dict[dt.datetime, list[tuple]] = {}
    for r in rows:
        by_hour.setdefault(r[0].replace(minute=0), []).append(r)
    out = []
    for h, rs in sorted(by_hour.items()):
        rs.sort()
        out.append((h, rs[0][1], max(r[2] for r in rs), min(r[3] for r in rs), rs[-1][4], sum(r[5] for r in rs)))
    return out


def month_bars(symbol: str, year: int, month: int) -> list[tuple]:
    origin = dt.datetime(year, month, 1)
    raw = _get(f"{BASE}/{symbol}/{year}/{month - 1:02d}/BID_candles_hour_1.bi5")
    rows = _decode(raw, origin, symbol) if raw else []
    if rows:
        return rows
    minutes: list[tuple] = []
    day = origin
    while day.month == month:
        raw = _get(f"{BASE}/{symbol}/{year}/{month - 1:02d}/{day.day:02d}/BID_candles_min_1.bi5")
        if raw:
            minutes.extend(_decode(raw, day, symbol))
        day += dt.timedelta(days=1)
        time.sleep(0.05)
    return _hours_from_minutes(minutes)


def months(start: str, end: str):
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    while (y, m) <= (ey, em):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def fetch(symbol: str, start: str, end: str) -> dict:
    cache = OUT / "cache" / symbol
    cache.mkdir(parents=True, exist_ok=True)
    empty = []
    for y, m in months(start, end):
        f = cache / f"{y}-{m:02d}.csv"
        if f.exists():
            continue
        rows = month_bars(symbol, y, m)
        # Dukascopy repeats the last price on closed hours with zero volume; keep only traded hours.
        rows = [r for r in rows if r[5] > 0]
        with f.open("w", newline="") as fh:
            w = csv.writer(fh)
            for r in rows:
                w.writerow([r[0].strftime("%Y-%m-%d %H:%M"), *[f"{x:.5f}" for x in r[1:5]], f"{r[5]:.2f}"])
        print(f"{symbol} {y}-{m:02d}: {len(rows)} bars", flush=True)
        time.sleep(0.2)
    rows = []
    for y, m in months(start, end):
        with (cache / f"{y}-{m:02d}.csv").open() as fh:
            got = list(csv.reader(fh))
        if not got:
            empty.append(f"{y}-{m:02d}")
        rows.extend(got)
    rows.sort()
    path = OUT / f"{symbol.lower()}_1h.csv"
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["time_utc", "open", "high", "low", "close", "volume"])
        w.writerows(rows)
    meta = {"symbol": symbol, "source": "Dukascopy BID hourly candles", "requested": [start, end],
            "bars": len(rows), "first": rows[0][0] if rows else None, "last": rows[-1][0] if rows else None,
            "months_without_data": empty, "fetched_at": dt.datetime.now().isoformat(timespec="seconds")}
    (OUT / f"{symbol.lower()}_1h.meta.json").write_text(json.dumps(meta, indent=1))
    return meta


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--symbols", nargs="+", default=["XAUUSD", "XAGUSD"])
    p.add_argument("--start", default="2010-01")
    p.add_argument("--end", default="2026-09")
    a = p.parse_args()
    for s in a.symbols:
        if s not in RANGES:
            p.error(f"unknown symbol {s}")
        meta = fetch(s, a.start, a.end)
        print(json.dumps(meta, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
