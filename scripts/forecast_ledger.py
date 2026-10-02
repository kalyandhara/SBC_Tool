#!/usr/bin/env python3
"""Intraday forecast ledger CLI (run_app.py also does freeze/score automatically).

  python scripts/forecast_ledger.py freeze [YYYY-MM-DD]     # default: today (IST)
  python scripts/forecast_ledger.py score                   # score settled, unscored days
  python scripts/forecast_ledger.py backfill 2026-08-10 2026-09-30
  python scripts/forecast_ledger.py summary [--days 60]

Backfilled days are a back-test and are reported separately from forecasts
frozen on the day. yfinance keeps only ~60 days of 5-minute bars, so older
backfills cannot be scored.
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402,F401  (build_response for the SBC component)
from sbc import forecast_ledger as ledger  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("date", nargs="?")
    sub.add_parser("score")
    b = sub.add_parser("backfill")
    b.add_argument("first")
    b.add_argument("last")
    s = sub.add_parser("summary")
    s.add_argument("--days", type=int, default=60)
    args = ap.parse_args()

    if args.cmd == "freeze":
        day = dt.date.fromisoformat(args.date) if args.date else ledger._now_ist().date()
        row = ledger.freeze(day)
        print(f"{row['date']}: {row['kind']} (frozen {row['frozen_at']}, model {row['model_version']})")
    elif args.cmd == "score":
        print("scored:", ledger.score_pending() or "nothing pending")
    elif args.cmd == "backfill":
        d, last = dt.date.fromisoformat(args.first), dt.date.fromisoformat(args.last)
        while d <= last:
            if d.weekday() < 5:
                row = ledger.freeze(d, backfill=True)
                m = ledger.score_day(d)
                print(f"{d}: {row['kind']}", f"hit {m['hit_rate']} vs base {m['baseline']}" if m else "no bars")
            d += dt.timedelta(days=1)
    elif args.cmd == "summary":
        print(json.dumps(ledger.summary(args.days)["groups"], indent=2))


if __name__ == "__main__":
    main()
