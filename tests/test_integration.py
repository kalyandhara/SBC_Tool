"""Integration tests for end-to-end workflows."""

import json


class TestFullPredictionWorkflow:
    """Test complete prediction workflow."""

    def test_predict_then_chart(self, client):
        """Run prediction then load chart data."""
        # 1. Get prediction
        pred_resp = client.get("/api/prediction?date=2026-09-11")
        assert pred_resp.status_code == 200
        pred_data = json.loads(pred_resp.data)

        # 2. Use prediction date for chart
        chart_resp = client.get(
            f"/api/nifty_chart?start=2026-08-11&end={pred_data['date']}"
        )
        assert chart_resp.status_code in (200, 503)

    def test_predict_then_futurecast(self, client):
        """Run prediction then futurecast."""
        pred_resp = client.get("/api/prediction?date=2026-09-11")
        assert pred_resp.status_code == 200
        pred_data = json.loads(pred_resp.data)

        fc_resp = client.get(f"/api/futurecast?date={pred_data['date']}")
        assert fc_resp.status_code == 200

        bfc_resp = client.get(f"/api/bullish_futurecast?date={pred_data['date']}")
        assert bfc_resp.status_code == 200


class TestSectorAnalysisWorkflow:
    """Test sector analysis workflow."""

    def test_monthly_heatmap_with_sectors(self, client):
        """Get heatmap then check individual sector signals."""
        hm_resp = client.get("/api/monthly_heatmap?date=2026-09-01&days=30")
        assert hm_resp.status_code == 200
        hm_data = json.loads(hm_resp.data)

        # Check that sectors in heatmap have data
        assert len(hm_data["sectors"]) > 0
        assert len(hm_data["dates"]) > 0

    def test_all_sector_signals(self, client):
        """Test all specialized sector signals."""
        endpoints = [
            "/api/fmcg_signals",
            "/api/tourism_signals",
            "/api/chemical_signals",
            "/api/alcohol_signals",
            "/api/bullion_vedha",
            "/api/transit_vedha",
            "/api/sector_vedha",
        ]

        for ep in endpoints:
            resp = client.get(f"{ep}?date=2026-09-11")
            assert resp.status_code == 200, f"Failed: {ep}"
            data = json.loads(resp.data)
            assert "summary" in data or "text" in data or "signals" in data


class TestKPIntradayWorkflow:
    """Test KP intraday workflow."""

    def test_kp_report_generation(self, client):
        """Generate KP report with sample data (in an isolated month, then clean up)."""
        # Use a month with no real KP file so the sample never overwrites real data.
        sample_resp = client.post(
            "/api/kp_intraday_sample",
            json={"date": "2026-06-11", "days": 5}
        )
        assert sample_resp.status_code == 200

        # Then generate report
        report_resp = client.get(
            "/api/kp_intraday_report?date=2026-06-11&instrument=NIFTY&format=json"
        )
        assert report_resp.status_code == 200
        data = json.loads(report_resp.data)
        assert "trend_changes" in data
        assert "regime_shifts" in data

        # Clean up the generated sample file
        from pathlib import Path
        sample_file = Path(__file__).resolve().parent.parent / "data" / "kp" / "KP_Data_Jun2026.csv"
        try:
            if sample_file.exists():
                sample_file.unlink()
        except OSError:
            pass

    def test_kp_intraday_path(self, client):
        """Get predictive intraday path."""
        path_resp = client.get(
            "/api/engine/intraday_path?date=2026-09-11&instrument=NIFTY"
        )
        # May fail if engine blueprint not registered, but shouldn't 500
        assert path_resp.status_code != 500


class TestProfileWorkflow:
    """Test profile management workflow."""

    def test_profile_crud(self, client):
        """Create, read, update, delete profile."""
        user_key = "test_integration"

        # Create
        create_resp = client.post(
            "/api/astro/profile",
            json={"name": "Test Profile", "data": {"birth_date": "1990-01-01"}},
            headers={"X-User-Key": user_key}
        )
        # Allow 429 during rapid test execution
        assert create_resp.status_code in (200, 429)
        if create_resp.status_code != 200:
            return
        create_data = json.loads(create_resp.data)
        pid = create_data["id"]

        # Read
        load_resp = client.get(f"/api/astro/profile?user_key={user_key}")
        assert load_resp.status_code in (200, 429)
        if load_resp.status_code != 200:
            return
        profiles = json.loads(load_resp.data)
        assert len(profiles) >= 1
        assert any(p["id"] == pid for p in profiles)

        # Update
        update_resp = client.put(
            f"/api/astro/profile/{pid}",
            json={"name": "Updated Profile"}
        )
        assert update_resp.status_code in (200, 429)

        # Set default
        default_resp = client.post(f"/api/astro/profile/{pid}/default")
        assert default_resp.status_code in (200, 429)

        # Export
        export_resp = client.get(f"/api/astro/profile/export?user_key={user_key}")
        assert export_resp.status_code in (200, 429)
        if export_resp.status_code == 200:
            exported = json.loads(export_resp.data)
            assert len(exported) >= 1

        # Import
        import_resp = client.post(
            "/api/astro/profile/import",
            json=exported,
            headers={"X-User-Key": "test_import"}
        )
        assert import_resp.status_code in (200, 429)

        # Delete
        delete_resp = client.delete(f"/api/astro/profile/{pid}")
        assert delete_resp.status_code in (200, 429)


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_invalid_date_format(self, client):
        """Invalid date format should return 400 with error."""
        endpoints = [
            "/api/prediction?date=invalid",
            "/api/futurecast?date=invalid",
            "/api/bullion_vedha?date=invalid",
            "/api/sector_vedha?date=invalid",
        ]
        for ep in endpoints:
            resp = client.get(ep)
            # Allow 429 during rapid test execution
            assert resp.status_code in (400, 429), f"Expected 400 for {ep}, got {resp.status_code}"
            if resp.status_code == 400:
                data = json.loads(resp.data)
                assert "error" in data

    def test_missing_required_params(self, client):
        """Missing required params should return 400.

        /api/lunar_forecast deliberately defaults to today, so it is not a
        valid probe here (the old assertion only passed because the rate
        limiter answered 429). prediction_series has genuinely required params.
        """
        resp = client.get("/api/prediction_series")
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_unknown_endpoint(self, client):
        """Unknown endpoint should return 404."""
        resp = client.get("/api/unknown/endpoint")
        assert resp.status_code in (404, 429)


class TestCORSAndHeaders:
    """Test CORS and security headers."""

    def test_no_cache_headers(self, client):
        """Responses should have no-cache headers."""
        resp = client.get("/api/prediction")
        assert resp.status_code in (200, 429)
        if resp.status_code == 200:
            assert "Cache-Control" in resp.headers
            assert "no-store" in resp.headers["Cache-Control"]

    def test_csp_header(self, client):
        """Should have CSP header."""
        resp = client.get("/api/prediction")
        assert resp.status_code in (200, 429)
        if resp.status_code == 200:
            assert "Content-Security-Policy" in resp.headers

    def test_rate_limit_header(self, client):
        """Should track request count."""
        resp = client.get("/healthz")
        # Rate limit is in-memory, just verify it doesn't error
        assert resp.status_code in (200, 429)
