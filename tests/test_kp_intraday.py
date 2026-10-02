"""Tests for KP Intraday trend change prediction."""

import tempfile
from datetime import date, datetime, time
from pathlib import Path

import pytest

from sbc.kp_config import get_config, get_instrument_config
from sbc.kp_intraday import (
    DayChartSignature,
    Direction,
    HoraQuality,
    HoraSlot,
    KPDataParser,
    KPIntradayReport,
    KPRuleEngine,
    RegimeShift,
    SignalGrade,
    TrendChangeSignal,
    WindowScore,
    build_cumulative_path,
    generate_kp_intraday_report,
    generate_sample_kp_csv,
)


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


def _make_synthetic_report(trading_day=None):
    """Hand-built report for deterministic cumulative path tests."""
    trading_day = trading_day or date(2026, 9, 11)
    day_signature = DayChartSignature(
        day_lord="Jupiter",
        moon_sign="Cancer",
        moon_star="Pushya",
        opening_sublord="Venus",
        moon_speed=13.2,
        day_bias_score=1.0,
        day_bias_label="Day-level bias (Day Lord + Moon Star Lord): +1.00 -> bullish.",
        moon_affliction_gate="Moon Affliction Gate (Rule A-14): PASSED.",
        hora_slots=[
            HoraSlot(start=time(9, 15), end=time(10, 15), lord="Jupiter", quality=HoraQuality.FRUITFUL),
            HoraSlot(start=time(10, 15), end=time(11, 15), lord="Saturn", quality=HoraQuality.SLUGGISH),
            HoraSlot(start=time(11, 15), end=time(12, 15), lord="Moon", quality=HoraQuality.NEUTRAL),
        ],
    )
    regime_shifts = [
        RegimeShift(
            timestamp=time(10, 15),
            planet="Moon",
            old_sublord="Venus",
            new_sublord="Rahu",
            house_set_strength=2.0,
            regime_label="sell-on-rise",
            direction=Direction.BEARISH,
        ),
    ]
    trend_changes = [
        TrendChangeSignal(
            timestamp=time(10, 15),
            grade=SignalGrade.REGIME_SHIFT,
            direction=Direction.BEARISH,
            trigger="Moon sub change Venus->Rahu",
            asc_sub_house_set="2",
            hora_lord="Saturn",
            score=4.0,
        ),
    ]
    bullish_windows = [
        WindowScore(start=time(9, 15), end=time(9, 30), score=2.5, direction=Direction.BULLISH),
    ]
    bearish_windows = [
        WindowScore(start=time(10, 15), end=time(10, 30), score=3.0, direction=Direction.BEARISH),
    ]
    return KPIntradayReport(
        trading_day=trading_day,
        instrument="NIFTY",
        market="NSE Mumbai",
        ayanamsa="KP Ayanamsha",
        source_file="synthetic.csv",
        generated_at=datetime.now(),
        brand="test",
        day_signature=day_signature,
        regime_shifts=regime_shifts,
        trend_changes=trend_changes,
        bullish_windows=bullish_windows,
        bearish_windows=bearish_windows,
        strongest_bullish=bullish_windows[0],
        strongest_bearish=bearish_windows[0],
        exhaustion_warnings=[],
    )


