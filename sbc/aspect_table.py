"""Exact-time geocentric sidereal aspect table (B-43).

Uses Swiss Ephemeris with Lahiri sidereal mode, IST times, hourly scan with
bisection to minute precision.  Moon is included.  Aspects are 0/30/45/60/90/120/135/
150/180 plus orb-entry KSc/KSp events.

The public entry point is get_aspects(start_date, end_date) -> list[dict].
"""

from __future__ import annotations

import datetime as dt
from datetime import date, datetime, time, timedelta
from typing import Any, Callable, Dict, List, Tuple

import swisseph as swe

from .kp_ephemeris import _julday_ist
from .market_events import ASPECT_ORBS
from .muhurta import ghabad_kind_at

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IST = dt.timedelta(hours=5, minutes=30)

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

SIGN_ABBREV = {
    "Aries": "Ar", "Taurus": "Ta", "Gemini": "Ge", "Cancer": "Ca",
    "Leo": "Le", "Virgo": "Vi", "Libra": "Li", "Scorpio": "Sc",
    "Sagittarius": "Sa", "Capricorn": "Cp", "Aquarius": "Aq", "Pisces": "Pi"
}

PLANET_SWE = [
    ("Sun", swe.SUN),
    ("Moon", swe.MOON),
    ("Mercury", swe.MERCURY),
    ("Venus", swe.VENUS),
    ("Mars", swe.MARS),
    ("Jupiter", swe.JUPITER),
    ("Saturn", swe.SATURN),
    ("Uranus", swe.URANUS),
    ("Neptune", swe.NEPTUNE),
    ("Pluto", swe.PLUTO),
    ("Rahu", swe.TRUE_NODE),
]

SWE_BODY = dict(PLANET_SWE)

COMBUST_ORB = {
    "Moon": 12.0, "Mars": 17.0, "Mercury": 14.0,
    "Jupiter": 11.0, "Venus": 10.0, "Saturn": 15.0
}

# planetary war rank – tie-breaker for winner
RANK = {
    "Sun": 10, "Moon": 9, "Mars": 8, "Mercury": 7, "Jupiter": 6,
    "Venus": 5, "Saturn": 4, "Uranus": 3, "Neptune": 2, "Pluto": 1,
    "Rahu": 0, "Ketu": 0
}

ASPECT_ANGLES = [0, 30, 45, 60, 90, 120, 135, 150, 180]

# map angle -> orb (degrees).  Fall back to 2° for non-standard angles.
ANGLE_ORB_MAP = {
    0: ASPECT_ORBS.get("conjunction", 8.0),
    60: ASPECT_ORBS.get("sextile", 6.0),
    90: ASPECT_ORBS.get("square", 8.0),
    120: ASPECT_ORBS.get("trine", 8.0),
    180: ASPECT_ORBS.get("opposition", 8.0),
}
DEFAULT_ORB = 2.0

# How far to walk from an event looking for its orb entry or exact partner.
MAX_ORB_WALK_DAYS = 400

FLAGS = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED


def _sidereal_flags():
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return FLAGS


