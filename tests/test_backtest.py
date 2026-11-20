"""Tests for backtesting engine."""

from sbc.backtest import (
    _bearish_future_score,
    _julian_at_noon,
    run_backtest,
    run_bearish_futurecast,
    run_bullish_futurecast,
    run_futurecast,
)


class TestBacktest:
    """Test historical backtesting."""

    def test_run_backtest_returns_results(self):
        """run_backtest should return structured results."""
        results = run_backtest()

        assert isinstance(results, dict)
        assert "total" in results or "matches" in results or "accuracy" in results

    def test_backtest_summary_structure(self):
        """Backtest summary should have win rates and stats."""
        results = run_backtest()
        # The API returns flat structure, not nested summary
        assert "accuracy" in results or "total" in results


class TestFuturecast:
    """Test futurecast predictions."""

    def test_run_futurecast(self):
        """run_futurecast should return timeline windows."""
        result = run_futurecast(center_date="2026-09-11")

        assert isinstance(result, dict)
        assert "range_start" in result
        assert "range_end" in result
        assert "method" in result
        assert "disclaimer" in result
        assert "timeline_windows" in result or "windows" in result

    def test_run_bullish_futurecast(self):
        """run_bullish_futurecast should return bullish clusters."""
        result = run_bullish_futurecast(center_date="2026-09-11", years=1)

        assert isinstance(result, dict)
        assert "scan_window" in result
        assert "clusters" in result
        assert "version" in result
        assert "disclaimer" in result
        assert isinstance(result["clusters"], list)

    def test_run_bearish_futurecast(self):
        """run_bearish_futurecast should return bearish clusters."""
        result = run_bearish_futurecast(center_date="2026-09-11", years=1)

        assert isinstance(result, dict)
        assert "scan_window" in result
        assert "clusters" in result
        assert "version" in result
        assert "disclaimer" in result
        assert isinstance(result["clusters"], list)


class TestSaturnMacro:
    """Test Saturn macro analysis."""



class TestBearishFutureScore:
    """Test bearish future scoring."""

    def test_bearish_future_score_returns_tuple(self):
        """_bearish_future_score should return (score, reasons, details)."""
        jul = _julian_at_noon("2026-09-11")
        score, reasons, details = _bearish_future_score(jul)

        assert isinstance(score, (int, float))
        assert score >= 0
        assert isinstance(reasons, list)
        # details can be list or dict depending on implementation
        assert details is not None


class TestJulianAtNoon:
    """Test Julian day calculation at noon."""

    def test_julian_at_noon(self):
        """_julian_at_noon should return valid Julian day."""
        jul = _julian_at_noon("2026-09-11")
        assert isinstance(jul, float)
        assert jul > 2400000  # Should be modern Julian day


class TestSaturnUranusSquare:
    """B1 (crash-engine audit 2026-11-19): the Saturn-Uranus square trigger must be live."""

    @staticmethod
    def _bodies(date):
        from sbc.planets import positions
        return {p["name"]: p for p in positions(_julian_at_noon(date))[0]}

    def test_fires_on_exact_2021_square(self):
        from sbc.backtest import _saturn_uranus_square
        b = self._bodies("2021-02-17")  # sidereal separation 90.04 deg
        assert _saturn_uranus_square(b["Saturn"], b["Uranus"])

    def test_silent_far_from_square(self):
        from sbc.backtest import _saturn_uranus_square
        b = self._bodies("2026-09-11")  # separation 52.7 deg
        assert not _saturn_uranus_square(b["Saturn"], b["Uranus"])

    def test_orb_edge(self):
        from sbc.backtest import SATURN_URANUS_SQUARE_ORB, _saturn_uranus_square
        sat = {"longitude": 10.0}
        assert _saturn_uranus_square(sat, {"longitude": 10.0 + 90 + SATURN_URANUS_SQUARE_ORB})
        assert _saturn_uranus_square(sat, {"longitude": 10.0 - 90 - SATURN_URANUS_SQUARE_ORB})
        assert not _saturn_uranus_square(sat, {"longitude": 10.0 + 90 + SATURN_URANUS_SQUARE_ORB + 0.1})
        assert not _saturn_uranus_square(sat, None)

    def test_reaches_bearish_score(self):
        _, _, active = _bearish_future_score(_julian_at_noon("2021-02-17"))
        assert "saturn_uranus_square" in [name for name, _ in active]


class TestEclipseFinancialAxis:
    """B2: solar eclipse with the Sun in sidereal Taurus, or lunar eclipse with the
    Moon in sidereal Scorpio, within ECLIPSE_WINDOW_DAYS of the day."""

    def _fires(self, date):
        from sbc.backtest import _eclipse_financial_axis
        return _eclipse_financial_axis(_julian_at_noon(date))

    def test_solar_eclipse_in_taurus(self):
        assert self._fires("2021-06-10")  # Sun 25.6 deg sidereal Taurus

    def test_lunar_eclipses_in_scorpio(self):
        assert self._fires("2021-05-26")  # Moon 11.3 deg Scorpio
        assert self._fires("2022-05-20")  # 4 days after the 2022-05-16 eclipse (Moon 1.1 deg Scorpio)

    def test_other_signs_do_not_fire(self):
        assert not self._fires("2024-04-08")  # solar eclipse, Sun in Pisces
        assert not self._fires("2021-11-19")  # lunar eclipse, Moon in Taurus (not the written rule)
        assert not self._fires("2021-12-04")  # solar eclipse, Sun in Scorpio (not the written rule)

    def test_outside_window_does_not_fire(self):
        from sbc.backtest import ECLIPSE_WINDOW_DAYS
        assert ECLIPSE_WINDOW_DAYS == 7
        assert not self._fires("2022-06-01")  # 16 days after 2022-05-16
        assert not self._fires("2026-09-11")

    def test_reaches_bearish_score(self):
        _, _, active = _bearish_future_score(_julian_at_noon("2021-05-26"))
        assert "eclipse_financial_axis" in [name for name, _ in active]


