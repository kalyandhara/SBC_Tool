"""UI review P1 fixes (B-60..B-63)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_next_session_skips_weekend_and_holiday(client):
    sun = client.get("/api/market/next_session?date=2026-10-11").get_json()
    assert sun == {"date": "2026-10-11", "session": "2026-10-12", "moved": True, "reason": "Weekend"}
    mon = client.get("/api/market/next_session?date=2026-10-12").get_json()
    assert mon["session"] == "2026-10-12" and mon["moved"] is False and mon["reason"] is None
    assert client.get("/api/market/next_session?date=bad").status_code == 400


def test_next_session_moves_past_an_nse_holiday(client):
    from sbc.market_holidays import NSE_HOLIDAYS
    holiday = min(d for d in NSE_HOLIDAYS if d.year == 2026)
    body = client.get(f"/api/market/next_session?date={holiday.isoformat()}").get_json()
    assert body["moved"] and body["session"] > holiday.isoformat() and body["reason"] == NSE_HOLIDAYS[holiday]


def test_stylesheet_has_no_rule_nested_inside_a_rule():
    """B-62: an unclosed .nav-tab block swallowed the Advanced analysis dropdown rules."""
    css = re.sub(r"/\*.*?\*/", "", (ROOT / "static/style.css").read_text(encoding="utf-8"), flags=re.S)
    stack, pos = [], 0
    for m in re.finditer(r"[{}]", css):
        if m.group() == "{":
            selector = css[pos:m.start()].strip().split(";")[-1].strip()
            assert not (stack and not stack[-1].startswith("@")), f"'{selector[:40]}' nested in '{stack[-1][:40]}'"
            stack.append(selector)
        else:
            stack.pop()
        pos = m.end()
    assert not stack


def test_header_date_defaults_to_ist_and_next_session():
    js = (ROOT / "static/app.js").read_text(encoding="utf-8")
    assert 'localTodayISO("Asia/Kolkata")' in js
    assert "defaultToNextSession().finally(() => { updateNavAsOf(); run()" in js


def test_secondary_loads_cannot_mark_prediction_unavailable():
    js = (ROOT / "static/app.js").read_text(encoding="utf-8")
    assert 'quietly("Futurecast", loadFuturecast(' in js and 'quietly("Lunar forecast", loadLunarForecast(' in js
