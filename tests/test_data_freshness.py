"""B-05: 'data as of' stamps that turn amber after one trading session."""

import datetime as dt
from zoneinfo import ZoneInfo

from sbc import data_freshness as f

IST = ZoneInfo("Asia/Kolkata")


def at(day, hour=18):
    return dt.datetime.fromisoformat(day).replace(hour=hour, tzinfo=IST)


def test_expected_session_skips_holidays_and_waits_for_the_close():
    # 2026-10-02 is Gandhi Jayanti, 3-4 Oct a weekend: Sunday expects Thursday's bar.
    assert f.expected_last_session(at("2026-10-04")) == dt.date(2026, 10, 1)
    # Before 16:00 IST today's bar isn't settled yet.
    assert f.expected_last_session(at("2026-10-05", 10)) == dt.date(2026, 10, 1)
    assert f.expected_last_session(at("2026-10-05", 17)) == dt.date(2026, 10, 5)


def test_stamp_counts_trading_sessions_behind():
    current = f.stamp("2026-10-01", now=at("2026-10-04"))
    assert current == {"as_of": "2026-10-01", "expected": "2026-10-01",
                       "sessions_behind": 0, "stale": False}
    # Monday evening: one session (5 Oct) missing -> amber.
    behind = f.stamp("2026-10-01", now=at("2026-10-05"))
    assert behind["sessions_behind"] == 1 and behind["stale"]
    # The holiday and weekend don't count.
    assert f.stamp("2026-09-30", now=at("2026-10-04"))["sessions_behind"] == 1
    assert f.stamp(None, now=at("2026-10-04"))["stale"]


def test_stamp_before_caps_what_a_past_forecast_needs():
    # A card for 2026-09-15 only needs data through 2026-09-11
    # (14 Sep is Ganesh Chaturthi, 12-13 a weekend).
    s = f.stamp("2026-09-11", now=at("2026-10-04"), before="2026-09-15")
    assert s["expected"] == "2026-09-11" and not s["stale"]


def test_csv_last_date(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("Date,Close\n2026-09-30,1\n2026-10-01,2\n\n", encoding="utf-8")
    assert f.csv_last_date(p) == "2026-10-01"
    assert f.csv_last_date(tmp_path / "missing.csv") is None


def test_kota_coverage_from_filename():
    name = "Prediction_Kota_Chakra_01.09.2026 till 15.09.2026.xlsx"
    c = f.kota_coverage(name, today=dt.date(2026, 10, 4))
    assert (c["from"], c["to"], c["covers_today"], c["stale"]) == ("2026-09-01", "2026-09-15", False, True)
    assert f.kota_coverage(name, today=dt.date(2026, 9, 10))["covers_today"]
    assert f.kota_coverage("kota.xlsx")["to"] is None


def test_kota_routes_report_coverage(client, tmp_path, monkeypatch):
    import openpyxl
    path = tmp_path / "Prediction_Kota_Chakra_01.09.2026 till 15.09.2026.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Dashboard"
    ws.append(["Date", "Signal"])
    ws.append(["2026-09-10", "Up"])
    wb.save(path)
    monkeypatch.setenv("SBC_KOTA_XLSX", str(path))
    body = client.get("/api/engine/kota/daily?date=2026-09-10").get_json()
    assert body["coverage"]["to"] == "2026-09-15"
    assert body["coverage"]["stale"] is (dt.date.today() > dt.date(2026, 9, 15))


def test_market_ohlc_says_when_there_is_no_bar_source(client, monkeypatch):
    import sbc.market_ohlc as mo
    monkeypatch.setattr(mo, "load_week_ohlc", lambda symbol, days: [])
    body = client.get("/api/engine/market/ohlc").get_json()
    assert body["bars"] == [] and body["freshness"]["stale"]
    assert "no 3-minute bar source" in body["note"]
