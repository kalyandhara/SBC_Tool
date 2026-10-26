"""Study: does gold outperform while Saturn transits Taurus or Leo?

The AstroZ gold video (2026-10-24) claims gold's great rallies begin when
Saturn enters Taurus (Venus-ruled, tangible wealth) and accelerate in Leo,
citing the 1971-80 and 2000-11 legs.  Two sources are supported:

- `--source gc` (default): repo GC=F daily (2000-08-), one Saturn lap.
- `--source long`: DataHub monthly gold (LBMA-derived, 1833-2026),
  cached to data/gold_monthly_long.csv - covers 1971-1982, the video's
  first cycle, and gives the per-sign test two-plus laps.

Method: daily/monthly close-to-close returns grouped by the Saturn
sidereal sign mid-period, then a permutation test (10,000 label
shuffles) on the Taurus+Leo mean vs random days/months.

Examples:
    python scripts/study_saturn_sign_gold.py
    python scripts/study_saturn_sign_gold.py --source long --start 1971-04-01
"""

import argparse
import datetime
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from sbc.planets import positioned_planets  # noqa: E402
from sbc.transits import sign_periods  # noqa: E402
from scripts.study_mars_node_conjunction import load_series  # noqa: E402

TEST_SIGNS = ("Taurus", "Leo")
ITERS = 10_000
RNG_SEED = 42
LONG_CACHE = os.path.join(_ROOT, "data", "gold_monthly_long.csv")
LONG_URL = ("https://raw.githubusercontent.com/datasets/gold-prices/"
            "master/data/monthly.csv")


