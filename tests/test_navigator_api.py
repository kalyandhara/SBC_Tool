"""Navigator routes. Postgres tests write only to NAV_TEST_DATABASE_URL."""
import json
import logging
import os
import threading as _threading
import time

import numpy as np
import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict

from sbc import market_store
from sbc.api.blueprints import navigator_bp as bp
from sbc.app_factory import create_app
from sbc.navigator import analogs as A
from sbc.navigator import backtest as B
from sbc.navigator import store
from sbc.navigator.profile import SAMPLE_PROFILE, chart_hash

pg = pytest.mark.skipif(not os.environ.get("NAV_TEST_DATABASE_URL"), reason="needs Postgres")

GOOD = {"label": "Mine", "birth_date": "1971-03-04", "birth_time": "07:08:09",
        "tz": "Asia/Kolkata", "lat": 12.3456, "lon": 76.5432}
BIRTH_VALUES = ("1971-03-04", "07:08:09", "12.3456", "76.5432")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("SBC_API_TOKEN", raising=False)
    monkeypatch.setattr(bp, "_migrated", False)


def _down(monkeypatch):
    def boom():
        raise store.StoreUnavailable("x")
    monkeypatch.setattr(store, "connect", boom)


def _bars(n=900, start="2020-01-01"):
    days = [str(d)[:10] for d in np.busday_offset(start, np.arange(n), roll="forward")]
    drift = np.cumsum(np.sin(np.arange(n) / 7.0))
    return [{"date": d, "open": 100.0 + x, "high": 102.0 + x, "low": 99.0 + x,
             "close": 101.0 + x + .3 * np.cos(i), "volume": 1}
            for i, (d, x) in enumerate(zip(days, drift + 50))]


@pytest.fixture
def market(monkeypatch):
    nifty = _bars()
    vix = _bars(1300, "2018-11-01")   # lead-in before NIFTY, and runs past its last session

    def get_daily(symbol, start=None, end=None):
        return {"NIFTY": nifty, "INDIAVIX": vix}[symbol]
    monkeypatch.setattr(market_store, "get_daily", get_daily)
    return nifty


@pytest.fixture
def db(monkeypatch):
    test_url = os.environ["NAV_TEST_DATABASE_URL"]
    live = os.environ.get("NAV_DATABASE_URL", "")
    assert not live or conninfo_to_dict(live).get("dbname") != conninfo_to_dict(test_url).get("dbname")
    monkeypatch.setenv("NAV_DATABASE_URL", test_url)
    store.migrate()

    def wipe():
        with store.connect() as c:
            c.execute("truncate natal_profile, daily_score, backtest_run restart identity cascade")
    wipe()
    yield
    wipe()


def _profile(client, **over):
    r = client.post("/api/navigator/profile", json={**GOOD, **over})
    assert r.status_code == 201
    return r.get_json()["id"]


def _wait(client, run_id, status="done"):
    deadline = time.time() + 60
    while time.time() < deadline:
        body = client.get(f"/api/navigator/backtest/{run_id}").get_json()
        if body["status"] in ("done", "failed"):
            assert body["status"] == status, body
            return body
        time.sleep(.05)
    raise AssertionError("run did not finish")


def _rows(sql, *args):
    with store.connect() as c:
        return c.execute(sql, args).fetchall()


# ---- guard --------------------------------------------------------------------
@pytest.mark.parametrize("header", ["X-Forwarded-For", "X-Real-IP", "Forwarded", "X-Forwarded-Proto"])
def test_proxied_read_refused(client, header):
    r = client.get("/api/navigator/profile", headers={header: "8.8.8.8"})
    assert r.status_code in (401, 403)


def test_remote_read_refused(client):
    r = client.get("/api/navigator/profile", environ_base={"REMOTE_ADDR": "10.0.0.9"})
    assert r.status_code == 403


@pytest.mark.parametrize("method,path", [
    ("get", "/api/navigator/profile"), ("post", "/api/navigator/profile"),
    ("get", "/api/navigator/chart?profile_id=1"), ("get", "/api/navigator/score?profile_id=1"),
    ("post", "/api/navigator/backtest"), ("get", "/api/navigator/backtest/1"),
    ("get", "/api/navigator/backtest/latest?profile_id=1"), ("get", "/api/navigator/analogs?profile_id=1")])
def test_guard_covers_every_route_before_postgres(client, monkeypatch, method, path):
    _down(monkeypatch)    # a route that reached the store would be a 503
    r = getattr(client, method)(path, headers={"X-Forwarded-For": "8.8.8.8"},
                                json={} if method == "post" else None)
    assert r.status_code == 403


def test_token_required_when_set(client, monkeypatch):
    monkeypatch.setenv("SBC_API_TOKEN", "s3cret")
    _down(monkeypatch)
    assert client.get("/api/navigator/profile").status_code == 401
    bad = client.get("/api/navigator/profile", headers={"X-API-Token": "wrong"})
    assert bad.status_code == 401


def test_non_ascii_token_is_refused_not_a_crash(client, monkeypatch):
    monkeypatch.setenv("SBC_API_TOKEN", "s3cret")
    r = client.get("/api/navigator/profile", headers={"X-API-Token": "café"})
    assert r.status_code == 401


