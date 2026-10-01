"""Prefetch historical OHLC data for all study assets into data/*.csv.

Downloads full history (2000-01-01 to today) for NIFTY, Gold and Silver
into the local CSV caches used by sbc.market_data, then prints a
summary.  Run periodically to refresh the tails.
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc.market_data import _ASSETS, get_ohlc  # noqa: E402


def main():
    today = datetime.date.today().isoformat()
    failed = False
    for asset in sorted(_ASSETS):
        try:
            rows = get_ohlc(asset, "2000-01-01", today)
        except Exception as exc:
            print(f"{asset}: FAILED ({exc})")
            failed = True
            continue
        if not rows:
            print(f"{asset}: no data")
            failed = True
            continue
        print(f"{asset}: {len(rows)} rows "
              f"({rows[0]['time']} .. {rows[-1]['time']})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
