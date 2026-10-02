#!/usr/bin/env python3
"""Generate data/kp/KP_Data_<Mon><YYYY>.csv from Swiss Ephemeris.

Usage (from the repo root):
  python scripts/generate_kp_data.py 2026-10              # one month
  python scripts/generate_kp_data.py 2026-08 2026-12      # inclusive range
  python scripts/generate_kp_data.py 2026-10 --step 1     # 1-minute rows

Existing files are replaced only when they fail the KP sanity check (old
random samples) unless --force is given.
"""

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sbc.kp_ephemeris import generate_kp_month, month_file  # noqa: E402
from sbc.kp_intraday import assess_kp_data  # noqa: E402


def _months(first, last):
    y, m = first
    while (y, m) <= last:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def _ym(s):
    y, m = s.split("-")
    return int(y), int(m)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("first", help="YYYY-MM")
    ap.add_argument("last", nargs="?", help="YYYY-MM (inclusive, default = first)")
    ap.add_argument("--step", type=int, default=3, help="minutes between rows (default 3)")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "kp")
    ap.add_argument("--force", action="store_true", help="overwrite files that pass the sanity check")
    args = ap.parse_args()

    first = _ym(args.first)
    last = _ym(args.last) if args.last else first
    for y, m in _months(first, last):
        path = month_file(args.out_dir, y, m)
        if path.exists() and not args.force:
            with open(path, encoding="utf-8") as f:
                if not assess_kp_data(list(csv.DictReader(f)))["synthetic"]:
                    print(f"skip {path.name}: already ephemeris data (use --force)")
                    continue
            print(f"replacing synthetic {path.name}")
        info = generate_kp_month(y, m, path, step_minutes=args.step)
        print(f"wrote {path.name}: {info['days']} days, {info['rows']} rows")


if __name__ == "__main__":
    main()
