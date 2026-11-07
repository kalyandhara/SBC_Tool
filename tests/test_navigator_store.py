import os
import subprocess
import sys
from pathlib import Path

import pytest

from sbc.navigator import store

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_connect_without_url_raises_unavailable(monkeypatch):
    monkeypatch.delenv("NAV_DATABASE_URL", raising=False)
    with pytest.raises(store.StoreUnavailable):
        store.connect()


@pytest.mark.parametrize(
    "url, message",
    [
        ("postgresql://x:s3cretpw@127.0.0.1:1/none", "Postgres is unreachable"),
        ("postgresql://x:s3cretpw@[bad/none", "NAV_DATABASE_URL is invalid"),
        ("postgresql://x:p%zzs3cretpw@127.0.0.1:1/n", "NAV_DATABASE_URL is invalid"),
    ],
    ids=["unreachable", "malformed", "bad-percent-encoding"],
)
def test_connect_failure_carries_no_trace_of_the_url(monkeypatch, url, message):
    monkeypatch.setenv("NAV_DATABASE_URL", url)
    with pytest.raises(store.StoreUnavailable) as exc:
        store.connect()
    assert str(exc.value) == message
    assert "s3cretpw" not in repr(exc.value)
    # Both links must be empty: `from None` alone keeps the original on __context__.
    assert exc.value.__context__ is None
    assert exc.value.__cause__ is None


def test_app_boot_does_not_touch_postgres(monkeypatch):
    import psycopg

    calls = []
    monkeypatch.setattr(psycopg, "connect", lambda *a, **k: calls.append((a, k)))
    monkeypatch.setenv("NAV_DATABASE_URL", "postgresql://x:y@127.0.0.1:1/none")
    from sbc.app_factory import create_app

    app = create_app()
    assert calls == []
    assert any(r.rule == "/healthz" for r in app.url_map.iter_rules())


def test_importing_store_does_not_touch_postgres():
    # Fresh interpreter: psycopg.connect is patched before the store is imported.
    script = "; ".join(
        [
            "import psycopg",
            "calls = []",
            "psycopg.connect = lambda *a, **k: calls.append((a, k))",
            "import sbc.navigator.store",
            "print('calls=%d' % len(calls))",
        ]
    )
    env = {**os.environ, "NAV_DATABASE_URL": "postgresql://x:y@127.0.0.1:1/none"}
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "calls=0"


@pytest.mark.skipif(not os.environ.get("NAV_TEST_DATABASE_URL"), reason="needs Postgres")
def test_migrate_is_idempotent(monkeypatch):
    monkeypatch.setenv("NAV_DATABASE_URL", os.environ["NAV_TEST_DATABASE_URL"])
    store.migrate()
    store.migrate()
    with store.connect() as c:
        assert c.execute(
            "select count(*) from information_schema.tables where table_name='backtest_run'"
        ).fetchone()[0] == 1


# ---- Task 8: queries and job state (real Postgres; the db fixture truncates) ----
import math  # noqa: E402

from sbc.navigator.profile import SAMPLE_PROFILE, Profile  # noqa: E402

pg = pytest.mark.skipif(not os.environ.get("NAV_TEST_DATABASE_URL"), reason="needs Postgres")

META = dict(instrument="NIFTY", weights_version="w", data_asof="2026-01-01",
            engine_version="e", chart_hash="h", params={})
KEY_COLUMNS = ("profile_id", "day", "weights_version", "data_asof", "engine_version", "chart_hash")


@pytest.fixture
def db(monkeypatch):
    """Only ever points at NAV_TEST_DATABASE_URL; truncates before and after."""
    test_url = os.environ["NAV_TEST_DATABASE_URL"]
    from psycopg.conninfo import conninfo_to_dict

    live = os.environ.get("NAV_DATABASE_URL", "")
    assert not live or conninfo_to_dict(live).get("dbname") != conninfo_to_dict(test_url).get(
        "dbname"), "NAV_DATABASE_URL names the test database; refusing to truncate a live database"
    monkeypatch.setenv("NAV_DATABASE_URL", test_url)
    store.migrate()

    def wipe():
        with store.connect() as c:
            c.execute("truncate natal_profile, daily_score, backtest_run restart identity cascade")

    wipe()
    yield
    wipe()