class TestBuildCumulativePath:
    """Test the build_cumulative_path helper."""

    def test_basic_shape_from_report(self):
        """Path should cover the NSE session with expected keys."""
        report = _make_synthetic_report()
        path = build_cumulative_path(report, step_minutes=60)

        assert isinstance(path, list)
        assert len(path) == 7  # 09:15 .. 15:15 hourly
        assert path[0]["time"] == "09:15"
        assert path[-1]["time"] == "15:15"
        for point in path:
            for key in ("time", "cumulative", "score", "hora_lord", "hora_quality",
                        "regime_delta", "window_delta", "dl_hora", "dahan",
                        "chand_vat", "markers"):
                assert key in point
            assert isinstance(point["dl_hora"], bool)
            assert isinstance(point["dahan"], bool)
            assert isinstance(point["chand_vat"], bool)
            assert isinstance(point["markers"], list)

    def test_cumulative_matches_running_sum(self):
        """Cumulative at each point equals the running sum of scores."""
        report = _make_synthetic_report()
        path = build_cumulative_path(report, step_minutes=60)

        running = 0.0
        for point in path:
            running = round(running + point["score"], 3)
            assert point["cumulative"] == pytest.approx(running, abs=1e-6)

    def test_hora_quality_contribution(self):
        """Fruitful Jupiter hora scores +0.5; Sluggish Saturn hora scores -0.5."""
        report = _make_synthetic_report()
        path = build_cumulative_path(report, step_minutes=60)

        by_time = {p["time"]: p for p in path}
        assert by_time["09:15"]["hora_lord"] == "Jupiter"
        assert by_time["09:15"]["hora_quality"] == pytest.approx(0.5)
        assert by_time["10:15"]["hora_lord"] == "Saturn"
        assert by_time["10:15"]["hora_quality"] == pytest.approx(-0.5)

    def test_regime_shift_delta_applied(self):
        """Bearish regime shift at 10:15 contributes -1.5 to that interval only."""
        report = _make_synthetic_report()
        path = build_cumulative_path(report, step_minutes=60)

        by_time = {p["time"]: p for p in path}
        assert by_time["10:15"]["regime_delta"] == pytest.approx(-1.5)
        assert by_time["11:15"]["regime_delta"] == pytest.approx(0.0)

    def test_window_votes_applied(self):
        """Active windows contribute ±1.0 per window within their span."""
        report = _make_synthetic_report()
        path = build_cumulative_path(report, step_minutes=15)

        by_time = {p["time"]: p for p in path}
        assert by_time["09:15"]["window_delta"] == pytest.approx(1.0)
        assert by_time["09:30"]["window_delta"] == pytest.approx(0.0)
        assert by_time["10:15"]["window_delta"] == pytest.approx(-1.0)

    def test_flags_fire_on_expected_conditions(self):
        """DL-hora fires on day-lord hora; Dahan on malefic downgraded hora;
        Chand-Vat on benefic hora with non-negative quality."""
        report = _make_synthetic_report()
        path = build_cumulative_path(report, step_minutes=60)

        by_time = {p["time"]: p for p in path}
        # Day lord is Jupiter; 09:15 hora is Jupiter (Fruitful) -> DL-hora
        assert by_time["09:15"]["dl_hora"] is True
        # 10:15 hora is Saturn (Sluggish, malefic) -> Dahan
        assert by_time["10:15"]["dahan"] is True
        # 11:15 hora is Moon (Neutral benefic) -> Chand-Vat
        assert by_time["11:15"]["chand_vat"] is True

    def test_markers_present_at_signal_times(self):
        """Signal markers attach to the interval matching the signal timestamp."""
        report = _make_synthetic_report()
        path = build_cumulative_path(report, step_minutes=60)

        by_time = {p["time"]: p for p in path}
        assert len(by_time["10:15"]["markers"]) == 1
        assert by_time["10:15"]["markers"][0]["grade"] == "REGIME SHIFT"
        assert by_time["10:15"]["markers"][0]["direction"] == "Bearish"
        assert by_time["09:15"]["markers"] == []

    def test_fifteen_minute_steps_cover_session(self):
        """15-minute steps produce 26 points covering 09:15..15:30."""
        report = _make_synthetic_report()
        path = build_cumulative_path(report, step_minutes=15)

        assert len(path) == 26
        assert path[0]["time"] == "09:15"
        assert path[-1]["time"] == "15:30"

    def test_invalid_step_minutes_raises(self):
        """Non-positive step_minutes should raise ValueError."""
        report = _make_synthetic_report()
        with pytest.raises(ValueError):
            build_cumulative_path(report, step_minutes=0)
        with pytest.raises(ValueError):
            build_cumulative_path(report, step_minutes=-15)

    def test_deterministic_output(self):
        """Same report should produce identical output on repeated calls."""
        report = _make_synthetic_report()
        assert build_cumulative_path(report) == build_cumulative_path(report)

    def test_works_with_csv_generated_report(self):
        """Helper should work on a full report generated from sample CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "test_kp.csv"
            generate_sample_kp_csv(csv_path, "2026-09-01", 5)

            config = get_config()
            inst_config = get_instrument_config("NIFTY", config)
            report = generate_kp_intraday_report(csv_path, date(2026, 9, 11), "NIFTY", inst_config)

            path = build_cumulative_path(report, step_minutes=60)
            assert isinstance(path, list)
            assert len(path) == 7
            running = 0.0
            for point in path:
                running = round(running + point["score"], 3)
                assert point["cumulative"] == pytest.approx(running, abs=1e-6)


class TestKPDataQuality:
    """assess_kp_data flags files that are not real ephemeris output."""

    def test_consistent_rows_pass(self):
        from sbc.kp_intraday import _KP_SIGNS, _KP_STARS, assess_kp_data
        rows = [{"star": _KP_STARS[int(lon // (40 / 3))], "sign": _KP_SIGNS[int(lon // 30)]}
                for lon in [x * 0.25 + 0.01 for x in range(1440)]]  # off exact boundaries
        dq = assess_kp_data(rows)
        assert dq["rows_checked"] == 1440
        assert dq["impossible_rows"] == 0
        assert dq["synthetic"] is False

    def test_random_sample_file_is_flagged(self, tmp_path):
        import csv
        from datetime import date
        from sbc.kp_intraday import assess_kp_data, generate_sample_kp_csv
        path = tmp_path / "KP_Data_Dec2026.csv"
        generate_sample_kp_csv(path, date(2026, 12, 1), 3)
        with open(path, encoding="utf-8") as f:
            dq = assess_kp_data(list(csv.DictReader(f)))
        assert dq["synthetic"] is True
        assert dq["impossible_pct"] > 50

    def test_report_and_path_carry_data_quality(self, client):
        rep = client.get("/api/kp_intraday_report?date=2026-09-15&instrument=NIFTY").get_json()
        assert "data_quality" in rep and "synthetic" in rep["data_quality"]
        path = client.get("/api/engine/intraday_path?date=2026-09-15&instrument=NIFTY").get_json()
        assert path["data_quality"] == rep["data_quality"]