def test_valid_token_passes_proxied(client, monkeypatch):
    monkeypatch.setenv("SBC_API_TOKEN", "s3cret")
    _down(monkeypatch)
    r = client.get("/api/navigator/profile",
                   headers={"X-API-Token": "s3cret", "X-Forwarded-For": "8.8.8.8"})
    assert r.status_code == 503    # past the guard


LOCAL_OK = ["localhost", "localhost:5000", "LOCALHOST:8", "127.0.0.1", "127.0.0.1:65535",
            "[::1]", "[::1]:5000"]
LOCAL_BAD = ["evil.example", "evil.example:5000", "localhost.evil.example", "evil.localhost",
             "127.0.0.1.evil.example", "localhost:", "localhost:abc",
             "localhost:5000:1", "::1", "[::1", "[::1]5000", "[::2]:5000", "[::ffff:127.0.0.1]",
             "user@localhost", "localhost, evil.example", "localhost."]


@pytest.mark.parametrize("host", LOCAL_OK)
def test_local_host_passes(client, monkeypatch, host):
    _down(monkeypatch)    # a 503 proves the request got past the guard
    r = client.get("/api/navigator/profile", headers={"Host": host})
    assert r.status_code == 503


@pytest.mark.parametrize("host", LOCAL_BAD)
def test_rebound_host_refused(client, monkeypatch, host):
    _down(monkeypatch)
    r = client.get("/api/navigator/profile", headers={"Host": host})
    assert r.status_code == 403


def test_out_of_range_host_port_refused():   # the test client itself cannot send this one
    assert bp._local_authority(bp._HOST_RE, "localhost:65535")
    assert not bp._local_authority(bp._HOST_RE, "localhost:65536")
    assert not bp._local_authority(bp._HOST_RE, "localhost:99999")


@pytest.mark.parametrize("origin", ["http://localhost:5000", "http://127.0.0.1:5000",
                                    "https://localhost", "http://[::1]:5000"])
def test_local_origin_passes(client, monkeypatch, origin):
    _down(monkeypatch)
    r = client.post("/api/navigator/profile", json=GOOD, headers={"Origin": origin})
    assert r.status_code == 503


def test_absent_origin_passes(client, monkeypatch):
    _down(monkeypatch)
    assert client.get("/api/navigator/profile").status_code == 503


@pytest.mark.parametrize("origin", ["http://evil.example", "http://localhost.evil.example",
                                    "http://localhost@evil.example", "null", "localhost",
                                    "ftp://localhost", "http://localhost:5000/x",
                                    "http://localhost:99999", ""])
def test_foreign_origin_refused(client, monkeypatch, origin):
    _down(monkeypatch)
    r = client.post("/api/navigator/profile", json=GOOD, headers={"Origin": origin})
    assert r.status_code == 403


def test_token_branch_ignores_host(client, monkeypatch):
    monkeypatch.setenv("SBC_API_TOKEN", "s3cret")
    _down(monkeypatch)
    r = client.get("/api/navigator/profile",
                   headers={"X-API-Token": "s3cret", "Host": "evil.example"})
    assert r.status_code == 503


@pytest.mark.parametrize("header", ["True-Client-IP", "CF-Connecting-IP", "X-Client-IP",
                                    "X-Cluster-Client-IP", "X-Original-Forwarded-For",
                                    "Fastly-Client-IP", "X-Forwarded-Server", "Via"])
def test_more_proxy_headers_refused(client, monkeypatch, header):
    _down(monkeypatch)
    r = client.get("/api/navigator/profile", headers={header: "8.8.8.8"})
    assert r.status_code == 403


def test_proxy_headers_do_not_block_a_valid_token(client, monkeypatch):
    monkeypatch.setenv("SBC_API_TOKEN", "s3cret")
    _down(monkeypatch)
    r = client.get("/api/navigator/profile",
                   headers={"X-API-Token": "s3cret", "True-Client-IP": "8.8.8.8"})
    assert r.status_code == 503


# ---- availability -------------------------------------------------------------
def test_503_when_store_down(client, monkeypatch):
    _down(monkeypatch)
    r = client.get("/api/navigator/profile")
    assert r.status_code == 503
    assert r.get_json() == {"error": "Navigator database is unavailable. Start Postgres and retry."}
    assert client.get("/healthz").status_code == 200


def test_503_when_migration_hits_a_driver_error(client, monkeypatch):
    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, *a):
            raise psycopg.OperationalError("password=hunter2")
    monkeypatch.setattr(store, "connect", Conn)
    r = client.get("/api/navigator/profile")
    assert r.status_code == 503 and b"hunter2" not in r.data


def test_app_boots_without_touching_postgres(monkeypatch):
    calls = []
    monkeypatch.setattr(store, "connect", lambda: calls.append(1))
    monkeypatch.setattr(store, "migrate", lambda: calls.append(1))
    assert create_app().test_client().get("/healthz").status_code == 200
    assert calls == []


