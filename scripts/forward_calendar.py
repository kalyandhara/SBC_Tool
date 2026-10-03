"""Write the NIFTY forward calendar to reports/calendar/ (Markdown, HTML and JSON).

  python scripts/forward_calendar.py                    # from the next trading day, 4 weeks
  python scripts/forward_calendar.py --start 2026-10-12 --weeks 8
  python scripts/forward_calendar.py --weekly           # this week's scheduled copy, if not written yet

run_app.py does the --weekly run itself every Saturday from 08:00 IST; use this
script from Windows Task Scheduler when the server isn't running.
"""

import argparse
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc import forward_calendar as fcal  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", help="first day (YYYY-MM-DD); default the next trading day")
    parser.add_argument("--weeks", type=int, default=4, help="1-8 weeks (default 4)")
    parser.add_argument("--weekly", action="store_true", help="write this week's scheduled calendar if missing")
    args = parser.parse_args()

    if args.weekly:
        written = fcal.generate_if_due()
        print(written or f"already written for week {fcal.week_key(dt.datetime.now(fcal.IST))}")
        return 0
    cal = fcal.build(args.start, args.weeks)
    print(fcal.write(cal, f"{cal['start']}_{args.weeks}w"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
