"""Heliocentric aspect windows: Earth against each planet (B-39 ENTRY layer).

Longitudes are heliocentric and tropical (Swiss Ephemeris, Moshier). The angle
between two bodies doesn't depend on the zodiac, so Lahiri vs tropical makes no
difference to an aspect. Earth's heliocentric longitude is the geocentric Sun
+ 180 deg.

scan(start, end) samples the Earth-planet separation every `step_minutes`
(default 60) and returns each window in which it sits within `orb` (default 2
deg) of an aspect angle. Entry and exit times are refined by bisection to the
minute, and the exact time is the minimum of |separation - angle|. Times are IST.
A window shorter than the step can be missed. Mercury's fastest relative motion
(~5.5 deg/day) still gives a 4-deg window of ~17 h, so the 60-minute step catches
every one.
"""

from __future__ import annotations

import datetime as dt
from functools import lru_cache

import numpy as np
import swisseph as swe

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
PLANETS = {
    "Mercury": swe.MERCURY, "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO,
}
ASPECTS = {"CONJ": 0.0, "OPP": 180.0, "TRI": 120.0, "SQ": 90.0, "SXT": 60.0,
           "QCX": 150.0, "SS": 45.0, "SSQ": 135.0}
ASPECT_NAMES = {"CONJ": "Conjunction", "OPP": "Opposition", "TRI": "Trine", "SQ": "Square",
                "SXT": "Sextile", "QCX": "Quincunx", "SS": "Semi-square", "SSQ": "Sesquiquadrate"}
ORB = 2.0
_FLAGS = swe.FLG_MOSEPH | swe.FLG_HELCTR


def _jd(t: dt.datetime) -> float:
    t = t.astimezone(dt.UTC)
    return swe.julday(t.year, t.month, t.day, t.hour + t.minute / 60 + t.second / 3600)


def _to_ist(jd: float) -> dt.datetime:
    y, m, d, h = swe.revjul(jd)
    base = dt.datetime(y, m, d, tzinfo=dt.UTC) + dt.timedelta(hours=h)
    return base.astimezone(IST).replace(second=0, microsecond=0)


def helio_longitude(body: int, jd: float) -> float:
    return swe.calc_ut(jd, body, _FLAGS)[0][0] % 360.0


def separation(planet: str, jd: float) -> float:
    """Unsigned angle between Earth and `planet`, 0..180 deg."""
    d = abs(helio_longitude(swe.EARTH, jd) - helio_longitude(PLANETS[planet], jd)) % 360.0
    return 360.0 - d if d > 180.0 else d


def _deviation(planet: str, angle: float, jd: float) -> float:
    return abs(separation(planet, jd) - angle)


def _bisect(planet: str, angle: float, orb: float, inside: float, outside: float) -> float:
    """Boundary between a jd inside the orb and one outside, to ~1 minute."""
    while abs(inside - outside) > 1.0 / 1440:
        mid = (inside + outside) / 2
        if _deviation(planet, angle, mid) <= orb:
            inside = mid
        else:
            outside = mid
    return inside


def _exact(planet: str, angle: float, lo: float, hi: float) -> tuple[float, float]:
    """(jd, deviation) of the closest approach in [lo, hi] (golden-section, ~1 minute)."""
    g = (5 ** 0.5 - 1) / 2
    a, b = lo, hi
    while b - a > 1.0 / 1440:
        c, d = b - g * (b - a), a + g * (b - a)
        if _deviation(planet, angle, c) < _deviation(planet, angle, d):
            b = d
        else:
            a = c
    jd = (a + b) / 2
    return jd, _deviation(planet, angle, jd)


@lru_cache(maxsize=16)
def _separation_grid(planet: str, jd0: float, jd1: float, step: float) -> tuple[np.ndarray, np.ndarray]:
    grid = np.arange(jd0, jd1 + step / 2, step)
    return grid, np.array([separation(planet, j) for j in grid])


@lru_cache(maxsize=128)
def _windows(planet: str, code: str, jd0: float, jd1: float, step: float, orb: float) -> tuple:
    angle = ASPECTS[code]
    grid, sep = _separation_grid(planet, jd0, jd1, step)
    inside = np.abs(sep - angle) <= orb
    out = []
    i = 0
    n = len(grid)
    while i < n:
        if not inside[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and inside[j + 1]:
            j += 1
        entry = grid[i] if i == 0 else _bisect(planet, angle, orb, grid[i], grid[i - 1])
        exit_ = grid[j] if j == n - 1 else _bisect(planet, angle, orb, grid[j], grid[j + 1])
        exact_jd, dev = _exact(planet, angle, entry, exit_)
        out.append((entry, exact_jd, exit_, dev, i == 0, j == n - 1))
        i = j + 1
    return tuple(out)


def scan(start: str, end: str, planets=None, aspects=None, orb: float = ORB,
         step_minutes: int = 60) -> list[dict]:
    """Earth-planet aspect windows overlapping [start, end] (dates, IST), sorted by entry."""
    planets = list(planets or PLANETS)
    aspects = list(aspects or ASPECTS)
    bad = [p for p in planets if p not in PLANETS] + [a for a in aspects if a not in ASPECTS]
    if bad:
        raise ValueError(f"unknown planet/aspect: {', '.join(bad)}")
    d0 = dt.datetime.combine(dt.date.fromisoformat(start), dt.time(0, 0), IST)
    d1 = dt.datetime.combine(dt.date.fromisoformat(end), dt.time(23, 59), IST)
    if d1 < d0:
        raise ValueError("end before start")
    jd0, jd1 = _jd(d0), _jd(d1)
    step = step_minutes / 1440.0
    rows = []
    for planet in planets:
        for code in aspects:
            for entry, exact, exit_, dev, open_start, open_end in _windows(planet, code, jd0, jd1, step, orb):
                e, x, ex = _to_ist(entry), _to_ist(exit_), _to_ist(exact)
                rows.append({
                    "pair": f"Earth-{planet}", "planet": planet, "aspect": code,
                    "aspect_name": ASPECT_NAMES[code], "angle": ASPECTS[code],
                    "entry_date": e.date().isoformat(), "entry_time": e.strftime("%H:%M"),
                    "exact_date": ex.date().isoformat(), "exact_time": ex.strftime("%H:%M"),
                    "exit_date": x.date().isoformat(), "exit_time": x.strftime("%H:%M"),
                    "min_orb": round(dev, 3),
                    "starts_before_range": open_start, "ends_after_range": open_end,
                })
    rows.sort(key=lambda r: (r["entry_date"], r["entry_time"], r["planet"], r["aspect"]))
    return rows


def tv_payload(windows: list[dict], label: str | None = None) -> dict:
    """The TradingView indicator payload: unique entry dates, ascending."""
    dates = sorted({w["entry_date"] for w in windows if not w["starts_before_range"]})
    if label is None:
        codes = sorted({w["aspect"] for w in windows})
        label = "+".join(codes) if codes else "NONE"
    return {"dates": dates, "label": label, "skip_holidays": False}


def active_on(day: str, planets=None, aspects=None, orb: float = ORB) -> list[dict]:
    """Windows in force at 09:15 IST on `day` (for the daily forecast component)."""
    t = dt.datetime.combine(dt.date.fromisoformat(day), dt.time(9, 15), IST)
    jd = _jd(t)
    out = []
    for planet in planets or PLANETS:
        sep = separation(planet, jd)
        for code in aspects or ASPECTS:
            if abs(sep - ASPECTS[code]) <= orb:
                out.append({"planet": planet, "aspect": code, "orb": round(abs(sep - ASPECTS[code]), 3)})
    return out
