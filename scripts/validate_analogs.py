"""Walk-forward test of the analog engine on NIFTY (sbc.analog_validation).

  python scripts/validate_analogs.py               # writes docs/research/analog_validation_<date>.md + .json
  python scripts/validate_analogs.py --perm 200    # faster, coarser p-values
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc import analog_validation as av  # noqa: E402
from scripts.validate_rules import render, write  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--perm", type=int, default=1000, help="permutations per test")
    parser.add_argument("--start", default=av.START)
    args = parser.parse_args()

    t0 = time.perf_counter()
    report = av.run(n_perm=args.perm, start=args.start)
    best = report["best_similarity"]["analog_overall"]["5"]
    intro = [
        "Each session is forecast from analogs whose outcome was complete by the previous "
        f"close (no lookahead). The engine takes the top {report['k']} analogs (at least "
        f"{av.an.MIN_SPACING} sessions apart) and leans the way their average outcome beat "
        "the drift of all eligible sessions. `analog_random` is the control.",
        f"Best overall similarity found per session: median {best['median_best']:.0%}, "
        f"max {best['max_best']:.0%}. Whole-sky 90% matches don't occur in this history.",
    ]
    write(report, "analog_validation",
          render(report, "Analog engine walk-forward", "scripts/validate_analogs.py", intro))
    print(f"wrote docs/research/analog_validation_*.md/.json in {time.perf_counter() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
