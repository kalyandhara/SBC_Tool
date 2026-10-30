"""Validate transit events against NIFTY (sbc.transit_event_validation, B-58).

  python scripts/validate_transit_events.py            # writes docs/research/transit_event_validation_<date>.md + .json
  python scripts/validate_transit_events.py --perm 200
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc import transit_event_validation as tv  # noqa: E402
from scripts.validate_rules import write  # noqa: E402


def _f(x, d=3):
    return "–" if x is None or x != x else f"{x:.{d}f}"


def render(report: dict) -> str:
    s = report["sample"]
    lines = [
        "# Transit events and NIFTY (B-58)", "",
        f"Generated {report['generated']} by `scripts/validate_transit_events.py`. "
        f"Hypotheses, windows and pass rule were registered before this run: `{report['preregistration']}`.", "",
        f"Sample: {s['first']} to {s['last']}, {s['sessions']} NIFTY sessions. "
        f"Permutations per test: {report['n_permutations']}. Horizons: {', '.join(map(str, report['horizons']))} sessions.", "",
        "Events in the sample (sidereal Lahiri): " + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in report["event_counts"].items()) + ".", "",
        "Share of sessions each signal is active: " + ", ".join(f"`{k}` {v:.0%}" for k, v in report["signal_share"].items()) + ".", "",
        "## Results", "",
        "Pass = q < 0.05 (BH across all 15 tests) with the same direction in both eras, **and** the incremental test "
        "against the market controls q < 0.05.", "",
        "| Hypothesis | h | n | effect | p | q | eras | beyond market (q) | verdict |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(report["results"], key=lambda r: (r["rule"], r["horizon"])):
        b = r.get("beyond_market") or {}
        eras = ", ".join(f"{k}: {_f(v, 4)}" for k, v in (r.get("eras") or {}).items())
        effect = r.get("excess", r.get("effect", r.get("stat")))
        passes = r.get("verdict", "").startswith("edge") or r.get("verdict") == "pass"
        both = passes and b.get("verdict") == "adds information"
        lines.append(f"| `{r['rule']}` | {r['horizon']} | {r.get('n', '–')} | {_f(effect, 5)} | {_f(r.get('p'))} | "
                     f"{_f(r.get('q'))} | {eras} | {b.get('verdict', '–')} ({_f(b.get('q'))}) | "
                     f"{'**PASS**' if both else r.get('verdict', '–')} |")
    lines += ["", "## Control (no astro)", ""]
    for r in report["control"]:
        lines.append(f"- `{r['rule']}` h={r['horizon']}: p {_f(r.get('p'))}, verdict {r.get('verdict', '–')}")
    lines += ["", f"Sessions inside at least one window: {report['window_share']:.0%}.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--perm", type=int, default=1000)
    args = parser.parse_args()
    t0 = time.perf_counter()
    report = tv.run(n_perm=args.perm)
    write(report, "transit_event_validation", render(report))
    print(f"wrote docs/research/transit_event_validation_*.md/.json in {time.perf_counter() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
