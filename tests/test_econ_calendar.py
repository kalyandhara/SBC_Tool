"""B-59: agency calendar parsing, ET->IST conversion, merge, and MCX session hours."""

import datetime as dt

from sbc import bullion_week as bw
from sbc import econ_calendar as ec

BLS = """BEGIN:VCALENDAR\r
VERSION:2.0\r
BEGIN:VEVENT\r
UID:1\r
DTSTART;TZID=US-Eastern:20261014T083000\r
SUMMARY:Consumer Price Index\r
END:VEVENT\r
BEGIN:VEVENT\r
UID:2\r
DTSTART;TZID=US-Eastern:20261204T083000\r
SUMMARY:Employment Situ\r
 ation\r
END:VEVENT\r
BEGIN:VEVENT\r
UID:3\r
DTSTART;TZID=US-Eastern:20261015T100000\r
SUMMARY:Metropolitan Area Employment and Unemployment (Monthly)\r
END:VEVENT\r
BEGIN:VEVENT\r
UID:4\r
DTSTART;VALUE=DATE:20261020\r
SUMMARY:Producer Price Index\r
END:VEVENT\r
END:VCALENDAR\r
"""


def test_parse_converts_et_to_ist_across_daylight_time():
    rows = ec.parse_ics(BLS, "BLS")
    assert [(r["date"], r["time"], r["name"]) for r in rows] == [
        ("2026-10-14", "18:00", "US CPI"),            # EDT: 8:30 ET = 18:00 IST
        ("2026-12-04", "19:00", "US Nonfarm Payrolls"),  # EST: 8:30 ET = 19:00 IST; folded line joined
    ]  # unwatched release and all-day entry skipped


def test_merge_keeps_manual_and_drops_superseded():
    existing = [{"date": "2026-10-14", "time": "18:00", "name": "US CPI (Sep)", "source": "manual"},
                {"date": "2026-10-15", "time": "18:00", "name": "US Retail Sales (Sep)", "source": "manual"},
                {"date": "2026-09-11", "time": "18:00", "name": "US CPI", "source": "BLS"}]
    rows = ec.merge(existing, ec.parse_ics(BLS, "BLS"))
    names = [(r["date"], r["name"]) for r in rows]
    assert ("2026-10-14", "US CPI (Sep)") not in names and ("2026-10-14", "US CPI") in names
    assert ("2026-10-15", "US Retail Sales (Sep)") in names
    assert ("2026-09-11", "US CPI") not in names  # stale feed rows are replaced by the fresh fetch


def test_mcx_session_follows_us_daylight_time():
    assert bw.session_for(dt.date(2026, 10, 30)) == (9.0, 23.5)
    assert bw.session_for(dt.date(2026, 11, 2)) == (9.0, 23 + 55 / 60)  # US clocks fell back on 1 Nov
    assert bw.day_block(dt.date(2026, 11, 2))["session_label"] == "09:00–23:55"
