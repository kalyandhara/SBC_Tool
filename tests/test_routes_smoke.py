"""Every GET route answers without crashing.

This is the net the API layer was missing: /api/contra_signals shipped
returning 500 on every request because nothing exercised it. A 4xx for a
route that wants specific params is acceptable here; a 5xx never is.
"""

import pytest

from app import app as flask_app

# One permissive query string that satisfies most routes' required params.
DEFAULTS = {
    "date": "2026-09-11", "start": "2026-09-10", "end": "2026-09-11",
    "time": "09:15", "tz": "Asia/Kolkata", "anchor": "nse", "school": "allthree",
    "days": "3", "instrument": "NIFTY", "symbol": "NIFTY", "ticker": "^NSEI",
    "sector": "Nifty Bank", "user_key": "default", "format": "json",
    "offset": "0", "week": "2026-09-07", "q": "mumbai", "lat": "19.07",
    "lon": "72.87", "months": "1", "multi_tf": "false", "regime": "false",
    "volume": "false", "vedha": "false",
}

# Routes that reach the network or take minutes; covered elsewhere or by hand.
SKIP = {
    "/api/backtest": "downloads market data (yfinance)",
    "/api/backtest/moon": "downloads market data (yfinance)",
    "/api/backtest/walkforward": "downloads market data (yfinance)",
    "/api/price": "downloads market data (yfinance)",
    "/api/cgsp_backtest": "downloads market data (yfinance)",
    "/api/crash_backtest": "downloads market data (yfinance)",
    "/api/research/walk-forward": "downloads market data (yfinance)",
    "/api/research/event-study": "downloads market data (yfinance)",
}


def _get_routes():
    for rule in flask_app.url_map.iter_rules():
        if "GET" not in rule.methods or rule.endpoint == "static":
            continue
        if "<" in rule.rule:  # parameterised paths need a real id
            continue
        yield rule.rule


@pytest.mark.parametrize("path", sorted(set(_get_routes())))
def test_get_route_does_not_crash(client, path):
    if path in SKIP:
        pytest.skip(SKIP[path])
    resp = client.get(path, query_string=DEFAULTS)
    assert resp.status_code < 500, (
        f"{path} -> {resp.status_code}: {resp.data[:300]!r}"
    )


def test_write_routes_reject_remote_callers_without_token(app):
    """Binding to 0.0.0.0 must not let a LAN device rewrite data."""
    remote = app.test_client()
    resp = remote.post(
        "/webhook/sbc", json={"x": 1},
        environ_base={"REMOTE_ADDR": "192.168.1.50"},
    )
    assert resp.status_code in (401, 403)


def test_webhook_rejects_non_object_bodies(client):
    assert client.post("/webhook/sbc", json=[1, 2, 3]).status_code == 400
    assert client.post("/webhook/sbc", data="not json",
                       content_type="application/json").status_code == 400
