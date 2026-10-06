"""Planetary stations timed to the minute (IST), including the true-node Rahu (B-42).

A station is where a body's geocentric sidereal (Lahiri) longitude speed
changes sign. `between(start, end)` scans Swiss Ephemeris speed in hourly
steps, then bisects each sign change down to a few seconds.

Unlike sbc.forward_calendar (which dates a station to the first 09:15 IST
fingerprint after it), these times are exact. Sidereal speed differs from
tropical speed by the ayanamsa rate (~0.00004 deg/day), which moves the
station of a slow planet by hours (Pluto: ~3 h), so the zodiac matters.

Rahu here is the true (osculating) node, which stations several times a
month; sbc.planets uses the mean node, which never does. Ketu mirrors Rahu
and is not listed separately.

Checked against a third-party October 2026 table (screenshot 7 of the
monthly-projection note): Venus R 03-10 12:43, Rahu R 07-10 06:48 (06:49),
Pluto D 16-10 11:02 and Mercury R 24-10 12:42 match to within a minute.
Rahu D 03-10 comes out at 22:01 against the source's 19:06; the true node's
speed is nearly flat there (~0.001 deg/day per hour), so a small difference
in lunar theory (Moshier here, no ephemeris files) moves it by hours.
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import swisseph as swe

IST = ZoneInfo("Asia/Kolkata")
BODIES = (
    ("Mercury", swe.MERCURY), ("Venus", swe.VENUS), ("Mars", swe.MARS),
    ("Jupiter", swe.JUPITER), ("Saturn", swe.SATURN), ("Uranus", swe.URANUS),
    ("Neptune", swe.NEPTUNE), ("Pluto", swe.PLUTO), ("Rahu", swe.TRUE_NODE),
)
STEP_DAYS = 1.0 / 24.0
_FLAGS = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
_BISECT = 20  # one hour / 2**20 ~ 3.4 ms


def _jd(when: dt.datetime) -> float:
    u = when.astimezone(dt.UTC)
    return float(swe.julday(u.year, u.month, u.day,
                            u.hour + u.minute / 60 + u.second / 3600 + u.microsecond / 3.6e9))


def _from_jd(jd: float) -> dt.datetime:
    y, m, d, h = swe.revjul(jd)
    utc = dt.datetime(y, m, d, tzinfo=dt.UTC) + dt.timedelta(hours=h)
    return utc.astimezone(IST)


def _speed(jd: float, body: int) -> float:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return float(swe.calc_ut(jd, body, _FLAGS)[0][3])


def _refine(lo: float, hi: float, body: int, s_lo: float) -> float:
    for _ in range(_BISECT):
        mid = (lo + hi) / 2
        if (_speed(mid, body) > 0) == (s_lo > 0):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _as_ist(x: dt.date | dt.datetime) -> dt.datetime:
    if isinstance(x, dt.datetime):
        return x.replace(tzinfo=IST) if x.tzinfo is None else x.astimezone(IST)
    return dt.datetime.combine(x, dt.time(0, 0), IST)


def between(start: dt.date | dt.datetime, end: dt.date | dt.datetime,
            bodies: tuple[str, ...] | None = None) -> list[dict]:
    """Stations in [start, end) sorted by time; a date means 00:00 IST that day.

    Each row: {planet, direction ('retrograde'|'direct'), time (IST ISO, minutes),
    date (IST), label e.g. 'Mercury stations retrograde 12:42'}.
    """
    t0, t1 = _as_ist(start), _as_ist(end)
    if t1 <= t0:
        raise ValueError("end must be after start")
    if (t1 - t0).days > 3660:
        raise ValueError("range is limited to ten years")
    wanted = set(bodies) if bodies else None
    jd0, jd1 = _jd(t0), _jd(t1)
    out = []
    for name, body in BODIES:
        if wanted is not None and name not in wanted:
            continue
        jd, s = jd0, _speed(jd0, body)
        while jd < jd1:
            nxt = min(jd + STEP_DAYS, jd1)
            s2 = _speed(nxt, body)
            if s != 0 and (s > 0) != (s2 > 0):
                when = _from_jd(_refine(jd, nxt, body, s))
                direction = "retrograde" if s > 0 else "direct"
                out.append({
                    "planet": name, "direction": direction,
                    "time": when.strftime("%Y-%m-%dT%H:%M"), "date": when.date().isoformat(),
                    "label": f"{name} stations {direction} {when.strftime('%H:%M')}",
                })
            jd, s = nxt, s2
    return sorted(out, key=lambda r: (r["time"], r["planet"]))


def by_date(start: dt.date, end: dt.date, bodies: tuple[str, ...] | None = None) -> dict[str, list[dict]]:
    """Stations from start through end (inclusive), grouped by IST date."""
    out: dict[str, list[dict]] = {}
    for row in between(start, end + dt.timedelta(days=1), bodies):
        out.setdefault(row["date"], []).append(row)
    return out
