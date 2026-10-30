"""Validate the transit-to-natal model (sbc.natal_validation).

  python scripts/validate_natal.py               # writes docs/research/natal_validation_<date>.md + .json
  python scripts/validate_natal.py --perm 200 --sets 200
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc import natal_validation as nv  # noqa: E402
from scripts.validate_rules import write  # noqa: E402
from scripts.validate_swing import render_report  # noqa: E402

PREREG = "docs/research/natal_transit_preregistration_2026-10-10.md"
INTRO = [
    "Transiting planets (Sun, Mercury, Venus, Mars, Jupiter, Saturn, Rahu) aspecting the natal chart of "
    "NIFTY (1995-11-03 00:00 IST, geocentric sidereal Lahiri; eight aspects, orb ±2°) as trend-reversal "
    f"zones. Hypotheses and pass rule were registered before this run: `{PREREG}`. Part A grades the "
    "*timing*: does NIFTY reverse its 10-session trend, or move more, on sessions inside a window? "
    "Part B grades the full swing model on these windows. `lecture5` is the five aspects the lecture names.",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--perm", type=int, default=1000)
    parser.add_argument("--sets", type=int, default=nv.sv.RANDOM_SETS)
    args = parser.parse_args()
    t0 = time.perf_counter()
    report = nv.run(n_perm=args.perm, n_sets=args.sets)
    text = render_report(report, title="Transit-to-natal model (B-53) — entry timing",
                         generator="scripts/validate_natal.py", intro=INTRO)
    write(report, "natal_validation", text)
    print(f"wrote docs/research/natal_validation_*.md/.json in {time.perf_counter() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
