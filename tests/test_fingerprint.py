"""Astro fingerprint (sbc.fingerprint) and its store (sbc.fingerprint_store)."""

import datetime as dt

import pytest

from sbc import bhadra, fingerprint_store
from sbc import engine_version as ev
from sbc import fingerprint as fpm
from sbc import kp_ephemeris as kpe


@pytest.fixture(scope="module")
def fp_2026_10_01():
    return fpm.fingerprint("2026-10-01")


def test_known_positions_2026_10_01(fp_2026_10_01):
    p = fp_2026_10_01["planets"]
    assert p["Sun"]["sign_name"] == "Virgo"
    assert p["Jupiter"]["sign_name"] == "Cancer" and p["Jupiter"]["dignity"] == "exalted"
    assert p["Saturn"]["sign_name"] == "Pisces" and p["Saturn"]["retrograde"]
    assert p["Rahu"]["sign_name"] == "Aquarius" and p["Ketu"]["sign_name"] == "Leo"
    assert p["Moon"]["sign_name"] == "Taurus" and p["Moon"]["dignity"] == "exalted"
    # Full moon 2026-09-26 -> Krishna Panchami five days later.
    assert fp_2026_10_01["panchang"]["tithi"] == 20
    assert fp_2026_10_01["panchang"]["paksha"] == "Krishna"


def test_known_mercury_retrograde():
    # Mercury was retrograde 2024-04-01 .. 2024-04-25.
    assert fpm.fingerprint("2024-04-10")["planets"]["Mercury"]["retrograde"]
    assert not fpm.fingerprint("2024-05-20")["planets"]["Mercury"]["retrograde"]


def test_eclipse_distances():
    # Total solar eclipse over India, 2009-07-22 ~02:35 UT (08:05 IST), before the open.
    ecl = fpm.fingerprint("2009-07-22")["eclipse"]
    assert ecl["since_type"] == "solar" and 0 < ecl["days_since"] < 0.2
    assert fpm.fingerprint("2026-10-01")["eclipse"]["to_type"] == "solar"
    assert fpm.fingerprint("1970-01-05")["eclipse"]["days_to"] is None  # outside the table


def test_vishti_matches_bhadra_module():
    for i in range(0, 60, 3):
        day = dt.date(2026, 9, 1) + dt.timedelta(days=i)
        jd = kpe._julday_ist(dt.datetime.combine(day, dt.time(9, 15)))
        assert fpm.fingerprint(day)["panchang"]["vishti"] == bhadra._is_vishti(jd), day


def test_hora_lord_matches_schedule(fp_2026_10_01):
    sched = kpe.hora_schedule(dt.date(2026, 10, 1))
    assert fp_2026_10_01["panchang"]["hora_lord"] == kpe._hora_at(sched, dt.datetime(2026, 10, 1, 9, 15))
    assert fp_2026_10_01["panchang"]["weekday_lord"] == "Jupiter"  # Thursday


def test_aspect_tier_is_the_faster_planet(fp_2026_10_01):
    for asp in fp_2026_10_01["aspects"]:
        tiers = {fpm.TIER[asp["a"]], fpm.TIER[asp["b"]]}
        expected = "fast" if "fast" in tiers else "medium" if "medium" in tiers else "slow"
        assert asp["tier"] == expected
        assert asp["orb"] <= fpm.ASPECT_ORBS[asp["aspect"]]


def test_feature_vector_shape_is_fixed():
    a = fpm.feature_vector(fpm.fingerprint("1995-03-15"))
    b = fpm.feature_vector(fpm.fingerprint("2030-11-02"))
    assert [n for n, _, _ in a] == [n for n, _, _ in b]
    assert len({n for n, _, _ in a}) == len(a)
    assert {t for _, t, _ in a} == set(fpm.TIERS)
    assert all(isinstance(v, float) and v == v for _, _, v in a)


def test_module_version_tracks_astro_code():
    def reader(suffix):
        def read(path):
            text = path.read_text(encoding="utf-8")
            return text + "\n# edit\n" if path.as_posix().endswith(suffix) else text
        return read

    base = ev.module_version("sbc.fingerprint")
    assert ev.module_version("sbc.fingerprint", reader("sbc/fingerprint.py")) != base
    assert ev.module_version("sbc.fingerprint", reader("sbc/planets.py")) != base
    assert ev.module_version("sbc.fingerprint", reader("sbc/kp_docx.py")) == base


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(fingerprint_store, "DB_PATH", tmp_path / "fp.db")
    return fingerprint_store


def test_store_builds_only_missing_and_rebuilds_on_version_change(store, monkeypatch):
    assert store.build("2026-09-28", "2026-10-02")["computed"] == 5
    assert store.build("2026-09-28", "2026-10-03")["computed"] == 1
    assert [f["date"] for f in store.get_range("2026-09-30", "2026-10-01")] == ["2026-09-30", "2026-10-01"]

    monkeypatch.setattr(store, "current_version", lambda: "other")
    assert store.status()["rows"] == 0 and store.status()["stale_rows"] == 6
    assert store.purge_stale() == 6
    assert store.build("2026-09-28", "2026-10-03")["computed"] == 6
    assert store.status()["stale_rows"] == 0


def test_store_get_computes_and_caches(store):
    fp = store.get("2026-10-01")
    assert fp["date"] == "2026-10-01"
    assert store.missing("2026-10-01", "2026-10-01") == []


def test_fingerprint_endpoint(client):
    resp = client.get("/api/engine/fingerprint?date=2026-10-01&vector=1")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["planets"]["Jupiter"]["sign_name"] == "Cancer"
    assert len(body["vector"]) == len(fpm.feature_vector(body))
    assert client.get("/api/engine/fingerprint?date=nope").status_code == 400
    assert client.get("/api/engine/fingerprint/status").status_code == 200
