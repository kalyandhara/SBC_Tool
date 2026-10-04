"""Engine-versioned series cache (sbc.engine_version, sbc.series_cache)."""

import sqlite3

import pytest

from sbc import engine_version as ev
from sbc import series_cache


def rel(paths):
    return {p.relative_to(ev.ROOT).as_posix() for p in paths}


def reader_with(path_suffix, transform):
    """A file reader that alters one file's text, to simulate an edit."""
    def read(path):
        text = path.read_text(encoding="utf-8")
        return transform(text) if path.as_posix().endswith(path_suffix) else text
    return read


def test_closure_covers_the_engine_and_skips_unrelated_modules():
    _, paths = ev.dependency_closure()
    files = rel(paths)
    for must in ("sbc/engine.py", "sbc/prediction.py", "sbc/planets.py", "sbc/market_calendar.py",
                 "sbc/muhurta.py", "sbc/kp_ephemeris.py", "sbc/nakshatra.py"):
        assert must in files, must
    for never in ("sbc/kp_docx.py", "sbc/kp_intraday.py", "sbc/forecast_ledger.py",
                  "sbc/series_cache.py", "sbc/__init__.py"):
        assert never not in files, never


def test_version_is_stable():
    assert ev.compute_engine_version() == ev.compute_engine_version()


@pytest.mark.parametrize("suffix,edit", [
    ("sbc/muhurta.py", lambda t: t + "\n# engine tweak\n"),
    ("sbc/prediction.py", lambda t: t.replace("def place_planets", "def place_planets", 1) + "\nX = 1\n"),
    ("sbc/engine.py", lambda t: t.replace("def build_response(date_str, time_str, tz_name, anchor_key, school):",
                                          "def build_response(date_str, time_str, tz_name, anchor_key, school):\n    pass", 1)),
    ("sbc/api/blueprints/chart_bp.py", lambda t: t.replace('"lunar_phase": lunar_phase,',
                                                           '"lunar_phase": lunar_phase, "x": 1,', 1)),
])
def test_engine_edits_change_the_version(suffix, edit):
    assert ev.compute_engine_version(reader_with(suffix, edit)) != ev.compute_engine_version()


@pytest.mark.parametrize("suffix,edit", [
    ("sbc/kp_docx.py", lambda t: t + "\n# unrelated\n"),
    ("sbc/api/blueprints/profile_bp.py", lambda t: t.replace("def api_cities_search():", "def api_cities_search():\n    pass", 1)),
    ("sbc/api/blueprints/chart_bp.py", lambda t: t.replace("def nifty_chart():", "def nifty_chart():\n    pass", 1)),
])
def test_unrelated_edits_keep_the_version(suffix, edit):
    original = (ev.ROOT / suffix).read_text(encoding="utf-8")
    assert edit(original) != original  # the simulated edit really happens
    assert ev.compute_engine_version(reader_with(suffix, edit)) == ev.compute_engine_version()


@pytest.fixture
def temp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(series_cache, "DB_PATH", tmp_path / "series.db")
    monkeypatch.setattr(series_cache, "_ready", False)
    return tmp_path / "series.db"


def test_rows_from_another_engine_are_not_served(temp_cache):
    series_cache.put_many({"2027-02-18": {"date": "2027-02-18", "score": 1}}, "nifty", "classical",
                          engine="old")
    assert series_cache.get_many(["2027-02-18"], "nifty", "classical", engine="new") == {}
    assert "2027-02-18" in series_cache.get_many(["2027-02-18"], "nifty", "classical", engine="old")
    assert series_cache.purge_stale(engine="new") == 1
    assert series_cache.get_many(["2027-02-18"], "nifty", "classical", engine="old") == {}


def test_pre_versioning_database_is_migrated_and_treated_as_stale(temp_cache):
    conn = sqlite3.connect(temp_cache)
    conn.execute("CREATE TABLE series (date TEXT NOT NULL, anchor TEXT NOT NULL, school TEXT NOT NULL,"
                 " payload TEXT NOT NULL, PRIMARY KEY (date, anchor, school))")
    conn.execute("INSERT INTO series VALUES ('2027-02-18','nifty','classical','{\"score\": 1}')")
    conn.commit()
    conn.close()
    assert series_cache.get_many(["2027-02-18"], "nifty", "classical") == {}
    cols = {r[1] for r in sqlite3.connect(temp_cache).execute("PRAGMA table_info(series)")}
    assert "engine" in cols
    assert series_cache.purge_stale() == 1


def test_default_engine_is_the_current_version(temp_cache):
    series_cache.put_many({"2027-03-18": {"date": "2027-03-18"}}, "nifty", "classical")
    row = sqlite3.connect(temp_cache).execute("SELECT engine FROM series").fetchone()
    assert row[0] == ev.engine_version()