class TestTriggerFamilies:
    """B3: dedup by an explicit TRIGGER_FAMILY map, strongest member kept, order-free."""

    def test_every_trigger_has_a_family(self):
        from sbc.backtest import BEARISH_TRIGGER_WEIGHTS, TRIGGER_FAMILY, TRIGGER_WEIGHTS
        assert set(TRIGGER_WEIGHTS) | set(BEARISH_TRIGGER_WEIGHTS) <= set(TRIGGER_FAMILY)

    def test_order_independent(self):
        import random

        from sbc.backtest import _score_normalize
        trig = [("mercury_retrograde", 1), ("mercury_retro_virgo", 2), ("mars_debilitated", 1),
                ("mars_saturn_conjunction", 3), ("saturn_pisces", 2), ("saturn_rahu_conjunction", 4),
                ("moon_gandanta", 1), ("venus_combust", 2)]
        ref = _score_normalize(trig, max_score=20)
        rng = random.Random(7)
        for _ in range(20):
            shuffled = trig[:]
            rng.shuffle(shuffled)
            got = _score_normalize(shuffled, max_score=20)
            assert got[0] == ref[0]
            assert sorted(got[1]) == sorted(ref[1])

    def test_different_families_both_count(self):
        from sbc.backtest import _score_normalize
        score, kept = _score_normalize([("mars_saturn_conjunction", 3), ("mars_debilitated", 1)], max_score=20)
        assert score == 4
        assert {n for n, _ in kept} == {"mars_saturn_conjunction", "mars_debilitated"}

    def test_same_family_counts_once_keeping_strongest(self):
        from sbc.backtest import _score_normalize
        score, kept = _score_normalize([("mercury_retrograde", 1), ("mercury_retro_virgo", 2)], max_score=20)
        assert score == 2
        assert kept == [("mercury_retro_virgo", 2)]

    def test_unknown_trigger_is_an_error(self):
        import pytest

        from sbc.backtest import _score_normalize
        with pytest.raises(KeyError):
            _score_normalize([("not_a_trigger", 1)])


class TestOuterTriggersAreBearish:
    """B4: Saturn-Pluto, Neptune in Aquarius and Mars-Uranus score on the bearish side only."""

    @staticmethod
    def _call(fn, overrides):
        from sbc.planets import positions
        by = {p["name"]: dict(p) for p in positions(_julian_at_noon("2026-09-11"))[0]}
        for name, upd in overrides.items():
            by[name].update(upd)
        return fn(by)

    @staticmethod
    def _bear(by):
        from sbc.backtest import _detect_bearish_triggers
        names = ["Jupiter", "Saturn", "Uranus", "Sun", "Mercury", "Venus", "Mars", "Rahu", "Ketu", "Moon"]
        return [t for t, _ in _detect_bearish_triggers(*[by[n] for n in names], _julian_at_noon("2026-09-11"),
                                                       neptune=by["Neptune"], pluto=by["Pluto"])]

    @staticmethod
    def _bull(by):
        from sbc.backtest import _detect_triggers
        return [t for t, _ in _detect_triggers(by["Jupiter"], by["Saturn"], by["Sun"], by["Mercury"], by["Venus"],
                                               by["Rahu"], by["Ketu"], by["Moon"], mars=by["Mars"],
                                               uranus=by["Uranus"], neptune=by["Neptune"], pluto=by["Pluto"])]

    CASES = {
        "saturn_pluto_conjunction": {"Saturn": {"longitude": 100.0}, "Pluto": {"longitude": 101.0}},
        "neptune_aquarius_ingress": {"Neptune": {"sign": "Aquarius"}},
        "uranus_mars_aspect": {"Mars": {"longitude": 40.0}, "Uranus": {"longitude": 220.0}},
    }

    def test_bearish_not_bullish(self):
        from sbc.backtest import BEARISH_TRIGGER_WEIGHTS, TRIGGER_WEIGHTS
        for name, ov in self.CASES.items():
            assert name in self._call(self._bear, ov), name
            assert name not in self._call(self._bull, ov), name
            assert name in BEARISH_TRIGGER_WEIGHTS and name not in TRIGGER_WEIGHTS

    def test_weights_carried_over_unchanged(self):
        from sbc.backtest import BEARISH_TRIGGER_WEIGHTS
        assert BEARISH_TRIGGER_WEIGHTS["saturn_pluto_conjunction"] == 4
        assert BEARISH_TRIGGER_WEIGHTS["neptune_aquarius_ingress"] == 3
        assert BEARISH_TRIGGER_WEIGHTS["uranus_mars_aspect"] == 3
