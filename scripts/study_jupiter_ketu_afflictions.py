"""Study: the video rule "Jupiter afflicted in a Ketu nakshatra -> crash".

The AstroZ crash video (2026-10-22) claims Dow/NIFTY falls cluster while
Jupiter transits a Ketu-ruled nakshatra (Ashwini/Magha/Mula) AND is
afflicted.  This study turns that into a falsifiable rule and publishes
the hit AND miss table:

1. Every Jupiter stay in a Ketu nakshatra 1990-2035 (nakshatra_periods).
2. Affliction sub-windows inside each stay, day-grain at 09:15 IST:
   Ju-Sat mutual 6/8 (Shashtashtaka), Ju-node conj <= 10 deg,
   Ju-Mars conj <= 10 deg, combustion (Ju-Sun <= 11 deg).
3. Event study on NIFTY: stay return and afflicted-window return
   (first open -> last close) plus forward +21 sessions, bootstrapped
   against random same-length windows (repo convention).
4. False-negative ledger: every NIFTY drawdown >= 15% (close basis) and
   whether a stay / affliction was active at the peak (or within
   +/-15 sessions of it).

Example:
    python scripts/study_jupiter_ketu_afflictions.py
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
from sbc.transits import nakshatra_periods  # noqa: E402
from scripts.study_mars_node_conjunction import (  # noqa: E402
    bootstrap,
    load_series,
)
from scripts.study_node_jupiter_events import KETU_NAKSHATRAS  # noqa: E402

JUPITER_COMBUST_ORB = 11.0
CONJ_ORB_DEG = 10.0
DD_THRESHOLD_PCT = -15.0
PEAK_WINDOW_SESSIONS = 15


def sep_deg(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def affliction_flags(date_str):
    """Affliction flags for Jupiter at 09:15 IST on a calendar date."""
    planets, _ay, _sun, _moon, _tithi = positioned_planets(date_str)
    p = {x["name"]: x for x in planets}
    ju = p["Jupiter"]["longitude"]
    sat_68 = (p["Jupiter"]["sign_index"] - p["Saturn"]["sign_index"]) % 12
    return {
        "ju_nak": p["Jupiter"]["nakshatra"],
        "sat_68": sat_68 in (5, 7),
        "sat_same": sat_68 == 0,
        "node_10": (sep_deg(ju, p["Rahu"]["longitude"]) <= CONJ_ORB_DEG
                    or sep_deg(ju, p["Ketu"]["longitude"]) <= CONJ_ORB_DEG),
        "mars_10": sep_deg(ju, p["Mars"]["longitude"]) <= CONJ_ORB_DEG,
        "combust": sep_deg(ju, p["Sun"]["longitude"]) <= JUPITER_COMBUST_ORB,
    }


def flag_str(flags):
    marks = []
    for key, label in (("sat_68", "6/8Sat"), ("sat_same", "Sat"),
                       ("node_10", "Node"), ("mars_10", "Mars"),
                       ("combust", "Comb")):
        if flags[key]:
            marks.append(label)
    return "+".join(marks) if marks else "-"


def afflicted_sub_windows(start_str, end_str):
    """Contiguous day runs inside a stay where any affliction holds."""
    start = datetime.date.fromisoformat(start_str)
    end = datetime.date.fromisoformat(end_str)
    windows = []
    run_start = None
    d = start
    while d <= end:
        flags = affliction_flags(d.isoformat())
        if any(flags[k] for k in ("sat_68", "sat_same", "node_10",
                                  "mars_10", "combust")):
            if run_start is None:
                run_start = d
            last = d
        else:
            if run_start is not None:
                windows.append((run_start, last))
                run_start = None
        d += datetime.timedelta(days=1)
    if run_start is not None:
        windows.append((run_start, last))
    return [{"start": a.isoformat(), "end": b.isoformat(),
             "days": (b - a).days + 1}
            for a, b in windows]


def stay_window_return(rows, start_str, end_str):
    """(first-open -> last-close) % inside [start, end], or None."""
    i0 = next((i for i, r in enumerate(rows) if r["time"] >= start_str),
              None)
    if i0 is None:
        return None
    i1 = i0
    for i, r in enumerate(rows):
        if r["time"] > end_str:
            break
        i1 = i
    if i1 <= i0:
        return None
    return (rows[i1]["close"] / rows[i0]["open"] - 1.0) * 100.0


def window_study(rows, windows, label, lines):
    """Repo-convention event study over {start, end} windows."""
    scored = []
    for w in windows:
        ret = stay_window_return(rows, w["start"], w["end"])
        if ret is not None:
            scored.append((w, ret))
    if len(scored) < 5:
        lines.append(f"\n## {label}: {len(scored)} scored windows "
                     "(too few for statistics)\n")
        return
    lens = []
    for w, _ret in scored:
        i0 = next(i for i, r in enumerate(rows) if r["time"] >= w["start"])
        i1 = i0
        for i, r in enumerate(rows):
            if r["time"] > w["end"]:
                break
            i1 = i
        lens.append(i1 - i0 + 1)
    obs = float(np.mean([r for _w, r in scored]))
    boot = bootstrap(rows, lens, obs)
    lines.append(f"\n## {label}\n")
    lines.append("| start | end | days | NIFTY % |")
    lines.append("|-------|-----|------|---------|")
    for w, ret in scored:
        lines.append(f"| {w['start']} | {w['end']} | {w['days']} "
                     f"| {ret:+.2f} |")
    lines.append(f"\nmean {obs:+.2f}% | win "
                 f"{float(np.mean([r > 0 for _w, r in scored])) * 100:.0f}% "
                 f"| random {boot['random_mean']:+.2f}% "
                 f"| p {boot['p_two_sided']:.3f}")


def drawdown_episodes(rows, threshold):
    """(peak_row, trough_row, depth%) for every close-basis drawdown."""
    episodes = []
    peak, peak_i = rows[0]["close"], 0
    trough, trough_i = peak, 0
    in_dd = False
    for i, r in enumerate(rows):
        c = r["close"]
        if c >= peak:
            if in_dd and (trough / peak - 1.0) * 100.0 <= threshold:
                episodes.append((rows[peak_i], rows[trough_i],
                                 (trough / peak - 1.0) * 100.0))
            peak, peak_i = c, i
            trough, trough_i = c, i
            in_dd = False
        else:
            if c < trough:
                trough, trough_i = c, i
            in_dd = True
    if in_dd and (trough / peak - 1.0) * 100.0 <= threshold:
        episodes.append((rows[peak_i], rows[trough_i],
                         (trough / peak - 1.0) * 100.0))
    return episodes


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", type=datetime.date.fromisoformat,
                        default="1990-01-01")
    parser.add_argument("--end", type=datetime.date.fromisoformat,
                        default="2035-12-31")
    parser.add_argument("--save", default=os.path.join(
        "reports", "jupiter_ketu_affliction_study_2026-10-23.md"))
    args = parser.parse_args()

    lines = ["# Jupiter afflicted in a Ketu nakshatra: hit/miss study",
             "",
             f"Range {args.start} .. {args.end}; Lahiri, mean node, "
             "09:15 IST flags; NIFTY close-basis; entry = first open "
             "on/after window start (repo convention)."]

    stays = [p for p in nakshatra_periods("Jupiter", args.start, args.end)
             if p["nakshatra"] in KETU_NAKSHATRAS and p["days"] >= 20.0]

    rows = load_series("nifty", args.start, args.end)
    have_data = len(rows) >= 100

    # Per-stay table with affliction flags and NIFTY return.
    lines.append(f"\n## All {len(stays)} Ketu-nakshatra stays "
                 "(hits AND misses)\n")
    lines.append("| start | end | nakshatra | afflictions | NIFTY stay % |")
    lines.append("|-------|-----|-----------|-------------|--------------|")
    afflicted_windows = []
    for s in stays:
        flags = affliction_flags(s["start"])
        fstr = flag_str(flags)
        ret_v = (stay_window_return(rows, s["start"], s["end"])
                 if have_data else None)
        ret = f"{ret_v:+.1f}" if ret_v is not None else "n/a"
        lines.append(f"| {s['start']} | {s['end']} | {s['nakshatra']} "
                     f"| {fstr} | {ret} |")
        subs = afflicted_sub_windows(s["start"], s["end"])
        for w in subs:
            w["nakshatra"] = s["nakshatra"]
        afflicted_windows.extend(w for w in subs if w["days"] >= 10)

    if have_data:
        window_study(rows, [dict(s) for s in stays],
                     "Whole Ketu-nakshatra stays (the video's sample)",
                     lines)
        window_study(rows, afflicted_windows,
                     "Afflicted sub-windows (the video's actual rule: "
                     "6/8 or same-sign Saturn, node <=10 deg, Mars "
                     "<=10 deg, combust <=11 deg)", lines)

        # False-negative ledger.
        lines.append(f"\n## False-negative ledger: NIFTY drawdowns "
                     f">= {abs(DD_THRESHOLD_PCT):.0f}% close-basis\n")
        lines.append("| peak | trough | depth % | stay at peak | "
                     "affliction at peak (+/-15 sessions) |")
        lines.append("|------|--------|---------|--------------|"
                     "--------------------------------------|")
        episodes = drawdown_episodes(rows, DD_THRESHOLD_PCT)
        covered = 0
        for peak_row, trough_row, depth in episodes:
            peak_d = peak_row["time"]
            pi = rows.index(peak_row)
            near = rows[max(0, pi - PEAK_WINDOW_SESSIONS):
                        min(len(rows), pi + PEAK_WINDOW_SESSIONS + 1)]
            stay_here = [s for s in stays
                         if s["start"] <= peak_d <= s["end"]]
            aff_here = []
            for r in near:
                flags = affliction_flags(r["time"])
                if any(flags[k] for k in ("sat_68", "sat_same", "node_10",
                                          "mars_10", "combust")):
                    aff_here.append(flag_str(flags))
            covered += bool(stay_here or aff_here)
            lines.append(
                f"| {peak_d} | {trough_row['time']} | {depth:+.1f} | "
                f"{', '.join(s['nakshatra'] for s in stay_here) or '-'} | "
                f"{', '.join(aff_here[:3]) or '-'} |")
        lines.append(f"\n{covered}/{len(episodes)} drawdowns had a "
                     "Ketu-nakshatra stay or affliction at/near the peak.")

    report = "\n".join(lines) + "\n"
    print(report)
    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        with open(args.save, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"saved: {args.save}")


if __name__ == "__main__":
    main()
