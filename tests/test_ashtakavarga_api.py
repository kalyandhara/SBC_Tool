"""Ashtakavarga endpoint: allow-listed params, live computation, generic errors."""

import pytest

from sbc import ashtakavarga as av

PLANETS = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}


def test_default_request(client):
    r = client.get("/api/ashtakavarga")
    assert r.status_code == 200
    body = r.get_json()
    assert (body["anchor"], body["mode"], body["status"]) == ("nifty", "seven", "experimental")
    assert body["transit_time"] == "09:15 IST" and body["lagna_reliable"] is False
    assert body["lagna_reason"] == "birth time approximate"
    assert body["ambiguous_contributors"] == {"Moon": ["Aquarius", "Pisces"]}
    assert len(body["signs"]) == 12 and "nifty" in body["anchors"]
    assert set(body["natal"]["bav"]) == PLANETS and len(body["natal"]["sav"]) == 12
    assert set(body["transit"]) == PLANETS


def test_explicit_params(client):
    r = client.get("/api/ashtakavarga?anchor=india&date=2026-10-30&lagna_mode=classical")
    assert r.status_code == 200
    body = r.get_json()
    assert (body["mode"], body["lagna_reliable"], body["date"]) == ("classical", True, "2026-10-30")
    assert body["natal"]["max_per_sign"] == 8 and sum(body["natal"]["sav"]) == 337


@pytest.mark.parametrize("qs", [
    "anchor=../../etc", "anchor=NIFTY", "anchor=", "date=2026-13-01", "date=1899-12-31",
    "date=2101-01-01", "date=20261030", "date=2026-10-30T09:15", "lagna_mode=both",
    "foo=1", "date=2026-W44-1", "date=２０２６-10-30",
    "anchor=nifty&anchor=x", "date=2026-10-30&date=2026-10-31",
])
def test_rejects_bad_params(client, qs):
    assert client.get(f"/api/ashtakavarga?{qs}").status_code == 400


def test_post_is_not_served(client):
    assert client.post("/api/ashtakavarga").status_code != 200


def test_calculation_failure_is_a_generic_500(client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("C:/secret/path leaked")
    monkeypatch.setattr(av, "transit_scores", boom)
    r = client.get("/api/ashtakavarga")
    assert r.status_code == 500
    assert "secret" not in r.get_data(as_text=True)


def test_ashtakavarga_tab_is_wired():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    html = (root / "templates" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "js" / "ashtakavarga.js").read_text(encoding="utf-8")
    research = html.split('class="advanced-workspace-tabs"', 1)[1].split("</details>", 1)[0]
    assert 'data-tab="tab-ashtakavarga"' in research
    assert 'id="tab-ashtakavarga"' in html and 'src="/static/js/ashtakavarga.js' in html
    assert "innerHTML" not in js and "/api/ashtakavarga" in js