def test_migrate_runs_once_and_retries_after_failure(client, monkeypatch):
    calls = []

    def migrate():
        calls.append(1)
        if len(calls) == 1:
            raise store.StoreUnavailable("x")
    monkeypatch.setattr(store, "migrate", migrate)
    monkeypatch.setattr(store, "ensure_sample", lambda: 1)
    monkeypatch.setattr(store, "list_profiles", lambda: [])
    assert client.get("/api/navigator/profile").status_code == 503
    assert client.get("/api/navigator/profile").status_code == 200
    assert client.get("/api/navigator/profile").status_code == 200
    assert len(calls) == 2


def test_unexpected_error_is_clean_json_and_logs_no_message(client, monkeypatch, caplog):
    def boom(*a):
        raise RuntimeError("1971-03-04")
    monkeypatch.setattr(store, "migrate", lambda: None)
    monkeypatch.setattr(store, "get_profile", lambda i: SAMPLE_PROFILE)
    monkeypatch.setattr(bp, "natal_points", boom)
    caplog.set_level(logging.DEBUG)
    r = client.get("/api/navigator/chart?profile_id=1")
    assert r.status_code == 500 and b"1971" not in r.data
    assert "1971-03-04" not in caplog.text


# ---- profile ------------------------------------------------------------------
def test_bad_profile_400(client, monkeypatch):
    monkeypatch.setattr(store, "migrate", lambda: None)
    r = client.post("/api/navigator/profile", json={"birth_time": "99:99"})
    assert r.status_code == 400 and b"99:99" not in r.data


@pytest.mark.parametrize("body", ["[1]", '"x"', "not json", "null"])
def test_non_object_profile_400(client, monkeypatch, body):
    monkeypatch.setattr(store, "migrate", lambda: None)
    r = client.post("/api/navigator/profile", data=body, content_type="application/json")
    assert r.status_code == 400


@pytest.mark.parametrize("url", ["/api/navigator/profile", "/api/navigator/backtest"])
def test_deeply_nested_json_is_a_fixed_400(client, monkeypatch, url):
    monkeypatch.setattr(store, "migrate", lambda: None)
    r = client.post(url, data="[" * 200000, content_type="application/json")
    assert r.status_code == 400
    want = "invalid birth data" if url.endswith("profile") else "profile_id must be a positive integer"
    assert r.get_json() == {"error": want}


@pytest.mark.parametrize("path", ["chart", "score", "profile"])
@pytest.mark.parametrize("pid", ["0", "000"])
def test_zero_profile_id_is_400_on_get(client, monkeypatch, path, pid):
    monkeypatch.setattr(store, "migrate", lambda: None)
    r = client.get(f"/api/navigator/{path}?profile_id={pid}")
    assert r.status_code == 400
    assert r.get_json() == {"error": "profile_id must be a positive integer"}


def test_zero_profile_id_is_400_on_post(client, monkeypatch):
    monkeypatch.setattr(store, "migrate", lambda: None)
    r = client.post("/api/navigator/backtest", json={"profile_id": 0})
    assert r.status_code == 400
    assert r.get_json() == {"error": "profile_id must be a positive integer"}


@pg
def test_client_cannot_set_is_sample(client, db):
    r = client.post("/api/navigator/profile", json={**GOOD, "is_sample": True})
    assert r.status_code == 201
    assert r.get_json()["is_sample"] is False
    assert store.get_profile(r.get_json()["id"]).is_sample is False


@pg
def test_list_has_only_id_label_sample_and_seeds_the_sample(client, db):
    pid = _profile(client)
    rows = client.get("/api/navigator/profile").get_json()["profiles"]
    assert pid in {r["id"] for r in rows}
    assert any(r["is_sample"] for r in rows)
    assert all(set(r) == {"id", "label", "is_sample"} for r in rows)


@pg
def test_profile_detail_returns_birth_fields_without_hash(client, db):
    pid = _profile(client)
    body = client.get(f"/api/navigator/profile?profile_id={pid}").get_json()
    assert body["birth_date"] == GOOD["birth_date"] and body["lat"] == GOOD["lat"]
    assert "chart_hash" not in body


@pg
@pytest.mark.parametrize("path", ["profile", "chart", "score"])
@pytest.mark.parametrize("pid", ["999999", "999999999999999999"])
def test_unknown_profile_404(client, db, path, pid):
    assert client.get(f"/api/navigator/{path}?profile_id={pid}").status_code == 404


@pytest.mark.parametrize("path", ["chart", "score"])
@pytest.mark.parametrize("pid", ["abc", "-1", "", "1e3", "9" * 5000])
def test_malformed_profile_id_400(client, monkeypatch, path, pid):
    monkeypatch.setattr(store, "migrate", lambda: None)
    assert client.get(f"/api/navigator/{path}?profile_id={pid}").status_code == 400


def test_chart_requires_profile_id(client, monkeypatch):
    monkeypatch.setattr(store, "migrate", lambda: None)
    assert client.get("/api/navigator/chart").status_code == 400


@pg
def test_chart_rows(client, db):
    pid = store.ensure_sample()
    body = client.get(f"/api/navigator/chart?profile_id={pid}").get_json()
    names = [p["name"] for p in body["points"]]
    assert "Moon" in names and "Lagna" in names and "Uranus" not in names
    assert all(p["sign"] and 0 <= p["longitude"] < 360 for p in body["points"])
    assert body["is_sample"] is True
    assert chart_hash(SAMPLE_PROFILE) not in json.dumps(body)


