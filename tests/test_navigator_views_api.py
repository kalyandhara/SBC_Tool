"""Navigator view routes: chart view, dasha, decision, timeline, rule backtest."""
import datetime as dt

import pytest

from sbc.api.blueprints import navigator_bp as bp
from sbc.api.blueprints import navigator_views as views
from sbc.navigator import store
from sbc.navigator.profile import SAMPLE_PROFILE


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("SBC_API_TOKEN", raising=False)
    monkeypatch.setattr(bp, "_migrated", False)
    monkeypatch.setattr(store, "migrate", lambda: None)
    monkeypatch.setattr(store, "get_profile", lambda i: SAMPLE_PROFILE if i == 1 else None)


def _down(monkeypatch):
    def boom():
        raise store.StoreUnavailable("x")
    monkeypatch.setattr(store, "connect", boom)


def test_chart_adds_view_fields_and_keeps_old_ones(client):
    body = client.get("/api/navigator/chart?profile_id=1").get_json()
    assert {"profile_id", "label", "is_sample", "points", "lagna", "houses"} <= set(body)
    sun = next(p for p in body["points"] if p["name"] == "Sun")
    assert {"longitude", "sign", "degree", "nakshatra", "pada", "bhava", "dignity",
            "combust", "retro", "sign_sa", "code"} <= set(sun)
    lagna = next(p for p in body["points"] if p["name"] == "Lagna")
    assert lagna["bhava"] == 1 and lagna["dignity"] is None and lagna["retro"] is False


def test_dasha_route(client, monkeypatch):
    monkeypatch.setattr(views, "_now_ist", lambda: dt.datetime(2026, 11, 17, 10, 0))
    body = client.get("/api/navigator/dasha?profile_id=1").get_json()
    assert set(body["running"]) == {"maha", "antar", "pratyantar"} and body["periods"]


@pytest.mark.parametrize("query", ["profile_id=1&profile_id=1", "profile_id=1&x=2", "profile_id=0"])
def test_dasha_rejects_bad_params(client, query):
    assert client.get(f"/api/navigator/dasha?{query}").status_code == 400


def test_dasha_unknown_profile_404(client):
    assert client.get("/api/navigator/dasha?profile_id=9").status_code == 404


@pytest.mark.parametrize("method,path", [("get", "/api/navigator/dasha?profile_id=1")])
def test_guard_covers_new_routes(client, monkeypatch, method, path):
    _down(monkeypatch)
    r = getattr(client, method)(path, headers={"X-Forwarded-For": "8.8.8.8"},
                                json={} if method == "post" else None)
    assert r.status_code == 403
    r = getattr(client, method)(path, headers={"Origin": "http://evil.example"},
                                json={} if method == "post" else None)
    assert r.status_code == 403


import pandas as pd  # noqa: E402


@pytest.mark.parametrize("method,path", [
    ("post", "/api/navigator/rule-backtest"), ("get", "/api/navigator/rule-backtest/1"),
    ("get", "/api/navigator/rule-backtest/latest?profile_id=1")])
def test_guard_covers_rule_routes(client, monkeypatch, method, path):
    _down(monkeypatch)
    r = getattr(client, method)(path, headers={"X-Forwarded-For": "8.8.8.8"},
                                json={} if method == "post" else None)
    assert r.status_code == 403


def test_rule_read_404_for_score_run(client, monkeypatch):
    monkeypatch.setattr(store, "expire_stale", lambda *a: 0)
    monkeypatch.setattr(store, "get_run", lambda i: {"id": i, "profile_id": 1, "kind": "score"})
    assert client.get("/api/navigator/rule-backtest/5").status_code == 404


def test_score_read_404_for_rule_run(client, monkeypatch):
    monkeypatch.setattr(store, "expire_stale", lambda *a: 0)
    monkeypatch.setattr(store, "get_run", lambda i: {"id": i, "profile_id": 1, "kind": "rule"})
    assert client.get("/api/navigator/backtest/5").status_code == 404


def test_rule_post_returns_existing_run(client, monkeypatch):
    monkeypatch.setattr(views, "_market", lambda: (pd.DataFrame({"date": ["2026-11-16"]}), {}))
    monkeypatch.setattr(store, "expire_stale", lambda *a: 0)
    calls = []
    monkeypatch.setattr(store, "start_run", lambda pid, meta, kind="score": (calls.append(kind) or (7, False)))
    r = client.post("/api/navigator/rule-backtest", json={"profile_id": 1})
    assert r.status_code == 202 and r.get_json() == {"run_id": 7, "is_new": False} and calls == ["rule"]
