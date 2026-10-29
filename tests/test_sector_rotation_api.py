"""Sector rotation endpoint: allow-listed parameters, precomputed JSON only, auth parity."""

import json

import pytest

from sbc.api.blueprints import sector_rotation_bp as srb


@pytest.fixture
def reports_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(srb, "REPORTS", str(tmp_path))
    payload = {"confirmatory": [], "forecast": {}, "breadth": "not computed"}
    (tmp_path / "sector_rotation_2026-10-29.json").write_text(json.dumps(payload), encoding="utf-8")
    return tmp_path


def test_rejects_unknown_event(client, reports_dir):
    assert client.get("/api/sector_rotation?event=../../etc").status_code == 400


def test_rejects_unknown_horizon(client, reports_dir):
    assert client.get("/api/sector_rotation?h=7").status_code == 400


def test_rejects_non_integer_horizon_text(client, reports_dir):
    assert client.get("/api/sector_rotation?h=5;DROP").status_code == 400


def test_serves_precomputed_json(client, reports_dir):
    r = client.get("/api/sector_rotation?event=all&h=5")
    assert r.status_code == 200
    body = r.get_json()
    assert body["data"]["confirmatory"] == [] and body["h"] == 5


def test_never_calls_build(client, reports_dir, monkeypatch):
    import scripts.sector_rotation_report as rep
    def boom(*a, **k):
        raise AssertionError("endpoint must not recompute")
    monkeypatch.setattr(rep, "build", boom)
    assert client.get("/api/sector_rotation?event=all&h=5").status_code == 200


def test_404_when_no_report_exists(client, tmp_path, monkeypatch):
    monkeypatch.setattr(srb, "REPORTS", str(tmp_path))
    assert client.get("/api/sector_rotation").status_code == 404


def test_read_auth_parity_with_siblings(client, reports_dir):
    # Siblings serve GET with no token; the app-wide guard gates only writes.
    sibling = client.get("/api/monthly_heatmap?date=2026-10-29")
    mine = client.get("/api/sector_rotation")
    assert mine.status_code == 200 and sibling.status_code != 401
    assert client.post("/api/sector_rotation").status_code in (401, 403, 405)


def test_no_extra_routes_added(app):
    rules = {r.rule for r in app.url_map.iter_rules() if "sector_rotation" in r.rule}
    assert rules == {"/api/sector_rotation"}
