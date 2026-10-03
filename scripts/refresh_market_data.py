"""Refresh data/market.db: NIFTY, SENSEX, India VIX daily bars and NSE FII/DII flows.

  python scripts/refresh_market_data.py            # tail refresh (daily use)
  python scripts/refresh_market_data.py --full     # re-download full history

run_app.py does the tail refresh after each close; this script is for the
first backfill and for Windows Task Scheduler if the app isn't running.
Exit code 1 if anything failed or a series is still stale.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc import market_store  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--full", action="store_true", help="re-download full history")
    args = parser.parse_args()

    report = market_store.refresh_all(full=args.full)
    fresh = market_store.freshness()
    print(json.dumps({"refresh": report, "freshness": fresh}, indent=2))
    return 1 if report["errors"] or fresh["stale"] else 0


if __name__ == "__main__":
    sys.exit(main())
