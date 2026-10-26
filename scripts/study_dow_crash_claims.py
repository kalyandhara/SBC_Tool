"""Study: grade the AstroZ crash video's Dow claims with real data.

The 2026-10-22 crash video's Dow half (1966, 1973-74, 1979-80, 1987)
predates every free Dow series this repo can fetch - FRED carries only a
10-year DJIA window, WSJ 401s, Stooq is JS-challenge + IP-denied - so:

- 1992-2026: repo Dow (^DJI daily, market_data asset `djia`).
- 1965-1992: DataHub/Shiller S&P 500 monthly closes (cached
  data/sp500_monthly_long.csv, reaches 2026-09) as a documented proxy;
  S&P tracks the Dow within a few points in these episodes.

Sections:
1. The four claimed Dow episodes, depths computed from the proxy.
2. Every >=20% (and 15-20%) drawdown episode 1965-1992 and 1992-2026,
   flagged for Jupiter-in-Ketu-nakshatra stays and afflictions (the
   video's rule) - the Dow-side false-negative ledger (B2's twin).

Example:
    python scripts/study_dow_crash_claims.py
"""

import argparse
import datetime
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from sbc.transits import nakshatra_periods  # noqa: E402
from scripts.study_jupiter_ketu_afflictions import (  # noqa: E402
    affliction_flags,
    flag_str,
)
from scripts.study_mars_node_conjunction import load_series  # noqa: E402

KETU_NAKS = {"Ashwini", "Magha", "Mula"}
SP500_CACHE = os.path.join(_ROOT, "data", "sp500_monthly_long.csv")
FLAG_KEYS = ("sat_68", "sat_same", "node_10", "mars_10", "combust")

# The video's Dow table, as (label, peak window, trough window).
CLAIMED = [
    ("1966 Dow -25%+ (Feb -> Oct 1966)",
     ("1966-01-01", "1966-06-30"), ("1966-07-01", "1966-12-31")),
    ("1973-74 Dow -45%",
     ("1973-01-01", "1973-12-31"), ("1974-01-01", "1974-12-31")),
    ("1979-80 Dow -20%",
     ("1979-10-01", "1980-02-29"), ("1980-03-01", "1980-05-31")),
    ("1987 Dow -23% in a day",
     ("1987-01-01", "1987-09-30"), ("1987-10-01", "1987-12-31")),
]


def sp500_monthly():
    """(times, closes) monthly S&P closes from the cached DataHub file."""
    import csv as _csv

    with open(SP500_CACHE, encoding="utf-8") as fh:
        recs = list(_csv.DictReader(fh))
    times, closes = [], []
    for rec in recs:
        try:
            c = float(rec["SP500"])
        except (KeyError, ValueError):
            continue
        if c <= 0:
            continue
        times.append(rec["Date"])
        closes.append(c)
    return times, closes


def drawdown_episodes(closes, threshold):
    """[(peak_i, trough_i, depth_frac)] for close-basis drawdowns."""
    out = []
    peak, peak_i = closes[0], 0
    trough, trough_i = closes[0], 0
    in_dd = False
    for i, c in enumerate(closes):
        if c >= peak:
            if in_dd and trough / peak - 1.0 <= threshold:
                out.append((peak_i, trough_i, trough / peak - 1.0))
            peak, peak_i = c, i
            trough, trough_i = c, i
            in_dd = False
        else:
            if c < trough:
                trough, trough_i = c, i
            in_dd = True
    if in_dd and trough / peak - 1.0 <= threshold:
        out.append((peak_i, trough_i, trough / peak - 1.0))
    return out


def month_mid(d):
    y, m = int(d[:4]), int(d[5:7])
    return f"{y:04d}-{m:02d}-15"


def month_shift(d, k):
    y, m = int(d[:4]), int(d[5:7])
    m += k
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return f"{y:04d}-{m:02d}-01"


def ketu_cover(times, peak_i, stays):
    """Ketu-nakshatra / affliction status near a monthly episode peak."""
    peak_dt = datetime.date.fromisoformat(month_mid(times[peak_i]))
    lo = (peak_dt - datetime.timedelta(days=90)).isoformat()
    hi = (peak_dt + datetime.timedelta(days=90)).isoformat()
    stay_here = [s for s in stays if s["start"] <= hi and s["end"] >= lo]
    flags = []
    for k in range(-3, 4):
        f = affliction_flags(month_mid(month_shift(times[peak_i], k)))
        if any(f[x] for x in FLAG_KEYS):
            flags.append(flag_str(f))
    return stay_here, flags


def daily_ketu_cover(rows, peak_i, stays):
    """Same check around a daily episode peak (+/-45 days / 15 sessions)."""
    peak_dt = datetime.date.fromisoformat(rows[peak_i]["time"])
    lo = (peak_dt - datetime.timedelta(days=45)).isoformat()
    hi = (peak_dt + datetime.timedelta(days=45)).isoformat()
    stay_here = [s for s in stays if s["start"] <= hi and s["end"] >= lo]
    flags = []
    for r in rows[max(0, peak_i - 15):peak_i + 16]:
        f = affliction_flags(r["time"])
        if any(f[x] for x in FLAG_KEYS):
            flags.append(flag_str(f))
    return stay_here, flags


