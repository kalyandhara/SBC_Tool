"""Yearly transit almanac (sbc.transit_almanac, B-55) against a published 2026 chart."""

import datetime as dt

import pytest

from sbc import transit_almanac as ta


@pytest.fixture(scope="module")
def trop():
    return {b["name"]: b for b in ta.build(2026, "tropical")["bodies"]}


def dates(body, **match):
    return [e["date"] for e in body["events"] if all(e.get(k) == v for k, v in match.items())]


# Source: "2026 Astrological Aspects" chart, tropical, dates in UT+5:30.
@pytest.mark.parametrize("name,kind,date", [
    ("Pluto", "Retrograde", "2026-05-06"), ("Pluto", "Direct", "2026-10-16"),
    ("Neptune", "Retrograde", "2026-07-07"), ("Neptune", "Direct", "2026-12-13"),
    ("Uranus", "Direct", "2026-02-04"), ("Uranus", "Retrograde", "2026-09-10"),
    ("Saturn", "Retrograde", "2026-07-27"), ("Saturn", "Direct", "2026-12-11"),
    ("Jupiter", "Direct", "2026-03-11"), ("Jupiter", "Retrograde", "2026-12-13"),
    ("Venus", "Retrograde", "2026-10-03"), ("Venus", "Direct", "2026-11-14"),
    ("Mercury", "Retrograde", "2026-02-26"), ("Mercury", "Direct", "2026-03-21"),
    ("Mercury", "Retrograde", "2026-06-29"), ("Mercury", "Direct", "2026-07-24"),
    ("Mercury", "Retrograde", "2026-10-24"), ("Mercury", "Direct", "2026-11-13"),
])
def test_stations(trop, name, kind, date):
    assert date in dates(trop[name], type="station", kind=kind)


@pytest.mark.parametrize("name,sign,date", [
    ("Neptune", "Aries", "2026-01-26"), ("Uranus", "Gemini", "2026-04-26"),
    ("Saturn", "Aries", "2026-02-14"), ("Jupiter", "Leo", "2026-06-30"),
    ("Mars", "Taurus", "2026-05-19"), ("Mars", "Gemini", "2026-06-29"),
    ("Venus", "Cancer", "2026-05-19"), ("Mercury", "Gemini", "2026-05-17"),
])
def test_sign_changes(trop, name, sign, date):
    assert date in dates(trop[name], type="ingress", sign=sign)


@pytest.mark.parametrize("fast,aspect,slow,date", [
    ("Mars", "square", "Pluto", "2026-05-26"), ("Mars", "sextile", "Jupiter", "2026-06-28"),
    ("Mars", "trine", "Pluto", "2026-07-05"), ("Uranus", "sextile", "Neptune", "2026-07-16"),
    ("Uranus", "trine", "Pluto", "2026-07-18"), ("Jupiter", "trine", "Saturn", "2026-09-01"),
])
def test_aspects(trop, fast, aspect, slow, date):
    assert date in dates(trop[fast], type="aspect", aspect=aspect, other=slow)


def test_eclipses_and_node(trop):
    row = trop["Nodes & Eclipses"]
    assert dates(row, type="eclipse", kind="Solar") == ["2026-02-17", "2026-08-12"]
    assert dates(row, type="eclipse", kind="Lunar") == ["2026-03-03", "2026-08-28"]
    assert dates(row, type="ingress") == ["2026-08-19"]


def test_segments_cover_the_year(trop):
    for b in trop.values():
        segs = b["segments"]
        assert segs[0]["a"] == 0 and segs[-1]["b"] == 1
        assert all(x["b"] == y["a"] for x, y in zip(segs, segs[1:]))


def test_sidereal_differs_and_survives_kp_mode():
    from sbc import kp_ephemeris
    first = ta.build.__wrapped__(2026, "sidereal")
    kp_ephemeris.kp_point(10.0)
    kp_ephemeris.chart_at(dt.datetime(2026, 1, 1, 9, 15))
    assert ta.build.__wrapped__(2026, "sidereal") == first
    assert first != ta.build(2026, "tropical")


def test_rejects_bad_input():
    with pytest.raises(ValueError):
        ta.build(2026, "draconic")
    with pytest.raises(ValueError):
        ta.build(1800)


def test_endpoint(client):
    r = client.get("/api/engine/transit-almanac?year=2026&zodiac=tropical")
    assert r.status_code == 200 and r.get_json()["year"] == 2026
    assert client.get("/api/engine/transit-almanac?year=abc").status_code == 400
    assert client.get("/api/engine/transit-almanac?zodiac=x").status_code == 400
