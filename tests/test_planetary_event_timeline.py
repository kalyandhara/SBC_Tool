"""Planetary event timeline (B-71): episode logic, decile control and permutation test."""

import numpy as np
import pytest

from sbc import planetary_event_timeline as pet


def _planets(mars_nak, moon_nak):
    return {"Mars": {"nakshatra": mars_nak}, "Moon": {"nakshatra": moon_nak}}


def test_is_event_needs_both_conditions():
    assert pet.is_event(_planets("Pushya", "Rohini"))
    assert not pet.is_event(_planets("Pushya", "Ashlesha"))
    assert not pet.is_event(_planets("Ardra", "Rohini"))


def test_episode_starts_marks_first_session_of_each_run():
    flags = [False, True, True, False, True, False, True, True, True]
    assert np.flatnonzero(pet.episode_starts(flags)).tolist() == [1, 4, 6]


def test_episode_starts_handles_all_false_and_leading_true():
    assert not pet.episode_starts([False, False]).any()
    assert np.flatnonzero(pet.episode_starts([True, True])).tolist() == [0]


def test_same_day_returns_first_session_nan():
    r0 = pet.same_day_returns([100.0, 110.0, 99.0])
    assert np.isnan(r0[0])
    assert r0[1] == pytest.approx(0.10)
    assert r0[2] == pytest.approx(99.0 / 110.0 - 1.0)


def test_decile_labels_cover_zero_to_nine_and_mark_undefined():
    r0 = np.concatenate(([np.nan], np.linspace(-0.05, 0.05, 100)))
    labels = pet.decile_labels(r0)
    assert labels[0] == -1
    assert set(labels[1:]) == set(range(10))
    assert labels[1] == 0 and labels[-1] == 9


def test_forward_returns_nan_past_sample_end():
    fwd = pet.forward_returns([100.0, 101.0, 102.0, 103.0], 2)
    assert fwd[0] == pytest.approx(0.02)
    assert fwd[1] == pytest.approx(103.0 / 101.0 - 1.0)
    assert np.isnan(fwd[2]) and np.isnan(fwd[3])


def test_excess_statistic_compares_with_same_decile_control():
    # decile 0 = sessions 0-2, decile 1 = sessions 3-5; events at 0 and 3
    fwd = np.array([0.02, 0.01, 0.01, 0.00, 0.05, 0.02])
    labels = np.array([0, 0, 0, 1, 1, 1])
    ev = np.array([True, False, False, True, False, False])
    # event 0: 0.02 - mean(0.01, 0.01) = +0.01; event 3: 0.00 - mean(0.05, 0.02) = -0.035
    assert pet.excess_statistic(fwd, labels, ev) == pytest.approx((0.01 - 0.035) / 2)
    ev2 = np.array([True, False, False, True, True, False])
    # events 0, 3, 4; controls: decile 0 -> {1, 2}, decile 1 -> {5}
    # event 0: +0.01; event 3: 0.00 - 0.02 = -0.02; event 4: 0.05 - 0.02 = +0.03
    assert pet.excess_statistic(fwd, labels, ev2) == pytest.approx((0.01 - 0.02 + 0.03) / 3)


def test_excess_statistic_nan_without_events():
    fwd = np.array([0.01, 0.02])
    assert np.isnan(pet.excess_statistic(fwd, np.array([0, 0]), np.array([False, False])))


def test_permutation_p_is_deterministic_and_bounded():
    rng = np.random.default_rng(0)
    n = 300
    closes = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
    labels = pet.decile_labels(pet.same_day_returns(closes))
    fwd = pet.forward_returns(closes, 5)
    ev = np.zeros(n, dtype=bool)
    ev[[20, 80, 140, 200, 250]] = True
    obs = pet.excess_statistic(fwd, labels, ev)
    a = pet.permutation_p(fwd, labels, ev, obs, iters=200)
    assert a == pet.permutation_p(fwd, labels, ev, obs, iters=200)
    assert 0.0 < a <= 1.0


def test_permutation_p_small_for_planted_effect():
    rng = np.random.default_rng(1)
    n = 800
    closes = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
    labels = pet.decile_labels(pet.same_day_returns(closes))
    fwd = pet.forward_returns(closes, 5)
    ev = np.zeros(n, dtype=bool)
    ev[np.arange(10, n - 10, 40)] = True
    fwd_planted = fwd.copy()
    fwd_planted[ev] += 0.05  # plant a clear +5% excess on the events
    obs = pet.excess_statistic(fwd_planted, labels, ev)
    assert pet.permutation_p(fwd_planted, labels, ev, obs, iters=500) < 0.01


def test_event_path_normalizes_to_event_close_and_pads_edges():
    closes = np.arange(1.0, 31.0) * 10.0  # 10, 20, ..., 300
    starts = np.zeros(30, dtype=bool)
    starts[1] = True  # event close = 20 -> 100
    path = pet.event_path(closes, starts, before=5, after=20)
    assert path.shape == (1, 26)
    assert np.isnan(path[0, :4]).all()  # before the sample start
    assert path[0, 5] == pytest.approx(100.0)
    assert path[0, 6] == pytest.approx(150.0)  # next close 30 / 20


def test_grade_applies_registered_rule():
    assert pet.grade(10, 0.01, 0.01, True) == "insufficient"
    assert pet.grade(20, 0.01, 0.01, True) == "edge"
    assert pet.grade(20, 0.01, 0.01, False) == "no edge"
    assert pet.grade(20, 0.04, 0.04, True) == "edge"
    assert pet.grade(20, 0.20, 0.20, True) == "no edge"


def test_horizons_and_primary_match_registration():
    assert pet.HORIZONS == (1, 5, 10, 20)
    assert pet.PRIMARY_HORIZON == 5
    assert pet.MIN_EPISODES == 15
    assert pet.N_PERMUTATIONS == 10_000
    assert pet.SEED == 42
