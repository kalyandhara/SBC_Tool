"""Transit-to-natal aspect windows (B-51): a transiting planet aspecting a planet in
an instrument's own natal chart (sbc.natal).

This is the "Kundali method" of the lecture in docs/KUNDALI_METHOD_INGEST_2026-10-10.md:
cast the instrument's D1 chart once, then date every contact a transiting planet
makes with a natal planet. It differs from sbc.helio_aspects, which dates contacts
between two moving bodies (Earth and a planet, heliocentric). Here one end is a
fixed natal longitude and the transit is geocentric sidereal (Lahiri), the same
convention as sbc.planets.

The aspects and the 2 deg orb are the B-39 ones (sbc.helio_aspects.ASPECTS, ORB), and
every window has the same fields as sbc.helio_aspects.scan, so sbc.swing_model and
sbc.swing_validation read it unchanged. Two extra fields name the natal end:
`natal` and `natal_longitude`. `planet` is the transiting planet and `pair`
reads "Mars -> natal Sun".

Transit planets default to Sun, Mercury, Venus, Mars, Jupiter, Saturn and Rahu. The
Moon is left out: at 13 deg/day it is inside some 2 deg orb on most days, which makes
"in a window" a near-constant call. Ketu is left out because it is always Rahu + 180,
so its contacts repeat Rahu's. Pass `planets=` to include the Moon. Natal points are
all nine grahas.

    scan(natal, start, end)      windows overlapping [start, end] (dates, IST), sorted by entry
    active_on(natal, day)        contacts in force at 09:15 IST on `day`
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from functools import lru_cache

import numpy as np
import swisseph as swe

from sbc.helio_aspects import ASPECT_NAMES, ASPECTS, IST, ORB, _jd, _to_ist
from sbc.planets import SWE_BODIES, _flags

BODY = {name: body for body, name in SWE_BODIES}
TRANSIT_PLANETS = ["Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu"]


def _lon(planet: str, jd: float) -> float:
    return float(swe.calc_ut(jd, BODY[planet], _flags())[0][0]) % 360.0


def _fold(diff: np.ndarray | float) -> np.ndarray | float:
    """Unsigned angle 0..180 between two longitudes, given their difference."""
    d = np.abs(diff) % 360.0
    return np.where(d > 180.0, 360.0 - d, d) if isinstance(d, np.ndarray) else (360.0 - d if d > 180.0 else d)


def _deviation(planet: str, natal_lon: float, angle: float, jd: float) -> float:
    return float(abs(_fold(_lon(planet, jd) - natal_lon) - angle))


def _bisect(planet: str, natal_lon: float, angle: float, orb: float, inside: float, outside: float) -> float:
    """Boundary between a jd inside the orb and one outside, to ~1 minute."""
    while abs(inside - outside) > 1.0 / 1440:
        mid = (inside + outside) / 2
        if _deviation(planet, natal_lon, angle, mid) <= orb:
            inside = mid
        else:
            outside = mid
    return inside


def _exact(planet: str, natal_lon: float, angle: float, lo: float, hi: float) -> tuple[float, float]:
    """(jd, deviation) of the closest approach in [lo, hi] (golden-section, ~1 minute)."""
    g = (5 ** 0.5 - 1) / 2
    a, b = lo, hi
    while b - a > 1.0 / 1440:
        c, d = b - g * (b - a), a + g * (b - a)
        if _deviation(planet, natal_lon, angle, c) < _deviation(planet, natal_lon, angle, d):
            b = d
        else:
            a = c
    jd = (a + b) / 2
    return jd, _deviation(planet, natal_lon, angle, jd)


@lru_cache(maxsize=16)
def _lon_grid(planet: str, jd0: float, jd1: float, step: float) -> tuple[np.ndarray, np.ndarray]:
    grid = np.arange(jd0, jd1 + step / 2, step)
    return grid, np.array([_lon(planet, j) for j in grid])


def _windows(planet: str, natal_lon: float, code: str, jd0: float, jd1: float, step: float,
             orb: float) -> list[tuple]:
    angle = ASPECTS[code]
    grid, lon = _lon_grid(planet, jd0, jd1, step)
    inside = np.abs(_fold(lon - natal_lon) - angle) <= orb
    out = []
    i, n = 0, len(grid)
    while i < n:
        if not inside[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and inside[j + 1]:
            j += 1
        entry = grid[i] if i == 0 else _bisect(planet, natal_lon, angle, orb, grid[i], grid[i - 1])
        exit_ = grid[j] if j == n - 1 else _bisect(planet, natal_lon, angle, orb, grid[j], grid[j + 1])
        exact_jd, dev = _exact(planet, natal_lon, angle, entry, exit_)
        out.append((entry, exact_jd, exit_, dev, i == 0, j == n - 1))
        i = j + 1
    return out


def _check(natal: dict[str, float], planets: list[str], points: list[str], aspects: list[str]) -> None:
    bad = ([p for p in planets if p not in BODY] + [a for a in aspects if a not in ASPECTS]
           + [p for p in points if p not in natal])
    if bad:
        raise ValueError(f"unknown planet/aspect/natal point: {', '.join(bad)}")


def scan(natal: dict[str, float], start: str, end: str, planets: Iterable[str] | None = None,
         natal_points: Iterable[str] | None = None, aspects: Iterable[str] | None = None,
         orb: float = ORB, step_minutes: int = 60) -> list[dict]:
    """Transit-to-natal windows overlapping [start, end] (dates, IST), sorted by entry.

    `natal` is {planet: longitude} from sbc.natal.chart. A window shorter than the step
    can be missed; the slowest-relative-motion case that matters (a station right at the
    orb edge) leaves a sliver with min_orb near the full orb, which is not a usable window.
    """
    planets = list(planets or TRANSIT_PLANETS)
    points = list(natal_points or natal)
    aspects = list(aspects or ASPECTS)
    _check(natal, planets, points, aspects)
    d0 = dt.datetime.combine(dt.date.fromisoformat(start), dt.time(0, 0), IST)
    d1 = dt.datetime.combine(dt.date.fromisoformat(end), dt.time(23, 59), IST)
    if d1 < d0:
        raise ValueError("end before start")
    jd0, jd1 = _jd(d0), _jd(d1)
    step = step_minutes / 1440.0
    rows = []
    for planet in planets:
        for point in points:
            for code in aspects:
                for entry, exact, exit_, dev, open_start, open_end in _windows(
                        planet, natal[point], code, jd0, jd1, step, orb):
                    e, x, ex = _to_ist(entry), _to_ist(exit_), _to_ist(exact)
                    rows.append({
                        "pair": f"{planet} -> natal {point}", "planet": planet, "natal": point,
                        "natal_longitude": round(natal[point], 4), "aspect": code,
                        "aspect_name": ASPECT_NAMES[code], "angle": ASPECTS[code],
                        "entry_date": e.date().isoformat(), "entry_time": e.strftime("%H:%M"),
                        "exact_date": ex.date().isoformat(), "exact_time": ex.strftime("%H:%M"),
                        "exit_date": x.date().isoformat(), "exit_time": x.strftime("%H:%M"),
                        "min_orb": round(dev, 3),
                        "starts_before_range": open_start, "ends_after_range": open_end,
                    })
    rows.sort(key=lambda r: (r["entry_date"], r["entry_time"], r["planet"], r["natal"], r["aspect"]))
    return rows


def active_on(natal: dict[str, float], day: str, planets: Iterable[str] | None = None,
              natal_points: Iterable[str] | None = None, aspects: Iterable[str] | None = None,
              orb: float = ORB) -> list[dict]:
    """Contacts in force at 09:15 IST on `day` (the session flag for validation)."""
    planets = list(planets or TRANSIT_PLANETS)
    points = list(natal_points or natal)
    aspects = list(aspects or ASPECTS)
    _check(natal, planets, points, aspects)
    jd = _jd(dt.datetime.combine(dt.date.fromisoformat(day), dt.time(9, 15), IST))
    out = []
    for planet in planets:
        lon = _lon(planet, jd)
        for point in points:
            sep = float(_fold(lon - natal[point]))
            for code in aspects:
                if abs(sep - ASPECTS[code]) <= orb:
                    out.append({"planet": planet, "natal": point, "aspect": code,
                                "orb": round(abs(sep - ASPECTS[code]), 3)})
    return out