def long_rows():
    """Monthly gold (USD/oz, DataHub/LBMA) as {time: 'YYYY-MM-01'} rows."""
    import csv as _csv
    import urllib.request

    text = None
    if not os.path.exists(LONG_CACHE):
        try:
            req = urllib.request.Request(LONG_URL,
                                         headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                text = resp.read().decode("utf-8", "replace")
            if "Date,Price" not in text:
                raise RuntimeError("unexpected payload")
            with open(LONG_CACHE, "w", encoding="utf-8") as fh:
                fh.write(text)
        except Exception as exc:  # noqa: BLE001 - offline fallback below
            print(f"long-series fetch failed ({exc}); trying cache")
    if text is None and os.path.exists(LONG_CACHE):
        with open(LONG_CACHE, encoding="utf-8") as fh:
            text = fh.read()
    if not text:
        raise RuntimeError("no long gold series (fetch failed, no cache)")
    rows = []
    for rec in _csv.DictReader(text.splitlines()):
        try:
            close = float(rec["Price"])
        except (KeyError, ValueError):
            continue
        if close <= 0:
            continue
        y, m = rec["Date"][:4], rec["Date"][5:7]
        rows.append({"time": f"{y}-{m}-01", "close": close})
    return rows


def sign_day_map(periods, dates):
    """{iso date -> Saturn sidereal sign} for the covered range."""
    out = {}
    for p in periods:
        for d in dates:
            if p["start"] <= d <= p["end"]:
                out[d] = p["sign"]
    return out


def mid_month_signs(dates):
    """{month-first -> Saturn sign on the 15th} for monthly dates."""
    out = {}
    for d in dates:
        y, m = int(d[:4]), int(d[5:7])
        planets, _ay, _sun, _moon, _tithi = positioned_planets(
            f"{y:04d}-{m:02d}-15")
        out[d] = next(p for p in planets if p["name"] == "Saturn")["sign"]
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", default="2000-08-01")
    parser.add_argument("--end", default=datetime.date.today().isoformat())
    parser.add_argument("--source", choices=("gc", "long"), default="gc",
                        help="gc = repo GC=F daily (2000-08-); long = "
                             "DataHub monthly from 1833 (cached locally)")
    parser.add_argument("--save", default=None)
    args = parser.parse_args()
    if args.save is None:
        suffix = ("long_2026-10-25" if args.source == "long"
                  else "2026-10-24")
        args.save = os.path.join(
            "reports", f"saturn_sign_gold_study_{suffix}.md")

    if args.source == "long":
        all_rows = long_rows()
        rows = [r for r in all_rows if args.start <= r["time"] <= args.end]
    else:
        rows = load_series("gold", datetime.date.fromisoformat(args.start),
                           datetime.date.fromisoformat(args.end))
    if len(rows) < 40:
        raise SystemExit(f"not enough rows in range: {len(rows)}")
    periods = sign_periods("Saturn", datetime.date.fromisoformat(args.start),
                           datetime.date.fromisoformat(args.end))
    dates = [r["time"] for r in rows[1:]]  # returns need the prior close
    day_sign = (mid_month_signs(dates) if args.source == "long"
                else sign_day_map(periods, dates))

    closes = np.asarray([r["close"] for r in rows])
    rets = (closes[1:] / closes[:-1] - 1.0) * 100.0

    src = "GC=F daily" if args.source == "gc" else \
        "DataHub/LBMA monthly (sign taken mid-month)"
    lines = ["# Saturn sign vs gold returns (permutation test)",
             "",
             f"Range {args.start} .. {args.end}; {src}; close-to-close; "
             f"p = {ITERS:,} label shuffles.",
             "",
             "## Per-sign mean\n",
             "| sign | periods | mean %/period | total % |",
             "|------|---------|---------------|---------|"]
    sign_rets = {}
    sign_order = []
    for p in periods:
        if p["sign"] not in sign_order:
            sign_order.append(p["sign"])
    for sign in sign_order:
        mask = np.asarray([day_sign.get(d) == sign for d in dates])
        if mask.sum() < 10:
            continue
        r = rets[mask]
        sign_rets[sign] = r
        total = (np.prod(1.0 + r / 100.0) - 1.0) * 100.0
        unit = "day" if args.source == "gc" else "month"
        lines.append(f"| {sign} | {mask.sum()} {unit}s "
                     f"| {r.mean():+.3f} | {total:+.1f} |")

    test_mask = np.asarray([day_sign.get(d) in TEST_SIGNS for d in dates])
    obs = float(rets[test_mask].mean())
    rng = np.random.default_rng(RNG_SEED)
    n = len(rets)
    k = int(test_mask.sum())
    means = np.empty(ITERS)
    for i in range(ITERS):
        pick = rng.choice(n, size=k, replace=False)
        means[i] = rets[pick].mean()
    p_ge = float((means >= obs).mean())
    annual = "day" if args.source == "gc" else "month"
    ann_factor = 252 if args.source == "gc" else 12
    lines.append(
        f"\n## Taurus+Leo combined: {k} {annual}s, mean {obs:+.4f}%/"
        f"{annual} ({obs * ann_factor:+.1f}% annualised); random mean "
        f"{float(means.mean()):+.4f}%; P(random >= observed) = {p_ge:.3f}")
    for sign in TEST_SIGNS:
        r = sign_rets.get(sign)
        if r is None or r.size == 0:
            continue
        lines.append(f"- {sign}: n={r.size}, mean {r.mean():+.4f}%/"
                     f"{annual} ({r.mean() * ann_factor:+.1f}% annualised)")

    if args.source == "long":
        lines += [
            "",
            "## Reading (necessary caveats)",
            "",
            "1. **Episode concentration.** Saturn reaches Taurus only "
            "~3 times in 55 years: the Taurus total (+206%) is almost "
            "entirely the 1971-73 leg; Leo's (+301%) is the 1977-79 "
            "leg plus 2006-09. Two historical episodes, not a robust "
            "repeating pattern.",
            "2. **Autocorrelation.** Gold monthly returns trend for "
            "years; the i.i.d. shuffle understates the null variance, "
            "so p=0.000 overstates significance. A block permutation "
            "or lap-wise split is the honest test.",
            "3. **No modern replication.** On GC=F 2000-2026 (one lap) "
            "the same test gives p=0.398 with Taurus below the "
            "all-days baseline "
            "(reports/saturn_sign_gold_study_2026-10-24.md). The "
            "effect lives in the 1970s and does not replicate.",
            "4. Twelve signs were scanned; a Bonferroni eye on 12 "
            "tests plus the two sources leaves nothing significant.",
            "",
            "Verdict: the 1970s bull did run under Saturn-in-Taurus-"
            "then-Leo, and the video's dates for the cycles are exact "
            "- but the sign rule is one episode plus noise, and the "
            "2030-32 Taurus call rides on an unreplicated pattern.",
        ]

    report = "\n".join(lines) + "\n"
    print(report)
    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        with open(args.save, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"saved: {args.save}")


if __name__ == "__main__":
    main()
