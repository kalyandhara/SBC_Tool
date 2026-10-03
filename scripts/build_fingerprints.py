"""Build data/fingerprints.db: the astro fingerprint of every day (default 1990-2035).

  python scripts/build_fingerprints.py                     # missing/stale days only
  python scripts/build_fingerprints.py 2020-01-01 2026-12-31
  python scripts/build_fingerprints.py --purge             # drop rows from old code versions

Only days without a current-version row are computed, so re-running is cheap
and an edit to the astro code triggers a full rebuild automatically.
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc import fingerprint_store as store  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("start", nargs="?", default=store.DEFAULT_RANGE[0])
    parser.add_argument("end", nargs="?", default=store.DEFAULT_RANGE[1])
    parser.add_argument("--purge", action="store_true", help="delete rows from other code versions")
    args = parser.parse_args()

    if args.purge:
        print(f"purged {store.purge_stale()} stale rows")
    t0 = time.perf_counter()

    def progress(done, total):
        print(f"\r{done}/{total} days", end="", flush=True)

    report = store.build(args.start, args.end, progress=progress)
    print(f"\n{json.dumps(report)} in {time.perf_counter() - t0:.1f}s")
    print(json.dumps(store.status()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
