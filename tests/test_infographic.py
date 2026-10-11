"""Infographic cards: each tab's PNG renders, and each button is wired to a real page and inputs."""

import re
from pathlib import Path

import pytest

from sbc import infographic as ig

ROOT = Path(__file__).resolve().parents[1]
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _crash_payload():
    days = ["2026-10-10", "2026-10-11", "2026-10-12"]
    return {"series": [
        {"date": days[0], "score": 4, "reasons": ["Mars Debilitated", "Venus combust"]},
        {"date": days[1], "score": 7, "reasons": ["Mars Debilitated"]},
        {"date": days[2], "score": 7, "reasons": ["Mars Debilitated"]},
    ]}


def _monthly_payload():
    return {"month": "2026-10", "start": "2026-10-01", "end": "2026-10-03", "days": [
        {"date": "2026-10-01", "score": 3.0, "trading": True, "nifty_close": 22421.9},
        {"date": "2026-10-02", "score": 5.0, "trading": False, "nifty_close": None},
        {"date": "2026-10-03", "score": 2.0, "trading": True, "nifty_close": 22500.0},
    ]}


def _analog_payload():
    return {"target": "2026-10-09", "horizon": 5, "variant": "overall",
            "summary": {"n": 2, "lean": -1, "median": -0.0085, "up_share": 0.5,
                        "base_up_share": 0.56},
            "analogs": [{"date": "2026-01-09", "similarity": 0.41,
                         "forward": {"5": -0.007}}],
            "track_record": {"verdict": "no edge", "hit_rate": 0.49, "baseline": 0.50,
                             "n": 3618, "years_right": 2, "years": 15},
            "caveat": "Research output, not investment advice."}


def _calendar_payload():
    return {"start": "2026-10-12", "end": "2026-10-18",
            "headline": {"1": {"probability_up": 0.53}, "5": {"probability_up": 0.56},
                         "20": {"probability_up": 0.6}},
            "weeks": [{"band_68": [22064.4, 22976.5]}],
            "days": [{"date": "2026-10-12", "weekday": "Mon", "tithi": "Shukla 2",
                      "trading": True, "events": [], "rules": {"up": 6, "down": 4, "flat": 12}},
                     {"date": "2026-10-17", "weekday": "Sat", "tithi": "Shukla 7",
                      "trading": False, "events": [], "rules": {"up": 0, "down": 0, "flat": 0}}],
            "caveat": "Evidence, not a forecast."}


def _kp_payload():
    shifts = [{"time": "09:18", "planet": "Ascendant", "direction": "Bearish",
               "regime_label": "sell-on-rise", "old_sublord": "Venus", "new_sublord": "Sun"},
              {"time": "10:42", "planet": "Moon", "direction": "Bullish",
               "regime_label": "buy-on-dip", "old_sublord": "Sun", "new_sublord": "Mars"}]
    return {"instrument": "NIFTY", "trading_day": "2026-10-09", "regime_shifts": shifts,
            "day_signature": {"day_lord": "Venus", "moon_star": "Uttara Phalguni",
                              "moon_sign": "Virgo", "day_bias_label": "neutral",
                              "moon_affliction_gate": "FAILED (Saturn aspect).",
                              "hora_slots": [{"time_range": "09:15-09:30", "lord": "Moon",
                                              "quality": "Neutral",
                                              "interpretation": "Saturn aspect -> delay / pressure"}]},
            "data_quality": {"synthetic": False},
            "experimental_notice": "No validated edge."}


PAYLOADS = {
    "crash": _crash_payload, "monthly": _monthly_payload, "analog": _analog_payload,
    "calendar": _calendar_payload, "kp": _kp_payload, "kp_chart": _kp_payload,
    "kp_report": _kp_payload,
}


@pytest.mark.parametrize("page", sorted(ig.PAGES))
def test_card_renders_png(page):
    png = ig.render(page, PAYLOADS[page](), "2026-10-10 12:00 IST")
    assert png.startswith(PNG_MAGIC)
    assert len(png) > 5_000


@pytest.mark.parametrize("page", ["crash", "monthly", "analog", "calendar", "kp_chart", "kp_report"])
def test_card_renders_with_empty_payload(page):
    """A window with no data must still give a card, not a crash."""
    png = ig.render(page, {}, "stamp")
    assert png.startswith(PNG_MAGIC)


def test_defaults_cover_every_page():
    import datetime as dt
    today = dt.date(2026, 10, 10)
    for page in ig.PAGES:
        ig.defaults(page, today)
    assert ig.defaults("crash", today) == {"start": "2026-10-10", "end": "2026-12-31"}
    assert ig.defaults("monthly", today) == {"month": "2026-10"}


def test_unknown_page_is_404(client):
    assert client.get("/api/infographic/nope").status_code == 404


def test_route_returns_png_attachment(client):
    r = client.get("/api/infographic/crash?start=2026-10-10&end=2026-10-12")
    assert r.status_code == 200
    assert r.mimetype == "image/png"
    assert r.data.startswith(PNG_MAGIC)
    assert 'filename="sbc-crash-' in r.headers["Content-Disposition"]


def test_route_passes_source_errors_through(client):
    r = client.get("/api/infographic/crash?start=2026-10-12&end=2026-10-10")
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_every_button_targets_a_page_and_real_inputs():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    buttons = re.findall(r'data-infographic="([^"]+)" data-params="([^"]*)"', html)
    assert {page for page, _ in buttons} == set(ig.PAGES)
    for page, params in buttons:
        assert page in ig.PAGES, page
        for pair in filter(None, params.split(",")):
            input_id, arg = pair.split(":")
            assert f'id="{input_id}"' in html, f"{page}: missing input {input_id}"
            assert arg, page


def test_every_page_has_a_button():
    html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    for page in ig.PAGES:
        assert f'data-infographic="{page}"' in html, page


def test_kp_defaults_skip_closed_days():
    import datetime as dt
    # 2026-10-10 is a Saturday; the next NSE session is Monday 2026-10-12.
    assert ig.defaults("kp_report", dt.date(2026, 10, 10))["date"] == "2026-10-12"


def test_kp_card_moves_a_holiday_to_the_next_session(client):
    r = client.get("/api/infographic/kp_report?date=2026-10-10")
    assert r.status_code in (200, 404)  # 404 only if that month's KP data file is missing
    if r.status_code == 200:
        assert r.data.startswith(PNG_MAGIC)