def ledger_table(lines, header, rows_out, covered, total, strict_n):
    lines.append(header)
    lines.append("| peak | trough | depth % | stay near peak | "
                 "affliction near peak |")
    lines.append("|-------|--------|---------|----------------|------|")
    lines.extend(rows_out)
    lines.append(f"\ncovered (stay OR affliction near peak): "
                 f"{covered}/{total}; strict (Ketu-nakshatra stay active "
                 f"at the peak AND afflicted): {strict_n}/{total}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--save", default=os.path.join(
        "reports", "dow_crash_claims_study_2026-10-25.md"))
    args = parser.parse_args()

    lines = ["# Dow crash-claim grading + Jupiter-Ketu-nakshatra ledger",
             "",
             "Pre-1992 depths on the S&P 500 monthly proxy (Shiller/"
             "DataHub; pre-1992 Dow daily is not reachable from free "
             "sources this repo can use); 1992-2026 on repo ^DJI daily. "
             "Flags: Jupiter in Ashwini/Magha/Mula plus afflictions "
             "(6/8 or same-sign Saturn, node <=10 deg, Mars <=10 deg, "
             "combust <=11 deg) near the peak."]

    times, closes = sp500_monthly()
    sel = [i for i, t in enumerate(times) if "1965-01-01" <= t < "1992-01-01"]
    times = [times[i] for i in sel]
    closes = [closes[i] for i in sel]

    lines.append("\n## 1. The video's four Dow episodes (proxy depths)\n")
    lines.append("| claim | proxy peak | proxy trough | proxy depth |")
    lines.append("|-------|------------|--------------|-------------|")
    for label, (pa, pb), (ta, tb) in CLAIMED:
        pw = [i for i, t in enumerate(times) if pa <= t <= pb]
        tw = [i for i, t in enumerate(times) if ta <= t <= tb]
        peak = max(pw, key=lambda i: closes[i])
        trough = min(tw, key=lambda i: closes[i])
        depth = (closes[trough] / closes[peak] - 1.0) * 100.0
        lines.append(f"| {label} | {times[peak]} ({closes[peak]:.2f}) "
                     f"| {times[trough]} ({closes[trough]:.2f}) "
                     f"| {depth:+.1f}% |")
    lines += [
        "",
        "Proxy notes: 1966 monthly S&P closes give -17.3% (the Dow's "
        "intramonth -26.5% and the S&P's intraday -22% are deeper - "
        "monthly closes understate); 1973-74 ~-43% on monthly closes "
        "matches the Dow's -45%; the 1979-80 close-basis dip "
        "understates the Dow's -16.1% intraday (the video's -20% was "
        "already flagged as inflated); 1987's one-day -22.6% cannot be "
        "seen in monthly closes - the proxy shows the full quarterly "
        "-27%.",
    ]

    stays = [p for p in nakshatra_periods(
        "Jupiter", datetime.date(1965, 1, 1), datetime.date(2026, 12, 31))
        if p["nakshatra"] in KETU_NAKS and p["days"] >= 20.0]

    eps = drawdown_episodes(closes, -0.20)
    near = drawdown_episodes(closes, -0.15)
    rows_out, covered, strict_n = [], 0, 0
    for peak_i, trough_i, depth in eps:
        stay_here, flags = ketu_cover(times, peak_i, stays)
        covered += bool(stay_here or flags)
        stay_at = [s for s in stays
                   if s["start"] <= times[peak_i] <= s["end"]]
        strict_n += bool(stay_at) and bool(flags)
        rows_out.append(
            f"| {times[peak_i]} | {times[trough_i]} | {depth * 100:+.1f} "
            f"| {', '.join(s['nakshatra'] for s in stay_here) or '-'} "
            f"| {', '.join(sorted(set(flags))[:3]) or '-'} |")
    lines.append("\n## 2. Drawdown ledger 1965-1992 (S&P monthly proxy)\n")
    ledger_table(lines, f"{len(eps)} episodes >=20% ({len(near) - len(eps)}"
                 f" more in the 15-20% band):", rows_out, covered, len(eps),
                 strict_n)

    d_rows = load_series("djia", datetime.date(1992, 1, 1),
                         datetime.date.today())
    d_closes = list(np.asarray([r["close"] for r in d_rows]))
    d_eps = drawdown_episodes(d_closes, -0.20)
    rows_out, covered_d, strict_d = [], 0, 0
    for peak_i, trough_i, depth in d_eps:
        stay_here, flags = daily_ketu_cover(d_rows, peak_i, stays)
        covered_d += bool(stay_here or flags)
        stay_at = [s for s in stays if s["start"] <= d_rows[peak_i]["time"]
                   <= s["end"]]
        strict_d += bool(stay_at) and bool(flags)
        rows_out.append(
            f"| {d_rows[peak_i]['time']} | {d_rows[trough_i]['time']} "
            f"| {depth * 100:+.1f} "
            f"| {', '.join(s['nakshatra'] for s in stay_here) or '-'} "
            f"| {', '.join(sorted(set(flags))[:3]) or '-'} |")
    lines.append("\n## 3. Drawdown ledger 1992-2026 (repo Dow daily)\n")
    ledger_table(lines, f"{len(d_eps)} episodes >=20%:", rows_out,
                 covered_d, len(d_eps), strict_d)

    lines.append(
        "\nVerdict: the video's four Dow dates and depths are broadly "
        "right as history, and the 1970s legs did coincide with "
        "Jupiter afflictions - but under its own strict rule "
        "(Ketu-nakshatra stay at the peak AND afflicted) it covers "
        f"only {strict_n}/{len(eps)} pre-1992 episodes and "
        f"{strict_d}/{len(d_eps)} since 1992 (loose: {covered}/{len(eps)}"
        f" and {covered_d}/{len(d_eps)}), against NIFTY's 4/7 "
        "(reports/jupiter_ketu_affliction_study_2026-10-23.md). "
        "Cherry-picked hits, not a screened rule.")

    report = "\n".join(lines) + "\n"
    print(report)
    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        with open(args.save, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"saved: {args.save}")


if __name__ == "__main__":
    main()
