"""Tests for crash analyzer."""

import pytest
from sbc.crash_analyzer import (
    analyze_crash_risk,
    daily_crash_briefing,
    backtest_crashes,
)


class TestCrashAnalyzer:
    """Test crash risk analysis."""

    def test_analyze_crash_risk_returns_structure(self):
        """analyze_crash_risk should return complete analysis."""
        result = analyze_crash_risk("2026-09-11")

        assert isinstance(result, object)
        assert hasattr(result, "date")
        assert hasattr(result, "crash_score")
        assert hasattr(result, "market_condition")
        assert hasattr(result, "signatures")
        assert hasattr(result, "signature_details")
        assert hasattr(result, "jupiter_analysis")
        assert hasattr(result, "jupiter_saturn_angle")
        assert hasattr(result, "jupiter_saturn_aspect")
        assert hasattr(result, "mars_ketu_angle")
        assert hasattr(result, "confluence")
        assert hasattr(result, "applicable_setups")
        assert hasattr(result, "tradingview_links")
        assert hasattr(result, "research_package")

    def test_crash_score_range(self):
        """Crash score should be non-negative."""
        result = analyze_crash_risk("2026-09-11")
        assert result.crash_score >= 0

    def test_market_condition_values(self):
        """Market condition should be one of expected values."""
        result = analyze_crash_risk("2026-09-11")
        valid_conditions = {"NORMAL", "ELEVATED_RISK", "CORRECTION_RISK", "CRASH_RISK"}
        assert result.market_condition in valid_conditions

    def test_jupiter_analysis_structure(self):
        """Jupiter analysis should have active flag and level."""
        result = analyze_crash_risk("2026-09-11")
        ja = result.jupiter_analysis
        assert isinstance(ja, dict)
        assert "active" in ja
        assert "level" in ja
        assert "bias" in ja
        assert "reasons" in ja

    def test_confluence_structure(self):
        """Confluence should have overall signal and weights."""
        result = analyze_crash_risk("2026-09-11")
        conf = result.confluence
        assert isinstance(conf, dict)
        assert "overall" in conf
        assert "highlights" in conf
        overall = conf["overall"]
        assert "signal" in overall
        assert "bullish_weight" in overall
        assert "bearish_weight" in overall
        assert "net" in overall


class TestDailyCrashBriefing:
    """Test daily crash briefing."""

    def test_daily_crash_briefing_returns_string(self):
        """daily_crash_briefing should return formatted string."""
        briefing = daily_crash_briefing("2026-09-11")
        assert isinstance(briefing, str)
        assert len(briefing) > 0


class TestBacktestCrashes:
    """Test crash backtesting."""

    def test_backtest_crashes_returns_list(self):
        """backtest_crashes should return list of results."""
        results = backtest_crashes()
        assert isinstance(results, list)
        assert len(results) > 0

    def test_backtest_result_structure(self):
        """Each backtest result should have required fields."""
        results = backtest_crashes()
        for r in results:
            assert "date" in r
            assert "crash_score" in r
            assert "condition" in r
            # Historical event format uses 'name' instead of 'signatures'
            assert "name" in r or "signatures" in r