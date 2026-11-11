import numpy as np
import pytest

from sbc.confluence_engine import confluence_signal, detect_ma_cross, net_trade_return


def test_detect_ma_cross():
    fast = np.array([10.0, 10.0, 12.0, 11.0, 9.0])
    slow = np.array([11.0, 11.0, 11.0, 11.0, 11.0])
    # diff = [-1, -1, 1, 0, -2]
    cross = detect_ma_cross(fast, slow)
    assert cross[2] == 1
    assert cross[4] == -1
    assert list(cross) == [0, 0, 1, 0, -1]


def test_detect_ma_cross_first_bar_never_cross():
    fast = np.array([12.0, 13.0])
    slow = np.array([11.0, 11.0])
    cross = detect_ma_cross(fast, slow)
    assert cross[0] == 0


def test_detect_ma_cross_nan_warmup_no_cross():
    fast = np.array([np.nan, np.nan, 12.0, 13.0])
    slow = np.array([11.0, 11.0, 11.0, 11.0])
    cross = detect_ma_cross(fast, slow)
    # First valid bar follows NaN, so it is not treated as a crossover
    assert list(cross) == [0, 0, 0, 0]


def test_detect_ma_cross_flat_bar_then_cross():
    fast = np.array([10.0, 11.0, 11.0, 12.0])
    slow = np.array([11.0, 11.0, 11.0, 11.0])
    # diff = [-1, 0, 0, 1]: bullish cross occurs on bar 3 after flat bars
    cross = detect_ma_cross(fast, slow)
    assert list(cross) == [0, 0, 0, 1]


def test_detect_ma_cross_bearish_after_flat_bar():
    fast = np.array([12.0, 11.0, 10.0])
    slow = np.array([11.0, 11.0, 11.0])
    # diff = [1, 0, -1]
    cross = detect_ma_cross(fast, slow)
    assert list(cross) == [0, 0, -1]


def test_detect_ma_cross_no_cross_when_trending_one_way():
    fast = np.array([10.0, 11.0, 12.0, 13.0])
    slow = np.array([11.0, 11.0, 11.0, 11.0])
    cross = detect_ma_cross(fast, slow)
    # Only one crossover (bullish at bar 2), no repeat signals while above
    assert list(cross) == [0, 0, 1, 0]


def test_confluence_signal_aligned():
    assert confluence_signal(1, "bullish") == "BUY"
    assert confluence_signal(-1, "bearish") == "SELL"
    assert confluence_signal(1, 1.5, astro_threshold=0.5) == "BUY"
    assert confluence_signal(-1, -1.5, astro_threshold=0.5) == "SELL"


def test_confluence_signal_filtered():
    # Technical bull cross but astro is bearish -> HOLD
    assert confluence_signal(1, "bearish") == "HOLD"
    # Technical bear cross but astro is bullish -> HOLD
    assert confluence_signal(-1, "bullish") == "HOLD"
    # No technical cross -> HOLD
    assert confluence_signal(0, "bullish") == "HOLD"
    assert confluence_signal(0, 1.0) == "HOLD"


def test_confluence_neutral_rejected():
    assert confluence_signal(1, "neutral") == "HOLD"
    assert confluence_signal(-1, "neutral") == "HOLD"
    assert confluence_signal(1, 0.0) == "HOLD"
    assert confluence_signal(-1, 0.0) == "HOLD"


def test_confluence_threshold_boundary():
    # Strictly greater than threshold is required
    assert confluence_signal(1, 0.5, astro_threshold=0.5) == "HOLD"
    assert confluence_signal(-1, -0.5, astro_threshold=0.5) == "HOLD"
    assert confluence_signal(1, 0.51, astro_threshold=0.5) == "BUY"


def test_confluence_numeric_bias_directional():
    # Numeric bias of the wrong sign rejects the cross
    assert confluence_signal(1, -1.0) == "HOLD"
    assert confluence_signal(-1, 1.0) == "HOLD"
    assert confluence_signal(1, 1.0) == "BUY"
    assert confluence_signal(-1, -1.0) == "SELL"


def test_confluence_numpy_numeric_bias():
    assert confluence_signal(1, np.float64(1.0)) == "BUY"
    assert confluence_signal(-1, np.int64(-1)) == "SELL"


def test_confluence_nan_bias_rejected():
    assert confluence_signal(1, float("nan")) == "HOLD"
    assert confluence_signal(-1, float("nan")) == "HOLD"


def test_net_trade_return():
    gross = 0.01  # +1.0%
    net = net_trade_return(gross, round_trip_cost_pct=0.20)
    assert net == pytest.approx(0.008, abs=1e-9)  # +0.8%


def test_net_trade_return_default_cost():
    assert net_trade_return(0.01) == pytest.approx(0.008, abs=1e-9)


def test_net_trade_return_negative_gross():
    assert net_trade_return(-0.01) == pytest.approx(-0.012, abs=1e-9)


def test_net_trade_return_zero_cost():
    assert net_trade_return(0.015, round_trip_cost_pct=0.0) == pytest.approx(0.015)
