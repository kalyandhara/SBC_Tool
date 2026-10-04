"""'Data as of' stamps for every panel that shows price or Kota data (B-05).

A daily series is current when its last bar is the last settled NSE session
(today after 16:00 IST, otherwise the previous trading day). Each session it
falls behind adds one to ``sessions_behind``; the UI turns the stamp amber from
one session behind.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from sbc.market_holidays import is_trading_day
from sbc.market_store import settled_date


def expected_last_session(now: dt.datetime | None = None) -> dt.date:
    """The most recent NSE session whose daily bar should exist by now."""
    day = settled_date(now)
    while not is_trading_day(day):
        day -= dt.timedelta(days=1)
    return day


def sessions_between(last: dt.date, expected: dt.date) -> int:
    """Trading sessions after ``last`` up to and including ``expected``."""
    count, day = 0, last + dt.timedelta(days=1)
    while day <= expected:
        count += is_trading_day(day)
        day += dt.timedelta(days=1)
    return count


def stamp(as_of: str | dt.date | None, now: dt.datetime | None = None,
          before: str | dt.date | None = None) -> dict:
    """{as_of, expected, sessions_behind, stale} for a daily series ending at as_of.

    ``before``: the series only needs to reach the last session before this date
    (a forecast for a past session isn't stale because newer bars exist).
    """
    expected = expected_last_session(now)
    if before is not None:
        cap = before if isinstance(before, dt.date) else dt.date.fromisoformat(str(before)[:10])
        cap -= dt.timedelta(days=1)
        while not is_trading_day(cap):
            cap -= dt.timedelta(days=1)
        expected = min(expected, cap)
    if as_of is None:
        return {"as_of": None, "expected": expected.isoformat(),
                "sessions_behind": None, "stale": True}
    last = as_of if isinstance(as_of, dt.date) else dt.date.fromisoformat(str(as_of)[:10])
    behind = sessions_between(last, expected)
    return {"as_of": last.isoformat(), "expected": expected.isoformat(),
            "sessions_behind": behind, "stale": behind >= 1}


def csv_last_date(path: str | Path) -> str | None:
    """Date in the first column of a CSV's last non-empty line (cheap tail read)."""
    path = Path(path)
    if not path.exists():
        return None
    with path.open("rb") as fh:
        fh.seek(0, 2)
        fh.seek(max(0, fh.tell() - 4096))
        lines = [ln for ln in fh.read().decode("utf-8", "replace").splitlines() if ln.strip()]
    if not lines:
        return None
    first = lines[-1].split(",", 1)[0].strip()
    return first[:10] if re.fullmatch(r"\d{4}-\d{2}-\d{2}.*", first) else None


_KOTA_RANGE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})\D+(\d{2})\.(\d{2})\.(\d{4})")


def kota_coverage(path: str | Path, today: dt.date | None = None) -> dict:
    """Date range a Kota workbook covers (from its filename) and whether today is in it.

    Kota workbooks are supplied by hand, named like
    ``Prediction_Kota_Chakra_01.09.2026 till 15.09.2026.xlsx``.
    """
    today = today or dt.date.today()
    match = _KOTA_RANGE.search(Path(path).name)
    if not match:
        return {"file": Path(path).name, "from": None, "to": None, "covers_today": None,
                "stale": True}
    d1, m1, y1, d2, m2, y2 = (int(g) for g in match.groups())
    start, end = dt.date(y1, m1, d1), dt.date(y2, m2, d2)
    return {"file": Path(path).name, "from": start.isoformat(), "to": end.isoformat(),
            "covers_today": start <= today <= end, "stale": today > end}
