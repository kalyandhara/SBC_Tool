"""Forward intraday forecast (sbc.intraday_forecast) and its ledger."""

import datetime as dt

import pytest

from sbc import forecast_ledger as ledger
from sbc import intraday_forecast as fc

DAY = dt.date(2026, 10, 5)  # Monday
IST = ledger.IST


@pytest.fixture(scope="module")
def forecast():
    import app  # noqa: F401  (build_response for the SBC component)
    return fc.build_forecast(DAY)


def test_shape_and_running_sum(forecast):
    b = forecast["buckets"]
    assert len(b) == 75 and b[0]["time"] == "09:15" and b[-1]["time"] == "15:25"
    run = 0.0
    for k in b:
        assert abs(sum(k["components"].values()) - k["score"]) < 0.01
        run += k["score"]
        assert abs(run - k["cumulative"]) < 0.02
    assert forecast["status"] == "experimental"


def test_deterministic_and_versioned(forecast):
    again = fc.build_forecast(DAY)
    assert again["buckets"] == forecast["buckets"]
    assert forecast["model_version"] == fc.model_version()
    assert fc.model_version({**fc.FORECAST_WEIGHTS, "sbc": 0.9}) != fc.model_version()


def test_transitions_are_real_sub_lord_changes(forecast):
    from sbc import kp_ephemeris as k
    tr = forecast["transitions"]
    assert tr and all(t["old_sublord"] != t["new_sublord"] for t in tr)
    for t in [x for x in tr if x["body"] == "Moon"][:3]:
        hh, mm = map(int, t["time"].split(":"))
        at = dt.datetime.combine(DAY, dt.time(hh, mm))
        before = k.kp_point(k.chart_at(at - dt.timedelta(minutes=1))["lons"]["Moon"])["sublord"]
        now = k.kp_point(k.chart_at(at)["lons"]["Moon"])["sublord"]
        assert (before, now) == (t["old_sublord"], t["new_sublord"])


def test_horas_cover_session_in_chaldean_order(forecast):
    h = forecast["horas"]
    assert h[0]["start"] == "09:15" and h[-1]["end"] == "15:30"
    assert all(a["end"] == b["start"] for a, b in zip(h, h[1:]))
    order = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
    for a, b in zip(h, h[1:]):
        assert order[(order.index(a["lord"]) + 1) % 7] == b["lord"]


def test_sub_direction_rule():
    assert fc.sub_direction("Jupiter", 2.0) == 1
    assert fc.sub_direction("Saturn", 2.0) == -1
    assert fc.sub_direction("Jupiter", -1.0) == 0
    assert fc.sub_direction("Mercury", 3.0) == 0


# ---------------------------------------------------------------- ledger ----

def _bars_following(forecast, invert=False):
    """Synthetic 5-min bars whose moves agree (or disagree) with each bucket score."""
    bars, price = [], 22000.0
    for k in forecast["buckets"]:
        move = (1 if k["score"] > 0 else -1 if k["score"] < 0 else 0) * (-1 if invert else 1) * 5
        bars.append({"time": k["time"], "open": price, "high": price + 6,
                     "low": price - 6, "close": price + move})
        price += move
    return bars


def test_score_forecast_perfect_and_inverted(forecast):
    good = ledger.score_forecast(forecast, _bars_following(forecast))
    bad = ledger.score_forecast(forecast, _bars_following(forecast, invert=True))
    assert good["hit_rate"] == 1.0 and bad["hit_rate"] == 0.0
    assert good["buckets_scored"] == sum(1 for k in forecast["buckets"] if k["score"] != 0)
    assert good["corr_path_price"] > 0.9


