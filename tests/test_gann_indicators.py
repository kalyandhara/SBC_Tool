"""Tests for the Gann indicator toolkit (should/could-have backlog items)."""

import pytest

from sbc.gann_indicators import (
    apex_reversal,
    harmonic_opens,
    harmonic_vibrations,
    lightning_scalper,
    mega_trend,
    momentum_levels,
    run_indicator,
    wave_levels,
)


def _bars():
    """Eight daily bars with a clear up-trend."""
    rows = [
        ("2026-09-01", 100, 102, 99, 101),
        ("2026-09-02", 101, 103, 100, 102),
        ("2026-09-03", 102, 104, 101, 103),
        ("2026-09-04", 103, 105, 102, 104),
        ("2026-09-07", 104, 106, 103, 105),
        ("2026-09-08", 105, 107, 104, 106),
        ("2026-09-09", 106, 108, 105, 107),
        ("2026-09-10", 107, 109, 106, 108),
    ]
    return [{"date": d, "open": o, "high": h, "low": low, "close": c}
            for d, o, h, low, c in rows]


class TestMomentumLevels:
    def test_bullish_momentum_levels(self):
        result = momentum_levels(_bars())
        assert result["trend"] == "bullish"
        assert result["long"]["trigger"] == 109.0   # swing high
        assert result["long"]["stop_loss"] == 99.0  # swing low
        assert result["short"]["trigger"] == 99.0

    def test_requires_two_bars(self):
        with pytest.raises(ValueError):
            momentum_levels([{"date": "2026-09-10", "open": 1, "high": 2, "low": 0.5, "close": 1.5}])


class TestApexReversal:
    def test_bearish_reversal_near_high(self):
        result = apex_reversal(_bars())
        # close 108 within 3% of range (99-109) of high 109 (>= 108.7? no)
        # 109 - 10*0.03 = 108.7 -> close 108 is below -> no bearish signal
        assert result["signals"] == []

    def test_bearish_reversal_fires_at_extreme(self):
        bars = _bars()
        bars[-1]["close"] = 108.9
        result = apex_reversal(bars)
        assert any(s["direction"] == "bearish" for s in result["signals"])
        sig = next(s for s in result["signals"] if s["direction"] == "bearish")
        assert sig["target"] == 104.0  # range mid
        assert sig["stop_loss"] > 109.0

    def test_bullish_reversal_fires_at_low(self):
        bars = _bars()
        bars[-1]["close"] = 99.2
        result = apex_reversal(bars)
        assert any(s["direction"] == "bullish" for s in result["signals"])


class TestHarmonicOpens:
    def test_period_opens_with_buffers(self):
        result = harmonic_opens(_bars())
        periods = {o["period"]: o for o in result["opens"]}
        assert set(periods) == {"weekly", "monthly", "quarterly", "yearly"}
        assert periods["weekly"]["date"] == "2026-09-07"   # Monday
        assert periods["monthly"]["date"] == "2026-09-01"
        assert periods["yearly"]["date"] == "2026-09-01"   # all bars in 2026
        # buy_above above open, sell_below below open
        assert periods["weekly"]["buy_above"] > periods["weekly"]["open"]
        assert periods["weekly"]["sell_below"] < periods["weekly"]["open"]

    def test_requires_bars(self):
        with pytest.raises(ValueError):
            harmonic_opens([])


class TestHarmonicVibrations:
    def test_eighth_divisions(self):
        result = harmonic_vibrations(_bars(), swing_high=112.0, swing_low=96.0)
        assert result["swing_high"] == 112.0
        assert result["swing_low"] == 96.0
        prices = [lvl["price"] for lvl in result["levels"]]
        assert len(prices) == 7
        assert prices[0] == 98.0    # 96 + 16/8
        assert prices[3] == 104.0   # 4/8 mid
        assert prices[-1] == 110.0  # 7/8
        assert result["levels"][3]["support_resistance"] == "pivot"

    def test_swing_high_must_exceed_low(self):
        with pytest.raises(ValueError):
            harmonic_vibrations(_bars(), swing_high=90.0, swing_low=100.0)


class TestWaveLevels:
    def test_wave_levels_from_prev_day(self):
        result = wave_levels(_bars())
        assert result["reference_date"] == "2026-09-09"
        assert result["prev_day_bias"] == "bullish"
        assert result["bullish"]["valid_above"] == 108.0
        assert result["bearish"]["resistance"] == 108.0

    def test_requires_two_bars(self):
        with pytest.raises(ValueError):
            wave_levels([{"date": "2026-09-10", "open": 1, "high": 2, "low": 0.5, "close": 1.5}])


class TestLightningScalper:
    def test_tight_scalping_levels(self):
        result = lightning_scalper(_bars())
        assert result["buy_above"] == 108.0
        assert result["sell_below"] == 105.0
        assert result["sl_distance"] == 0.3   # 10% of 3-point range
        assert result["target_above"] == 108.6
        assert result["target_below"] == 104.4

    def test_zero_range_raises(self):
        bars = _bars()[:-2] + [
            {"date": "2026-09-11", "open": 108, "high": 108, "low": 108, "close": 108},
            {"date": "2026-09-14", "open": 108, "high": 109, "low": 107, "close": 108},
        ]
        with pytest.raises(ValueError):
            lightning_scalper(bars)


class TestMegaTrend:
    def test_trend_and_levels(self):
        result = mega_trend(_bars())
        assert result["trend"] == "bullish"  # close 108 above mid of year range
        assert result["monthly"]["level"] == 100.0
        assert result["annual"]["level"] == 100.0
        assert result["monthly"]["buy_above"] > 100.0

    def test_requires_bars(self):
        with pytest.raises(ValueError):
            mega_trend([])


class TestRunIndicator:
    def test_unknown_kind_raises(self):
        with pytest.raises(ValueError):
            run_indicator("nope", _bars())

    def test_all_kinds_run(self):
        for kind in ("momentum", "apex_reversal", "harmonic_opens",
                     "harmonic_vibrations", "wave_levels", "lightning_scalper",
                     "mega_trend"):
            assert run_indicator(kind, _bars()) is not None
