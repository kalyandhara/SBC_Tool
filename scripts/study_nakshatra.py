"""Transit-wise historical study: asset performance during planet
nakshatra transits.

For a planet and asset, computes every nakshatra stay period (entry to
exit) via sbc.transits.nakshatra_periods and prices with the same
first/last trading day convention as the Mars-Jupiter same-sign study.
Reports per-nakshatra aggregate statistics (visits, positive/negative
count, average and total move) — the aggregate across visits is the
headline, since fast planets revisit nakshatras through retrograde
loops.  The full per-period table is saved to CSV.

Examples:
    python scripts/study_nakshatra.py --planet Jupiter --asset gold
    python scripts/study_nakshatra.py --planet Mars --asset nifty
    python scripts/study_nakshatra.py --planet Moon --asset gold --start 2010-01-01
"""

import argparse
import datetime
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from study_same_sign import classify, price_lookup  # noqa: E402

from sbc.market_data import get_ohlc  # noqa: E402
from sbc.transits import nakshatra_periods  # noqa: E402

NAKSHATRAS_27 = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "P.Phalguni", "U.Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "P.Ashadha", "U.Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "P.Bhadrapada", "U.Bhadrapada", "Revati",
]


def study(asset, planet, start_date, end_date):
    """Return (rows, agg, overall) for a planet nakshatra study."""
    rows_ohlc = get_ohlc(asset, start_date.isoformat(), end_date.isoformat())
    if not rows_ohlc:
        raise SystemExit(f"no price data for {asset}")
    open_on_or_after, close_on_or_before = price_lookup(rows_ohlc)

    rows = []
    for period in nakshatra_periods(planet, start_date, end_date):
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
            "nakshatra": period["nakshatra"],
            "pada": period["pada"],
            "days": period["days"],
            "open": first["open"],
            "close": last["close"],
            "move_pct": round(move_pct, 2),
            "result": classify(move_pct),
        })

    agg = {}
    for r in rows:
        a = agg.setdefault(r["nakshatra"],
                           {"visits": 0, "pos": 0, "neg": 0, "moves": []})
        a["visits"] += 1
        a["moves"].append(r["move_pct"])
        if r["result"] == "Positive":
            a["pos"] += 1
        elif r["result"] == "Negative":
            a["neg"] += 1
    for a in agg.values():
        a["avg_move"] = round(sum(a["moves"]) / len(a["moves"]), 2)
        a["total_move"] = round(sum(a["moves"]), 2)
        a["pos_pct"] = round(a["pos"] / a["visits"] * 100.0, 1)

    overall = {
        "asset": asset,
        "planet": planet,
        "range": f"{start_date} .. {end_date}",
        "total": len(rows),
        "positive": sum(1 for r in rows if r["result"] == "Positive"),
        "negative": sum(1 for r in rows if r["result"] == "Negative"),
    }
    if rows:
        overall["positive_pct"] = round(
            overall["positive"] / overall["total"] * 100.0, 1)
    return rows, agg, overall


def print_report(agg, overall):
    print(f"{overall['planet'].upper()} NAKSHATRA TRANSITS  "
          f"{overall['asset'].upper()}  ({overall['range']})")
    header = (f"{'Nakshatra':15s} {'Visits':>6s} {'Pos':>5s} {'Neg':>5s} "
              f"{'Pos%':>6s} {'Avg %':>8s} {'Total %':>9s}")
    print(header)
    print("-" * len(header))
    for nak in sorted(agg, key=lambda n: agg[n]["avg_move"], reverse=True):
        a = agg[nak]
        print(f"{nak:15s} {a['visits']:>6d} {a['pos']:>5d} {a['neg']:>5d} "
              f"{a['pos_pct']:>6.1f} {a['avg_move']:>+8.2f} "
              f"{a['total_move']:>+9.2f}")
    print()
    print("SUMMARY")
    print(f"  Periods analysed: {overall['total']}")
    print(f"  Positive: {overall['positive']} "
          f"({overall.get('positive_pct', 0.0)}%)")
    print(f"  Negative: {overall['negative']}")


def save_csv(rows, overall, out_dir="data/output"):
    import csv

    os.makedirs(out_dir, exist_ok=True)
    start_d, end_d = (datetime.date.fromisoformat(x)
                      for x in overall["range"].split(" .. "))
    name = (f"study_{overall['asset']}_{overall['planet'].lower()}_nakshatra"
            f"_{start_d.year}_{end_d.year}.csv")
    path = os.path.join(out_dir, name)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved: {path}")


def main():
    parser = argparse.ArgumentParser(description="Nakshatra transit study")
    parser.add_argument("--planet", default="Jupiter")
    parser.add_argument("--asset", default="gold",
                        help="nifty, gold or silver")
    parser.add_argument("--start", default="2002-01-01")
    parser.add_argument("--end", default=datetime.date.today().isoformat())
    parser.add_argument("--no-csv", action="store_true")
    args = parser.parse_args()

    if args.planet not in ("Sun", "Moon", "Mars", "Mercury", "Jupiter",
                           "Venus", "Saturn", "Rahu", "Ketu"):
        raise SystemExit(f"unknown planet {args.planet!r}")

    rows, agg, overall = study(args.asset, args.planet,
                               datetime.date.fromisoformat(args.start),
                               datetime.date.fromisoformat(args.end))
    print_report(agg, overall)
    if rows and not args.no_csv:
        save_csv(rows, overall)


if __name__ == "__main__":
    main()
