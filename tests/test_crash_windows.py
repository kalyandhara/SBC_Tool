import datetime as dt

import pytest

swe = pytest.importorskip("swisseph")
from sbc.crash_windows import build  # noqa: E402


def test_q4_2026_matches_reference_study():
    r = build(dt.date(2026, 10, 1), dt.date(2026, 12, 31))
    assert r["days_scanned"] == 92
    assert (r["n_high"], r["n_elevated"], r["days_covered"]) == (1, 0, 8)
    p = r["periods"][0]
    assert (p["start"], p["end"], p["level"], p["peak_date"]) == ("2026-11-06", "2026-11-13", "HIGH", "2026-11-06")
    assert {x["key"] for x in p["reasons"]} == {
        "jup_fire", "venus11", "sun_lib", "sun_sat_68", "merc_rx", "mars_can", "guru_chandal"}
    assert r["strong_slow_active"] == []


def test_empty_range_of_one_day():
    r = build(dt.date(2026, 10, 1), dt.date(2026, 10, 1))
    assert r["days_scanned"] == 1 and len(r["series"]) == 1
