"""Sector rotation endpoint: allow-listed parameters, precomputed JSON only, auth parity."""

import datetime as dt
import json

import pytest

from sbc.api.blueprints import sector_rotation_bp as srb


@pytest.fixture
def reports_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(srb, "REPORTS", str(tmp_path))
    payload = {"confirmatory": [], "forecast": {}, "breadth": "not computed"}
    (tmp_path / "sector_rotation_2026-10-29.json").write_text(json.dumps(payload), encoding="utf-8")
    return tmp_path


def test_rejects_unknown_event(client, reports_dir):
    assert client.get("/api/sector_rotation?event=../../etc").status_code == 400


def test_rejects_unknown_horizon(client, reports_dir):
    assert client.get("/api/sector_rotation?h=7").status_code == 400


def test_rejects_non_integer_horizon_text(client, reports_dir):
    assert client.get("/api/sector_rotation?h=5;DROP").status_code == 400


def test_serves_precomputed_json(client, reports_dir):
    r = client.get("/api/sector_rotation?event=all&h=5")
    assert r.status_code == 200
    body = r.get_json()
    assert body["data"]["confirmatory"] == [] and body["h"] == 5


def test_never_calls_build(client, reports_dir, monkeypatch):
    import scripts.sector_rotation_report as rep
    def boom(*a, **k):
        raise AssertionError("endpoint must not recompute")
    monkeypatch.setattr(rep, "build", boom)
    assert client.get("/api/sector_rotation?event=all&h=5").status_code == 200


def test_404_when_no_report_exists(client, tmp_path, monkeypatch):
    monkeypatch.setattr(srb, "REPORTS", str(tmp_path))
    assert client.get("/api/sector_rotation").status_code == 404


def test_read_auth_parity_with_siblings(client, reports_dir):
    # Siblings serve GET with no token; the app-wide guard gates only writes.
    sibling = client.get("/api/monthly_heatmap?date=2026-10-29")
    mine = client.get("/api/sector_rotation")
    assert mine.status_code == 200 and sibling.status_code != 401
    assert client.post("/api/sector_rotation").status_code in (401, 403, 405)


def test_no_extra_routes_added(app):
    rules = {r.rule for r in app.url_map.iter_rules() if "sector_rotation" in r.rule}
    assert rules == {"/api/sector_rotation", "/api/sector_rotation/upcoming"}


DESCRIPTIVE = {"SOLAR_ECLIPSE": {"5": [
    {"sector": "CNXPHARMA", "n_raw": 9, "n_clusters": 6, "mean_relative": 0.02, "beat_rate": 0.6,
     "heat": "dark_green", "volatility": 0.01, "sharpe": 0.1, "top5_rate": 0.5},
    {"sector": "CNXIT", "n_raw": 9, "n_clusters": 6, "mean_relative": -0.01, "beat_rate": 0.4,
     "heat": "orange", "volatility": 0.01, "sharpe": 0.0, "top5_rate": 0.2},
]}, "event_summary": {}}


@pytest.fixture
def upcoming_env(client, tmp_path, monkeypatch):
    monkeypatch.setattr(srb, "REPORTS", str(tmp_path))
    payload = {"confirmatory": [], "descriptive": {"SOLAR_ECLIPSE": DESCRIPTIVE["SOLAR_ECLIPSE"]},
               "events": {"SOLAR_ECLIPSE": {"raw": 9, "clusters": 6}},
               "input": {"last_session": {"NIFTY": "2026-10-29"}}}
    (tmp_path / "sector_rotation_2026-10-29.json").write_text(json.dumps(payload), encoding="utf-8")
    today = dt.datetime.now(srb.ms.IST).date()
    fixed = [{"date": (today + dt.timedelta(days=3)).isoformat(), "event": "SOLAR_ECLIPSE"},
             {"date": (today + dt.timedelta(days=200)).isoformat(), "event": "LUNAR_ECLIPSE"}]
    monkeypatch.setattr(srb, "_core_event_dates", lambda a, b: tuple(fixed))
    return today


def test_upcoming_rejects_window_outside_allow_list(client, upcoming_env):
    assert client.get("/api/sector_rotation/upcoming?days=7").status_code == 400
    assert client.get("/api/sector_rotation/upcoming?days=60;DROP").status_code == 400


def test_upcoming_returns_only_events_inside_window_with_outlook(client, upcoming_env):
    body = client.get("/api/sector_rotation/upcoming?days=60").get_json()
    assert [e["event"] for e in body["events"]] == ["SOLAR_ECLIPSE"]
    ev = body["events"][0]
    assert ev["label"] == "Solar eclipse" and ev["raw"] == 9 and ev["clusters"] == 6
    assert ev["outlook"]["5"]["strongest"][0]["sector"] == "CNXPHARMA"
    assert ev["outlook"]["5"]["weakest"][0]["sector"] == "CNXIT"
    assert body["last_session"] == "2026-10-29"
    assert "not graded" in body["caveat"]


def test_upcoming_carries_scorecard_forecast_and_sample_floor(client, upcoming_env):
    body = client.get("/api/sector_rotation/upcoming?days=60").get_json()
    assert body["sample_floor"] == srb.sr.MIN_CLUSTERS
    ev = body["events"][0]
    assert ev["forecast"] == {}  # fixture report carries no forecast block for this event
    card = ev["outlook"]["5"]["strongest"][0]["scorecard"]
    assert card["validity"] == "Descriptive" and card["forecast"] == "No call"


def test_upcoming_404_without_report(client, tmp_path, monkeypatch, upcoming_env):
    monkeypatch.setattr(srb, "REPORTS", str(tmp_path / "empty"))
    assert client.get("/api/sector_rotation/upcoming?days=60").status_code == 404
