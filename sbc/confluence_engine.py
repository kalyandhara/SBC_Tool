"""Astro-technical confluence decision engine: combines technical crossovers with astrological bias filters."""

from numbers import Real
from typing import Literal

import numpy as np


def detect_ma_cross(fast_ma: np.ndarray, slow_ma: np.ndarray) -> np.ndarray:
    """Detect bullish (+1) and bearish (-1) crossovers on closed bars.

    The first bar has no prior bar, so it can never be a cross. NaN values
    (e.g. EMA warm-up) never produce a cross.
    """
    diff = np.asarray(fast_ma, dtype=float) - np.asarray(slow_ma, dtype=float)
    prev_diff = np.roll(diff, 1)
    prev_diff[0] = np.nan

    cross = np.zeros(len(diff), dtype=int)
    cross[(prev_diff <= 0) & (diff > 0)] = 1
    cross[(prev_diff >= 0) & (diff < 0)] = -1
    return cross


def confluence_signal(
    technical_cross: int,
    astro_bias: Literal["bullish", "bearish", "neutral"] | float,
    astro_threshold: float = 0.0,
) -> Literal["BUY", "SELL", "HOLD"]:
    """Generate trade signal when technical cross aligns with astrological bias."""
    numeric_bias = isinstance(astro_bias, Real) and not isinstance(astro_bias, bool)
    if technical_cross == 1 and (
        astro_bias == "bullish" or (numeric_bias and astro_bias > astro_threshold)
    ):
        return "BUY"
    if technical_cross == -1 and (
        astro_bias == "bearish" or (numeric_bias and astro_bias < -astro_threshold)
    ):
        return "SELL"
    return "HOLD"


def net_trade_return(gross_return: float, round_trip_cost_pct: float = 0.20) -> float:
    """Calculate net return after subtracting transaction costs (in percent)."""
    return gross_return - (round_trip_cost_pct / 100.0)
