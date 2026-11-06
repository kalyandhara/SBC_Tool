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
