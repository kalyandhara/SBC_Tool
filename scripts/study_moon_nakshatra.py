"""Transit-wise historical study: Moon daily nakshatra volatility profile.

For each trading day the Moon's sidereal nakshatra at the market open
(09:15 IST — the repo-wide convention, same as
scripts/backtest_nakshatra_ruler.py) is attributed to the day, then
per-nakshatra statistics are computed: average daily range, gap
behaviour, open-to-close move, positive-day rate, and best/worst
single days.  The Moon ingresses roughly once a day, so open-time
attribution is the standard day-level convention.

Examples:
    python scripts/study_moon_nakshatra.py --asset nifty
    python scripts/study_moon_nakshatra.py --asset gold --start 2010-01-01
"""

import argparse
import csv
import datetime
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from zoneinfo import ZoneInfo  # noqa: E402

import swisseph as swe  # noqa: E402

from sbc.market_data import get_ohlc  # noqa: E402
from sbc.nakshatra import nakshatra_of  # noqa: E402
from sbc.planets import positions  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")


def moon_nakshatra_at_open(date):
    """Return (nakshatra, pada) of the Moon at 09:15 IST on `date`."""
    dt = datetime.datetime.combine(date, datetime.time(9, 15), tzinfo=IST)
    dt_utc = dt.astimezone(ZoneInfo("UTC"))
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day,
                    dt_utc.hour + dt_utc.minute / 60.0
                    + dt_utc.second / 3600.0)
    planets, _ = positions(jd)
    moon = next(p for p in planets if p["name"] == "Moon")
    return nakshatra_of(moon["longitude"])


def study(asset, start_date, end_date):
    """Return (day_rows, agg, overall) for the Moon nakshatra profile."""
    rows_ohlc = get_ohlc(asset, start_date.isoformat(), end_date.isoformat())
    if not rows_ohlc:
        raise SystemExit(f"no price data for {asset}")

    day_rows = []
    prev_close = None
    for r in rows_ohlc:
        d = datetime.date.fromisoformat(r["time"])
        nak, pada = moon_nakshatra_at_open(d)
        o, high, low, c = r["open"], r["high"], r["low"], r["close"]
        gap_pct = ((o - prev_close) / prev_close * 100.0
                   if prev_close else None)
        move_pct = (c - o) / o * 100.0
        range_pct = (high - low) / o * 100.0
        if prev_close is None or c > prev_close:
            result = "up"
        elif c < prev_close:
            result = "down"
        else:
            result = "flat"
        day_rows.append({
            "date": r["time"],
            "nakshatra": nak,
            "pada": pada,
            "open": o,
            "high": high,
            "low": low,
            "close": c,
            "prev_close": prev_close,
            "gap_pct": round(gap_pct, 2) if gap_pct is not None else "",
            "move_pct": round(move_pct, 2),
            "range_pct": round(range_pct, 2),
            "result": result,
        })
        prev_close = c

    agg = {}
    for r in day_rows:
        a = agg.setdefault(r["nakshatra"],
                           {"days": 0, "up": 0, "ranges": [], "gaps": [],
                            "moves": []})
        a["days"] += 1
        a["ranges"].append(r["range_pct"])
        a["moves"].append(r["move_pct"])
        if r["gap_pct"] != "":
            a["gaps"].append(abs(r["gap_pct"]))
        if r["result"] == "up":
            a["up"] += 1
    for a in agg.values():
        a["avg_range"] = round(sum(a["ranges"]) / len(a["ranges"]), 2)
        a["avg_gap"] = (round(sum(a["gaps"]) / len(a["gaps"]), 2)
                        if a["gaps"] else 0.0)
        a["avg_move"] = round(sum(a["moves"]) / len(a["moves"]), 2)
        a["up_pct"] = round(a["up"] / a["days"] * 100.0, 1)

    up_days = sum(1 for r in day_rows if r["result"] == "up")
    overall = {
        "asset": asset,
        "range": f"{start_date} .. {end_date}",
        "days": len(day_rows),
        "up_days": up_days,
        "up_pct": round(up_days / len(day_rows) * 100.0, 1) if day_rows else 0.0,
        "avg_range": (round(sum(r["range_pct"] for r in day_rows)
                            / len(day_rows), 2) if day_rows else 0.0),
        "best": max(day_rows, key=lambda r: r["move_pct"], default=None),
        "worst": min(day_rows, key=lambda r: r["move_pct"], default=None),
    }
    return day_rows, agg, overall


def print_report(agg, overall):
    print(f"MOON DAILY NAKSHATRA PROFILE  {overall['asset'].upper()}  "
          f"({overall['range']})")
    header = (f"{'Nakshatra':15s} {'Days':>6s} {'Up%':>6s} "
              f"{'AvgRange%':>10s} {'AvgGap%':>9s} {'AvgMove%':>9s}")
    print(header)
    print("-" * len(header))
    for nak in sorted(agg, key=lambda n: agg[n]["avg_range"], reverse=True):
        a = agg[nak]
        print(f"{nak:15s} {a['days']:>6d} {a['up_pct']:>6.1f} "
              f"{a['avg_range']:>10.2f} {a['avg_gap']:>9.2f} "
              f"{a['avg_move']:>+9.2f}")
    print()
    print("SUMMARY")
    print(f"  Trading days: {overall['days']}  (up {overall['up_pct']}%)")
    print(f"  Average daily range: {overall['avg_range']:.2f}%")
    if overall["best"]:
        b = overall["best"]
        print(f"  Best day:  {b['date']} {b['nakshatra']} {b['move_pct']:+.2f}%")
    if overall["worst"]:
        w = overall["worst"]
        print(f"  Worst day: {w['date']} {w['nakshatra']} {w['move_pct']:+.2f}%")


def save_csv(day_rows, agg, overall, out_dir="data/output"):
    start_d, end_d = (datetime.date.fromisoformat(x)
                      for x in overall["range"].split(" .. "))
    base = (f"study_{overall['asset']}_moon_nakshatra_daily"
            f"_{start_d.year}_{end_d.year}")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, base + ".csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(day_rows[0].keys()))
        writer.writeheader()
        writer.writerows(day_rows)

    agg_rows = []
    for nak, a in agg.items():
        agg_rows.append({"nakshatra": nak, "days": a["days"],
                         "up_pct": a["up_pct"], "avg_range": a["avg_range"],
                         "avg_gap": a["avg_gap"], "avg_move": a["avg_move"]})
    path = os.path.join(out_dir, base + "_agg.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(agg_rows[0].keys()))
        writer.writeheader()
        writer.writerows(agg_rows)
    print(f"\nSaved: {path} (+ _agg.csv)")


def main():
    parser = argparse.ArgumentParser(
        description="Moon daily nakshatra volatility profile")
    parser.add_argument("--asset", default="nifty",
                        help="nifty, gold or silver")
    parser.add_argument("--start", default="2007-01-01")
    parser.add_argument("--end", default=datetime.date.today().isoformat())
    parser.add_argument("--no-csv", action="store_true")
    args = parser.parse_args()

    day_rows, agg, overall = study(args.asset,
                                   datetime.date.fromisoformat(args.start),
                                   datetime.date.fromisoformat(args.end))
    print_report(agg, overall)
    if day_rows and not args.no_csv:
        save_csv(day_rows, agg, overall)


if __name__ == "__main__":
    main()