# ---- score --------------------------------------------------------------------
@pg
def test_score_lineage_sums_and_is_cached(client, db, market, monkeypatch):
    pid = store.ensure_sample()
    day = market[-3]["date"]
    r = client.get(f"/api/navigator/score?profile_id={pid}&day={day}")
    body = r.get_json()
    assert r.status_code == 200 and body["cached"] is False
    total = sum(c["contribution"] for c in body["lineage"]["contributions"])
    assert total == pytest.approx(body["score"], abs=1e-9)
    assert body["band"] and body["action"]
    assert body["status"] == "unvalidated research output"
    assert "not personal financial advice" in body["disclaimer"]
    assert body["future"] is False and body["vol_neutral"] is False
    assert len(_rows("select 1 from daily_score")) == 1

    monkeypatch.setattr(bp, "build_sky", lambda d: pytest.fail("cache hit must not recompute"))
    again = client.get(f"/api/navigator/score?profile_id={pid}&day={day}").get_json()
    assert again["cached"] is True
    keys = ("score", "band", "action", "lineage", "vol_neutral")
    assert {k: again[k] for k in keys} == {k: body[k] for k in keys}


@pg
@pytest.mark.parametrize("field,value", [("data_asof", "2001-01-01"), ("weights_version", "old"),
                                         ("engine_version", "old"), ("chart_hash", "old")])
def test_cache_needs_every_key_field(client, db, market, field, value):
    pid = store.ensure_sample()
    url = f"/api/navigator/score?profile_id={pid}&day={market[-3]['date']}"
    client.get(url)
    with store.connect() as c:
        c.execute("update daily_score set score=7, " + field + "=%s", (value,))
    body = client.get(url).get_json()
    assert body["cached"] is False and body["score"] != 7


@pytest.fixture
def nov4(monkeypatch):
    """NIFTY through 2026-11-04 while VIX stops at 11-02, so that day's T-1 close is missing."""
    nifty = [b for b in _bars(1100, "2023-01-02") if b["date"] <= "2026-11-04"]
    box = {"vix": [b for b in _bars(1400, "2022-01-03") if b["date"] <= "2026-11-02"]}

    def get_daily(symbol, start=None, end=None):
        return nifty if symbol == "NIFTY" else box["vix"]
    monkeypatch.setattr(market_store, "get_daily", get_daily)

    def backfill():
        box["vix"] = [b for b in _bars(1400, "2022-01-03") if b["date"] <= "2026-11-03"]
    return backfill


@pg
def test_neutral_vol_is_never_cached_and_backfill_gives_real_vol(client, db, nov4):
    pid = store.ensure_sample()
    url = f"/api/navigator/score?profile_id={pid}&day=2026-11-04"
    stale = client.get(url).get_json()
    assert stale["data_asof"] == "2026-11-04" and stale["vol_neutral"] is True
    assert _rows("select 1 from daily_score") == []
    assert client.get(url).get_json()["cached"] is False

    nov4()
    fresh = client.get(url).get_json()
    assert fresh["vol_neutral"] is False and fresh["cached"] is False
    assert len(_rows("select 1 from daily_score")) == 1
    assert client.get(url).get_json()["cached"] is True


@pg
def test_vix_backfill_misses_a_row_cached_before_it(client, db, nov4):
    pid = store.ensure_sample()
    url = f"/api/navigator/score?profile_id={pid}&day=2026-11-03"
    assert client.get(url).get_json()["vol_neutral"] is False   # its T-1 close exists
    assert client.get(url).get_json()["cached"] is True
    nov4()
    assert client.get(url).get_json()["cached"] is False


@pg
@pytest.mark.parametrize("missing", [None, float("nan")])
def test_data_asof_is_the_last_session_with_a_close(client, db, market, missing):
    good = market[-1]["date"]
    market.append({**market[-1], "date": "2026-01-05", "close": missing})
    pid = store.ensure_sample()
    body = client.get(f"/api/navigator/score?profile_id={pid}&day={good}").get_json()
    assert body["data_asof"] == good and body["future"] is False


def test_no_nifty_close_at_all_is_no_market_data(monkeypatch):
    bars = [{**b, "close": None} for b in _bars(3)]
    monkeypatch.setattr(market_store, "get_daily", lambda *a, **k: bars)
    with pytest.raises(bp._NoMarketData):
        bp._market()


@pg
def test_future_day_not_stored_and_vol_neutral_flagged(client, db, market):
    pid = store.ensure_sample()
    r = client.get(f"/api/navigator/score?profile_id={pid}&day=2099-06-01")
    body = r.get_json()
    assert r.status_code == 200 and body["future"] is True and body["vol_neutral"] is True
    vol = next(c for c in body["lineage"]["contributions"] if c["term"] == "vol")
    assert vol["raw"] == 50.0 and vol["factors"][0]["neutral"] is True
    assert _rows("select 1 from daily_score") == []


@pg
def test_next_session_after_data_is_also_future(client, db, market):
    pid = store.ensure_sample()
    day = str(np.busday_offset(market[-1]["date"], 1))[:10]
    body = client.get(f"/api/navigator/score?profile_id={pid}&day={day}").get_json()
    assert body["future"] is True and body["vol_neutral"] is True
    assert _rows("select 1 from daily_score") == []


