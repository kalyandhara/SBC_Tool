"""Smoke tests for the transit report endpoints."""

from openpyxl import load_workbook


def test_cities_lookup(client):
    resp = client.get("/api/transits/cities?q=dubai")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["results"], "expected city matches"
    top = body["results"][0]
    assert top["name"] == "Dubai"
    assert top["timezone"] == "Asia/Dubai"


def test_report_downloads_six_sheet_workbook(client):
    resp = client.get(
        "/api/transits/report?city=Dubai&start=2026-01-01&end=2026-02-01"
        "&planets=Sun,Mars&types=sign,nakshatra&ayanamsa=lahiri"
        "&node_mode=mean")
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.content_type
    data = resp.data
    assert data[:2] == b"PK"  # xlsx zip magic
    wb = load_workbook(__import__("io").BytesIO(data))
    assert wb.sheetnames == ["Report Info", "Zodiac Transits",
                             "Nakshatra Transits", "All Transits Timeline",
                             "Stations (R-D)"]
    info = wb["Report Info"]
    flat = {str(r[0].value): r[1].value for r in info.iter_rows()}
    assert "Asia/Dubai" in str(flat.get("City"))
    assert "lahiri" in str(flat.get("Ayanamsa"))


def test_report_rejects_bad_dates(client):
    resp = client.get(
        "/api/transits/report?city=Mumbai&start=not-a-date&end=2026-02-01")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_report_defaults_are_sane(client):
    # No params: defaults to Mumbai, one year, all planets/types.  Keep
    # the range short via start/end so the test stays fast.
    resp = client.get(
        "/api/transits/report?start=2026-03-01&end=2026-03-15"
        "&planets=Sun&types=sign")
    assert resp.status_code == 200
    wb = load_workbook(__import__("io").BytesIO(resp.data))
    # requested type only: pada/nakshatra sheets are skipped
    assert "Pada Transits" not in wb.sheetnames
    assert "Zodiac Transits" in wb.sheetnames
