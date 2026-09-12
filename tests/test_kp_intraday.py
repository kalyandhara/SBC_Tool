"""Tests for KP Intraday trend change prediction."""

import pytest
from datetime import date
from sbc.kp_intraday import (
    generate_kp_intraday_report,
    generate_sample_kp_csv,
    KPIntradayReport,
    KPDataParser,
    KPRuleEngine,
    KPReportGenerator,
)
from sbc.kp_config import get_config, get_instrument_config
from pathlib import Path
import tempfile
import os


class TestKPConfig:
    """Test KP configuration."""

    def test_get_config(self):
        """get_config should return valid config object."""
        config = get_config()
        assert config is not None
        assert hasattr(config, "to_dict")

    def test_get_instrument_config(self):
        """get_instrument_config should return instrument-specific config."""
        config = get_config()
        for inst in ["NIFTY", "BANK NIFTY", "FINNIFTY"]:
            inst_config = get_instrument_config(inst, config)
            assert inst_config is not None
            assert isinstance(inst_config, dict)
            assert "weights" in inst_config


class TestKPDataParser:
    """Test KP CSV data parsing."""

    def test_parse_sample_csv(self):
        """Should parse generated sample CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test_kp.csv"
            generate_sample_kp_csv(csv_path, "2026-09-01", 3)

            parser = KPDataParser(csv_path)
            data = parser.parse_csv(csv_path)
            assert isinstance(data, list)
            assert len(data) > 0

    def test_parsed_data_structure(self):
        """Parsed rows should have required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test_kp.csv"
            generate_sample_kp_csv(csv_path, "2026-09-01", 3)

            parser = KPDataParser(csv_path)
            data = parser.parse_csv(csv_path)

            for row in data:
                assert "timestamp" in row
                assert "planet" in row
                assert "sign" in row
                assert "star" in row
                assert "sublord" in row


class TestKPRuleEngine:
    """Test KP rule engine."""

    def test_engine_initialization(self):
        """KPRuleEngine should initialize with config."""
        config = get_config()
        inst_config = get_instrument_config("NIFTY", config)
        engine = KPRuleEngine(inst_config)
        assert engine is not None

    def test_compute_day_bias(self):
        """Day bias computation should work."""
        config = get_config()
        inst_config = get_instrument_config("NIFTY", config)
        engine = KPRuleEngine(inst_config)

        # Test with known planet combinations
        score, label = engine.compute_day_bias("Jupiter", "Venus")
        assert isinstance(score, float)
        assert isinstance(label, str)
        assert "bullish" in label or "bearish" in label or "neutral" in label

        score, label = engine.compute_day_bias("Saturn", "Mars")
        assert isinstance(score, float)
        assert isinstance(label, str)
        assert "bullish" in label or "bearish" in label or "neutral" in label


class TestKPIntradayReport:
    """Test full KP intraday report generation."""

    def test_generate_sample_kp_csv(self):
        """Should generate valid CSV file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test_kp.csv"
            generate_sample_kp_csv(csv_path, "2026-09-01", 5)
            assert csv_path.exists()
            assert csv_path.stat().st_size > 0

    def test_generate_kp_intraday_report(self):
        """Should generate complete report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test_kp.csv"
            generate_sample_kp_csv(csv_path, "2026-09-01", 5)

            config = get_config()
            inst_config = get_instrument_config("NIFTY", config)

            report = generate_kp_intraday_report(csv_path, date(2026, 9, 11), "NIFTY", inst_config)

            assert isinstance(report, KPIntradayReport)
            assert report.instrument == "NIFTY"
            assert report.trading_day.isoformat() == "2026-09-11"
            assert hasattr(report, "day_signature")
            assert hasattr(report, "regime_shifts")
            assert hasattr(report, "trend_changes")
            assert hasattr(report, "bullish_windows")
            assert hasattr(report, "bearish_windows")
            assert hasattr(report, "exhaustion_warnings")

    def test_report_serialization(self):
        """Report should serialize to dict properly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test_kp.csv"
            generate_sample_kp_csv(csv_path, "2026-09-01", 5)

            config = get_config()
            inst_config = get_instrument_config("NIFTY", config)

            report = generate_kp_intraday_report(csv_path, date(2026, 9, 11), "NIFTY", inst_config)

            # Check that all sections are present
            assert report.day_signature is not None
            assert isinstance(report.regime_shifts, list)
            assert isinstance(report.trend_changes, list)
            assert isinstance(report.bullish_windows, list)
            assert isinstance(report.bearish_windows, list)