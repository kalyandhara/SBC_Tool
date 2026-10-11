"""Natal (D1) chart: planet longitudes at an instrument's birth moment (B-49).

Geocentric sidereal with the Lahiri ayanamsa, from sbc.planets.positions, the
same convention as the rest of the engine. The birth moment is either an
sbc.engine.ANCHORS key ("nifty", "nse", ...) or a date given by hand. Every
existing anchor is stored at 00:00 IST, so a bare date defaults to that.

    chart("nifty")                       -> {"Sun": 196.2, "Moon": ..., ..., "Ketu": ...}
    chart("2007-03-21", "10:00")         -> a hand-supplied birth moment
    chart_detail("nifty")                -> the same, with sign, nakshatra and degree

The result is a fixed set of longitudes, so it is cached.
"""

from __future__ import annotations

from functools import lru_cache

from sbc.engine import ANCHORS, _julday, _utc_from_local
from sbc.planets import positions

DEFAULT_TIME = "00:00"
DEFAULT_TZ = "Asia/Kolkata"


def _birth(anchor_or_date: str, time: str | None, tz: str | None) -> tuple[str, str, str]:
    """(date, time, tz) for an anchor key or an ISO date."""
    if anchor_or_date in ANCHORS:
        a = ANCHORS[anchor_or_date]
        return a["date"], time or a["time"], tz or a["tz"]
    return anchor_or_date, time or DEFAULT_TIME, tz or DEFAULT_TZ


@lru_cache(maxsize=64)
def _planets(date: str, time: str, tz: str) -> tuple[dict, ...]:
    try:
        utc = _utc_from_local(date, time, tz)
    except ValueError as exc:
        raise ValueError(f"invalid birth date/time: {date} {time}") from exc
    planets, _ayanamsa = positions(_julday(utc))
    return tuple(planets)


def chart_detail(anchor_or_date: str, time: str | None = None, tz: str | None = None) -> list[dict]:
    """Every planet's longitude, sign, nakshatra and speed at the birth moment."""
    return [dict(p) for p in _planets(*_birth(anchor_or_date, time, tz))]


def chart(anchor_or_date: str, time: str | None = None, tz: str | None = None) -> dict[str, float]:
    """{planet: sidereal longitude in degrees} for the nine grahas (Rahu and Ketu included)."""
    return {p["name"]: p["longitude"] for p in chart_detail(anchor_or_date, time, tz)}
