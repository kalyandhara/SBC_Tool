"""Validate the bullion KP sub-lord rules (sbc.bullion_sublord_validation, B-57).

  python scripts/fetch_dukascopy.py             # first, on a machine that can reach Dukascopy
  python scripts/validate_bullion_sublords.py   # writes docs/research/bullion_sublord_validation_<date>.md + .json
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc import bullion_sublord_validation as bv  # noqa: E402
from scripts.validate_rules import write  # noqa: E402


def render(r: dict) -> str:
    f = lambda x, d=4: "–" if x is None or x != x else f"{x:.{d}f}"  # noqa: E731
    lines = ["# Bullion KP sub-lord rules (B-57)", "",
             f"Generated {r['generated']} by `scripts/validate_bullion_sublords.py`. Registered before any intraday "
             f"data existed: {', '.join(f'`{p}`' for p in r['preregistration'])}.", "",
             f"Sample {r['sample'][0]} to {r['sample'][1]} (IST), Dukascopy hourly spot, MCX session window. "
             f"{r['n_permutations']} whole-session permutations per test.", ""]
    for m, info in r["metals"].items():
        d = info.get("data") or {}
        lines.append(f"- **{m}**: {info['sessions']} sessions, {info['bars']} bars, {info['total_segments']} segments; "
                     f"halves split at {info['split']}; data {d.get('first')} to {d.get('last')}, "
                     f"months without data: {', '.join(d.get('months_without_data') or []) or 'none'}.")
    lines += ["", "Effects are per-hour log returns (up/down) or absolute per-hour log returns (volatile/stable), "
              "relative to the all-segment mean and signed so the sheet's claim is positive.", "",
              "Pass = q < 0.05 (BH across 8) **and** the claimed sign in both halves **and** controlled q < 0.05.", "",
              "| Metal | Group | Lords | Segments | Effect | p | q | 1st half | 2nd half | Controlled q | Verdict |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for x in r["results"]:
        lines.append(f"| {x['metal']} | {x['group']} | {', '.join(x['lords'])} | {x['segments']} | {f(x['effect'], 6)} | "
                     f"{f(x['p'])} | {f(x['q'])} | {f(x['first_half'], 6)} | {f(x['second_half'], 6)} | "
                     f"{f(x['controlled_q'])} | {'**PASS**' if x['verdict'] == 'PASS' else x['verdict']} |")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--perm", type=int, default=bv.N_PERM)
    a = p.parse_args()
    t0 = time.perf_counter()
    report = bv.run(n_perm=a.perm)
    write(report, "bullion_sublord_validation", render(report))
    print(f"wrote docs/research/bullion_sublord_validation_*.md/.json in {time.perf_counter() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