@pg
def test_past_non_session_400(client, db, market):
    pid = store.ensure_sample()
    assert client.get(f"/api/navigator/score?profile_id={pid}&day=2020-01-04").status_code == 400


@pytest.mark.parametrize("day", ["2026-13-01", "garbage", "20260101", "2026-1-1", "9999-01-01"])
def test_malformed_day_400(client, monkeypatch, day):
    monkeypatch.setattr(store, "migrate", lambda: None)
    r = client.get(f"/api/navigator/score?profile_id=1&day={day}")
    assert r.status_code == 400 and day.encode() not in r.data


@pg
def test_missing_market_data_is_503(client, db, monkeypatch):
    monkeypatch.setattr(market_store, "get_daily", lambda *a, **k: [])
    pid = store.ensure_sample()
    r = client.get(f"/api/navigator/score?profile_id={pid}")
    assert r.status_code == 503 and "market data" in r.get_json()["error"].lower()


# ---- backtest -----------------------------------------------------------------
@pg
def test_backtest_runs_to_done_and_hides_hash(client, db, market, monkeypatch):
    monkeypatch.setitem(B.DEFAULT_PARAMS, "n_placebo", 2)
    monkeypatch.setitem(B.DEFAULT_PARAMS, "n_perm", 20)
    pid = store.ensure_sample()
    r = client.post("/api/navigator/backtest", json={"profile_id": pid})
    assert r.status_code == 202 and r.get_json()["is_new"] is True
    body = _wait(client, r.get_json()["run_id"])
    assert body["results"]["label"] == "Sample chart: pipeline check only"
    assert body["label"] == "Sample chart: pipeline check only"
    assert body["results"]["verdict"] == B.NO_EDGE
    assert body["folds"] and "folds" not in body["results"]
    assert "chart_hash" not in json.dumps(body)
    assert chart_hash(SAMPLE_PROFILE) not in json.dumps(body)
    meta = _rows("select data_asof::text, weights_version, chart_hash from backtest_run")[0]
    assert meta == (market[-1]["date"], "nav-1", chart_hash(SAMPLE_PROFILE))


@pg
def test_repeat_post_returns_active_run_without_a_second_thread(client, db, market, monkeypatch):
    pid = store.ensure_sample()
    started = []
    monkeypatch.setattr(bp, "_start_job", lambda *a: started.append(a))
    first = client.post("/api/navigator/backtest", json={"profile_id": pid}).get_json()
    second = client.post("/api/navigator/backtest", json={"profile_id": pid}).get_json()
    assert first["run_id"] == second["run_id"] and second["is_new"] is False
    assert len(started) == 1


@pg
def test_post_expires_a_dead_run_first(client, db, market, monkeypatch):
    pid = store.ensure_sample()
    monkeypatch.setattr(bp, "_start_job", lambda *a: None)
    old = client.post("/api/navigator/backtest", json={"profile_id": pid}).get_json()["run_id"]
    with store.connect() as c:
        c.execute("update backtest_run set heartbeat_at=now()-interval '1 hour'")
    new = client.post("/api/navigator/backtest", json={"profile_id": pid}).get_json()
    assert new["is_new"] is True and new["run_id"] != old


@pg
def test_get_expires_a_dead_run(client, db, market, monkeypatch):
    pid = store.ensure_sample()
    monkeypatch.setattr(bp, "_start_job", lambda *a: None)
    run = client.post("/api/navigator/backtest", json={"profile_id": pid}).get_json()["run_id"]
    with store.connect() as c:
        c.execute("update backtest_run set heartbeat_at=now()-interval '1 hour'")
    assert client.get(f"/api/navigator/backtest/{run}").get_json()["status"] == "failed"


@pg
def test_failure_stores_generic_message_only(client, db, market, monkeypatch, caplog):
    def boom(*a, **k):
        raise RuntimeError("1971-03-04 leaked")
    monkeypatch.setattr(B, "run", boom)
    caplog.set_level(logging.DEBUG)
    pid = _profile(client)
    run = client.post("/api/navigator/backtest", json={"profile_id": pid}).get_json()["run_id"]
    body = _wait(client, run, "failed")
    assert body["error"] == bp.RUN_FAILED and "1971" not in json.dumps(body)
    assert "1971-03-04" not in caplog.text


@pg
def test_thread_start_failure_marks_run_failed_and_is_a_fixed_500(client, db, market, monkeypatch):
    def boom(*a):
        raise RuntimeError("no thread 1971-03-04")
    monkeypatch.setattr(bp.threading.Thread, "start", boom)
    pid = store.ensure_sample()
    r = client.post("/api/navigator/backtest", json={"profile_id": pid})
    assert r.status_code == 500
    assert r.get_json() == {"error": bp.RUN_NOT_STARTED}
    assert _rows("select status, error from backtest_run") == [("failed", bp.RUN_FAILED)]


