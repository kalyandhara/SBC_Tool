"""NSE holiday calendar (sbc.market_holidays) and where it is enforced."""

import datetime as dt
from pathlib import Path

import pandas as pd
import pytest

from sbc import market_holidays as mh

D = dt.date


def test_known_days():
    assert mh.holiday_name(D(2026, 10, 2)) == "Mahatma Gandhi Jayanti"
    assert mh.holiday_name(D(2026, 1, 15)).startswith("Mumbai Municipal")
    assert mh.holiday_name(D(2026, 10, 3)) == "Weekend"
    assert mh.holiday_name(D(2026, 10, 1)) is None
    assert not mh.is_trading_day(D(2026, 9, 14)) and mh.is_trading_day(D(2026, 9, 15))


def test_all_listed_holidays_are_weekdays():
    assert all(d.weekday() < 5 for d in mh.NSE_HOLIDAYS)


def test_next_trading_day_skips_holiday_and_weekend():
    assert mh.next_trading_day(D(2026, 10, 1)) == D(2026, 10, 1)
    assert mh.next_trading_day(D(2026, 10, 2)) == D(2026, 10, 5)
    assert mh.next_trading_day(D(2026, 10, 1), inclusive=False) == D(2026, 10, 5)


def test_trading_days_october_2026():
    days = mh.trading_days(2026, 10)
    assert D(2026, 10, 2) not in days and D(2026, 10, 20) not in days
    assert len(days) == 20  # 22 weekdays - Gandhi Jayanti - Dussehra


def test_no_nifty_bar_on_any_listed_holiday():
    """The list is checked against real data: NSE printed no daily bar on these dates."""
    path = Path(__file__).resolve().parent.parent / "data" / "nifty_ohlc.csv"
    df = pd.read_csv(path, parse_dates=["Date"])
    # The list covers recent years only; the cache reaches back to 2007.
    bars = {d for d in df["Date"].dt.date if mh.is_covered(d)}
    lo, hi = min(bars), max(bars)
    listed = [d for d in mh.NSE_HOLIDAYS if lo <= d <= hi and d not in mh.MUHURAT_SESSIONS]
    assert listed, "no overlap between holiday list and cached bars"
    assert not [d for d in listed if d in bars]
    # ...and no unexplained weekday gap in the bars
    d, gaps = lo, []
    while d <= hi:
        if d.weekday() < 5 and d not in bars and d not in mh.NSE_HOLIDAYS:
            gaps.append(d)
        d += dt.timedelta(days=1)
    assert gaps == []


def test_kp_generation_skips_holidays():
    from sbc.kp_ephemeris import trading_days
    assert D(2026, 10, 2) not in trading_days(2026, 10)
    assert D(2026, 10, 2) in trading_days(2026, 10, holidays=set())  # explicit override


def test_freeze_refuses_holiday():
    from sbc import forecast_ledger
    with pytest.raises(ValueError, match="closed"):
        forecast_ledger.freeze(D(2026, 10, 2))


@pytest.mark.parametrize("url", [
    "/api/engine/intraday_forecast?date=2026-10-02",
    "/api/kp_intraday_report?date=2026-10-02&instrument=NIFTY",
    "/api/engine/intraday_path?date=2026-10-02&instrument=NIFTY",
])
def test_endpoints_refuse_holiday(client, url):
    resp = client.get(url)
    assert resp.status_code == 400
    assert resp.get_json()["holiday"] == "Mahatma Gandhi Jayanti"


def test_holidays_api(client):
    data = client.get("/api/market/holidays?year=2026").get_json()
    assert data["covered"] is True
    dates = {h["date"]: h["type"] for h in data["holidays"]}
    assert dates["2026-10-02"] == "holiday" and dates["2026-11-08"] == "muhurat"
    assert client.get("/api/market/holidays?year=2031").get_json()["covered"] is False
