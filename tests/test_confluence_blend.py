"""Tests for the unified daily forecast contract (blend + engine endpoint)."""

import pytest

from sbc.confluence import blend_forecast_scores


class TestBlendForecastScores:
    """Test component blending with weight renormalisation."""

    def test_all_components_available(self):
        result = blend_forecast_scores(
            {"sbc": 1.0, "kp": 0.5, "kota": -1.0},
            {"sbc": 0.4, "kp": 0.4, "kota": 0.2},
        )
        # 0.4*1 + 0.4*0.5 + 0.2*(-1) = 0.4
        assert result["net"] == pytest.approx(0.4)
        assert result["verdict"] == "BULLISH"
        assert result["weights_used"]["sbc"] == pytest.approx(0.4)

    def test_missing_component_redistributes_weight(self):
        result = blend_forecast_scores(
            {"sbc": 1.0, "kp": None, "kota": None},
            {"sbc": 0.4, "kp": 0.4, "kota": 0.2},
        )
        # kp/kota excluded; sbc weight renormalised to 1.0
        assert result["weights_used"] == {"sbc": 1.0}
        assert result["net"] == pytest.approx(1.0)
        assert "kp" not in result["components"]

    def test_no_components_available(self):
        result = blend_forecast_scores(
            {"sbc": None, "kp": None},
            {"sbc": 0.5, "kp": 0.5},
        )
        assert result["net"] == 0.0
        assert result["verdict"] == "NEUTRAL"

    def test_bearish_threshold(self):
        result = blend_forecast_scores({"sbc": -1.0}, {"sbc": 1.0})
        assert result["verdict"] == "BEARISH"
        assert result["net"] == -1.0

    def test_neutral_band(self):
        result = blend_forecast_scores({"sbc": 0.2, "kp": -0.2}, {"sbc": 0.5, "kp": 0.5})
        assert result["net"] == pytest.approx(0.0)
        assert result["verdict"] == "NEUTRAL"

    def test_unknown_weight_defaults_zero(self):
        result = blend_forecast_scores({"sbc": 1.0, "extra": 1.0}, {"sbc": 1.0})
        # extra has no configured weight -> excluded from blend
        assert result["net"] == pytest.approx(1.0)
        assert "extra" not in result["weights_used"]


class TestConfluenceDailyEndpoint:
    """Smoke test the unified daily forecast contract endpoint."""

    def test_confluence_daily_contract(self, client):
        response = client.get("/api/engine/confluence/daily?date=2026-09-11&instrument=NIFTY")
        assert response.status_code == 200
        data = response.get_json()
        assert data["date"] == "2026-09-11"
        assert data["instrument"] == "NIFTY"
        assert data["verdict"] in ("BULLISH", "BEARISH", "NEUTRAL")
        assert "net" in data and "components" in data
        # Trust metadata
        assert "calculation_version" in data
        assert "freshness" in data and "generated_at" in data["freshness"]
        assert "cache" in data and "cached" in data["cache"]

    def test_confluence_daily_cache_hit(self, client):
        first = client.get("/api/engine/confluence/daily?date=2026-09-12")
        assert first.status_code == 200
        assert first.get_json()["cache"]["cached"] is False
        second = client.get("/api/engine/confluence/daily?date=2026-09-12")
        assert second.status_code == 200
        body = second.get_json()
        assert body["cache"]["cached"] is True
        assert body["cache"]["cache_age_seconds"] >= 0
