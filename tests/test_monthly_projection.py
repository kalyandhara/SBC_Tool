"""Monthly-projection backlog (docs/BACKLOG_MONTHLY_PROJECTION_2026-10-05.md):
B-40 external series in the ledger, B-42 exact stations, B-44 latitude, B-45 planet series."""

import copy
import datetime as dt

import pytest

from sbc import fingerprint as fpm
from sbc import forecast_ledger as ledger
from sbc import forward_calendar as fcal
from sbc import planet_series as ps
from sbc import stations as st

IST = ledger.IST


# ── B-42 stations ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def october():
    return st.between(dt.date(2026, 10, 1), dt.date(2026, 11, 1))


@pytest.mark.parametrize("planet,direction,when", [
    ("Venus", "retrograde", "2026-10-03T12:43"),
    ("Rahu", "retrograde", "2026-10-07T06:49"),
    ("Pluto", "direct", "2026-10-16T11:02"),
    ("Mercury", "retrograde", "2026-10-24T12:42"),
])
def test_stations_match_the_source_table_within_five_minutes(october, planet, direction, when):
    target = dt.datetime.fromisoformat(when)
    found = [dt.datetime.fromisoformat(s["time"]) for s in october
             if s["planet"] == planet and s["direction"] == direction]
    assert min(abs(t - target) for t in found) <= dt.timedelta(minutes=5)


def test_true_node_stations_several_times_a_month(october):
    rahu = [s for s in october if s["planet"] == "Rahu"]
    assert len(rahu) >= 4
    # Known deviation: the source has Rahu direct at 19:06; the flat speed there moves it ~3 h.
    assert any(s["direction"] == "direct" and s["date"] == "2026-10-03" for s in rahu)


def test_station_range_is_validated():
    with pytest.raises(ValueError):
        st.between(dt.date(2026, 10, 5), dt.date(2026, 10, 1))


def test_forward_calendar_uses_exact_stations_when_given():
    fp = fpm.fingerprint("2026-10-05")
    prev, cur = copy.deepcopy(fp), copy.deepcopy(fp)
    cur["planets"]["Mercury"]["retrograde"] = not prev["planets"]["Mercury"]["retrograde"]
    exact = [{"label": "Venus stations retrograde 12:43"}]
    events = fcal.events_between(prev, cur, None, exact)
    assert "Venus stations retrograde 12:43 IST" in events
    assert not any(e.startswith("Mercury stations") for e in events)  # fingerprint flip ignored


def test_trap_calendar_lists_node_stations():
    from sbc.rahu_ketu_trap import generate_calendar
    cal = generate_calendar("2026-10-06", "2026-10-08", ["IT"])
    day = next(d for d in cal["calendar"] if d["date"] == "2026-10-07")
    assert any("Rahu stations retrograde" in s for s in day["node_stations"])


# ── B-44 latitude, B-45 series ─────────────────────────────────────────────

def test_fingerprint_carries_ecliptic_latitude():
    p = fpm.fingerprint("2026-10-01")["planets"]
    assert 4.5 < p["Moon"]["latitude"] < 5.5
    assert -7.5 < p["Venus"]["latitude"] < -6.5
    assert p["Rahu"]["latitude"] == 0.0


def test_moon_latitude_swings_through_october():
    d = ps.series("latitude", dt.date(2026, 10, 1), dt.date(2026, 10, 31))
    moon = d["series"]["Moon"]
    assert max(moon) > 4.5 and min(moon) < -4.5
    assert "Sun" not in d["series"] and "Rahu" not in d["series"]


def test_declination_ketu_mirrors_rahu_and_marks_out_of_bounds():
    d = ps.series("declination", dt.date(2026, 10, 1), dt.date(2026, 10, 3))
    assert d["series"]["Ketu"] == [-v for v in d["series"]["Rahu"]]
    assert d["reference"]["values"] == [-23.44, 23.44]
    assert d["planets"][0] == "Sun" and len(d["dates"]) == 3


def test_speed_series_sees_venus_retrograde():
    d = ps.series("speed", dt.date(2026, 10, 10), dt.date(2026, 10, 12))
    assert all(v < 0 for v in d["series"]["Venus"])


@pytest.mark.parametrize("metric,start,end", [
    ("colour", dt.date(2026, 10, 1), dt.date(2026, 10, 2)),
    ("speed", dt.date(2026, 10, 2), dt.date(2026, 10, 1)),
    ("speed", dt.date(2026, 1, 1), dt.date(2027, 6, 1)),
])
def test_series_rejects_bad_arguments(metric, start, end):
    with pytest.raises(ValueError):
        ps.series(metric, start, end)


