"""Tests for Flask API endpoints."""

import pytest
import json
from app import app


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_healthz(self, client):
        """Health endpoint should return OK."""
        response = client.get("/healthz")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "ok"
        assert data["engine"] == "sbc"


class TestPresetsEndpoint:
    """Test presets endpoint."""

    def test_presets(self, client):
        """Presets should return anchors and nakshatras."""
        response = client.get("/api/presets")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "anchors" in data
        assert "nakshatras" in data
        assert len(data["anchors"]) >= 4
        assert len(data["nakshatras"]) == 27


class TestPredictionEndpoint:
    """Test core prediction endpoint."""

    def test_prediction_default_params(self, client):
        """Prediction with defaults should work."""
        response = client.get("/api/prediction")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "date" in data
        assert "planets" in data
        assert "grid" in data
        assert "sentiment" in data
        assert "recommendation" in data

    def test_prediction_custom_params(self, client):
        """Prediction with custom params should work."""
        response = client.get(
            "/api/prediction?date=2026-09-11&time=09:15&tz=Asia/Kolkata&anchor=nse&school=classical"
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["school"] == "classical"
        assert data["anchor"]["key"] == "nse"

    def test_prediction_invalid_anchor(self, client):
        """Invalid anchor should return 400."""
        response = client.get("/api/prediction?anchor=invalid")
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_prediction_invalid_school(self, client):
        """Invalid school should return 400."""
        response = client.get("/api/prediction?school=invalid")
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_prediction_invalid_date(self, client):
        """Invalid date should return 400."""
        response = client.get("/api/prediction?date=invalid")
        assert response.status_code == 400


class TestPredictionSeriesEndpoint:
    """Test prediction series endpoint."""

    def test_prediction_series(self, client):
        """Prediction series should return daily predictions."""
        response = client.get(
            "/api/prediction_series?start=2026-09-01&end=2026-09-10&anchor=nifty"
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "series" in data
        assert "anchor" in data
        assert len(data["series"]) == 10

    def test_prediction_series_rebuilds_trimmed_cache_rows(self, client):
        """A trimmed L2 row (old boot warm-up shape) must be rebuilt in full."""
        from sbc import series_cache
        from sbc.api.blueprints import chart_bp
        day = "2026-02-03"
        series_cache.put_many({day: {"date": day, "score": 1, "net": 0.5}},
                              "nifty", "classical")
        chart_bp._series_cache.pop((day, "nifty", "classical"), None)
        resp = client.get(f"/api/prediction_series?start={day}&end={day}&anchor=nifty")
        row = json.loads(resp.data)["series"][0]
        assert chart_bp.SERIES_KEYS <= row.keys()
        stored = series_cache.get_many([day], "nifty", "classical")[day]
        assert chart_bp.SERIES_KEYS <= stored.keys()

    def test_prediction_series_invalid_range(self, client):
        """Too large range should return 400."""
        response = client.get(
            "/api/prediction_series?start=2020-01-01&end=2030-12-31&anchor=nifty"
        )
        assert response.status_code == 400


class TestDailyIndicationBalanceEndpoint:
    """Test daily indication balance endpoint."""

    def test_daily_indication_balance(self, client):
        """Should return 30-day bias data."""
        response = client.get("/api/daily_indication_balance?start=2026-09-01")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "days" in data
        assert "dates" in data
        assert "blend_bias" in data
        assert "jyotish_line" in data
        assert "kp_line" in data
        assert "western_line" in data
        assert len(data["days"]) == 30


class TestNiftyChartEndpoint:
    """Test NIFTY chart endpoint."""

    def test_nifty_chart(self, client):
        """Should return OHLC candles."""
        response = client.get("/api/nifty_chart?start=2026-08-01&end=2026-08-31")
        # May return empty if no data, but should not error
        assert response.status_code in (200, 503)
        if response.status_code == 200:
            data = json.loads(response.data)
            assert "candles" in data
            assert "symbol" in data


class TestFuturecastEndpoints:
    """Test futurecast endpoints."""

    def test_futurecast(self, client):
        """Crash futurecast should return windows."""
        response = client.get("/api/futurecast?date=2026-09-11")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "range_start" in data
        assert "range_end" in data

    def test_bullish_futurecast(self, client):
        """Bullish futurecast should return clusters."""
        response = client.get("/api/bullish_futurecast?date=2026-09-11&years=1")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "scan_window" in data
        assert "clusters" in data

    def test_bearish_futurecast(self, client):
        """Bearish futurecast should return clusters."""
        response = client.get("/api/bearish_futurecast?date=2026-09-11&years=1")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "scan_window" in data
        assert "clusters" in data


class TestBacktestEndpoints:
    """Test backtest endpoints."""

    def test_backtest(self, client):
        """Backtest should return results."""
        response = client.get("/api/backtest")
        assert response.status_code == 200
        data = json.loads(response.data)
        # API returns flat structure with accuracy, matches, etc.
        assert "accuracy" in data or "total" in data or "matches" in data

    def test_crash_backtest(self, client):
        """Crash backtest should return summary."""
        response = client.get("/api/crash_backtest")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "summary" in data
        assert "results" in data


class TestSectorEndpoints:
    """Test sector-related endpoints."""

    def test_sector_vedha(self, client):
        """Sector vedha should return signals."""
        response = client.get("/api/sector_vedha?date=2026-09-11")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "date" in data
        assert "signals" in data

    def test_monthly_heatmap(self, client):
        """Monthly heatmap should return matrix."""
        response = client.get("/api/monthly_heatmap?date=2026-09-01&days=30")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "sectors" in data
        assert "dates" in data
        assert "matrix" in data


class TestSpecializedSignalsEndpoints:
    """Test specialized sector signal endpoints."""

    def test_fmcg_signals(self, client):
        """FMCG signals should return analysis."""
        response = client.get("/api/fmcg_signals?date=2026-09-11")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "summary" in data
        assert "active_signals" in data
        assert "conviction" in data

    def test_tourism_signals(self, client):
        """Tourism signals should return analysis."""
        response = client.get("/api/tourism_signals?date=2026-09-11")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "summary" in data

    def test_chemical_signals(self, client):
        """Chemical signals should return analysis."""
        response = client.get("/api/chemical_signals?date=2026-09-11")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "summary" in data

    def test_alcohol_signals(self, client):
        """Alcohol signals should return analysis."""
        response = client.get("/api/alcohol_signals?date=2026-09-11")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "summary" in data

    def test_bullion_vedha(self, client):
        """Bullion vedha should return signals."""
        response = client.get("/api/bullion_vedha?date=2026-09-11")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "date" in data
        assert "text" in data
        assert "data" in data

    def test_transit_vedha(self, client):
        """Transit vedha should return signals."""
        response = client.get("/api/transit_vedha?date=2026-09-11")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "date" in data
        assert "data" in data


class TestKPEndpoints:
    """Test KP intraday endpoints."""

    def test_kp_intraday_report(self, client):
        """KP intraday report should generate."""
        response = client.get("/api/kp_intraday_report?date=2026-09-11&instrument=NIFTY&format=json")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "trading_day" in data
        assert "instrument" in data

    def test_kp_intraday_config(self, client):
        """KP config should return config dict."""
        response = client.get("/api/kp_intraday_config")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, dict)


class TestResearchEndpoints:
    """Test research lab endpoints."""

    def test_astro_lab(self, client):
        """Astro lab should return research data."""
        response = client.get("/api/research/astro_lab")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_walk_forward_validation(self, client):
        """Walk forward validation should return results."""
        response = client.get("/api/research/walk_forward_validation")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, dict)


