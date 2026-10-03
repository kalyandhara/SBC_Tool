"""Grade the Phase 6 candidate factors on NIFTY (sbc.factor_validation).

  python scripts/validate_factors.py              # writes docs/research/factor_validation_<date>.md + .json
  python scripts/validate_factors.py --perm 200
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc import factor_validation as fv  # noqa: E402
from scripts.validate_rules import _bps, _num, render, write  # noqa: E402

INTRO = [
    "Candidate factors from the gap analysis (G8), each with its direction written down in "
    "`sbc/factors.py` before this test was first run. They are a separate BH family from the "
    "Phase 2 rules.",
    "A factor counts in the forecast only if it shows an **edge** here *and* **adds "
    "information** beyond the market controls (last table). Event factors are tested on |return| "
    "after the controls, so they must beat VIX and recent volatility at predicting big moves.",
]


def render_report(report: dict) -> str:
    text = render(report, title="Phase 6 factor validation",
                  generator="scripts/validate_factors.py", intro=INTRO)
    lines = ["## Beyond the market controls", "",
             f"Controls: {', '.join(f'`{c}`' for c in report['controls'])}. "
             "beta = effect per unit of signal after the controls (bps of return for directional "
             "factors, bps of |return| for event factors); q = BH across this table.", "",
             "| factor | kind | h | signal days | beta bps | beta raw bps | p | q | beyond market |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(report["results"], key=lambda r: (r["rule"], r["horizon"])):
        b = r["beyond_market"]
        lines.append(f"| {r['rule']} | {r['kind']} | {r['horizon']} | {r['signal_days']} | {_bps(b['beta'])} | "
                     f"{_bps(b['beta_raw'])} | {_num(b['p'])} | {_num(b['q'])} | **{b['verdict']}** |")
    admitted = [f"{r['rule']} ({r['horizon']}d)" for r in report["results"]
                if r["verdict"] == "edge" and r["beyond_market"]["verdict"] == "adds information"]
    lines += ["", f"**Admitted to the forecast:** {', '.join(admitted) if admitted else 'none'}.", ""]
    return text + "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--perm", type=int, default=1000, help="permutations per test")
    args = parser.parse_args()
    t0 = time.perf_counter()
    report = fv.run(n_perm=args.perm)
    write(report, "factor_validation", render_report(report))
    print(f"wrote docs/research/factor_validation_*.md/.json in {time.perf_counter() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
