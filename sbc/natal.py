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

import swisseph as swe

from sbc.engine import ANCHORS, _julday, _utc_from_local
from sbc.planets import positions

DEFAULT_TIME = "00:00"
DEFAULT_TZ = "Asia/Kolkata"
DEFAULT_CITY = "Mumbai"


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


@lru_cache(maxsize=64)
def _lagna_longitude(date: str, time: str, tz: str, city: str) -> float:
    """Ascendant longitude (Lahiri, whole-sign house wheel) at the moment."""
    from sbc import cities  # noqa: PLC0415

    utc = _utc_from_local(date, time, tz)
    jd = _julday(utc)
    place = cities.resolve(city) or cities.resolve(DEFAULT_CITY)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    _cusps, ascmc = swe.houses_ex(jd, place["lat"], place["lon"], b"W",
                                  swe.FLG_SIDEREAL)
    return float(ascmc[0] % 360.0)


def lagna_longitude(anchor_or_date: str, time: str | None = None,
                    tz: str | None = None, city: str | None = None) -> float:
    """Ascendant (Lagna) sidereal longitude for the birth moment.

    `city` defaults to Mumbai for the built-in anchors (all Indian
    exchange anchors) and must be a city name cities.resolve knows for
    hand-supplied birth moments.
    """
    date, t, zone = _birth(anchor_or_date, time, tz)
    return _lagna_longitude(date, t, zone, city or DEFAULT_CITY)


def house_of(longitude: float, lagna_lon: float) -> int:
    """Whole-sign house (1-12) of a longitude counted from the Lagna sign."""
    return (int(longitude % 360.0 // 30) - int(lagna_lon % 360.0 // 30)) \
        % 12 + 1


def house_chart(anchor_or_date: str, time: str | None = None,
                tz: str | None = None, city: str | None = None) -> dict:
    """{lagna: sign name, lagna_longitude, houses: {planet: house 1-12}}."""
    from .nakshatra import RASHIS  # noqa: PLC0415

    lag = lagna_longitude(anchor_or_date, time, tz, city)
    return {
        "lagna_longitude": round(lag, 4),
        "lagna": RASHIS[int(lag // 30)],
        "houses": {p["name"]: house_of(p["longitude"], lag)
                   for p in chart_detail(anchor_or_date, time, tz)},
    }
