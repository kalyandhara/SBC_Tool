"""B-18: routes with no UI caller were deleted or kept as documented API-only routes."""

import pytest

DELETED = [
    "/api/astrogann/signal", "/api/bearish_futurecast", "/api/cgsp_backtest",
    "/api/cgsp_framework", "/api/contra_signals", "/api/crash_analysis",
    "/api/crash_backtest", "/api/engine/confluence/daily", "/api/engine/summary",
    "/api/engine/trace", "/api/gann/indicators", "/api/gann/turbo_zones",
    "/api/habits/summary", "/api/kp_intraday_config", "/api/saturn_macro",
    "/api/sector/planet_read", "/api/sector/vedha_read", "/api/trade_setups",
]

# Kept on purpose although no page calls them: infrastructure, the TradingView
# integration, and the prediction engine's operational endpoints.
API_ONLY = {
    "/healthz", "/webhook/sbc", "/api/sbc/latest",
    "/api/engine/aspect_windows", "/api/engine/fingerprint", "/api/engine/fingerprint/status",
    "/api/engine/forecast/ledger", "/api/engine/intraday_forecast/freeze",
    # Muhurta / journal endpoints with no panel yet.
    "/api/engine/aspect_table", "/api/engine/trade_journal",
    "/api/engine/intraday_forecast/score", "/api/engine/market/freshness", "/api/engine/version",
}


@pytest.mark.parametrize("path", DELETED)
def test_deleted_routes_are_gone(client, path):
    assert client.get(path).status_code == 404


def test_every_route_has_a_ui_caller_or_is_listed(app):
    """A new route needs a caller in static/ or templates/, or an entry in API_ONLY."""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    ui = "".join(p.read_text(encoding="utf-8", errors="ignore")
                 for p in [*(root / "static").rglob("*.js"), *(root / "templates").rglob("*.html")]
                 if "vendor" not in p.parts)
    orphans = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        base = re.sub(r"<[^>]+>.*", "", rule.rule).rstrip("/")
        if base and base not in ui and rule.rule not in API_ONLY:
            orphans.append(rule.rule)
    assert not orphans, f"routes with no UI caller: {sorted(orphans)}"
