"""Tests for the upgraded transit engine (sign/nakshatra/pada, 12 bodies).

Covers: outer bodies, Ketu, node mode (mean/true), ayanamsa selection
(Lahiri/KP/Raman), to-the-second timestamps, motion and re-entry flags,
gandanta flags, sign stay durations, pada sectors, and the city-timezone
helper.
"""

import datetime

from sbc import cities
from sbc.transits import (
    AYANAMSA_MODES,
    NODE_MODES,
    pada_ingresses,
    same_sign_periods,
    sign_ingresses,
    sign_periods,
)


def test_ayanamsa_and_node_mode_tables():
    assert set(AYANAMSA_MODES) == {"lahiri", "kp", "raman"}
    assert set(NODE_MODES) == {"mean", "true"}


def test_mercury_ingresses_have_seconds_motion_and_reentries():
    d0 = datetime.date(2024, 1, 1)
    d1 = datetime.date(2026, 12, 31)
    events = sign_ingresses("Mercury", d0, d1)
    assert len(events) > 30
    assert sum(1 for e in events if e["re_entry"]) >= 5
    # full-precision UTC timestamps (seconds, not hour-truncated)
    sample = events[0]["utc"]
    assert len(sample) == 25 and sample[-6] == "+" and sample[17] != ":"
    motions = {e["motion"] for e in events}
    assert motions <= {"D", "R", "S"} and "R" in motions


def test_ketu_mean_vs_true_node_differ():
    d0 = datetime.date(2026, 11, 1)
    d1 = datetime.date(2027, 1, 15)
    mean_ev = sign_ingresses("Ketu", d0, d1, node_mode="mean")
    true_ev = sign_ingresses("Ketu", d0, d1, node_mode="true")
    assert mean_ev and true_ev
    assert mean_ev[0]["label"] == "Cancer" and true_ev[0]["label"] == "Cancer"
    assert mean_ev[0]["utc"] != true_ev[0]["utc"]


def test_ayanamsa_choice_shifts_ingress_time():
    d0 = datetime.date(2026, 10, 1)
    d1 = datetime.date(2026, 11, 30)
    lahiri = sign_ingresses("Sun", d0, d1, ayanamsa="lahiri")
    kp = sign_ingresses("Sun", d0, d1, ayanamsa="kp")
    assert lahiri[0]["utc"] != kp[0]["utc"]


def test_outer_body_wiring_via_sign_periods():
    # Pluto stays in one sidereal sign for years: a one-year range must
    # yield exactly one (possibly clipped) stay.
    periods = sign_periods("Pluto", datetime.date(2026, 1, 1),
                           datetime.date(2026, 12, 31))
    assert len(periods) == 1
    assert periods[0]["days"] > 360
    assert periods[0]["sign"] in periods[0]["sign"]  # sanity


def test_sign_periods_sun_2026():
    periods = sign_periods("Sun", datetime.date(2026, 1, 1),
                           datetime.date(2026, 12, 31))
    # partial edge stays + 12 sign transits
    assert 12 <= len(periods) <= 14
    libra = [p for p in periods if p["sign"] == "Libra"]
    assert len(libra) == 1 and 29.0 < libra[0]["days"] < 31.0


def test_pada_ingresses_sunset_month():
    events = pada_ingresses("Sun", datetime.date(2026, 9, 15),
                            datetime.date(2026, 11, 20))
    assert 15 <= len(events) <= 25
    for e in events:
        assert e["kind"] == "pada"
        assert 0 <= e["pada_index"] <= 107
        assert e["label"].endswith(("P1", "P2", "P3", "P4"))
        assert e["label"] != e["from_label"]


def test_moon_gandanta_flags_monthly():
    events = sign_ingresses("Moon", datetime.date(2026, 9, 1),
                            datetime.date(2026, 9, 30))
    assert sum(1 for e in events if e["gandanta"]) == 3


def test_same_sign_periods_backward_compatible():
    periods = same_sign_periods("Sun", "Mercury",
                                datetime.date(2026, 10, 1),
                                datetime.date(2026, 11, 30))
    assert any(p["sign"] == "Libra" for p in periods)


def test_cities_local_time_helper():
    utc = datetime.datetime(2026, 11, 6, 7, 45, 1, tzinfo=datetime.UTC)
    mumbai = cities.local_time(utc, "Asia/Kolkata")
    assert mumbai.hour == 13 and mumbai.minute == 15
    london = cities.local_time(utc, "Europe/London")
    assert london.utcoffset().total_seconds() == 0  # GMT in November
    fallback = cities.local_time(utc, "Nowhere/None")
    assert fallback.utcoffset().total_seconds() == 0
    assert cities.resolve("Mumbai")["timezone"] == "Asia/Kolkata"
