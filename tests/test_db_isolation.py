"""Tests must never touch the real data/profiles.db."""

from pathlib import Path

from sbc import db

REAL_DB = (Path(__file__).resolve().parent.parent / "data" / "profiles.db").resolve()


def test_profiles_db_is_redirected_for_tests():
    assert Path(db._DB_PATH).resolve() != REAL_DB


def test_profile_writes_land_in_the_test_db(client):
    resp = client.post("/api/astro/profile", json={"name": "Iso"},
                       headers={"X-User-Key": "isolation"})
    assert resp.status_code < 400
    conn = db.connect()
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM profiles WHERE user_key='isolation'").fetchone()[0]
    finally:
        conn.close()
    assert n >= 1