def test_thread_start_failure_is_a_fixed_500_even_if_the_store_then_fails(client, monkeypatch):
    def boom(*a):
        raise RuntimeError("1971-03-04")

    def fail(*a):
        raise psycopg.OperationalError("password=hunter2")
    monkeypatch.setattr(store, "migrate", lambda: None)
    monkeypatch.setattr(store, "get_profile", lambda i: SAMPLE_PROFILE)
    monkeypatch.setattr(store, "expire_stale", lambda: None)
    monkeypatch.setattr(store, "start_run", lambda *a: (5, True))
    monkeypatch.setattr(store, "fail_run", fail)
    monkeypatch.setattr(bp, "_start_job", boom)
    monkeypatch.setattr(bp, "_market", lambda: (bp.pd.DataFrame({"date": ["2026-01-01"]}), {}))
    r = client.post("/api/navigator/backtest", json={"profile_id": 1})
    assert r.status_code == 500 and r.get_json() == {"error": bp.RUN_NOT_STARTED}


@pytest.mark.parametrize("error", [RuntimeError, psycopg.OperationalError, store.StoreUnavailable])
def test_job_fail_run_guard_logs_only_the_type(monkeypatch, caplog, error):
    def run(*a, **k):
        raise ValueError("1971-03-04 first")

    def fail(*a):
        raise error("1971-03-04 second")
    monkeypatch.setattr(store, "heartbeat", lambda i: True)
    monkeypatch.setattr(B, "run", run)
    monkeypatch.setattr(store, "fail_run", fail)
    caplog.set_level(logging.DEBUG)
    bp._job(7, SAMPLE_PROFILE, None, {})     # nothing reaches threading.excepthook
    assert "1971-03-04" not in caplog.text
    assert error.__name__ in caplog.text


@pg
def test_run_stops_when_heartbeat_says_expired(client, db, market, monkeypatch):
    seen, box = [], []

    def fake(profile, ohlc, vix, on_progress=None, **k):
        store.fail_run(box[0], "run stopped reporting")
        on_progress(1, 10)
        seen.append("kept going")
        return {}
    monkeypatch.setattr(B, "run", fake)
    monkeypatch.setattr(bp, "_start_job", lambda *a: None)
    pid = store.ensure_sample()
    box.append(client.post("/api/navigator/backtest", json={"profile_id": pid}).get_json()["run_id"])
    bp._job(box[0], store.get_profile(pid), *bp._market())
    assert seen == []
    row = store.get_run(box[0])
    assert row["status"] == "failed" and row["error"] == "run stopped reporting"


@pg
def test_numpy_results_reach_finish_as_plain_json(client, db, market, monkeypatch):
    monkeypatch.setattr(B, "run", lambda *a, **k: {
        "n": np.int64(3), "x": np.float64(1.5), "nan": np.float64("nan"), "ok": np.bool_(True),
        "folds": [{"sessions": np.int32(2)}]})
    pid = store.ensure_sample()
    run = client.post("/api/navigator/backtest", json={"profile_id": pid}).get_json()["run_id"]
    body = _wait(client, run)
    assert body["results"]["n"] == 3 and body["results"]["nan"] is None
    assert body["folds"] == [{"sessions": 2}]


@pg
@pytest.mark.parametrize("payload", [{"profile_id": "1"}, {"profile_id": True}, {},
                                     {"profile_id": -1}, [1]])
def test_backtest_bad_profile_id_400(client, db, payload):
    assert client.post("/api/navigator/backtest", json=payload).status_code == 400


@pg
def test_backtest_unknown_profile_404_and_no_run(client, db, market):
    assert client.post("/api/navigator/backtest", json={"profile_id": 999999}).status_code == 404
    assert _rows("select 1 from backtest_run") == []


@pg
@pytest.mark.parametrize("run", ["999999", "9" * 30])
def test_unknown_run_404(client, db, run):
    assert client.get(f"/api/navigator/backtest/{run}").status_code == 404


@pg
def test_latest_backtest_matches_the_run_read(client, db, market, monkeypatch):
    monkeypatch.setitem(B.DEFAULT_PARAMS, "n_placebo", 2)
    monkeypatch.setitem(B.DEFAULT_PARAMS, "n_perm", 20)
    pid = store.ensure_sample()
    assert client.get(f"/api/navigator/backtest/latest?profile_id={pid}").status_code == 404
    run = client.post("/api/navigator/backtest", json={"profile_id": pid}).get_json()["run_id"]
    by_id = _wait(client, run)
    r = client.get(f"/api/navigator/backtest/latest?profile_id={pid}")
    assert r.status_code == 200 and r.get_json() == by_id
    assert "chart_hash" not in r.get_data(as_text=True)
    assert "engine_version" not in r.get_json() and "heartbeat_at" not in r.get_json()


@pg
def test_latest_backtest_unknown_profile_404(client, db):
    assert client.get("/api/navigator/backtest/latest?profile_id=999").status_code == 404


@pytest.mark.parametrize("q", ["", "?profile_id=0", "?profile_id=abc", "?profile_id=" + "9" * 30])
def test_latest_backtest_bad_profile_id_400(client, monkeypatch, q):
    _down(monkeypatch)
    monkeypatch.setattr(bp, "_migrated", True)
    assert client.get(f"/api/navigator/backtest/latest{q}").status_code == 400


