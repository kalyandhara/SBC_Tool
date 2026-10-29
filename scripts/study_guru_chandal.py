"""Study: Guru-Chandal (Jupiter co-present with Rahu/Ketu) vs NIFTY.

The crash tool carries `guru_chandal` as a Trigger combo at weight 0.14,
defined as sign co-presence (sbc/crash_windows.py: Jupiter in the same
sign as Rahu or Ketu), and the AstroZ videos lean on it ("when Jupiter
is afflicted...").  This study enumerates every Jupiter-Rahu and
Jupiter-Ketu co-presence window 1990-2026 (same_sign_periods - the
crash tool's own definition), adds the exact-crossing moments
(conjunction_events, ~1 s precision), and runs the repo's
forward-return event study on NIFTY.

Example:
    python scripts/study_guru_chandal.py
"""

import argparse
import datetime
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from sbc.transits import conjunction_events, same_sign_periods  # noqa: E402
from scripts.study_mars_node_conjunction import (  # noqa: E402
    bootstrap,
    load_series,
)

WINDOWS = (5, 10, 21)


def stay_returns(rows, stays):
    """First-open -> last-close return per co-presence window."""
    out = []
    for w in stays:
        i0 = next((i for i, r in enumerate(rows)
                   if r["time"] >= w["start"]), None)
        if i0 is None:
            continue
        i1 = i0
        for i, r in enumerate(rows):
            if r["time"] > w["end"]:
                break
            i1 = i
        if i1 <= i0:
            continue
        fwd = ((rows[i1 + 21]["close"] / rows[i1]["close"] - 1.0) * 100.0
               if i1 + 21 < len(rows) else None)
        out.append({"start": w["start"], "end": w["end"],
                    "ret": (rows[i1]["close"] / rows[i0]["open"] - 1.0)
                    * 100.0, "fwd21": fwd})
    return out


def pair_section(rows, pair, start, end, lines):
    stays = same_sign_periods(pair[0], pair[1], start, end)
    crossings = [e for e in conjunction_events(pair[0], pair[1], start,
                                               end, step_hours=24)
                 if e["kind"] == "conjunction"]
    label = f"{pair[0]}-{pair[1]}"
    lines.append(f"\n## {label}: {len(stays)} co-presence windows, "
                 f"{len(crossings)} exact crossings\n")
    lines.append("| window | NIFTY stay % | forward +21d % |")
    lines.append("|--------|--------------|----------------|")
    scored = stay_returns(rows, stays)
    for s in scored:
        fwd = f"{s['fwd21']:+.2f}" if s["fwd21"] is not None else "n/a"
        lines.append(f"| {s['start']} .. {s['end']} | {s['ret']:+.2f} "
                     f"| {fwd} |")
    if len(scored) >= 5:
        obs = float(np.mean([s["ret"] for s in scored]))
        lens = []
        for s in scored:
            i0 = next(i for i, r in enumerate(rows)
                      if r["time"] >= s["start"])
            i1 = i0
            for i, r in enumerate(rows):
                if r["time"] > s["end"]:
                    break
                i1 = i
            lens.append(i1 - i0 + 1)
        boot = bootstrap(rows, lens, obs)
        lines.append(f"\nmean {obs:+.2f}% | win "
                     f"{float(np.mean([s['ret'] > 0 for s in scored])) * 100:.0f}%"
                     f" | random {boot['random_mean']:+.2f}% "
                     f"| p {boot['p_two_sided']:.3f}")
    else:
        lines.append(f"\nonly {len(scored)} scored windows - too few "
                     "for statistics; read as a research prompt, not a "
                     "signal.")
    if crossings:
        lines.append("\nExact crossings (IST): "
                     + ", ".join(e["ist_date"] for e in crossings))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", default="1990-01-01")
    parser.add_argument("--end", default=datetime.date.today().isoformat())
    parser.add_argument("--save", default=os.path.join(
        "reports", "guru_chandal_study_2026-10-25.md"))
    args = parser.parse_args()

    rows = load_series("nifty", datetime.date.fromisoformat(args.start),
                       datetime.date.fromisoformat(args.end))
    lines = ["# Guru-Chandal (Jupiter with Rahu/Ketu) vs NIFTY",
             "",
             f"Range {args.start} .. {args.end}; sign co-presence windows "
             "via same_sign_periods (the crash tool's guru_chandal "
             "definition, weight 0.14); entry = first open on/after the "
             "window start; forward = +21 sessions after the window ends."]

    for pair in (("Jupiter", "Rahu"), ("Jupiter", "Ketu")):
        pair_section(rows, pair, datetime.date.fromisoformat(args.start),
                     datetime.date.fromisoformat(args.end), lines)

    lines += [
        "",
        "Crash-tool cross-reference: guru_chandal fires on sign "
        "co-presence (not degree orb) with weight 0.14 as a Trigger; "
        "this study grades that definition directly. The 2023-05 "
        "window (Jupiter + Rahu in Ashwini) was NIFTY +6.9% - the "
        "live counter-example from the 2026-10-22 video review.",
        "Caveat: Jupiter reaches a node every ~7.3 years, so n stays "
        "tiny on a 2007+ price history; no significance claim is "
        "possible. Event studies are research prompts, not validated "
        "signals.",
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