def _key(pid, **over):
    return {**dict(profile_id=pid, day="2026-01-05", weights_version="w",
                   data_asof="2026-01-02", engine_version="e", chart_hash="h"), **over}


@pg
def test_single_active_run(db):
    pid = store.ensure_sample()
    a, new = store.start_run(pid, META)
    b, again = store.start_run(pid, META)
    assert new and not again and a == b


@pg
def test_new_run_allowed_after_finish(db):
    pid = store.ensure_sample()
    a, _ = store.start_run(pid, META)
    store.finish_run(a, {"x": 1}, [])
    b, new = store.start_run(pid, META)
    assert new and b != a


@pg
def test_stale_run_fails(db):
    pid = store.ensure_sample()
    rid, _ = store.start_run(pid, META)
    with store.connect() as c:
        c.execute("update backtest_run set heartbeat_at=now()-interval '1 hour' where id=%s", (rid,))
    store.expire_stale(120)
    run = store.get_run(rid)
    assert run["status"] == "failed" and run["error"] == "run stopped reporting"


@pg
def test_stale_run_without_heartbeat_uses_created_at(db):
    pid = store.ensure_sample()
    rid, _ = store.start_run(pid, META)
    with store.connect() as c:
        c.execute("update backtest_run set heartbeat_at=null, created_at=now()-interval '1 hour' "
                  "where id=%s", (rid,))
    store.expire_stale(120)
    assert store.get_run(rid)["status"] == "failed"


@pg
def test_fresh_and_finished_runs_are_not_expired(db):
    pid = store.ensure_sample()
    rid, _ = store.start_run(pid, META)
    store.heartbeat(rid)
    store.expire_stale(120)
    assert store.get_run(rid)["status"] == "running"
    store.finish_run(rid, {"v": 1}, [])
    with store.connect() as c:
        c.execute("update backtest_run set heartbeat_at=now()-interval '1 hour' where id=%s", (rid,))
    store.expire_stale(120)
    assert store.get_run(rid)["status"] == "done"


@pg
def test_finish_run_roundtrips_none_and_rejects_nan(db):
    pid = store.ensure_sample()
    rid, _ = store.start_run(pid, META)
    with pytest.raises(ValueError):
        store.finish_run(rid, {"p": math.nan}, [])
    assert store.get_run(rid)["status"] in ("queued", "running")
    store.finish_run(rid, {"p": None, "n": [1, None]}, [{"fold": 1, "edge": None}])
    run = store.get_run(rid)
    assert run["status"] == "done"
    assert run["results"] == {"p": None, "n": [1, None]}
    assert run["folds"] == [{"fold": 1, "edge": None}]


@pg
def test_fail_run_and_get_run_missing(db):
    pid = store.ensure_sample()
    rid, _ = store.start_run(pid, META)
    store.fail_run(rid, "boom")
    run = store.get_run(rid)
    assert run["status"] == "failed" and run["error"] == "boom"
    assert store.get_run(10**9) is None
    # a failed run frees the slot
    assert store.start_run(pid, META)[1] is True


@pg
def test_late_finish_does_not_resurrect_expired_run(db):
    pid = store.ensure_sample()
    rid, _ = store.start_run(pid, META)
    with store.connect() as c:
        c.execute("update backtest_run set heartbeat_at=now()-interval '1 hour' where id=%s", (rid,))
    store.expire_stale(120)
    store.finish_run(rid, {"v": 1}, [])
    assert store.get_run(rid)["status"] == "failed"