# ---- privacy ------------------------------------------------------------------
@pg
def test_birth_values_absent_from_logs(client, db, market, caplog):
    caplog.set_level(logging.DEBUG)
    pid = _profile(client)
    assert client.post("/api/navigator/profile", json={**GOOD, "lat": 500}).status_code == 400
    client.get(f"/api/navigator/chart?profile_id={pid}")
    client.get(f"/api/navigator/score?profile_id={pid}&day={market[-2]['date']}")
    for value in BIRTH_VALUES:
        assert value not in caplog.text


# ---- latest verdict beside the action label -------------------------------------
def _score_body(client, pid, market):
    r = client.get(f"/api/navigator/score?profile_id={pid}&day={market[-3]['date']}")
    assert r.status_code == 200
    return r.get_json()


@pg
def test_score_says_no_backtest_yet(client, db, market):
    body = _score_body(client, store.ensure_sample(), market)
    assert body["latest_verdict"] == {"available": True, "run_id": None, "verdict": None,
                                      "status": None, "data_asof": None, "stale": False,
                                      "text": "no backtest yet"}


@pg
def test_score_carries_the_latest_run_verdict_without_chart_hash(client, db, market, monkeypatch):
    pid = store.ensure_sample()
    run = {"id": 7, "profile_id": pid, "status": "done", "data_asof": "2023-05-01",
           "weights_version": bp.WEIGHTS_VERSION, "engine_version": bp._version(),
           "chart_hash": "secret-hash", "results": {"verdict": "no demonstrated edge"}}
    monkeypatch.setattr(store, "latest_run", lambda i: run if i == pid else None)
    body = _score_body(client, pid, market)
    v = body["latest_verdict"]
    assert v["available"] and v["run_id"] == 7 and v["verdict"] == "no demonstrated edge"
    assert v["status"] == "done" and v["data_asof"] == "2023-05-01" and v["stale"] is False
    assert "secret-hash" not in json.dumps(body) and "chart_hash" not in json.dumps(body)


@pg
@pytest.mark.parametrize("field", ["weights_version", "engine_version"])
def test_score_flags_a_stale_latest_run(client, db, market, monkeypatch, field):
    pid = store.ensure_sample()
    run = {"id": 3, "status": "done", "data_asof": "2023-05-01", "chart_hash": "h",
           "weights_version": bp.WEIGHTS_VERSION, "engine_version": bp._version(),
           "results": {"verdict": "no demonstrated edge"}, field: "old"}
    monkeypatch.setattr(store, "latest_run", lambda i: run)
    v = _score_body(client, pid, market)["latest_verdict"]
    assert v["stale"] is True and "stale" in v["text"]


@pg
def test_score_survives_a_latest_run_failure(client, db, market, monkeypatch):
    pid = store.ensure_sample()

    def boom(i):
        raise store.StoreUnavailable("x")
    monkeypatch.setattr(store, "latest_run", boom)
    body = _score_body(client, pid, market)
    assert body["score"] is not None
    assert body["latest_verdict"]["available"] is False
    assert body["latest_verdict"]["text"] == "verdict unavailable"


# ---- Phase 4: similar dates (/analogs) ----
FAKE_ANALOGS = {"version": "nav-analog-1", "data_asof": "2026-11-06", "window": {}, "mode": "top_scores",
                "targets": [], "notes": ["n"]}


@pytest.fixture
def analog_state(monkeypatch):
    monkeypatch.setattr(bp, "_analog_cache", bp.OrderedDict())
    monkeypatch.setattr(bp, "_analog_lock", _threading.Lock())
    market = A.Market(["2026-11-05", "2026-11-06"], {}, {})
    monkeypatch.setattr(A, "load_market", lambda: market)
    calls = []

    def fake_build(profile, mkt, days=30, **_):
        calls.append((profile.label, mkt.dates[-1], days))
        return {**FAKE_ANALOGS, "notes": ["n"]}
    monkeypatch.setattr(A, "build", fake_build)
    return {"market": market, "calls": calls}


def test_analogs_guarded(client, monkeypatch):
    _down(monkeypatch)
    r = client.get("/api/navigator/analogs?profile_id=1", headers={"X-Forwarded-For": "8.8.8.8"})
    assert r.status_code == 403


@pytest.mark.parametrize("days", ["4", "61", "x", "30.5", "", "-10", "0x10"])
def test_analogs_bad_days_400(client, monkeypatch, days):
    monkeypatch.setattr(store, "migrate", lambda: None)
    _down(monkeypatch)    # rejected before any store read
    r = client.get(f"/api/navigator/analogs?profile_id=1&days={days}")
    assert r.status_code == 400
    assert r.get_json() == {"error": "days must be an integer from 5 to 60"}


def test_analogs_store_down_503(client, monkeypatch):
    _down(monkeypatch)
    assert client.get("/api/navigator/analogs?profile_id=1").status_code == 503


@pg
def test_analogs_unknown_profile_404(client, db, analog_state):
    assert client.get("/api/navigator/analogs?profile_id=999").status_code == 404


@pg
def test_analogs_busy_429_without_blocking(client, db, analog_state):
    pid = _profile(client)
    assert bp._analog_lock.acquire()
    try:
        t0 = time.time()
        r = client.get(f"/api/navigator/analogs?profile_id={pid}")
        assert time.time() - t0 < 5
        assert r.status_code == 429 and r.get_json() == {"error": bp.ANALOGS_BUSY}
    finally:
        bp._analog_lock.release()
    assert client.get(f"/api/navigator/analogs?profile_id={pid}").status_code == 200


