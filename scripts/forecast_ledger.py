#!/usr/bin/env python3
"""Intraday forecast ledger CLI (run_app.py also does freeze/score automatically).

  python scripts/forecast_ledger.py freeze [YYYY-MM-DD]     # default: today (IST)
  python scripts/forecast_ledger.py score                   # score settled, unscored days
  python scripts/forecast_ledger.py backfill 2026-08-10 2026-09-30
  python scripts/forecast_ledger.py summary [--days 60]

External daily series (B-40), kept apart from our own forecasts:
  python scripts/forecast_ledger.py external-freeze data/projections/2026-10_third_party_monthly.csv       --source third_party_monthly --published 2026-10-05
  python scripts/forecast_ledger.py external-score --source third_party_monthly       --month 2026-10 [--symbol NIFTY|BANKNIFTY]

Backfilled days are a back-test and are reported separately from forecasts
frozen on the day. yfinance keeps only ~60 days of 5-minute bars, so older
backfills cannot be scored.
"""

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402,F401  (build_response for the SBC component)
from sbc import forecast_ledger as ledger  # noqa: E402

# Daily closes for external-score: NIFTY from data/market.db, BANKNIFTY from yfinance.
EXTERNAL_SYMBOLS = {"NIFTY": None, "BANKNIFTY": "^NSEBANK"}


def _closes(symbol: str, first: str, last: str) -> dict[str, float]:
    """Closes from ~10 days before `first` (for the first return) through the day after `last`."""
    from sbc import market_store
    lo = (dt.date.fromisoformat(first) - dt.timedelta(days=10))
    hi = (dt.date.fromisoformat(last) + dt.timedelta(days=5))
    ticker = EXTERNAL_SYMBOLS[symbol]
    bars = (market_store.get_daily(symbol, lo.isoformat(), hi.isoformat()) if ticker is None
            else market_store._yf_download(ticker, lo, hi))
    return {b["date"]: float(b["close"]) for b in bars}


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
    ef = sub.add_parser("external-freeze")
    ef.add_argument("csv", help="columns: date, score (others ignored)")
    ef.add_argument("--source", required=True)
    ef.add_argument("--published", required=True, help="YYYY-MM-DD the source published the series")
    es = sub.add_parser("external-score")
    es.add_argument("--source", required=True)
    es.add_argument("--month", required=True, help="YYYY-MM")
    es.add_argument("--symbol", default="NIFTY", choices=sorted(EXTERNAL_SYMBOLS))
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
    elif args.cmd == "external-freeze":
        with open(args.csv, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        added = ledger.freeze_external(args.source, rows, dt.date.fromisoformat(args.published))
        print(f"{args.source}: {added}")
    elif args.cmd == "external-score":
        rows = ledger.get_external(args.source, f"{args.month}-01", f"{args.month}-31")
        if not rows:
            sys.exit(f"nothing frozen for {args.source} in {args.month}")
        print(json.dumps(ledger.score_external(rows, _closes(args.symbol, rows[0]["date"], rows[-1]["date"])),
                         indent=2))


if __name__ == "__main__":
    main()
