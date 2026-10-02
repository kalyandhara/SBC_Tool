"""Tests for the unified AstroGann Pro signal."""

import pytest

from sbc.astrogann import (
    GANN_ZONE_SCORE,
    combine_astrogann,
    gann_zone_score_for_price,
)
from sbc.gann_zones import classify_gann_zones


class TestCombineAstrogann:
    """Test the astro + Gann blend."""

    def test_weights_must_be_valid(self):
        with pytest.raises(ValueError):
            combine_astrogann(1.0, 1.0, astro_weight=0, gann_weight=0)
        with pytest.raises(ValueError):
            combine_astrogann(1.0, 1.0, astro_weight=-1, gann_weight=2)

    def test_bullish_when_both_agree(self):
        result = combine_astrogann(3.0, 1.0)
        assert result["signal"] == "BULLISH"
        assert result["strength"] == "STRONG"
        assert result["net"] == pytest.approx(1.0)

    def test_bearish_when_both_agree(self):
        result = combine_astrogann(-3.0, -1.0)
        assert result["signal"] == "BEARISH"
        assert result["strength"] == "STRONG"

    def test_neutral_when_conflicting(self):
        result = combine_astrogann(3.0, -1.0)
        assert result["signal"] == "NEUTRAL"
        # 0.6*1 + 0.4*(-1) = 0.2 -> below threshold
        assert result["net"] == pytest.approx(0.2)

    def test_moderate_strength(self):
        result = combine_astrogann(3.0, 0.0)
        # 0.6*1 + 0.4*0 = 0.6 -> STRONG boundary
        assert result["signal"] == "BULLISH"
        assert result["strength"] in ("MODERATE", "STRONG")

    def test_components_normalized(self):
        result = combine_astrogann(6.0, 2.0)  # both beyond range
        assert result["astro_component"] == 1.0
        assert result["gann_component"] == 1.0

    def test_custom_weights(self):
        result = combine_astrogann(3.0, -1.0, astro_weight=0.5, gann_weight=0.5)
        assert result["net"] == pytest.approx(0.0)
        assert result["signal"] == "NEUTRAL"


class TestGannZoneScoreForPrice:
    """Test price position reading within Gann zones."""

    def _zones(self, close):
        zones, _, _ = classify_gann_zones(110.0, 90.0, close, "indices")
        return zones

    def test_bullish_trend_discount(self):
        """Price in the initiation zone of a bullish trend is a discount."""
        zones = self._zones(close=100.0)  # bullish
        read = gann_zone_score_for_price(97.63, zones)  # ~0.382 level
        assert read["trend"] == "bullish"
        assert read["zone"] in ("discount", "deep_discount")
        assert read["score"] > 0

    def test_bullish_trend_stretched_above_targets(self):
        zones = self._zones(close=100.0)
        read = gann_zone_score_for_price(111.0, zones)  # above swing high
        assert read["zone"] == "stretched"
        assert read["score"] < 0

    def test_bullish_trend_neutral_midzone(self):
        zones = self._zones(close=100.0)
        read = gann_zone_score_for_price(103.0, zones)
        assert read["zone"] == "neutral"
        assert read["score"] == 0.0

    def test_bearish_trend_deep_stretched(self):
        """Price in the initiation zone of a bearish trend is stretched."""
        zones = self._zones(close=100.0 - 5.0)  # close below mid -> bearish
        read = gann_zone_score_for_price(103.0, zones)
        assert read["trend"] == "bearish"
        assert read["zone"] in ("stretched", "deep_stretched")
        assert read["score"] < 0

    def test_unknown_zones(self):
        read = gann_zone_score_for_price(100.0, {})
        assert read["zone"] == "unknown"
        assert read["score"] == 0.0

    def test_zone_score_constant(self):
        assert GANN_ZONE_SCORE["deep_discount"] == 1.0
        assert GANN_ZONE_SCORE["deep_stretched"] == -1.0
