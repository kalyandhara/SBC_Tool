"""NSE trading holidays (equity and equity-derivative segments).

Weekday closures only; Saturdays and Sundays are always closed. Sources: NSE's
annual holiday circulars, plus special closures announced during the year
(elections, the 2024-01-22 special holiday). Each list was cross-checked
against data/nifty_ohlc.csv: every listed date has no regular-session bar.

Muhurat trading (a one-hour Diwali evening session) happens on a listed
holiday; the regular session is still closed, so for this tool the day is
not a trading day. MUHURAT_SESSIONS records them for reference.

Refresh yearly: NSE publishes the next year's circular in December. Dates
outside COVERED_YEARS fall back to weekends-only and is_covered() says so.
"""

from __future__ import annotations

import datetime as dt

NSE_HOLIDAYS: dict[dt.date, str] = {
    # 2024
    dt.date(2024, 1, 22): "Special holiday (Ram Mandir)",
    dt.date(2024, 1, 26): "Republic Day",
    dt.date(2024, 3, 8): "Mahashivratri",
    dt.date(2024, 3, 25): "Holi",
    dt.date(2024, 3, 29): "Good Friday",
    dt.date(2024, 4, 11): "Id-Ul-Fitr (Ramadan Eid)",
    dt.date(2024, 4, 17): "Shri Ram Navami",
    dt.date(2024, 5, 1): "Maharashtra Day",
    dt.date(2024, 5, 20): "General Parliamentary Elections (Mumbai)",
    dt.date(2024, 6, 17): "Bakri Id",
    dt.date(2024, 7, 17): "Muharram",
    dt.date(2024, 8, 15): "Independence Day / Parsi New Year",
    dt.date(2024, 10, 2): "Mahatma Gandhi Jayanti",
    dt.date(2024, 11, 1): "Diwali Laxmi Pujan",
    dt.date(2024, 11, 15): "Gurunanak Jayanti",
    dt.date(2024, 11, 20): "Maharashtra Assembly Election",
    dt.date(2024, 12, 25): "Christmas",
    # 2025
    dt.date(2025, 2, 26): "Mahashivratri",
    dt.date(2025, 3, 14): "Holi",
    dt.date(2025, 3, 31): "Id-Ul-Fitr (Ramadan Eid)",
    dt.date(2025, 4, 10): "Shri Mahavir Jayanti",
    dt.date(2025, 4, 14): "Dr. Baba Saheb Ambedkar Jayanti",
    dt.date(2025, 4, 18): "Good Friday",
    dt.date(2025, 5, 1): "Maharashtra Day",
    dt.date(2025, 8, 15): "Independence Day",
    dt.date(2025, 8, 27): "Ganesh Chaturthi",
    dt.date(2025, 10, 2): "Mahatma Gandhi Jayanti / Dussehra",
    dt.date(2025, 10, 21): "Diwali Laxmi Pujan",
    dt.date(2025, 10, 22): "Diwali Balipratipada",
    dt.date(2025, 11, 5): "Prakash Gurpurb Sri Guru Nanak Dev",
    dt.date(2025, 12, 25): "Christmas",
    # 2026
    dt.date(2026, 1, 15): "Mumbai Municipal Corporation Elections",
    dt.date(2026, 1, 26): "Republic Day",
    dt.date(2026, 3, 3): "Holi",
    dt.date(2026, 3, 26): "Shri Ram Navami",
    dt.date(2026, 3, 31): "Shri Mahavir Jayanti",
    dt.date(2026, 4, 3): "Good Friday",
    dt.date(2026, 4, 14): "Dr. Baba Saheb Ambedkar Jayanti",
    dt.date(2026, 5, 1): "Maharashtra Day",
    dt.date(2026, 5, 28): "Bakri Id",
    dt.date(2026, 6, 26): "Muharram",
    dt.date(2026, 9, 14): "Ganesh Chaturthi",
    dt.date(2026, 10, 2): "Mahatma Gandhi Jayanti",
    dt.date(2026, 10, 20): "Dussehra",
    dt.date(2026, 11, 10): "Diwali Balipratipada",
    dt.date(2026, 11, 24): "Guru Nanak Jayanti",
    dt.date(2026, 12, 25): "Christmas",
}

# One-hour Diwali evening sessions (regular session closed or weekend).
MUHURAT_SESSIONS: dict[dt.date, str] = {
    dt.date(2024, 11, 1): "Muhurat trading (Diwali Laxmi Pujan)",
    dt.date(2025, 10, 21): "Muhurat trading (Diwali Laxmi Pujan)",
    dt.date(2026, 11, 8): "Muhurat trading (Diwali Laxmi Pujan, Sunday)",
}

COVERED_YEARS = frozenset(d.year for d in NSE_HOLIDAYS)


def is_covered(day: dt.date) -> bool:
    """True when the holiday list for this date's year is loaded."""
    return day.year in COVERED_YEARS


def holiday_name(day: dt.date) -> str | None:
    if day.weekday() >= 5:
        return "Weekend"
    return NSE_HOLIDAYS.get(day)


def is_trading_day(day: dt.date) -> bool:
    """Regular NSE equity session open on this date."""
    return day.weekday() < 5 and day not in NSE_HOLIDAYS


def next_trading_day(day: dt.date, inclusive: bool = True) -> dt.date:
    d = day if inclusive else day + dt.timedelta(days=1)
    while not is_trading_day(d):
        d += dt.timedelta(days=1)
    return d


def trading_days(year: int, month: int) -> list[dt.date]:
    d = dt.date(year, month, 1)
    out = []
    while d.month == month:
        if is_trading_day(d):
            out.append(d)
        d += dt.timedelta(days=1)
    return out


def holidays_in(year: int) -> list[dict]:
    """Weekday holidays and Muhurat sessions of a year, for the UI and API."""
    rows = [{"date": d.isoformat(), "name": n, "type": "holiday"}
            for d, n in sorted(NSE_HOLIDAYS.items()) if d.year == year]
    rows += [{"date": d.isoformat(), "name": n, "type": "muhurat"}
             for d, n in sorted(MUHURAT_SESSIONS.items()) if d.year == year]
    return sorted(rows, key=lambda r: r["date"])