def test_freeze_kinds_and_existing_wins(forecast):
    before_open = dt.datetime(2026, 10, 5, 8, 30, tzinfo=IST)
    row = ledger.freeze(DAY, now=before_open)
    assert row["kind"] == "live" and row["model_version"] == forecast["model_version"]
    later = ledger.freeze(DAY, now=dt.datetime(2026, 10, 5, 11, 0, tzinfo=IST))
    assert later["frozen_at"] == row["frozen_at"]  # first freeze wins
    late_day = dt.date(2026, 10, 6)
    assert ledger.freeze(late_day, now=dt.datetime(2026, 10, 6, 10, 0, tzinfo=IST))["kind"] == "late"
    bf = dt.date(2026, 9, 29)
    assert ledger.freeze(bf, backfill=True)["kind"] == "backfill"


def test_score_day_and_summary_separate_backfill(monkeypatch, forecast):
    bf = dt.date(2026, 9, 28)
    ledger.freeze(bf, backfill=True)
    frozen = ledger.get_frozen(bf)["forecast"]
    monkeypatch.setattr(ledger, "_download_5m", lambda day: _bars_following(frozen))
    now = dt.datetime(2026, 10, 1, 18, 0, tzinfo=IST)
    m = ledger.score_day(bf, now)
    assert m["hit_rate"] == 1.0
    s = ledger.summary(days=30, now=now)
    assert s["groups"]["backfill"]["days"] >= 1
    assert all(r["kind"] == "backfill" for r in s["per_day"] if r["date"] == "2026-09-28")
    # cached: no second download
    monkeypatch.setattr(ledger, "_download_5m", lambda day: pytest.fail("should use cache"))
    assert ledger.actual_bars(bf, now)["source"] == "cache"


def test_actual_bars_future_and_too_old():
    now = dt.datetime(2026, 10, 1, 12, 0, tzinfo=IST)
    assert ledger.actual_bars(dt.date(2026, 10, 9), now)["source"] == "future"
    assert "unavailable" in ledger.actual_bars(dt.date(2026, 6, 1), now)["source"]


# ------------------------------------------------------------- endpoints ----

def test_forecast_endpoint(client):
    data = client.get("/api/engine/intraday_forecast?date=2026-10-05").get_json()
    assert data["status"] == "experimental" and len(data["buckets"]) == 75
    assert data["frozen"] is None or data["frozen"]["kind"] in ("live", "late", "backfill")
    assert client.get("/api/engine/intraday_forecast?date=2026-10-03").status_code == 400
    assert client.get("/api/engine/intraday_forecast?date=bad").status_code == 400
    assert len(client.get("/api/engine/intraday_forecast?date=2026-10-05&step=15")
               .get_json()["buckets"]) == 25


def test_ledger_endpoint_shape(client):
    data = client.get("/api/engine/intraday_forecast/ledger?days=30").get_json()
    assert set(data) == {"window_days", "groups", "per_day"}


def test_freeze_endpoint_rejects_remote(app):
    resp = app.test_client().post("/api/engine/intraday_forecast/freeze",
                                  json={"date": "2026-10-05"},
                                  environ_base={"REMOTE_ADDR": "192.168.1.50"})
    assert resp.status_code in (401, 403)


def test_page_has_forecast_panel(client):
    html = client.get("/").get_data(as_text=True)
    panel = html[html.index('id="intraday-forecast"'):html.index('id="kp-intraday"')]
    assert 'id="ifc-chart"' in panel and "experimental-badge" in panel
    assert "/static/intraday-forecast.js" in html


def test_get_forecast_never_freezes_for_remote_callers(app, monkeypatch):
    """The auto-freeze on GET is a write; LAN callers must not trigger it."""
    called = []
    monkeypatch.setattr(ledger, "freeze", lambda *a, **k: called.append(a) or None)
    monkeypatch.setattr(ledger, "get_frozen", lambda day: None)
    monkeypatch.setattr(ledger, "_now_ist",
                        lambda now=None: dt.datetime(2026, 10, 5, 8, 0, tzinfo=IST))
    resp = app.test_client().get("/api/engine/intraday_forecast?date=2026-10-05",
                                 environ_base={"REMOTE_ADDR": "192.168.1.50"})
    assert resp.status_code == 200 and called == []
