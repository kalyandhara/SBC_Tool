"""Phase 5: forward calendar, weekly schedule and the forecast evidence card."""

import copy
import datetime as dt

import numpy as np
import pytest

from sbc import analogs as an
from sbc import daily_ledger, market_store
from sbc import fingerprint as fpm
from sbc import forecast as fc
from sbc import forward_calendar as fcal
from sbc.market_holidays import next_trading_day

IST = market_store.IST


# ── sky events ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def base_fp():
    return fpm.fingerprint("2026-10-05")


def test_events_detect_ingress_station_and_exact_aspect(base_fp):
    prev, cur, nxt = (copy.deepcopy(base_fp) for _ in range(3))
    cur["planets"]["Jupiter"].update(sign=prev["planets"]["Jupiter"]["sign"] + 1, sign_name="Leo")
    cur["planets"]["Mercury"]["retrograde"] = not prev["planets"]["Mercury"]["retrograde"]
    aspect = {"a": "Mars", "b": "Saturn", "aspect": "trine", "applying": True, "tier": "medium"}
    prev["aspects"] = [{**aspect, "orb": 0.6}]
    cur["aspects"] = [{**aspect, "orb": 0.1}]
    nxt["aspects"] = [{**aspect, "orb": 0.5}]
    events = fcal.events_between(prev, cur, nxt)
    assert "Jupiter enters Leo" in events
    assert any(e.startswith("Mercury stations") for e in events)
    assert "Mars trine Saturn exact (0.10°)" in events
    assert fcal.events_between(prev, prev, prev) == []  # nothing changes, nothing exact


def test_moon_aspects_are_left_out(base_fp):
    prev, cur, nxt = (copy.deepcopy(base_fp) for _ in range(3))
    a = {"a": "Moon", "b": "Saturn", "aspect": "square", "applying": True, "tier": "fast"}
    prev["aspects"], cur["aspects"], nxt["aspects"] = [{**a, "orb": 0.5}], [{**a, "orb": 0.0}], [{**a, "orb": 0.5}]
    assert not any("Moon square" in e for e in fcal.events_between(prev, cur, nxt))


def test_week_key_is_the_owning_saturday():
    sat_early = dt.datetime(2026, 10, 3, 7, 0, tzinfo=IST)
    sat_late = dt.datetime(2026, 10, 3, 8, 0, tzinfo=IST)
    wed = dt.datetime(2026, 10, 7, 12, 0, tzinfo=IST)
    assert fcal.week_key(sat_early) == "2026-09-26"
    assert fcal.week_key(sat_late) == "2026-10-03"
    assert fcal.week_key(wed) == "2026-10-03"


# ── the calendar ───────────────────────────────────────────────────────────

def _sessions(n, start):
    days = [start + dt.timedelta(days=i) for i in range(int(n * 1.6))]
    return [d.isoformat() for d in days if d.weekday() < 5][:n]


@pytest.fixture(scope="module")
def history():
    dates = _sessions(500, dt.date(2024, 9, 2))
    closes = 1000 * np.exp(np.cumsum(np.random.default_rng(3).normal(0.0003, 0.01, len(dates))))
    return an.History.build(dates, closes, [fpm.fingerprint(d) for d in dates])


def test_build_covers_every_day_and_is_the_base_rate(history):
    first = next_trading_day(dt.date.fromisoformat(history.dates[-1]), inclusive=False)
    cal = fcal.build(first.isoformat(), weeks=2, history=history)
    assert cal["start"] == first.isoformat() and len(cal["days"]) == 14 and len(cal["weeks"]) == 2
    trading = [d for d in cal["days"] if d["trading"]]
    assert [d["session"] for d in trading] == list(range(1, len(trading) + 1))
    assert all(set(d["analogs"]) == {"overall", "slow", "medium", "fast"} for d in trading)
    for x in cal["headline"].values():
        assert x["validated"] == [] and x["probability_up"] == pytest.approx(x["base_up"], abs=1e-4)
    assert cal["weeks"][0]["sessions"] + cal["weeks"][1]["sessions"] == len(trading)
    with pytest.raises(ValueError):
        fcal.build(first.isoformat(), weeks=9, history=history)


