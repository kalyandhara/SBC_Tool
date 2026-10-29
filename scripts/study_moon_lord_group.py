"""Study: Moon in a nakshatra-lord group vs asset move magnitude.

Tests the class of rule "when the Moon transits X's nakshatras, asset A
makes big moves" (e.g. Moon in Rahu's nakshatras - Ardra, Swati,
Shatabhisha - against crude).  Periods come from
sbc.transits.nakshatra_periods (Lahiri sidereal); prices use the repo
convention: open of the first trading day on/after period start, close
of the last trading day on/before period end.

The headline is a magnitude comparison: mean |move| of in-group periods
vs all other Moon periods over the same span, with a label-permutation
test (10,000 shuffles) for the difference in means.  Direction stats are
reported for context but the claim tested is about volatility.

Examples:
    python scripts/study_moon_lord_group.py --asset crude --lord Rahu
    python scripts/study_moon_lord_group.py --asset nifty --lord Mercury
    python scripts/study_moon_lord_group.py --asset gold --lord Saturn \\
        --start 2010-01-01
"""

import argparse
import datetime
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from study_same_sign import classify, price_lookup  # noqa: E402

from sbc.market_data import get_ohlc  # noqa: E402
from sbc.transits import nakshatra_periods  # noqa: E402

NAKSHATRA_LORDS = {
    "Ketu": ["Ashwini", "Magha", "Mula"],
    "Venus": ["Bharani", "P.Phalguni", "P.Ashadha"],
    "Sun": ["Krittika", "U.Phalguni", "U.Ashadha"],
    "Moon": ["Rohini", "Hasta", "Shravana"],
    "Mars": ["Mrigashira", "Chitra", "Dhanishta"],
    "Rahu": ["Ardra", "Swati", "Shatabhisha"],
    "Jupiter": ["Punarvasu", "Vishakha", "P.Bhadrapada"],
    "Saturn": ["Pushya", "Anuradha", "U.Bhadrapada"],
    "Mercury": ["Ashlesha", "Jyeshtha", "Revati"],
}

PERMUTATIONS = 10_000
RNG_SEED = 42


def collect_periods(asset, lord, start_date, end_date):
    """Return (in_group, out_group) move lists and the row table."""
    rows_ohlc = get_ohlc(asset, start_date.isoformat(), end_date.isoformat())
    if not rows_ohlc:
        raise SystemExit(f"no price data for {asset}")
    open_on_or_after, close_on_or_before = price_lookup(rows_ohlc)
    in_names = set(NAKSHATRA_LORDS[lord])

    in_moves, out_moves, table = [], [], []
    for period in nakshatra_periods("Moon", start_date, end_date):
        p_start = datetime.date.fromisoformat(period["start"])
        p_end = datetime.date.fromisoformat(period["end"])
        first = open_on_or_after(p_start)
        last = close_on_or_before(p_end)
        if first is None or last is None or first["time"] > last["time"]:
            continue
        move = (last["close"] - first["open"]) / first["open"] * 100.0
        member = period["nakshatra"] in in_names
        bucket = in_moves if member else out_moves
        bucket.append(move)
        table.append({
            "start": first["time"], "end": last["time"],
            "nakshatra": period["nakshatra"], "move_pct": round(move, 2),
            "abs_move_pct": round(abs(move), 2),
            "group": "in" if member else "out",
            "result": classify(move),
        })
    return in_moves, out_moves, table


def permutation_p(in_moves, out_moves, iters=PERMUTATIONS, seed=RNG_SEED):
    """P(diff-in-mean |move| >= observed) under label shuffling."""
    a = np.abs(np.asarray(in_moves))
    b = np.abs(np.asarray(out_moves))
    pool = np.concatenate([a, b])
    n_in = len(a)
    observed = a.mean() - b.mean()
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(iters):
        rng.shuffle(pool)
        count += pool[:n_in].mean() - pool[n_in:].mean() >= observed
    return observed, float(count / iters)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--asset", default="crude",
                        help="nifty/gold/silver/crude")
    parser.add_argument("--lord", default="Rahu",
                        help="nakshatra lord group: " +
                             ", ".join(NAKSHATRA_LORDS))
    parser.add_argument("--start", default="2000-09-01")
    parser.add_argument("--end", default=datetime.date.today().isoformat())
    parser.add_argument("--save", default=None,
                        help="optional markdown report path")
    args = parser.parse_args()

    start_date = datetime.date.fromisoformat(args.start)
    end_date = datetime.date.fromisoformat(args.end)
    in_moves, out_moves, table = collect_periods(
        args.asset, args.lord, start_date, end_date)
    if not in_moves or not out_moves:
        raise SystemExit("not enough periods to compare")

    obs_diff, p_val = permutation_p(in_moves, out_moves)
    in_abs = np.abs(in_moves)
    out_abs = np.abs(out_moves)

    lines = []
    lines.append(f"# Moon in {args.lord} nakshatras - "
                 f"{args.asset} magnitude study")
    lines.append(f"\nRange {start_date} .. {end_date}. "
                 f"Group: {', '.join(NAKSHATRA_LORDS[args.lord])}. "
                 "Convention: first-open to last-close per Moon "
                 "nakshatra stay.")
    lines.append(f"\n- in-group periods: {len(in_moves)}, "
                 f"mean |move| {in_abs.mean():.2f}%, "
                 f"median {np.median(in_abs):.2f}%, "
                 f"p90 {np.percentile(in_abs, 90):.2f}%")
    lines.append(f"- other periods: {len(out_moves)}, "
                 f"mean |move| {out_abs.mean():.2f}%, "
                 f"median {np.median(out_abs):.2f}%, "
                 f"p90 {np.percentile(out_abs, 90):.2f}%")
    lines.append(f"- observed mean |move| uplift: {obs_diff:+.2f} pp, "
                 f"permutation p = {p_val:.4f}")
    up_in = sum(1 for m in in_moves if m > 0) / len(in_moves) * 100.0
    up_out = sum(1 for m in out_moves if m > 0) / len(out_moves) * 100.0
    lines.append(f"- direction (context only): in-group {up_in:.0f}% up "
                 f"vs others {up_out:.0f}% up")

    big = 2.0
    big_in = (in_abs >= big).mean() * 100.0
    big_out = (out_abs >= big).mean() * 100.0
    lines.append(f"- days with |move| >= {big:.0f}%: in-group "
                 f"{big_in:.1f}% vs others {big_out:.1f}%")

    report = "\n".join(lines) + "\n"
    print(report)
    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        with open(args.save, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"saved: {args.save}")


if __name__ == "__main__":
    main()
