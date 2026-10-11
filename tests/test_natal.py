"""B-49/B-51: natal charts and transit-to-natal aspect windows."""

import datetime as dt

import pytest

from sbc import helio_aspects as ha
from sbc import natal
from sbc import transit_natal as tn

NIFTY = natal.chart("nifty")


# ── B-49 natal chart ───────────────────────────────────────────────────────

def test_chart_has_every_graha_in_range():
    assert set(NIFTY) == {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                          "Saturn", "Rahu", "Ketu"}
    assert all(0.0 <= lon < 360.0 for lon in NIFTY.values())


def test_ketu_is_opposite_rahu():
    assert NIFTY["Ketu"] == pytest.approx((NIFTY["Rahu"] + 180) % 360, abs=1e-3)


def test_chart_matches_the_anchor_date():
    """The NIFTY anchor is 1995-11-03 00:00 IST; a bare date must give the same chart."""
    assert natal.chart("1995-11-03", "00:00", "Asia/Kolkata") == NIFTY


def test_sun_sits_where_early_november_puts_it():
    """3 Nov is sidereal Libra (Lahiri): Sun between 180 and 210 degrees."""
    assert 180.0 <= NIFTY["Sun"] < 210.0


def test_birth_time_moves_the_moon_but_not_saturn():
    noon = natal.chart("1995-11-03", "12:00")
    assert abs(noon["Moon"] - NIFTY["Moon"]) > 5.0      # ~13 deg/day
    assert abs(noon["Saturn"] - NIFTY["Saturn"]) < 0.1  # ~2 arcmin/day


def test_detail_carries_sign_and_nakshatra():
    sun = next(p for p in natal.chart_detail("nifty") if p["name"] == "Sun")
    assert sun["sign"] and sun["nakshatra"] and 1 <= sun["pada"] <= 4


def test_bad_date_is_rejected():
    with pytest.raises(ValueError):
        natal.chart("not-a-date")


# ── B-51 transit-to-natal windows ──────────────────────────────────────────

def test_window_shape_matches_helio_aspects():
    """swing_model consumes these, so the keys must match the B-39 windows."""
    helio = set(ha.scan("2026-01-01", "2026-02-28", planets=["Jupiter"], aspects=["CONJ"])[0])
    mine = set(tn.scan(NIFTY, "2026-01-01", "2026-02-28", planets=["Saturn"],
                       natal_points=["Sun"])[0])
    assert helio - mine == {"pair"} - {"pair"} == set()   # every B-39 key is present
    assert mine - helio == {"natal", "natal_longitude"}


def test_sun_returns_to_its_natal_longitude_each_year():
    """A solar return: the Sun conjoins its natal place once a year, near the birthday."""
    w = tn.scan(NIFTY, "2026-01-01", "2026-12-31", planets=["Sun"],
                natal_points=["Sun"], aspects=["CONJ"])
    assert len(w) == 1
    exact = dt.date.fromisoformat(w[0]["exact_date"])
    assert (exact.month, exact.day) == (11, 3) or abs((exact - dt.date(2026, 11, 3)).days) <= 2
    assert w[0]["min_orb"] < 0.05


def test_exact_time_really_is_within_orb_and_edges_are_on_it():
    # Mars crosses NIFTY's natal Saturn (324.5 deg) in late March 2026.
    w = tn.scan(NIFTY, "2026-01-01", "2026-06-30", planets=["Mars"],
                natal_points=["Saturn"], aspects=["CONJ"])[0]
    assert w["exact_date"] == "2026-03-26"
    t = dt.datetime.fromisoformat(f"{w['exact_date']}T{w['exact_time']}").replace(tzinfo=tn.IST)
    assert tn._deviation("Mars", NIFTY["Saturn"], 0.0, tn._jd(t)) < 0.05
    edge = dt.datetime.fromisoformat(f"{w['entry_date']}T{w['entry_time']}").replace(tzinfo=tn.IST)
    assert tn._deviation("Mars", NIFTY["Saturn"], 0.0, tn._jd(edge)) == pytest.approx(ha.ORB, abs=0.01)


def test_entry_before_exact_before_exit():
    for w in tn.scan(NIFTY, "2026-01-01", "2026-03-31", planets=["Venus"], natal_points=["Mars"]):
        if w["starts_before_range"] or w["ends_after_range"]:
            continue
        assert w["entry_date"] <= w["exact_date"] <= w["exit_date"]
        assert w["min_orb"] <= ha.ORB


def test_moon_and_ketu_are_not_transit_planets_by_default():
    """The Moon is in orb nearly every day; Ketu just repeats Rahu + 180."""
    assert "Moon" not in tn.TRANSIT_PLANETS and "Ketu" not in tn.TRANSIT_PLANETS
    planets = {w["planet"] for w in tn.scan(NIFTY, "2026-01-01", "2026-01-31")}
    assert planets <= set(tn.TRANSIT_PLANETS)


def test_moon_can_be_asked_for():
    w = tn.scan(NIFTY, "2026-01-01", "2026-01-31", planets=["Moon"], natal_points=["Sun"],
                aspects=["CONJ"])
    assert w and all(x["planet"] == "Moon" for x in w)


def test_active_on_agrees_with_scan():
    day = "2026-03-10"
    live = {(c["planet"], c["natal"], c["aspect"]) for c in tn.active_on(NIFTY, day)}
    spanning = {(w["planet"], w["natal"], w["aspect"])
                for w in tn.scan(NIFTY, "2026-03-01", "2026-03-20")
                if w["entry_date"] <= day <= w["exit_date"]}
    assert live <= spanning


def test_tighter_orb_gives_fewer_windows():
    wide = tn.scan(NIFTY, "2026-01-01", "2026-06-30", planets=["Saturn"])
    tight = tn.scan(NIFTY, "2026-01-01", "2026-06-30", planets=["Saturn"], orb=0.5)
    assert len(tight) < len(wide)
    assert all(w["min_orb"] <= 0.5 for w in tight)


def test_unknown_inputs_are_rejected():
    for kwargs in ({"planets": ["Nibiru"]}, {"aspects": ["ZZZ"]}, {"natal_points": ["Nibiru"]}):
        with pytest.raises(ValueError):
            tn.scan(NIFTY, "2026-01-01", "2026-01-31", **kwargs)
    with pytest.raises(ValueError):
        tn.scan(NIFTY, "2026-02-01", "2026-01-01")


# ── B-53 the grader is wired to the registered inputs ──────────────────────

def test_validation_groups_cover_the_registered_set():
    from sbc import natal_validation as nv

    g = nv.groups(NIFTY)
    assert "all" in g and "lecture5" in g
    assert {f"aspect_{a}" for a in ha.ASPECTS} <= set(g)
    assert {f"planet_{p}" for p in tn.TRANSIT_PLANETS} <= set(g)
    assert {f"natal_{p}" for p in NIFTY} <= set(g)
    assert len(g) == 1 + len(ha.ASPECTS) + 1 + len(tn.TRANSIT_PLANETS) + len(NIFTY) == 26


def test_lecture5_is_the_five_aspects_the_lecture_names():
    from sbc import natal_validation as nv

    assert set(nv.LECTURE_ASPECTS) == {"CONJ", "SQ", "SXT", "SS", "TRI"}
    match = nv.groups(NIFTY)["lecture5"]
    assert match({"aspect": "CONJ"}) and not match({"aspect": "OPP"})
