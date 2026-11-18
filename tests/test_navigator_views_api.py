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


@pytest.mark.parametrize("method,path", [("get", "/api/navigator/dasha?profile_id=1"),
                                         ("get", "/api/navigator/decision?profile_id=1")])
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
    r = getattr(client, method)(path, headers={"Origin": "http://evil.example"},
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


import time  # noqa: E402

import numpy as np  # noqa: E402

from sbc import market_store  # noqa: E402
from sbc.market_holidays import next_trading_day  # noqa: E402


def _bars(n=900, start="2023-01-02"):
    days = [str(d)[:10] for d in np.busday_offset(start, np.arange(n), roll="forward")]
    x = 100 + np.cumsum(np.sin(np.arange(n) / 7.0))
    return [{"date": d, "open": v, "high": v + 1, "low": v - 1, "close": v + .2, "volume": 1}
            for d, v in zip(days, x)]


@pytest.fixture
def market(monkeypatch):
    nifty, vix = _bars(), _bars(1300, "2021-06-01")
    monkeypatch.setattr(market_store, "get_daily",
                        lambda s, start=None, end=None: {"NIFTY": nifty, "INDIAVIX": vix}[s])
    monkeypatch.setattr(store, "latest_run", lambda pid, kind="score": None)
    views._CACHE.clear()
    return nifty


def _next_session_after(nifty):
    return next_trading_day(dt.date.fromisoformat(nifty[-1]["date"]), inclusive=False)


def test_decision_card_shape(client, monkeypatch, market):
    t = _next_session_after(market)
    monkeypatch.setattr(views, "_now_ist", lambda: dt.datetime.combine(t, dt.time(10, 0)))
    body = client.get("/api/navigator/decision?profile_id=1").get_json()
    assert body["day"] == t.isoformat() and body["disclaimer"] and body["evidence"]["text"]
    assert "unvalidated" in body["evidence"]["text"]
    assert body["stance"]["stance"] in ("Long bias", "Short bias", "Stand aside")
    assert {i["key"] for i in body["confluence"]} >= {"band", "trend", "vix", "tarabala", "sav"}
    assert body["windows"].get("text") or body["windows"]["available"]


def test_partial_row_for_t_is_ignored(client, monkeypatch, market):
    t = _next_session_after(market)
    monkeypatch.setattr(views, "_now_ist", lambda: dt.datetime.combine(t, dt.time(10, 0)))
    before = client.get("/api/navigator/decision?profile_id=1").get_json()
    market.append({"date": t.isoformat(), "open": 1.0, "high": 1.0, "low": 1.0, "close": 9999.0, "volume": 1})
    views._CACHE.clear()
    after = client.get("/api/navigator/decision?profile_id=1").get_json()
    assert after["stance"] == before["stance"] and after["score"] == before["score"]


def test_stale_when_t_minus_1_missing(client, monkeypatch, market):
    later = next_trading_day(_next_session_after(market), inclusive=False)
    monkeypatch.setattr(views, "_now_ist", lambda: dt.datetime.combine(later, dt.time(10, 0)))
    body = client.get("/api/navigator/decision?profile_id=1").get_json()
    assert body["stale"] is True and body["provisional"] is True


def test_uncovered_year_gives_no_stance(client, market):
    body = client.get("/api/navigator/decision?profile_id=1&day=2031-03-03").get_json()
    assert body["covered"] is False and body["stance"] is None and "not covered" in body["coverage_note"]


def test_non_session_day_400(client, market):
    assert client.get("/api/navigator/decision?profile_id=1&day=2026-11-21").status_code == 400


def test_windows_unavailable_when_forecast_fails(client, monkeypatch, market):
    def boom(_day):
        raise RuntimeError("x")
    monkeypatch.setattr(views, "build_forecast", boom)
    views._forecast_ok.cache_clear()
    body = client.get("/api/navigator/decision?profile_id=1&day=2026-11-18").get_json()
    assert body["windows"] == {"available": False, "text": "windows unavailable"}
    views._forecast_ok.cache_clear()


def test_windows_without_text_get_text(client, monkeypatch, market):
    monkeypatch.setattr(views, "_forecast_ok", lambda day: {"available": False})
    body = client.get("/api/navigator/decision?profile_id=1&day=2026-11-18").get_json()
    assert body["windows"] == {"available": False, "text": "windows unavailable"}


def test_decision_cached(client, monkeypatch, market):
    calls = []
    real = views._decision_body
    monkeypatch.setattr(views, "_decision_body", lambda *a: calls.append(1) or real(*a))
    for _ in range(2):
        client.get("/api/navigator/decision?profile_id=1&day=2026-11-18")
    assert len(calls) == 1


def _real_bars():
    import pandas as pd
    d = pd.read_csv("data/nifty_ohlc.csv")
    return [{"date": str(r.Date)[:10], "open": r.Open, "high": r.High, "low": r.Low, "close": r.Close, "volume": 0}
            for r in d.itertuples()]


def test_decision_budget_on_full_history(client, monkeypatch):
    bars = _real_bars()
    vix = [{**b, "close": 15.0} for b in bars]
    monkeypatch.setattr(market_store, "get_daily", lambda s, start=None, end=None: {"NIFTY": bars, "INDIAVIX": vix}[s])
    monkeypatch.setattr(store, "latest_run", lambda pid, kind="score": None)
    client.get("/api/navigator/decision?profile_id=1&day=2026-11-18")   # warm the intraday cache
    views._CACHE.clear()
    t0 = time.perf_counter()
    assert client.get("/api/navigator/decision?profile_id=1&day=2026-11-18").status_code == 200
    assert time.perf_counter() - t0 < 3.0


def test_score_and_decision_agree_on_day_and_value(client, monkeypatch, market):
    t = _next_session_after(market)
    monkeypatch.setattr(views, "_now_ist", lambda: dt.datetime.combine(t, dt.time(10, 0)))
    monkeypatch.setattr(store, "cached_score", lambda key: None)
    monkeypatch.setattr(store, "save_score", lambda key, row: None)
    score = client.get("/api/navigator/score?profile_id=1").get_json()
    card = client.get("/api/navigator/decision?profile_id=1").get_json()
    assert score["day"] == card["day"] == t.isoformat() and score["score"] == card["score"]


def _rule_run(engine_version, rule_version):
    return {"id": 7, "status": "done", "data_asof": "2026-11-17", "engine_version": engine_version,
            "results": {"rule_version": rule_version, "sides": {"long": {"verdict": "unvalidated"}}}}


def _current_engine():
    return f"{views._rule_version()}+{views.RULE_VERSION}"


def test_rule_evidence_fresh_run_not_stale(monkeypatch):
    monkeypatch.setattr(store, "latest_run",
                        lambda pid, kind="score": _rule_run(_current_engine(), views.RULE_VERSION))
    assert "stale" not in views._rule_evidence(1, "long")["text"]


def test_rule_evidence_old_engine_flagged(monkeypatch):
    monkeypatch.setattr(store, "latest_run", lambda pid, kind="score": _rule_run("old+rule-1", views.RULE_VERSION))
    assert "This run is stale" in views._rule_evidence(1, "long")["text"]


def test_rule_evidence_old_rule_version_flagged(monkeypatch):
    monkeypatch.setattr(store, "latest_run", lambda pid, kind="score": _rule_run(_current_engine(), "rule-0"))
    assert "This run is stale" in views._rule_evidence(1, "long")["text"]


def test_rule_runs_are_versioned_by_rule_backtest_module():
    from sbc.engine_version import module_version
    assert views._rule_version() == module_version("sbc.navigator.rule_backtest")


@pytest.mark.parametrize("query", ["profile_id=1&profile_id=1", "profile_id=1&x=2"])
def test_chart_rejects_repeated_or_extra_params(client, query):
    assert client.get(f"/api/navigator/chart?{query}").status_code == 400


def test_score_vol_real_for_session_after_data_neutral_a_day_further(client, monkeypatch, market):
    vix = _bars(1500, "2021-06-01")   # covers T-1, unlike the shared fixture's VIX
    monkeypatch.setattr(market_store, "get_daily",
                        lambda s, start=None, end=None: {"NIFTY": market, "INDIAVIX": vix}[s])
    monkeypatch.setattr(store, "cached_score", lambda key: None)
    monkeypatch.setattr(store, "save_score", lambda key, row: pytest.fail("future scores are never stored"))
    t = _next_session_after(market)
    later = next_trading_day(t, inclusive=False)
    near = client.get(f"/api/navigator/score?profile_id=1&day={t.isoformat()}").get_json()
    far = client.get(f"/api/navigator/score?profile_id=1&day={later.isoformat()}").get_json()
    assert near["vol_neutral"] is False and far["vol_neutral"] is True


# ---- fix round 1 (SBC_Tool-ds3) ----
def _count_builds(monkeypatch):
    calls = []
    real = views._decision_body
    monkeypatch.setattr(views, "_decision_body", lambda *a: calls.append(1) or real(*a))
    return calls


def test_decision_rebuilds_when_vix_row_arrives(client, monkeypatch, market):
    vix = _bars(1300, "2021-06-01")
    monkeypatch.setattr(market_store, "get_daily",
                        lambda s, start=None, end=None: {"NIFTY": market, "INDIAVIX": vix}[s])
    calls = _count_builds(monkeypatch)
    url = "/api/navigator/decision?profile_id=1&day=2026-11-18"
    client.get(url)
    nxt = str(np.busday_offset(vix[-1]["date"], 1, roll="forward"))
    assert nxt <= market[-1]["date"]          # still within NIFTY's data, so _market keeps it
    vix.append({**vix[-1], "date": nxt})
    client.get(url)
    assert len(calls) == 2


def test_decision_rebuilds_when_profile_relabelled(client, monkeypatch, market):
    import dataclasses
    calls = _count_builds(monkeypatch)
    url = "/api/navigator/decision?profile_id=1&day=2026-11-18"
    client.get(url)
    monkeypatch.setattr(views, "_require_profile",
                        lambda pid: dataclasses.replace(SAMPLE_PROFILE, label="renamed"))
    client.get(url)
    assert len(calls) == 2


def test_windows_recover_without_clearing_decision_cache(client, monkeypatch, market):
    state = {"n": 0}

    def flaky(_day):
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("x")
        return {"buckets": [{"time": "09:15", "score": 1.0}, {"time": "09:30", "score": 2.0}]}
    monkeypatch.setattr(views, "build_forecast", flaky)
    views._forecast_ok.cache_clear()
    url = "/api/navigator/decision?profile_id=1&day=2026-11-18"
    first = client.get(url).get_json()
    second = client.get(url).get_json()
    views._forecast_ok.cache_clear()
    assert first["windows"]["available"] is False
    assert second["windows"]["available"] is True


@pytest.mark.parametrize("sides", [{"long": {}}, {"long": None}, "oops", None, ["x"]])
def test_rule_evidence_tolerates_malformed_results(monkeypatch, sides):
    run = {"id": 7, "status": "done", "data_asof": "x", "engine_version": _current_engine(),
           "results": {"rule_version": views.RULE_VERSION, "sides": sides}}
    monkeypatch.setattr(store, "latest_run", lambda pid, kind="score": run)
    out = views._rule_evidence(1, "long")
    assert "unvalidated" in out["text"]
