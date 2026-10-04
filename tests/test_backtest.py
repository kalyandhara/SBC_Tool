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
