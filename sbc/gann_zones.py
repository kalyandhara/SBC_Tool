"""Gann precision zone classification.

Classifies Gann precision levels (Fibonacci-ratio retracements/extensions of
the swing range) into tradeable zones: purple initiation zones, red target
zones, and black stop-loss / trailing-stop levels. Used by the
/api/gann/precision endpoint and the unified AstroGann Pro signal.
"""

from typing import Any

GANN_ASSET_TICKS = {
    "stocks": 0.05,
    "indices": 0.05,
    "commodities": 1.0,
}


def gann_round(price: float, asset_type: str = "indices") -> float:
    """Round a Gann level to the instrument tick size for the asset type."""
    tick = GANN_ASSET_TICKS.get((asset_type or "indices").lower(), 0.05)
    return round(round(price / tick) * tick, 2)


def classify_gann_zones(
    high: float, low: float, close: float, asset_type: str = "indices"
) -> tuple[dict[str, Any], list[dict[str, Any]], bool]:
    """Classify Gann precision levels into tradeable zones.

    Purple levels mark high-probability initiation zones (retracement entries
    in the direction of the trend), red levels mark target/profit-booking
    zones (extensions), and black levels mark stop-loss and trailing stop.
    Returns (zones, levels, bullish).
    """
    range_ = high - low
    if range_ <= 0:
        range_ = max(abs(close) * 0.01, 0.05)
        low, high = close - range_ / 2, close + range_ / 2

    momentum_ref = low + range_ * 0.5
    bullish = close >= momentum_ref

    levels = []
    for frac in [0.236, 0.382, 0.5, 0.618, 0.786]:
        levels.append({"frac": frac, "price": gann_round(low + range_ * frac, asset_type)})

    def level_at(frac: float, invert: bool = False) -> float:
        price = high - range_ * frac if invert else low + range_ * frac
        return gann_round(price, asset_type)

    if bullish:
        zones = {
            "trend": "bullish",
            "initiation": [
                {"price": level_at(0.382), "frac": 0.382, "label": "buy-on-dip"},
                {"price": level_at(0.5), "frac": 0.5, "label": "deep buy-on-dip"},
            ],
            "target": [
                {"price": level_at(0.618), "frac": 0.618, "label": "target 1"},
                {"price": level_at(0.786), "frac": 0.786, "label": "target 2"},
                {"price": gann_round(high, asset_type), "frac": 1.0, "label": "swing high"},
            ],
            "stop_loss": [
                {"price": gann_round(low, asset_type), "frac": 0.0, "label": "swing low"},
            ],
            "trailing_stop": [
                {"price": level_at(0.236), "frac": 0.236, "label": "trailing SL"},
            ],
        }
    else:
        zones = {
            "trend": "bearish",
            "initiation": [
                {"price": level_at(0.382, invert=True), "frac": 0.382, "label": "sell-on-rise"},
                {"price": level_at(0.5, invert=True), "frac": 0.5, "label": "deep sell-on-rise"},
            ],
            "target": [
                {"price": level_at(0.618, invert=True), "frac": 0.618, "label": "target 1"},
                {"price": level_at(0.786, invert=True), "frac": 0.786, "label": "target 2"},
                {"price": gann_round(low, asset_type), "frac": 0.0, "label": "swing low"},
            ],
            "stop_loss": [
                {"price": gann_round(high, asset_type), "frac": 1.0, "label": "swing high"},
            ],
            "trailing_stop": [
                {"price": level_at(0.236, invert=True), "frac": 0.236, "label": "trailing SL"},
            ],
        }
    return zones, levels, bullish


__all__ = ["classify_gann_zones", "gann_round", "GANN_ASSET_TICKS"]
