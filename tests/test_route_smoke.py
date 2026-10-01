import pytest
from app import app

GET_ROUTES = [
    "/",
    "/healthz",
    "/api/prediction",
    "/api/prediction_series?start=2025-01-01&end=2025-01-02",
    "/api/monthly_heatmap?year=2025",
    "/api/bhadra_calendar",
]

@pytest.mark.parametrize("path", GET_ROUTES)
def test_get_routes_200(path):
    client = app.test_client()
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} returned {resp.status_code}"