class TestProfileEndpoints:
    """Test profile management endpoints."""

    def test_astro_profile_load(self, client):
        """Loading profiles should return list."""
        response = client.get("/api/astro/profile?user_key=test")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_astro_profile_save(self, client):
        """Saving profile should work."""
        response = client.post(
            "/api/astro/profile",
            json={"birth_date": "1990-01-01", "birth_time": "12:00", "city": "Mumbai"},
            headers={"X-User-Key": "test_save"}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "id" in data
        assert data["status"] == "saved"


class TestUtilitiesEndpoints:
    """Test utility endpoints."""

    def test_tz_offset(self, client):
        """Timezone offset should return offset info."""
        response = client.get("/api/tz/offset?tz=Asia/Kolkata&date=2026-09-11&time=09:15")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "offset_minutes" in data
        assert "offset_hours" in data

    def test_tz_from_coords(self, client):
        """Timezone from coordinates should work."""
        response = client.get("/api/tz/from_coords?lat=19.0760&lon=72.8777")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "timezone" in data

    def test_cities_search(self, client):
        """City search should return results."""
        response = client.get("/api/cities/search?q=Mumbai")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_price_endpoint(self, client):
        """Price endpoint should return candles."""
        response = client.get("/api/price?ticker=^NSEI&days=30")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_gann_turbo_zones(self, client):
        """Gann turbo zones should return levels."""
        response = client.get("/api/gann/turbo_zones?ticker=^NSEI&days=60")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "ticker" in data
        assert "zones" in data

    def test_gann_precision(self, client):
        """Gann precision should return levels and classified zones."""
        response = client.get("/api/gann/precision?ticker=^NSEI&days=90")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "ticker" in data
        assert "levels" in data
        zones = data["zones"]
        assert zones["trend"] in ("bullish", "bearish")
        assert zones["initiation"] and zones["target"]
        assert zones["stop_loss"] and zones["trailing_stop"]
        for zone_key in ("initiation", "target", "stop_loss", "trailing_stop"):
            for lvl in zones[zone_key]:
                assert "price" in lvl
                assert isinstance(lvl["price"], (int, float))

    def test_gann_precision_asset_types(self, client):
        """Asset type controls tick-size rounding; unknown type returns 400."""
        response = client.get("/api/gann/precision?ticker=^NSEI&days=90&asset_type=commodities")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["asset_type"] == "commodities"

        bad = client.get("/api/gann/precision?ticker=^NSEI&days=90&asset_type=crypto")
        assert bad.status_code == 400
        assert "error" in json.loads(bad.data)

    def test_astro_cycles(self, client):
        """AstroCycle Pro should return cycle bars and Moon ingresses."""
        response = client.get("/api/astro/cycles?date=2026-09-11&ticker=^NSEI")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["date"] == "2026-09-11"
        assert isinstance(data["bars"], list)
        assert isinstance(data["moon_ingresses"], list)
        for bar in data["bars"]:
            assert bar["type"] in ("mercury", "moon")
            for key in ("time", "end", "entry_above", "entry_below",
                        "stop_loss", "target_above", "target_below", "entry_rule"):
                assert key in bar

    def test_astro_cycles_invalid_date(self, client):
        """Invalid date should return 400."""
        response = client.get("/api/astro/cycles?date=invalid")
        assert response.status_code == 400
        assert "error" in json.loads(response.data)

    def test_expiry_range(self, client):
        """Expiry Range forecast should return levels for the next expiry."""
        response = client.get("/api/expiry/range?instrument=NIFTY&date=2026-09-11")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["instrument"] == "NIFTY"
        assert "expiry" in data
        levels = data["levels"]
        assert "pivot" in levels
        assert levels["resistances"] and levels["supports"]
        for lvl in levels["resistances"] + levels["supports"]:
            assert "price" in lvl
            assert "valid_above" in lvl or "valid_below" in lvl

    def test_expiry_backtest(self, client):
        """Expiry backtest should return containment metrics."""
        response = client.get("/api/expiry/backtest?instrument=NIFTY&months=2")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["instrument"] == "NIFTY"
        assert "expiry_days_evaluated" in data
        assert "containment_rate" in data
        assert isinstance(data["results"], list)

    def test_gann_indicators(self, client):
        """Gann toolkit should run each kind and reject unknown kinds."""
        for kind in ("momentum", "apex_reversal", "harmonic_opens",
                     "harmonic_vibrations", "wave_levels", "lightning_scalper",
                     "mega_trend"):
            response = client.get(f"/api/gann/indicators?kind={kind}&ticker=^NSEI&days=120")
            assert response.status_code == 200, kind
            data = json.loads(response.data)
            assert data["kind"] == kind

        bad = client.get("/api/gann/indicators?kind=nope&ticker=^NSEI&days=120")
        assert bad.status_code == 400
        assert "error" in json.loads(bad.data)


class TestRateLimiting:
    """Test rate limiting behavior."""

    def test_rate_limit_allows_normal_usage(self, client):
        """Normal request rate should be allowed."""
        for _ in range(10):
            response = client.get("/healthz")
            assert response.status_code == 200

class TestTradingSignalsPanel:
    """The overview Trading Signals panel must show live data, never demo text."""

    def test_astro_personal_exposes_tithi_bhadra_and_windows(self, client):
        # 2026-10-02 has a Bhadra window 10:15-21:07 IST; 2026-10-01 has none.
        on = json.loads(client.get("/api/astro/personal?date=2026-10-02").data)
        off = json.loads(client.get("/api/astro/personal?date=2026-10-01").data)
        assert on["bhadra"]["active_today"] is True
        assert on["bhadra"]["windows_today"][0]["begin"].startswith("2026-10-02T10:")
        assert off["bhadra"]["active_today"] is False
        assert off["bhadra"]["next"]["begin"].startswith("2026-10-02")
        assert off["tithi"]["name"] == "Panchami" and off["tithi"]["paksha"] == "Krishna"
        assert off["weekday"] == "Thursday"
        assert isinstance(off["reversal_windows"], list)

    def test_template_has_no_demo_literals(self, client):
        html = client.get("/").get_data(as_text=True)
        for literal in ("BADRA ACTIVE", "23:15 - 23:35", "Krishna Ashtami",
                        "inauspicious tithi", "favorable market day",
                        "trading-signals-tabs"):
            assert literal not in html, literal

    def test_panels_live_inside_tabs(self, client):
        html = client.get("/").get_data(as_text=True)
        assert html.index('id="tab-overview"') < html.index('id="trading-signals-astro"') \
            < html.index('id="tab-chart"')
        assert html.index('id="tab-sectors"') < html.index('id="daily-nakshatra-dashboard"') \
            < html.index('id="tab-kp"')


class TestIntradayPathExperimentalLabel:
    """The intraday path has no validated edge; UI and API must say so."""

    def test_api_marks_path_experimental(self, client):
        data = json.loads(client.get(
            "/api/engine/intraday_path?date=2026-09-15&instrument=NIFTY").data)
        assert data["status"] == "experimental"
        assert data["validation"]["verdict"] == "no edge over chance"

    def test_ui_labels_path_and_projection_experimental(self, client):
        html = client.get("/").get_data(as_text=True)
        path_panel = html[html.index('id="kp-intraday-path-chart"'):html.index('id="kp-path-container"')]
        assert "experimental-badge" in path_panel and "no validated edge" in path_panel
        assert "Intraday Path (experimental)" in html
        assert "Predictive intraday path (cumulative KP composite score)" not in html
        btn = html[html.index('id="trading-predicted-actual-load"'):]
        assert "experimental-badge" in btn[:300]
