"""Exact Guru / Ravi Pushya windows (sbc.muhurta) and the rules that use them."""

import datetime as dt

import pytest

from sbc.muhurta import (
    ghabad_kind_at,
    ghabad_status,
    ghabad_windows,
    guru_pushya_window,
    ravi_pushya_window,
)

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


# Ghabad windows from the October 2026 table in docs/research/ghabad_muhurat.md.
# The minutes there are rounded, so the check allows the default 2-minute tolerance.
GHABAD_OCT_2026 = [
    ("Ardha-ghabad", T(2026, 10, 1, 6, 3), T(2026, 10, 1, 12, 36)),
    ("Ghabad", T(2026, 10, 5, 3, 55), T(2026, 10, 5, 23, 10)),
    ("Ardha-ghabad", T(2026, 10, 6, 2, 9), T(2026, 10, 6, 22, 18)),
    ("Ghabad", T(2026, 10, 6, 22, 18), T(2026, 10, 7, 0, 36)),
    ("Ardha-ghabad", T(2026, 10, 7, 21, 41), T(2026, 10, 7, 23, 18)),
    ("Ardha-ghabad", T(2026, 10, 10, 21, 43), T(2026, 10, 11, 2, 21)),
    ("Ghabad", T(2026, 10, 15, 1, 14), T(2026, 10, 15, 4, 4)),
    ("Ardha-ghabad", T(2026, 10, 16, 3, 26), T(2026, 10, 16, 6, 48)),
    ("Ghabad", T(2026, 10, 16, 6, 48), T(2026, 10, 17, 5, 55)),
    ("Ardha-ghabad", T(2026, 10, 17, 9, 48), T(2026, 10, 18, 8, 29)),
    ("Ghabad", T(2026, 10, 22, 14, 49), T(2026, 10, 22, 20, 50)),
    ("Ardha-ghabad", T(2026, 10, 23, 14, 37), T(2026, 10, 23, 21, 4)),
    ("Ghabad", T(2026, 10, 23, 21, 4), T(2026, 10, 24, 12, 51)),
    ("Ardha-ghabad", T(2026, 10, 24, 12, 51), T(2026, 10, 24, 13, 38)),
    ("Ghabad", T(2026, 10, 28, 4, 8), T(2026, 10, 28, 13, 27)),
    ("Ardha-ghabad", T(2026, 10, 29, 1, 8), T(2026, 10, 29, 11, 12)),
    ("Ghabad", T(2026, 10, 29, 11, 12), T(2026, 10, 29, 22, 11)),
    ("Ardha-ghabad", T(2026, 10, 30, 9, 5), T(2026, 10, 30, 19, 26)),
]


def test_ghabad_windows_match_the_october_table():
    got = [(w["kind"], w["start"], w["end"]) for w in ghabad_windows(D(2026, 10, 1), D(2026, 10, 31))]
    assert [k for k, _, _ in got] == [k for k, _, _ in GHABAD_OCT_2026]
    for (kind, start, end), (want_kind, want_start, want_end) in zip(got, GHABAD_OCT_2026):
        assert kind == want_kind
        assert close(start, want_start) and close(end, want_end), (kind, start, end)


def test_ghabad_worked_example_on_5_oct():
    # Sun in Hasta (#13), Moon in Pushya (#8): count 23, tithi Krishna 10 = 25,
    # 23 * 3 + 25 = 94, remainder 3.
    s = ghabad_status(D(2026, 10, 5))
    assert (s["kind"], s["remainder"], s["nakshatra_count"], s["tithi"]) == ("Ghabad", 3, 23, 25)


def test_ghabad_kind_at_follows_the_window_edges():
    assert ghabad_kind_at(T(2026, 10, 5, 3, 0)) is None
    assert ghabad_kind_at(T(2026, 10, 5, 12, 0)) == "Ghabad"
    assert ghabad_kind_at(T(2026, 10, 5, 23, 30)) is None


def test_ghabad_windows_are_empty_for_a_quiet_day():
    # 2 Oct is not in the table, so no window should be reported for it.
    assert ghabad_windows(D(2026, 10, 2), D(2026, 10, 2)) == []