@pg
def test_analogs_cached_result_served_while_another_build_runs(client, db, analog_state):
    pid = _profile(client)
    url = f"/api/navigator/analogs?profile_id={pid}&days=10"
    assert client.get(url).status_code == 200
    assert bp._analog_lock.acquire()          # another computation is in flight
    try:
        r = client.get(url)
        assert r.status_code == 200 and r.get_json()["cached"] is True
        assert client.get(f"/api/navigator/analogs?profile_id={pid}&days=11").status_code == 429
    finally:
        bp._analog_lock.release()


@pg
def test_analogs_lock_released_after_error_and_error_not_cached(client, db, analog_state, monkeypatch, caplog):
    pid = _profile(client)
    def boom(*a, **k):
        raise ValueError("secret 12.3456")
    monkeypatch.setattr(A, "build", boom)
    with caplog.at_level(logging.ERROR):
        r = client.get(f"/api/navigator/analogs?profile_id={pid}")
    assert r.status_code == 500 and "12.3456" not in caplog.text and "ValueError" in caplog.text
    assert not bp._analog_lock.locked() and len(bp._analog_cache) == 0


@pg
def test_analogs_cache_hits_and_key_parts(client, db, analog_state, monkeypatch):
    pid = _profile(client)
    calls = analog_state["calls"]
    url = f"/api/navigator/analogs?profile_id={pid}&days=10"
    a = client.get(url).get_json()
    b = client.get(url).get_json()
    assert len(calls) == 1 and a["cached"] is False and b["cached"] is True
    assert any("Computed in" in n and "seconds" in n for n in a["notes"]) and not any("cached" in n for n in a["notes"])
    assert any("seconds (cached result)" in n for n in b["notes"]) and not any("seconds." in n for n in b["notes"])
    assert a["notes"] == ["n", a["notes"][1]] and len(b["notes"]) == 2
    client.get(f"/api/navigator/analogs?profile_id={pid}&days=11")
    assert len(calls) == 2
    analog_state["market"].dates.append("2026-11-09")       # data date
    client.get(url)
    assert len(calls) == 3
    monkeypatch.setattr(bp.G, "ANALOG_VERSION", "nav-analog-2")
    client.get(url)
    assert len(calls) == 4
    monkeypatch.setattr(bp, "_version", lambda: "other-engine")
    client.get(url)
    assert len(calls) == 5
    monkeypatch.setattr(bp, "_analog_version", lambda: "other-analogs")   # analogs.py / signature.py closure
    client.get(url)
    assert len(calls) == 6
    monkeypatch.setattr(bp, "chart_hash", lambda p: "other-chart")
    client.get(url)
    assert len(calls) == 7
    pid2 = _profile(client, label="Two")
    client.get(f"/api/navigator/analogs?profile_id={pid2}&days=10")
    assert len(calls) == 8


def test_analog_version_covers_analogs_and_signature():
    from sbc.engine_version import module_closure, ROOT, _read
    rel = {p.relative_to(ROOT).as_posix() for p in module_closure({"sbc.navigator.analogs"}, _read, frozenset())}
    assert {"sbc/navigator/analogs.py", "sbc/navigator/signature.py"} <= rel
    assert bp._analog_version() == bp.module_version("sbc.navigator.analogs")


@pg
def test_analogs_cache_holds_at_most_8(client, db, analog_state):
    pid = _profile(client)
    for d in range(5, 15):
        client.get(f"/api/navigator/analogs?profile_id={pid}&days={d}")
    assert len(bp._analog_cache) == 8


def _walk(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield ("key", k)
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)
    else:
        yield ("value", obj)


@pg
def test_analogs_real_run_redacted(client, db, synthetic, monkeypatch):
    market, sky, fp = synthetic
    monkeypatch.setattr(bp, "_analog_cache", bp.OrderedDict())
    monkeypatch.setattr(A, "load_market", lambda: market)
    real = A.build
    monkeypatch.setattr(A, "build", lambda p, m, days=30: real(p, m, days, sky_history=sky, fingerprint_fn=fp))
    pid = _profile(client)
    r = client.get(f"/api/navigator/analogs?profile_id={pid}&days=5")
    assert r.status_code == 200
    body = r.get_json()
    assert body["targets"] and body["version"] == "nav-analog-1"
    banned = {"chart_hash", "birth_date", "birth_time", "tz", "lat", "lon", "natal", "longitude",
              "longitudes", "natal_points"}
    items = list(_walk(body))
    keys = {v for kind, v in items if kind == "key"}
    assert not keys & (banned - {"natal"})
    for kind, v in items:
        if kind == "value" and isinstance(v, (int, float, str)) and not isinstance(v, bool):
            assert str(v) not in BIRTH_VALUES and v not in (12.3456, 76.5432)
    assert any("seconds" in n for n in body["notes"])
    ends = A.data_coverage_note(A.load_market())      # derived from the loaded data, not hard-coded
    assert ends in body["notes"] and any("VIX starts 2008-03" in n for n in body["notes"])
