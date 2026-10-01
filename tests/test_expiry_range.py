"""Tests for the Expiry Range Indicator."""

from datetime import date

import pytest

from sbc.expiry_range import (
    backtest_expiry,
    evaluate_expiry_day,
    expiry_range_levels,
    last_weekday_of_month,
    next_expiry,
)


class TestExpiryCalendar:
    """Test expiry calendar helpers."""

    def test_next_expiry_nifty_tuesday(self):
        """NIFTY weekly expiry is the next Tuesday."""
        # 2026-09-11 is a Friday -> next Tuesday is 2026-09-15
        assert next_expiry("NIFTY", date(2026, 9, 11)) == date(2026, 9, 15)
        # Expiry day itself -> same day
        assert next_expiry("NIFTY", date(2026, 9, 15)) == date(2026, 9, 15)
        # Wednesday -> next Tuesday
        assert next_expiry("NIFTY", date(2026, 9, 16)) == date(2026, 9, 22)

    def test_next_expiry_banknifty_monthly(self):
        """BANKNIFTY monthly expiry is the last Thursday of the month."""
        # 2026-09-11 -> last Thursday of Sep 2026 (Sep 1 is Tuesday; Thursdays:
        # 3,10,17,24 -> last = 24... check via helper)
        exp = next_expiry("BANKNIFTY", date(2026, 9, 11))
        assert exp == last_weekday_of_month(2026, 9, 3)
        assert exp.weekday() == 3
        # After this month's expiry -> next month
        after = next_expiry("BANKNIFTY", date(2026, 9, 25))
        assert after == last_weekday_of_month(2026, 10, 3)

    def test_last_weekday_of_month(self):
        """Last Thursday helper returns the last given weekday of the month."""
        from datetime import timedelta
        d = last_weekday_of_month(2026, 12, 3)
        assert d.month == 12
        assert d.weekday() == 3
        # One week later lands in the next month (no more Thursdays in Dec)
        assert (d + timedelta(days=7)).month == 1

    def test_unknown_instrument_defaults_to_tuesday(self):
        assert next_expiry("SENSEX", date(2026, 9, 11)).weekday() == 1


class TestExpiryRangeLevels:
    """Test pivot-based range forecast."""

    def test_levels_from_reference_ohlc(self):
        ohlc = {"open": 100.0, "high": 110.0, "low": 90.0, "close": 105.0}
        levels = expiry_range_levels(ohlc)

        assert levels["pivot"] == round((110 + 90 + 105) / 3, 2)  # 101.67
        r1 = levels["resistances"][0]
        s1 = levels["supports"][0]
        assert r1["price"] == round(2 * 101.66666666666667 - 90, 2)
        assert s1["price"] == round(2 * 101.66666666666667 - 110, 2)
        # Buffer pushes valid breakout thresholds away from the level
        assert r1["valid_above"] > r1["price"]
        assert s1["valid_below"] < s1["price"]

    def test_invalid_ohlc_raises(self):
        with pytest.raises(ValueError):
            expiry_range_levels({"open": 1, "high": 0, "low": 5, "close": 3})
        with pytest.raises(ValueError):
            expiry_range_levels({"open": 1, "high": 5, "low": 0, "close": 3})


class TestEvaluateExpiryDay:
    """Test forecast evaluation against actual expiry OHLC."""

    def _levels(self):
        return expiry_range_levels({"open": 100.0, "high": 110.0, "low": 90.0, "close": 105.0})

    def test_contained_day(self):
        ev = evaluate_expiry_day(self._levels(), {"open": 102, "high": 108, "low": 96, "close": 104})
        assert ev["contained"] is True
        assert ev["breakout_up"] is False
        assert ev["breakout_down"] is False

    def test_false_breakout_up(self):
        """Intraday break above R1 buffer that closes back inside R1 is false."""
        ev = evaluate_expiry_day(self._levels(), {"open": 102, "high": 115, "low": 98, "close": 110})
        assert ev["breakout_up"] is True
        assert ev["false_breakout_up"] is True

    def test_true_breakout_up(self):
        """Break above R1 buffer that closes above R1 is a true breakout."""
        ev = evaluate_expiry_day(self._levels(), {"open": 102, "high": 115, "low": 98, "close": 114})
        assert ev["breakout_up"] is True
        assert ev["false_breakout_up"] is False

    def test_true_breakout_down(self):
        ev = evaluate_expiry_day(self._levels(), {"open": 102, "high": 108, "low": 84, "close": 86})
        assert ev["breakout_down"] is True
        assert ev["false_breakout_down"] is False


class TestBacktestExpiry:
    """Test the expiry backtest harness with synthetic bars."""

    def _synthetic_bars(self):
        """Two weeks of daily bars around two NIFTY Tuesdays (2026-09-08, 2026-09-15)."""
        bars = []
        # Week 1: Mon 07 .. Fri 11; expiry Tuesdays 2026-09-08, 2026-09-15
        # Expiry days stay inside the previous day's S1/R1 buffer -> contained.
        for d, (o, h, low, c) in {
            "2026-09-07": (100, 102, 99, 101),
            "2026-09-08": (101, 102.4, 100.2, 101.8),   # expiry day (contained)
            "2026-09-09": (103, 105, 102, 104),
            "2026-09-10": (104, 106, 103, 105),
            "2026-09-11": (105, 107, 104, 106),
            "2026-09-14": (106, 108, 105, 107),
            "2026-09-15": (107, 108.4, 106.2, 107.5),   # expiry day (contained)
        }.items():
            bars.append({"date": d, "open": o, "high": h, "low": low, "close": c})
        return bars

    def test_backtest_with_synthetic_bars(self):
        result = backtest_expiry("NIFTY", months=1, bars=self._synthetic_bars())
        assert result["instrument"] == "NIFTY"
        assert result["expiry_days_evaluated"] == 2
        for r in result["results"]:
            assert "expiry" in r and "contained" in r
        # Tiny ranges with 0.25% buffer -> both days contained
        assert result["contained_days"] == 2
        assert result["containment_rate"] == 1.0

    def test_backtest_invalid_months(self):
        with pytest.raises(ValueError):
            backtest_expiry("NIFTY", months=0, bars=[])
        with pytest.raises(ValueError):
            backtest_expiry("NIFTY", months=30, bars=[])
