#!/usr/bin/env python3
"""SBC app entrypoint for local development.

Usage:
  python run_app.py
  python run_app.py --host 127.0.0.1 --port 8000 --debug
  python run_app.py --no-warm      # skip the background series-cache warmup

Run it with the interpreter you want (start.bat uses the venv's); this script
no longer re-executes itself, so stopping it stops the server.
"""

import argparse
import datetime
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

parser = argparse.ArgumentParser(description="Run SBC Flask app")
parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
parser.add_argument("--port", type=int, default=8000, help="Port to bind")
parser.add_argument("--debug", action="store_true", help="Run in debug mode")
parser.add_argument("--no-warm", action="store_true",
                    help="Do not pre-compute the chart's prediction series in the background")
parser.add_argument("--no-ledger", action="store_true",
                    help="Do not auto-freeze/score the intraday forecast ledger")
args = parser.parse_args()

from app import app  # noqa: E402  (path set up above)


def _warm_series_cache():
    """Pre-compute the chart overlay for the window the UI asks for on load.

    Results land in the on-disk series cache, so after the first ever boot this
    finishes in seconds; the first chart paint no longer waits ~100 s.
    """
    today = datetime.date.today()
    start = (today - datetime.timedelta(days=366)).isoformat()
    end = (today + datetime.timedelta(days=180)).isoformat()
    try:
        with app.test_client() as c:
            c.get(f"/api/prediction_series?start={start}&end={end}&anchor=nifty")
        app.logger.info("series cache warm: %s..%s", start, end)
    except Exception:  # never let warmup take the server down
        app.logger.exception("series cache warmup failed")


def _forecast_ledger_loop(interval_s=600):
    """Freeze today's intraday forecast before 09:15 IST; score after the close.

    sbc.forecast_ledger keeps the honest forward record. Freezing is a no-op
    once a day is stored; scoring only touches settled, unscored days.
    """
    import time as _time

    from sbc import forecast_ledger as ledger
    from sbc.market_holidays import is_trading_day
    while True:
        try:
            now = ledger._now_ist()
            day = now.date()
            if (is_trading_day(day) and datetime.time(6, 0) <= now.time() < datetime.time(9, 15)
                    and ledger.get_frozen(day) is None):
                ledger.freeze(day, now)
                app.logger.info("forecast ledger: froze %s", day)
            if now.time() >= datetime.time(16, 15):
                scored = ledger.score_pending(now)
                if scored:
                    app.logger.info("forecast ledger: scored %s", scored)
        except Exception:  # never let the ledger take the server down
            app.logger.exception("forecast ledger loop failed")
        _time.sleep(interval_s)


if __name__ == "__main__":
    if not args.no_ledger and not args.debug:
        threading.Thread(target=_forecast_ledger_loop, name="forecast-ledger", daemon=True).start()
    if not args.no_warm and not args.debug:
        threading.Thread(target=_warm_series_cache, name="series-warm", daemon=True).start()
    app.run(host=args.host, port=args.port, debug=args.debug)
