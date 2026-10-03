"""Exact muhurta windows for weekday + nakshatra yogas (Guru Pushya, Ravi Pushya).

A vara (weekday) runs from local sunrise to the next sunrise, so Thursday's
vara includes the small hours before Friday's sunrise. A yoga holds for the
part of that vara during which the Moon is in the nakshatra.

Conventions match the rest of the tool: sidereal Lahiri, Moshier ephemeris,
sunrise at NSE Mumbai (sbc.kp_ephemeris.sunrise_ist), times as naive IST.
Checked against Drik Panchang's 2027 Guru Pushya list (to the minute; Drik
uses Delhi sunrise). The strict vara rule also yields 2027-11-18, when Pushya
starts at 01:52 before Friday's sunrise; some published lists omit such
pre-dawn-only overlaps.
"""

from __future__ import annotations

import datetime as dt
from functools import lru_cache

import swisseph as swe

from sbc.kp_ephemeris import IST, sunrise_ist

NAKSHATRA_SPAN = 360.0 / 27.0
PUSHYA_INDEX = 7  # 0 = Ashwini; Pushya spans 93deg20' - 106deg40'
THURSDAY, SUNDAY = 3, 6


def _jd(t_ist: dt.datetime) -> float:
    u = t_ist - IST
    return swe.julday(u.year, u.month, u.day, u.hour + u.minute / 60 + u.second / 3600)


def _ist(jd: float) -> dt.datetime:
    y, m, d, h = swe.revjul(jd)
    return (dt.datetime(y, m, d) + dt.timedelta(hours=h) + IST).replace(microsecond=0)


def _moon_lon(jd: float) -> float:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return swe.calc_ut(jd, swe.MOON, swe.FLG_MOSEPH | swe.FLG_SIDEREAL)[0][0] % 360.0


def _in_nakshatra(jd: float, index: int) -> bool:
    return int(_moon_lon(jd) // NAKSHATRA_SPAN) % 27 == index


def _edge(a: float, b: float, index: int) -> float:
    """Bisect the moment the in-nakshatra state flips between a and b (to < 1 s)."""
    state_a = _in_nakshatra(a, index)
    for _ in range(40):
        mid = (a + b) / 2
        if _in_nakshatra(mid, index) == state_a:
            a = mid
        else:
            b = mid
    return b


@lru_cache(maxsize=512)
def vara_nakshatra_window(day: dt.date, nakshatra_index: int) -> tuple[dt.datetime, dt.datetime] | None:
    """(start, end) IST of the Moon in the nakshatra within `day`'s vara, or None."""
    v0 = _jd(sunrise_ist(day))
    v1 = _jd(sunrise_ist(day + dt.timedelta(days=1)))
    # The Moon crosses at most two boundaries in a day; 30-minute steps
    # cannot skip a 13deg20' nakshatra (the Moon needs ~24 h for it).
    step = 1 / 48
    start = v0 if _in_nakshatra(v0, nakshatra_index) else None
    end = None
    t = v0
    while t < v1:
        n = min(t + step, v1)
        a, b = _in_nakshatra(t, nakshatra_index), _in_nakshatra(n, nakshatra_index)
        if not a and b and start is None:
            start = _edge(t, n, nakshatra_index)
        if a and not b and start is not None:
            end = _edge(t, n, nakshatra_index)
            break
        t = n
    if start is None:
        return None
    return _ist(start), _ist(end if end is not None else v1)


def guru_pushya_window(day: dt.date) -> tuple[dt.datetime, dt.datetime] | None:
    """Guru Pushya Yoga window for a Thursday (sunrise-to-sunrise vara), else None."""
    if day.weekday() != THURSDAY:
        return None
    return vara_nakshatra_window(day, PUSHYA_INDEX)


def ravi_pushya_window(day: dt.date) -> tuple[dt.datetime, dt.datetime] | None:
    """Ravi Pushya Yoga window for a Sunday (sunrise-to-sunrise vara), else None."""
    if day.weekday() != SUNDAY:
        return None
    return vara_nakshatra_window(day, PUSHYA_INDEX)


def format_window(window: tuple[dt.datetime, dt.datetime]) -> str:
    """'21:06 Thu -> 07:05 Fri IST' style label."""
    s, e = window
    return f"{s:%H:%M %a} -> {e:%H:%M %a} IST"
