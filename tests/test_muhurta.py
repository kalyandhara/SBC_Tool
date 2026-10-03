"""Exact Guru / Ravi Pushya windows (sbc.muhurta) and the rules that use them."""

import datetime as dt

import pytest

from sbc.muhurta import guru_pushya_window, ravi_pushya_window

D = dt.date
T = dt.datetime


def close(a, b, minutes=2):
    return abs((a - b).total_seconds()) <= minutes * 60


# Drik Panchang's 2027 list (New Delhi). Ends that fall on the Moon leaving
# Pushya match to the minute; starts/ends set by sunrise differ by city, so
# those are checked against Mumbai sunrise from our own ephemeris instead.
@pytest.mark.parametrize("day,start,end", [
    (D(2027, 2, 18), T(2027, 2, 18, 21, 5), None),            # starts at Pushya ingress
    (D(2027, 3, 18), None, T(2027, 3, 19, 3, 21)),            # ends as Moon leaves Pushya
    (D(2027, 4, 15), None, T(2027, 4, 15, 9, 33)),
    (D(2027, 12, 16), T(2027, 12, 16, 9, 12), None),
])
def test_guru_pushya_matches_drik_panchang(day, start, end):
    w = guru_pushya_window(day)
    assert w is not None
    if start:
        assert close(w[0], start)
    if end:
        assert close(w[1], end)


def test_window_bounded_by_the_vara():
    from sbc.kp_ephemeris import sunrise_ist
    s, e = guru_pushya_window(D(2027, 2, 18))
    assert close(e, sunrise_ist(D(2027, 2, 19)))  # runs to Friday's sunrise
    s, e = guru_pushya_window(D(2027, 3, 18))
    assert close(s, sunrise_ist(D(2027, 3, 18)))


def test_no_window_off_thursday_or_without_pushya():
    assert guru_pushya_window(D(2027, 2, 19)) is None   # Friday
    assert guru_pushya_window(D(2027, 2, 11)) is None   # Thursday, Moon elsewhere
    assert ravi_pushya_window(D(2027, 2, 18)) is None   # not a Sunday


def test_ravi_pushya_window():
    s, e = ravi_pushya_window(D(2026, 11, 1))
    assert s.date() == D(2026, 11, 1) and e > s


def _planets_at(day, time="09:15"):
    import app
    from sbc.planets import positions
    utc = app._utc_from_local(day.isoformat(), time, "Asia/Kolkata")
    planets, _ = positions(app._julday(utc))
    return planets


def test_reversal_windows_catch_an_evening_guru_pushya():
    """18 Feb 2027: Pushya starts 21:06, so the old 09:15 test missed it."""
    from sbc.market_calendar import _pushya_reversal_windows
    day = D(2027, 2, 18)
    planets = _planets_at(day)
    moon = next(p for p in planets if p["name"] == "Moon")
    assert moon["nakshatra"] != "Pushya"  # the old rule's blind spot
    gp = [w for w in _pushya_reversal_windows(day, planets) if w["id"].startswith("guru-pushya")]
    assert len(gp) == 1
    assert gp[0]["start_time"].startswith("2027-02-18T21:0")
    assert "21:0" in gp[0]["title"] and "IST" in gp[0]["title"]


def test_reversal_windows_skip_thursday_without_pushya():
    from sbc.market_calendar import _pushya_reversal_windows
    day = D(2027, 2, 11)
    ids = [w["id"] for w in _pushya_reversal_windows(day, _planets_at(day))]
    assert not any(i.startswith("guru-pushya") for i in ids)


def test_yoga_glyphs_use_the_window():
    from sbc.market_calendar import daily_yoga_glyphs
    from sbc.nakshatra import tithi_of
    for day, expected in ((D(2027, 2, 18), True), (D(2027, 2, 11), False)):
        planets = _planets_at(day)
        sun = next(p for p in planets if p["name"] == "Sun")
        moon = next(p for p in planets if p["name"] == "Moon")
        names, _ = daily_yoga_glyphs(day, sun, moon, tithi_of(sun["longitude"], moon["longitude"]))
        assert ("Guru Pushya Yoga" in names) is expected
