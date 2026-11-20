"""Crash Cluster Index (CCI): one vote each from a backdrop, a trigger and a timing family.

Pure logic. The definitions are frozen in
docs/research/crash_cluster_index_preregistration_2026-11-19.md (T1.4 of the 2026-11-19 crash
audit). Don't change them here; a different choice is a new registration. Not wired into any
UI or production score. Research only, not financial advice.

    B (backdrop)  hard aspect between two of Saturn, Uranus, Neptune, Pluto, <= 3 deg, applying
    T (trigger)   hard Mars-Saturn <= 3 deg applying, or hard Mars-Uranus / Mars-Pluto <= 3 deg,
                  or a Mars station within +-3 sessions
    W (timing)    an eclipse within +-10 days, or a Saturn/Uranus/Neptune/Pluto station
                  within +-5 sessions
    CCI = B + T + W (0-3), each family 0 or 1. Fires at 3.

The sky is read at 09:15 IST, sidereal Lahiri, Moshier (sbc.planets). Flags depend on dates
only, never on prices; the ephemeris is computable in advance.
"""

from __future__ import annotations

import bisect
import datetime as dt
import itertools
from functools import lru_cache

import numpy as np
import swisseph as swe

from sbc import stations
from sbc.backtest import _eclipses_in_year
from sbc.planetary_event_timeline import episode_starts
from sbc.planets import _flags

ORB = 3.0
HARD = (0.0, 90.0, 180.0)
APPLY_DT = 0.01  # days, first-order step for "applying"
MARS_STATION_SESSIONS = 3
OUTER_STATION_SESSIONS = 5
ECLIPSE_DAYS = 10
OUTERS = ("Saturn", "Uranus", "Neptune", "Pluto")
_BODY = {"Mars": swe.MARS, "Saturn": swe.SATURN, "Uranus": swe.URANUS,
         "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO}


def _jd(day: str) -> float:
    d = dt.date.fromisoformat(day)
    return float(swe.julday(d.year, d.month, d.day, 9.25 - 5.5))  # 09:15 IST in UT


def _sep(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _hard(lon: dict, spd: dict, a: str, b: str, need_applying: bool) -> bool:
    s = _sep(lon[a], lon[b])
    target = min(HARD, key=lambda x: abs(s - x))
    gap = abs(s - target)
    if gap > ORB:
        return False
    if not need_applying:
        return True
    s1 = _sep(lon[a] + spd[a] * APPLY_DT, lon[b] + spd[b] * APPLY_DT)
    return abs(s1 - target) < gap


@lru_cache(maxsize=65536)
def sky_flags(day: str) -> dict:
    """The aspect members of B and T for one sky date (no windows)."""
    jd = _jd(day)
    lon, spd = {}, {}
    for name, body in _BODY.items():
        xx = swe.calc_ut(jd, body, _flags())[0]
        lon[name], spd[name] = xx[0] % 360.0, xx[3]
    return {
        "B": any(_hard(lon, spd, a, b, True) for a, b in itertools.combinations(OUTERS, 2)),
        "T_mars_saturn": _hard(lon, spd, "Mars", "Saturn", True),
        "T_mars_uranus": _hard(lon, spd, "Mars", "Uranus", False),
        "T_mars_pluto": _hard(lon, spd, "Mars", "Pluto", False),
    }


def _station_dates(first: dt.date, last: dt.date, bodies: tuple[str, ...]) -> list[str]:
    out, lo = [], first
    while lo <= last:
        hi = min(lo + dt.timedelta(3000), last + dt.timedelta(1))
        out += [r["date"] for r in stations.between(lo, hi, bodies)]
        lo = hi
    return sorted(set(out))


def _window_mask(sky: list[str], event_dates: list[str], k: int) -> np.ndarray:
    """True for sessions within +-k sessions of the first session whose sky date >= each event date."""
    mask = np.zeros(len(sky), dtype=bool)
    for e in event_dates:
        i = bisect.bisect_left(sky, e)
        if i < len(sky):
            mask[max(0, i - k):i + k + 1] = True
    return mask


def compute(session_dates: list[str], sky_offset_days: int = 0) -> dict[str, np.ndarray]:
    """Per-session flags, CCI, fire and episode starts.

    Each session's sky date is its date + `sky_offset_days` (0 for the real test; the
    shifted-sky placebo uses 180-720). Session dates must be ascending ISO dates.
    """
    sky = [(dt.date.fromisoformat(d) + dt.timedelta(sky_offset_days)).isoformat() for d in session_dates]
    n = len(sky)
    flags = [sky_flags(d) for d in sky]
    out = {k: np.array([f[k] for f in flags], dtype=bool)
           for k in ("B", "T_mars_saturn", "T_mars_uranus", "T_mars_pluto")}

    first = dt.date.fromisoformat(sky[0]) - dt.timedelta(30)
    last = dt.date.fromisoformat(sky[-1]) + dt.timedelta(30)
    out["T_mars_station"] = _window_mask(sky, _station_dates(first, last, ("Mars",)), MARS_STATION_SESSIONS)
    out["W_station"] = _window_mask(sky, _station_dates(first, last, OUTERS), OUTER_STATION_SESSIONS)

    ecl = [t for y in range(first.year, last.year + 1) for t, _kind, _sign in _eclipses_in_year(y)]
    jds = np.array([_jd(d) for d in sky])
    w_ecl = np.zeros(n, dtype=bool)
    for t in ecl:
        w_ecl |= np.abs(jds - t) <= ECLIPSE_DAYS
    out["W_eclipse"] = w_ecl

    out["T"] = out["T_mars_saturn"] | out["T_mars_uranus"] | out["T_mars_pluto"] | out["T_mars_station"]
    out["W"] = out["W_eclipse"] | out["W_station"]
    out["cci"] = out["B"].astype(int) + out["T"].astype(int) + out["W"].astype(int)
    out["fire"] = out["cci"] == 3
    out["episode_start"] = episode_starts(out["fire"])
    return out