def test_renderers_escape_and_mark_closed_days(history):
    first = next_trading_day(dt.date.fromisoformat(history.dates[-1]), inclusive=False)
    cal = fcal.build(first.isoformat(), weeks=1, history=history)
    cal["days"][0]["events"].append("<script>x</script>")
    page = fcal.render_html(cal)
    assert "<script>x" not in page and "&lt;script&gt;x" in page
    assert "class='closed'" in page and "not investment advice" in page
    md = fcal.render_markdown(cal)
    assert md.startswith("# NIFTY forward calendar") and "| Day |" in md


def test_generate_if_due_writes_once_per_week(tmp_path, monkeypatch, history):
    monkeypatch.setattr(an, "load_nifty_history", lambda: history)
    now = dt.datetime.combine(dt.date.fromisoformat(history.dates[-1]), dt.time(20, 0), IST)
    first = fcal.generate_if_due(now, directory=tmp_path, refresh_fingerprints=False)
    assert set(first) == {"md", "html", "json"}
    assert fcal.generate_if_due(now, directory=tmp_path, refresh_fingerprints=False) is None
    assert fcal.reports(tmp_path)[0]["key"] == fcal.week_key(now)


# ── evidence card ──────────────────────────────────────────────────────────

def test_card_prefers_the_frozen_copy(tmp_path, monkeypatch, history):
    monkeypatch.setattr(daily_ledger, "DB_PATH", tmp_path / "daily.db")
    day = next_trading_day(dt.date.fromisoformat(history.dates[-1]), inclusive=False).isoformat()
    daily_ledger.freeze(dt.date.fromisoformat(day), dt.datetime.combine(
        dt.date.fromisoformat(day), dt.time(8, 0), IST), horizons=(5,),
        make=lambda d, h: fc.forecast(d, h, history=history))
    c = fc.card(day, history=history)
    assert set(c["horizons"]) == {"1", "5", "20"}
    assert c["horizons"]["5"]["source"].startswith("frozen") and "(live)" in c["horizons"]["5"]["source"]
    assert c["horizons"]["1"]["source"] == "computed now"
    assert {x["name"] for x in c["components"]} >= {"bradley_sign", "analog_fast"}
    assert "not investment advice" in c["caveat"]


# ── endpoints ──────────────────────────────────────────────────────────────

def test_calendar_and_card_endpoints(client, monkeypatch, tmp_path, history):
    monkeypatch.setattr(an, "load_nifty_history", lambda: history)
    monkeypatch.setattr(fcal, "REPORT_DIR", tmp_path)
    first = next_trading_day(dt.date.fromisoformat(history.dates[-1]), inclusive=False).isoformat()
    body = client.get(f"/api/engine/calendar?start={first}&weeks=1").get_json()
    assert body["start"] == first and len(body["days"]) == 7
    page = client.get(f"/api/engine/calendar?start={first}&weeks=1&format=html")
    assert page.status_code == 200 and page.mimetype == "text/html"
    assert client.get("/api/engine/calendar?weeks=12").status_code == 400
    assert client.get("/api/engine/calendar?format=pdf").status_code == 400

    card = client.get(f"/api/engine/forecast/card?date={first}").get_json()
    assert set(card["horizons"]) == {"1", "5", "20"}
    assert client.get("/api/engine/forecast/card?date=2026-10-04").status_code == 400

    fcal.write(body, "2026-10-03", tmp_path)
    reports = client.get("/api/engine/calendar/reports").get_json()["reports"]
    assert reports[0]["html"] == "forward_calendar_2026-10-03.html"
    assert client.get("/api/engine/calendar/reports/forward_calendar_2026-10-03.html").status_code == 200
    assert client.get("/api/engine/calendar/reports/..%2Fapp.py").status_code == 404
    assert client.get("/api/engine/calendar/reports/forward_calendar_2026-10-03.json").status_code == 404
