"""Transit-wise historical study: asset performance during same-sign periods.

Replicates the Mars-Jupiter same-sign XAU/USD methodology (image
baseline, 2002-2024): for each period the opening price is the first
available trading day on or after the period start and the closing
price is the last available trading day on or before the period end
(weekend/holiday adjustment).  Result is Positive / Flat / Negative
with Flat when |move| < 0.1%.

Examples:
    python scripts/study_same_sign.py --asset gold
    python scripts/study_same_sign.py --asset silver --planet Mars --other Jupiter
    python scripts/study_same_sign.py --asset nifty --start 2007-01-01
"""

import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc.market_data import get_ohlc  # noqa: E402
from sbc.transits import same_sign_periods  # noqa: E402

FLAT_THRESHOLD_PCT = 0.1


def classify(move_pct):
    if abs(move_pct) < FLAT_THRESHOLD_PCT:
        return "Flat"
    return "Positive" if move_pct > 0 else "Negative"


def price_lookup(rows_ohlc):
    """Return (open_on_or_after, close_on_or_before) bound to OHLC rows.

    Implements the weekend/holiday adjustment: the opening price is the
    first available trading day on or after a date and the closing
    price is the last available trading day on or before a date.
    """
    dates = [datetime.date.fromisoformat(r["time"]) for r in rows_ohlc]

    def open_on_or_after(d):
        for r, dt in zip(rows_ohlc, dates, strict=True):
            if dt >= d:
                return r
        return None

    def close_on_or_before(d):
        result = None
        for r, dt in zip(rows_ohlc, dates, strict=True):
            if dt > d:
                break
            result = r
        return result

    return open_on_or_after, close_on_or_before


def study(asset, planet_a, planet_b, start_date, end_date):
    """Return (rows, summary) for the same-sign study of one asset."""
    rows_ohlc = get_ohlc(asset, start_date.isoformat(), end_date.isoformat())
    if not rows_ohlc:
        raise SystemExit(f"no price data for {asset}")
    open_on_or_after, close_on_or_before = price_lookup(rows_ohlc)

    rows = []
    for period in same_sign_periods(planet_a, planet_b, start_date, end_date):
        p_start = datetime.date.fromisoformat(period["start"])
        p_end = datetime.date.fromisoformat(period["end"])
        first = open_on_or_after(p_start)
        last = close_on_or_before(p_end)
        if first is None or last is None or first["time"] > last["time"]:
            continue
        move_pct = (last["close"] - first["open"]) / first["open"] * 100.0
        rows.append({
            "start": first["time"],
            "end": last["time"],
            "sign": period["sign"],
            "open": first["open"],
            "close": last["close"],
            "move_pct": round(move_pct, 2),
            "result": classify(move_pct),
        })

    positive = sum(1 for r in rows if r["result"] == "Positive")
    negative = sum(1 for r in rows if r["result"] == "Negative")
    avg = sum(r["move_pct"] for r in rows) / len(rows) if rows else 0.0
    best = max(rows, key=lambda r: r["move_pct"], default=None)
    worst = min(rows, key=lambda r: r["move_pct"], default=None)
    summary = {
        "asset": asset,
        "pair": f"{planet_a}-{planet_b} same sign",
        "range": f"{start_date} .. {end_date}",
        "total": len(rows),
        "positive": positive,
        "negative": negative,
        "positive_pct": round(positive / len(rows) * 100.0, 1) if rows else 0.0,
        "avg_move": round(avg, 2),
        "best": best,
        "worst": worst,
    }
    return rows, summary


def print_report(rows, summary):
    print(f"{summary['pair'].upper()}  {summary['asset'].upper()} "
          f"PERFORMANCE  ({summary['range']})")
    header = (f"{'Start':12s} {'End':12s} {'Sign':12s} {'Open':>10s} "
              f"{'Close':>10s} {'Move %':>8s}  Result")
    print(header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['start']:12s} {r['end']:12s} {r['sign']:12s} "
              f"{r['open']:>10.2f} {r['close']:>10.2f} "
              f"{r['move_pct']:>+8.2f}  {r['result']}")
    print()
    print("SUMMARY")
    print(f"  Total cycles: {summary['total']}")
    print(f"  Positive: {summary['positive']} ({summary['positive_pct']}%)")
    print(f"  Negative: {summary['negative']}")
    print(f"  Average change: {summary['avg_move']:+.2f}%")
    if summary["best"]:
        b = summary["best"]
        print(f"  Best: {b['start'][:4]} {b['sign']} {b['move_pct']:+.2f}%")
    if summary["worst"]:
        w = summary["worst"]
        print(f"  Worst: {w['start'][:4]} {w['sign']} {w['move_pct']:+.2f}%")


def save_csv(rows, summary, out_dir="data/output"):
    import csv

    os.makedirs(out_dir, exist_ok=True)
    start_d, end_d = (datetime.date.fromisoformat(x)
                      for x in summary["range"].split(" .. "))
    name = (f"study_{summary['asset']}_"
            f"{summary['pair'].replace(' ', '_').replace('-', '')}"
            f"_{start_d.year}_{end_d.year}.csv")
    path = os.path.join(out_dir, name)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        fh.write(f"# study: {summary['pair']} {summary['asset']}\n")
        fh.write(f"# range: {summary['range']}\n")
        fh.write(f"# flat_threshold_pct: {FLAT_THRESHOLD_PCT}\n")
        fh.write(f"# price_source: yfinance cache\n")
        fh.write(f"# generated: {datetime.date.today().isoformat()}\n")
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved: {path}")


def main():
    parser = argparse.ArgumentParser(description="Same-sign transit study")
    parser.add_argument("--asset", default="gold",
                        help="nifty, gold or silver")
    parser.add_argument("--planet", default="Mars")
    parser.add_argument("--other", default="Jupiter")
    parser.add_argument("--start", default="2002-01-01")
    parser.add_argument("--end", default=datetime.date.today().isoformat())
    parser.add_argument("--no-csv", action="store_true")
    args = parser.parse_args()

    rows, summary = study(args.asset, args.planet, args.other,
                          datetime.date.fromisoformat(args.start),
                          datetime.date.fromisoformat(args.end))
    print_report(rows, summary)
    if rows and not args.no_csv:
        save_csv(rows, summary)


if __name__ == "__main__":
    main()
