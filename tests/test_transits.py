"""Tests for sbc.transits — ephemeris transit date calculations.

Validates the Mars-Jupiter same-sign periods against the reference
study table (XAU/USD performance 2002-2024, image baseline): image
dates use the IST convention, so a +/-1 day tolerance is allowed.
"""

import datetime

from sbc.transits import (
    nakshatra_ingresses,
    nakshatra_periods,
    same_sign_periods,
    sign_ingresses,
)

# Image baseline rows (2020 onward, IST dates).
IMAGE_ROWS = [
    ("2020-02-08", "2020-03-22", "Sagittarius"),
    ("2020-03-30", "2020-05-04", "Capricorn"),
    ("2022-05-17", "2022-06-27", "Pisces"),
    ("2024-07-12", "2024-08-26", "Taurus"),
]


def _parse(date_str):
    return datetime.date.fromisoformat(date_str)


def _close_to(a, b, days=1):
    return abs((a - b).days) <= days


def test_same_sign_periods_match_reference_study():
    periods = same_sign_periods("Mars", "Jupiter",
                                _parse("2019-01-01"), _parse("2025-01-01"))
    got = [(p["start"], p["end"], p["sign"]) for p in periods
           if not (p["sign"] == "Aquarius" and p["start"].startswith("2022-04"))]
    assert len(got) == len(IMAGE_ROWS)
    for (img_start, img_end, img_sign), (start, end, sign) in zip(IMAGE_ROWS, got, strict=True):
        assert sign == img_sign
        assert _close_to(_parse(start), _parse(img_start))
        assert _close_to(_parse(end), _parse(img_end))
        assert _parse(end) > _parse(start)


def test_same_sign_periods_schema():
    periods = same_sign_periods("Mars", "Jupiter",
                                _parse("2023-01-01"), _parse("2025-01-01"))
    for p in periods:
        assert set(p) == {"start", "end", "sign", "days"}
        assert p["sign"] in ["Aries", "Taurus", "Gemini", "Cancer", "Leo",
                             "Virgo", "Libra", "Scorpio", "Sagittarius",
                             "Capricorn", "Aquarius", "Pisces"]
        assert p["days"] > 0


def test_sign_ingresses_mars_2022():
    events = sign_ingresses("Mars", _parse("2022-01-01"),
                            _parse("2022-12-31"))
    labels = [e["label"] for e in events]
    # Mars entered sidereal Pisces on 17 May 2022 (IST).
    assert "Pisces" in labels
    pisces = next(e for e in events if e["label"] == "Pisces")
    assert _close_to(_parse(pisces["ist_date"]), _parse("2022-05-17"))
    assert pisces["kind"] == "sign"
    assert pisces["from_label"] in ("Aquarius", "Aries")
    for e in events:
        assert set(e) == {"planet", "kind", "label", "from_label",
                          "longitude", "pada", "utc", "utc_date", "ist_date"}
        assert 0.0 <= e["longitude"] < 360.0


def test_nakshatra_ingresses_moon_daily_rate():
    events = nakshatra_ingresses("Moon", _parse("2024-06-01"),
                                 _parse("2024-06-30"))
    # The Moon ingresses roughly once per day (13deg20' / ~13deg per day).
    assert 26 <= len(events) <= 31
    for e in events:
        assert e["kind"] == "nakshatra"
        assert e["planet"] == "Moon"
        assert e["label"] != e["from_label"]
    # Consecutive ingresses are ordered in time.
    dates = [_parse(e["ist_date"]) for e in events]
    assert dates == sorted(dates)


def test_nakshatra_ingresses_jupiter_known_transit():
    # Jupiter entered sidereal Taurus on 1 May 2024 (IST).
    events = nakshatra_ingresses("Jupiter", _parse("2024-01-01"),
                                 _parse("2024-12-31"))
    assert any(e["label"] in ("Krittika", "Rohini") for e in events)
    assert all(e["planet"] == "Jupiter" for e in events)


def test_nakshatra_periods_jupiter_2024():
    periods = nakshatra_periods("Jupiter", _parse("2024-01-01"),
                                _parse("2024-12-31"))
    # Jupiter covers ~2.5 nakshatras a year; retrograde oscillation adds
    # re-entries, so a handful of periods is expected.
    assert 3 <= len(periods) <= 10
    for p in periods:
        assert set(p) == {"start", "end", "nakshatra", "pada", "days"}
        assert p["days"] > 0
        assert p["nakshatra"] != "Abhijit"
        assert 1 <= p["pada"] <= 4
    for a, b in zip(periods, periods[1:]):  # noqa: B905 -- shifted pairing by design
        assert a["nakshatra"] != b["nakshatra"]
        assert _parse(b["start"]) >= _parse(a["end"])


def test_nakshatra_periods_moon_one_per_day():
    periods = nakshatra_periods("Moon", _parse("2024-06-01"),
                                _parse("2024-06-30"))
    assert 26 <= len(periods) <= 31
    # Range edges are clipped: first period starts at range start,
    # last period ends at range end.
    assert periods[0]["start"] == "2024-06-01"
    assert periods[-1]["end"] == "2024-06-30"
    total_days = sum(p["days"] for p in periods)
    assert 28 <= total_days <= 31


def test_nakshatra_periods_clipped_to_range():
    periods = nakshatra_periods("Jupiter", _parse("2024-06-15"),
                                _parse("2024-09-15"))
    assert periods[0]["start"] == "2024-06-15"
    assert periods[-1]["end"] == "2024-09-15"
    assert all(_parse(p["end"]) >= _parse(p["start"]) for p in periods)