def test_planet_routes(client):
    r = client.get("/api/engine/planet_series?metric=speed&start=2026-10-01&end=2026-10-05")
    assert r.status_code == 200 and len(r.json["dates"]) == 5
    assert client.get("/api/engine/planet_series?metric=x").status_code == 400
    r = client.get("/api/engine/stations?start=2026-10-01&end=2026-10-31")
    assert r.status_code == 200 and r.json["count"] >= 5
    assert client.get("/api/engine/stations?start=nope").status_code == 400


# ── B-40 external series in the ledger ─────────────────────────────────────

@pytest.fixture
def tmp_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "DB_PATH", tmp_path / "ledger.db")


def test_external_freeze_marks_published_days_post_hoc(tmp_ledger):
    rows = [{"date": f"2026-10-0{d}", "score": 10 * d} for d in range(1, 8)]
    now = dt.datetime(2026, 10, 6, 1, 0, tzinfo=IST)
    added = ledger.freeze_external("src", rows, dt.date(2026, 10, 5), now)
    assert added == {"live": 2, "post_hoc": 5, "kept": 0}
    # Existing rows win: a later re-freeze with other numbers changes nothing.
    again = ledger.freeze_external("src", [{"date": "2026-10-06", "score": 99}], dt.date(2026, 10, 5), now)
    assert again["kept"] == 1
    got = {r["date"]: r for r in ledger.get_external("src")}
    assert got["2026-10-06"]["score"] == 60 and got["2026-10-06"]["kind"] == "live"


def test_external_freeze_after_the_open_is_post_hoc(tmp_ledger):
    now = dt.datetime(2026, 10, 6, 10, 0, tzinfo=IST)
    added = ledger.freeze_external("src", [{"date": "2026-10-06", "score": 1}], dt.date(2026, 10, 5), now)
    assert added["post_hoc"] == 1


def test_external_source_name_is_checked(tmp_ledger):
    with pytest.raises(ValueError):
        ledger.freeze_external("bad name;", [], dt.date(2026, 10, 5))


def test_score_external_by_hand():
    closes = {"2026-10-05": 100.0, "2026-10-06": 101.0, "2026-10-07": 100.0,
              "2026-10-08": 99.0, "2026-10-09": 100.0}
    rows = [{"date": "2026-10-05", "score": 50, "kind": "post_hoc"},
            {"date": "2026-10-06", "score": 60, "kind": "live"},   # +10, up day: hit
            {"date": "2026-10-07", "score": 40, "kind": "live"},   # -20, down day: hit
            {"date": "2026-10-08", "score": 50, "kind": "live"},   # +10, down day: miss
            {"date": "2026-10-09", "score": 50, "kind": "live"}]   # no change: not called
    m = ledger.score_external(rows, closes)
    assert m["live_sessions"] == 4
    assert (m["direction"]["called"], m["direction"]["hits"]) == (3, 2)
    assert m["direction"]["p_vs_coin"] == 0.5  # P(X>=2 | n=3)
    # Baseline on the called days: 07 up->down miss, 08 down->down hit (06 has no prior return).
    assert m["direction"]["persistence_hit_rate"] == 0.5
    assert m["spearman_next_return"]["n"] == 3  # the last day has no next session
    assert m["lowest_score_days"][0]["date"] == "2026-10-07"
    assert "too few" in m["caveat"]


# ── B-41 monthly score endpoint ────────────────────────────────────────────

def test_monthly_score_needs_a_valid_month(client):
    assert client.get("/api/engine/monthly_projection").status_code == 400
    assert client.get("/api/engine/monthly_projection?month=2026-13").status_code == 400


def test_monthly_score_covers_every_calendar_day(client):
    r = client.get("/api/engine/monthly_projection?month=2026-10")
    assert r.status_code == 200
    d = r.get_json()
    assert len(d["days"]) == 31
    assert d["disclaimer"] == "hypothetical, unvalidated"
    assert {x["trading"] for x in d["days"]} == {True, False}


def test_monthly_score_sends_no_closes_for_future_months(client):
    future = (dt.date.today() + dt.timedelta(days=60)).strftime("%Y-%m")
    d = client.get(f"/api/engine/monthly_projection?month={future}").get_json()
    assert all(x["nifty_close"] is None for x in d["days"])

