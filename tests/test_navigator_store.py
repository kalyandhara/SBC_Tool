import os

import pytest

from sbc.navigator import store


def test_connect_without_url_raises_unavailable(monkeypatch):
    monkeypatch.delenv("NAV_DATABASE_URL", raising=False)
    with pytest.raises(store.StoreUnavailable):
        store.connect()


def test_unreachable_error_does_not_leak_password(monkeypatch):
    monkeypatch.setenv("NAV_DATABASE_URL", "postgresql://x:s3cretpw@127.0.0.1:1/none")
    with pytest.raises(store.StoreUnavailable) as exc:
        store.connect()
    assert "s3cretpw" not in str(exc.value)


def test_app_boots_with_postgres_unreachable(monkeypatch):
    monkeypatch.setenv("NAV_DATABASE_URL", "postgresql://x:y@127.0.0.1:1/none")
    from sbc.app_factory import create_app

    assert create_app().url_map is not None


@pytest.mark.skipif(not os.environ.get("NAV_TEST_DATABASE_URL"), reason="needs Postgres")
def test_migrate_is_idempotent(monkeypatch):
    monkeypatch.setenv("NAV_DATABASE_URL", os.environ["NAV_TEST_DATABASE_URL"])
    store.migrate()
    store.migrate()
    with store.connect() as c:
        assert c.execute(
            "select count(*) from information_schema.tables where table_name='backtest_run'"
        ).fetchone()[0] == 1