@pg
def test_cache_key_includes_data_asof(db):
    pid = store.ensure_sample()
    key = _key(pid)
    store.save_score(key, dict(score=55, band="Normal", action="Reduce Position Size", lineage={}))
    assert store.cached_score(key)["score"] == 55
    assert store.cached_score({**key, "data_asof": "2026-01-03"}) is None


@pg
@pytest.mark.parametrize("col", KEY_COLUMNS)
def test_every_key_column_participates(db, col):
    pid = store.ensure_sample()
    other = store.create_profile(Profile("Other", False, "1990-02-03", "04:05:06", "UTC", 1.0, 2.0))
    alt = {"profile_id": other, "day": "2026-01-06", "weights_version": "w2",
           "data_asof": "2026-01-03", "engine_version": "e2", "chart_hash": "h2"}
    key = _key(pid)
    store.save_score(key, dict(score=1, band="b", action="a", lineage={}))
    assert store.cached_score({**key, col: alt[col]}) is None


@pg
def test_save_score_overwrites_same_key(db):
    pid = store.ensure_sample()
    key = _key(pid)
    store.save_score(key, dict(score=1, band="b", action="a", lineage={"k": None}))
    store.save_score(key, dict(score=2.5, band="c", action="d", lineage={"k": 1}))
    got = store.cached_score(key)
    assert (got["score"], got["band"], got["action"], got["lineage"]) == (2.5, "c", "d", {"k": 1})


@pg
def test_profile_roundtrip_and_listing(db):
    p = Profile("Mine", False, "1990-02-03", "04:05:06", "Asia/Kolkata", 12.5, 77.25)
    pid = store.create_profile(p)
    assert store.get_profile(pid) == p
    assert store.get_profile(10**9) is None
    assert store.list_profiles() == [{"id": pid, "label": "Mine", "is_sample": False}]
    assert "1990" not in repr(store.get_profile(pid))


@pg
def test_ensure_sample_is_idempotent(db):
    a, b = store.ensure_sample(), store.ensure_sample()
    assert a == b
    assert store.get_profile(a) == SAMPLE_PROFILE
    assert [x["id"] for x in store.list_profiles() if x["is_sample"]] == [a]


@pg
def test_query_errors_do_not_leak_connection_text(db):
    with pytest.raises(store.StoreUnavailable) as exc:
        store.start_run(10**9, META)  # foreign key violation
    assert exc.value.__context__ is None and exc.value.__cause__ is None
    assert "profile_id" not in str(exc.value)


def test_driver_error_text_never_escapes(monkeypatch):
    import psycopg

    class Boom:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, *a, **k):
            raise psycopg.OperationalError("connection to host failed password=s3cretpw")

    monkeypatch.setattr(store, "connect", lambda: Boom())
    with pytest.raises(store.StoreUnavailable) as exc:
        store.get_run(1)
    assert "s3cretpw" not in repr(exc.value) and "s3cretpw" not in str(exc.value)
    assert exc.value.__context__ is None and exc.value.__cause__ is None


@pg
@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_save_score_rejects_non_finite_and_stores_nothing(db, bad):
    pid = store.ensure_sample()
    key = _key(pid)
    with pytest.raises(ValueError):
        store.save_score(key, dict(score=bad, band="b", action="a", lineage={}))
    with store.connect() as c:
        assert c.execute("select count(*) from daily_score").fetchone()[0] == 0


@pg
def test_heartbeat_and_finish_report_whether_a_row_matched(db):
    pid = store.ensure_sample()
    rid, _ = store.start_run(pid, META)
    assert store.heartbeat(rid) is True
    with store.connect() as c:
        c.execute("update backtest_run set heartbeat_at=now()-interval '1 hour' where id=%s", (rid,))
    store.expire_stale(120)
    assert store.heartbeat(rid) is False
    assert store.finish_run(rid, {"v": 1}, []) is False
    rid2, _ = store.start_run(pid, META)
    assert store.finish_run(rid2, {"v": 1}, []) is True
    assert store.finish_run(10**9, {}, []) is False
