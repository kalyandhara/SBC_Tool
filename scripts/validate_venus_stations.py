"""Validate Venus stations and the Sun-Venus conjunction against NIFTY swing lows (B-70).

  python scripts/validate_venus_stations.py            # writes docs/research/venus_station_validation_<date>.md + .json
  python scripts/validate_venus_stations.py --perm 200
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc import venus_station_validation as vv  # noqa: E402
from scripts.validate_rules import write  # noqa: E402


def _f(x, d=3):
    return "–" if x is None else f"{x:.{d}f}"


def render(report: dict) -> str:
    s = report["sample"]
    lines = [
        "# Venus stations and the Sun-Venus conjunction against NIFTY swing lows (B-70)", "",
        f"Generated {report['generated']} by `scripts/validate_venus_stations.py`. "
        f"Hypotheses, pivot definition, window and pass rule were registered before this run: `{report['preregistration']}`.", "",
        f"Sample: {s['first']} to {s['last']}, {s['sessions']} NIFTY sessions. "
        f"Permutations per test: {report['n_permutations']}, seed {report['seed']}.", "",
        f"Events in the sample: {report['event_counts']['venus_stations']} Venus stations, "
        f"{report['event_counts']['inferior_conjunctions']} Sun-Venus conjunctions.", "",
        "## Results", "",
        "Pass = BH q < 0.05 across the two tests, and in each era the hit rate beats its shift null "
        "(lift > 0, one-sided p < 0.05). Under 20 events is reported as underpowered.", "",
        "| Hypothesis | n | hits | hit rate | null mean | lift | p | q | 2007-2020 lift (p) | 2021-2026 lift (p) | verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in report["results"]:
        e1, e2 = r["eras"]["2007-2020"], r["eras"]["2021-2026"]
        lines.append(
            f"| `{r['name']}` | {r['n']} | {r['hits']} | {_f(r['rate'])} | {_f(r['null_mean'])} | "
            f"{_f(r['lift'])} | {_f(r['p'])} | {_f(r['q'])} | {_f(e1['lift'])} ({_f(e1['p'])}) | "
            f"{_f(e2['lift'])} ({_f(e2['p'])}) | **{r['verdict']}** |")
    d = report["deck_claims"]
    lines += ["", "## Deck claims (reported, not graded)", ""]
    if d["total"]:
        lines += [
            f"- Retrograde windows (R to D, store-derived): {d['total']}. "
            f"Windows with a swing low inside: {d['with_pivot']} of {d['total']} (deck: 8 of 10).",
            f"- Median high-to-low close range inside a window: {_f(d['median_range_pct'], 1)}% over a median "
            f"{d['median_sessions']} sessions. Median range over rolling windows of that length: "
            f"{_f(d['normal_median_range_pct'], 1)}% (deck: 7–12% against about 5%).",
        ]
    lines += ["", "## Forward returns from each event (mean %, descriptive)", ""]
    for name, fr in report["forward_returns_pct"].items():
        lines.append(f"- `{name}`: 1 session {_f(fr['1'], 2)}, 5 sessions {_f(fr['5'], 2)}, 20 sessions {_f(fr['20'], 2)}")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--perm", type=int, default=1000)
    args = parser.parse_args()
    t0 = time.perf_counter()
    report = vv.run(n_perm=args.perm)
    write(report, "venus_station_validation", render(report))
    print(f"wrote docs/research/venus_station_validation_*.md/.json in {time.perf_counter() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
