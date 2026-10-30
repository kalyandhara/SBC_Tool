"""Tests for the B-70 Venus station validation (sbc.venus_station_validation)."""

import datetime as dt

import numpy as np
import pytest

from sbc import venus_station_validation as vv


def test_pivot_low_needs_five_sessions_either_side():
    closes = np.array([10, 9, 8, 7, 6, 5, 6, 7, 8, 9, 10, 11], dtype=float)
    pivots = vv.pivot_lows(closes)
    assert np.flatnonzero(pivots).tolist() == [5]


def test_pivot_at_the_edges_is_never_flagged():
    closes = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], dtype=float)
    assert not vv.pivot_lows(closes)[:vv.PIVOT_HALF].any()
    assert not vv.pivot_lows(closes)[-vv.PIVOT_HALF:].any()


def test_hit_counts_a_pivot_within_three_sessions():
    pivots = np.zeros(30, dtype=bool)
    pivots[10] = True
    events = np.array([7, 13, 20])
    assert vv.hits(pivots, events, 0, 30) == 2


def test_event_maps_to_the_next_session_when_it_falls_on_a_gap():
    dates = ["2020-01-06", "2020-01-08", "2020-01-09"]
    assert vv.event_sessions(dates, ["2020-01-07"]).tolist() == [1]
    assert vv.event_sessions(dates, ["2030-01-01"]).tolist() == []


def test_grade_reports_lift_against_the_shift_null():
    rng = np.random.default_rng(1)
    pivots = np.zeros(2000, dtype=bool)
    events = np.arange(100, 1900, 40)
    for e in events:
        pivots[e + 1] = True
    g = vv.grade(pivots, events, 0, 2000, 200, rng)
    assert g["n"] == len(events)
    assert g["hits"] == len(events)
    assert g["rate"] == 1.0
    assert g["lift"] > 0.3
    assert g["p"] < 0.05


def test_grade_with_no_events_returns_nulls():
    rng = np.random.default_rng(1)
    g = vv.grade(np.zeros(100, dtype=bool), np.array([], dtype=int), 0, 100, 10, rng)
    assert g["n"] == 0 and g["p"] is None


def test_shift_null_keeps_events_inside_their_era():
    rng = np.random.default_rng(2)
    pivots = np.zeros(400, dtype=bool)
    events = np.array([50, 120])
    null = vv.shift_null(pivots, events, 0, 200, 50, rng)
    assert len(null) == 50


def test_shift_null_refuses_events_outside_their_era():
    rng = np.random.default_rng(2)
    with pytest.raises(ValueError):
        vv.shift_null(np.zeros(400, dtype=bool), np.array([50, 300]), 0, 200, 5, rng)


def test_conjunction_dates_are_in_order_and_about_584_days_apart():
    days = [dt.date.fromisoformat(d) for d in vv.inferior_conjunctions(dt.date(2010, 1, 1), dt.date(2014, 1, 1))]
    gaps = [(b - a).days for a, b in zip(days, days[1:])]
    assert days == sorted(days)
    assert all(560 <= g <= 610 for g in gaps)


def test_sidereal_diff_is_wrapped_into_half_circle():
    d = vv.sidereal_diff(dt.date(2010, 10, 8))
    assert -180 < d <= 180
