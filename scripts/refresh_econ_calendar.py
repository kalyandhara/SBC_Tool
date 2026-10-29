"""Refresh data/econ_events.json from the BLS and BEA iCalendar feeds (B-59).

Run on a machine that can reach bls.gov and bea.gov (the user's PC):

    python scripts/refresh_econ_calendar.py

Keeps rows marked "source": "manual" (add Census retail sales there by hand). A feed
that fails is reported and its previous rows are kept, so one outage can't empty the file.
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc import econ_calendar as ec  # noqa: E402
from sbc.bullion_week import ECON_FILE  # noqa: E402


def main() -> int:
    try:
        existing = json.loads(ECON_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        existing = []
    fetched, failed = [], []
    for source, url in ec.FEEDS.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SBC-Tool research)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                rows = ec.parse_ics(r.read().decode("utf-8", "replace"), source)
            print(f"{source}: {len(rows)} watched releases")
            fetched += rows
        except Exception as exc:  # noqa: BLE001 - report and keep the old rows for this feed
            print(f"{source}: failed ({exc}); keeping previous rows")
            failed.append(source)
            fetched += [r for r in existing if r.get("source") == source]
    static = ec.static_rows()
    print(f"static: {len(static)} rows (FOMC decisions, US midterms)")
    fetched += static
    rows = ec.merge(existing, fetched)
    ECON_FILE.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"wrote {len(rows)} rows to {ECON_FILE}")
    return 1 if len(failed) == len(ec.FEEDS) else 0


if __name__ == "__main__":
    sys.exit(main())