def _sign_info(lon: float) -> Tuple[int, str, str]:
    idx = int(lon // 30) % 12
    name = SIGN_NAMES[idx]
    abbr = SIGN_ABBREV[name]
    return idx, name, abbr


def _angular_sep(lon1: float, lon2: float) -> float:
    d = abs((lon1 - lon2 + 180) % 360 - 180)
    return d


def _positions_at(when: datetime) -> Dict[str, Dict[str, Any]]:
    """Return planet data for a naive IST datetime."""
    jd = _julday_ist(when)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    out: Dict[str, Dict[str, Any]] = {}
    rahu_lon = rahu_speed = None
    for name, body in PLANET_SWE:
        xx, _ = swe.calc_ut(jd, body, FLAGS)
        lon = xx[0] % 360.0
        speed = xx[3]
        idx, sname, sabbr = _sign_info(lon)
        out[name] = {
            "lon": lon,
            "speed": speed,
            "retro": speed < 0,
            "sign_idx": idx,
            "sign": sname,
            "abbr": sabbr,
        }
        if name == "Rahu":
            rahu_lon, rahu_speed = lon, speed
    # Ketu mirrors Rahu
    if rahu_lon is not None:
        idx, sname, sabbr = _sign_info((rahu_lon + 180) % 360)
        out["Ketu"] = {
            "lon": (rahu_lon + 180) % 360.0,
            "speed": rahu_speed,
            "retro": rahu_speed < 0,
            "sign_idx": idx,
            "sign": sname,
            "abbr": sabbr,
        }
    return out


def _winner(pl_a: Dict[str, Any], pl_b: Dict[str, Any], name_a: str, name_b: str) -> str:
    s_a = abs(pl_a["speed"])
    s_b = abs(pl_b["speed"])
    if abs(s_a - s_b) > 1e-9:
        return name_a if s_a > s_b else name_b
    # tie – higher rank, Moon preference implicit in rank
    ra = RANK.get(name_a, 0)
    rb = RANK.get(name_b, 0)
    if ra != rb:
        return name_a if ra > rb else name_b
    return name_a


def _relations(sign_idx_a: int, sign_idx_b: int, aspect: int) -> str:
    if aspect == 0:
        return "1/7"
    if aspect == 180:
        return "7/1"
    diff = (sign_idx_a - sign_idx_b) % 12
    first = diff + 1
    second = (12 - diff) + 1
    return f"{first}/{second}"


def _combust(p_data: Dict[str, Any], sun_lon: float, planet_name: str) -> bool:
    if planet_name in ("Sun",):
        return False
    orb = COMBUST_ORB.get(planet_name)
    if orb is None:
        return False
    sep = _angular_sep(p_data["lon"], sun_lon)
    return sep < orb


def _targets(angle: int) -> Tuple[int, ...]:
    """Signed offsets of an aspect: 90 happens both ahead of and behind the other body."""
    return (angle,) if angle in (0, 180) else (angle, -angle)


def _pair_offset(when: datetime, name_a: str, name_b: str, target: int) -> float:
    """Signed distance in degrees from exact, in [-180, 180). Zero means exact.

    Signed, because the folded 0..180 separation touches 0 and 180 without ever
    crossing them, which is what hid conjunctions and oppositions.
    """
    jd = _julday_ist(when)
    swe.set_sid_mode(swe.SIDM_LAHIRI)

    def lon(name: str) -> float:
        base = SWE_BODY["Rahu" if name == "Ketu" else name]
        value = swe.calc_ut(jd, base, FLAGS)[0][0]
        return value + 180.0 if name == "Ketu" else value

    return (lon(name_a) - lon(name_b) - target + 180.0) % 360.0 - 180.0


def _bisect_time(lo: datetime, hi: datetime, fn: Callable[[datetime], float]) -> datetime:
    """Earlier end of a bracket under 30 seconds wide around fn's sign change."""
    f_lo = fn(lo)
    while hi - lo > timedelta(seconds=30):
        mid = lo + (hi - lo) / 2
        f_mid = fn(mid)
        if f_lo * f_mid <= 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return lo


def _walk_step(name_a: str, name_b: str) -> timedelta:
    return timedelta(hours=3) if "Moon" in (name_a, name_b) else timedelta(days=1)


def _orb_entry_before(exact: datetime, name_a: str, name_b: str, target: int, orb: float) -> datetime | None:
    """Most recent time before an exact aspect that the pair came inside the orb."""
    gap = lambda t: abs(_pair_offset(t, name_a, name_b, target)) - orb
    step = _walk_step(name_a, name_b)
    inside = exact
    limit = exact - timedelta(days=MAX_ORB_WALK_DAYS)
    while inside > limit:
        outside = inside - step
        if gap(outside) >= 0:
            return _bisect_time(outside, inside, gap)
        inside = outside
    return None


def _exact_after(entry: datetime, name_a: str, name_b: str, target: int, orb: float) -> datetime | None:
    """The exact aspect following an orb entry, or None if the pair leaves the orb first."""
    offset = lambda t: _pair_offset(t, name_a, name_b, target)
    step = _walk_step(name_a, name_b)
    prev = entry
    limit = entry + timedelta(days=MAX_ORB_WALK_DAYS)
    while prev < limit:
        cur = prev + step
        value = offset(cur)
        if offset(prev) * value <= 0:
            return _bisect_time(prev, cur, offset)
        if abs(value) > orb:
            return None
        prev = cur
    return None


def _stamp(when: datetime | None) -> str | None:
    return when.strftime("%Y-%m-%d %H:%M") if when else None


def _build_row(when: datetime, name_a: str, name_b: str, aspect_code: int | str, angle: int) -> Dict[str, Any]:
    pos = _positions_at(when)
    pa = pos[name_a]
    pb = pos[name_b]
    sun = pos["Sun"]
    rashi1 = pa["abbr"]
    rashi2 = pb["abbr"]
    rashis = f"{rashi1}-{rashi2}"
    relations = _relations(pa["sign_idx"], pb["sign_idx"], angle)
    combust = _combust(pa, sun["lon"], name_a) or _combust(pb, sun["lon"], name_b)
    retro = pa["retro"] or pb["retro"]
    winner = _winner(pa, pb, name_a, name_b)
    weekday = when.strftime("%A")
    return {
        "date": when.date().isoformat(),
        "weekday": weekday,
        "time": when.strftime("%H:%M"),
        "pl1": name_a,
        "aspect": aspect_code,
        "target_angle": angle,
        "pl2": name_b,
        "rashi1": pa["sign"],
        "rashi2": pb["sign"],
        "rashis": rashis,
        "relations": relations,
        "combust": bool(combust),
        "retro": bool(retro),
        "winner": winner,
        "muhurta": ghabad_kind_at(when) or "",
        "orb_entry": None,
        "exact_at": None,
    }


def get_aspects(start_date: date, end_date: date) -> List[Dict[str, Any]]:
    """Return exact sidereal aspects with Moon included for the date range.

    One row per exact crossing, found on an hourly grid and refined to the
    minute, plus one KSc/KSp row per orb entry. Exact rows carry the preceding
    orb_entry and entry rows the following exact_at, either of which may fall
    outside the range; both are None when the walk finds none. Rahu-Ketu is
    skipped: the pair is always 180 degrees apart, so it is not an event.
    Rahu and Ketu each keep their own rows.
    """
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    if end_date < start_date:
        raise ValueError("end_date must be >= start_date")

    planets = [name for name, _ in PLANET_SWE] + ["Ketu"]
    pairs = [(a, b) for i, a in enumerate(planets) for b in planets[i + 1:] if {a, b} != {"Rahu", "Ketu"}]

    start_dt = datetime.combine(start_date, time(0, 0))
    end_dt = datetime.combine(end_date + timedelta(days=1), time(0, 0))
    hours = int((end_dt - start_dt).total_seconds() // 3600)
    grid = [start_dt + timedelta(hours=h) for h in range(hours + 1)]
    lons = [{name: data["lon"] for name, data in _positions_at(t).items()} for t in grid]

    rows: List[Dict[str, Any]] = []
    for i in range(hours):
        t0, t1 = grid[i], grid[i + 1]
        lon0, lon1 = lons[i], lons[i + 1]
        for name_a, name_b in pairs:
            raw0 = lon0[name_a] - lon0[name_b]
            raw1 = lon1[name_a] - lon1[name_b]
            for angle in ASPECT_ANGLES:
                orb = ANGLE_ORB_MAP.get(angle, DEFAULT_ORB)
                entry_code = "KSp" if angle == 0 else "KSc"
                for target in _targets(angle):
                    f0 = (raw0 - target + 180.0) % 360.0 - 180.0
                    f1 = (raw1 - target + 180.0) % 360.0 - 180.0
                    if abs(f0) > 90.0:  # far side of the circle, the wrap is not a crossing
                        continue
                    offset = lambda t: _pair_offset(t, name_a, name_b, target)
                    gap = lambda t: abs(offset(t)) - orb
                    if f0 == 0 or f0 * f1 < 0:
                        exact = _bisect_time(t0, t1, offset).replace(second=0, microsecond=0)
                        row = _build_row(exact, name_a, name_b, angle, angle)
                        row["orb_entry"] = _stamp(_orb_entry_before(exact, name_a, name_b, target, orb))
                        rows.append(row)
                    if abs(f0) > orb >= abs(f1):
                        entry = _bisect_time(t0, t1, gap)
                        row = _build_row(entry.replace(second=0, microsecond=0), name_a, name_b, entry_code, angle)
                        row["exact_at"] = _stamp(_exact_after(entry, name_a, name_b, target, orb))
                        rows.append(row)

    rows.sort(key=lambda r: (r["date"], r["time"], r["pl1"], r["pl2"]))
    return rows
