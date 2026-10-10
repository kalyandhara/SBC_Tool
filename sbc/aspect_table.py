"""Exact-time geocentric sidereal aspect table (B-43).

Uses Swiss Ephemeris with Lahiri sidereal mode, IST times, hourly scan with
bisection to minute precision.  Moon is included.  Aspects are 0/30/45/60/90/120/135/
150/180 plus orb-entry KSc/KSp events.

The public entry point is get_aspects(start_date, end_date) -> list[dict].
"""

from __future__ import annotations

import datetime as dt
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Tuple

import swisseph as swe

from .kp_ephemeris import _julday_ist
from .market_events import ASPECT_ORBS

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


def _bisect_root(t0: datetime, t1: datetime, sep0: float, sep1: float, target: float) -> datetime | None:
    """Bisection to minute precision for sep==target inside [t0, t1]."""
    if sep0 == target:
        return t0
    if sep1 == target:
        return t1
    # sign change check
    if (sep0 - target) * (sep1 - target) > 0:
        return None
    lo, hi = t0, t1
    for _ in range(30):
        mid = lo + (hi - lo) / 2
        pos_mid = _positions_at(mid)
        # we need the two planets – caller will supply? We'll assume generic?
        # This helper is not used directly; kept for structure.
    return None


def _find_exact_between(t0: datetime, t1: datetime, pa: Dict[str, Any], pb: Dict[str, Any], name_a: str, name_b: str, angle: int) -> datetime | None:
    pos0_a = _positions_at(t0)[name_a]
    pos0_b = _positions_at(t0)[name_b]
    pos1_a = _positions_at(t1)[name_a]
    pos1_b = _positions_at(t1)[name_b]
    sep0 = _angular_sep(pos0_a["lon"], pos0_b["lon"])
    sep1 = _angular_sep(pos1_a["lon"], pos1_b["lon"])
    diff0 = sep0 - angle
    diff1 = sep1 - angle
    if abs(diff0) < 1e-6:
        return t0
    if abs(diff1) < 1e-6:
        return t1
    if diff0 * diff1 > 0:
        return None
    lo, hi = t0, t1
    for _ in range(35):
        mid = lo + (hi - lo) / 2
        mid_pos = _positions_at(mid)
        sep_mid = _angular_sep(mid_pos[name_a]["lon"], mid_pos[name_b]["lon"])
        diff_mid = sep_mid - angle
        if abs(diff_mid) < 1e-6:
            return mid
        if diff0 * diff_mid <= 0:
            hi = mid
            diff1 = diff_mid
        else:
            lo = mid
            diff0 = diff_mid
    return lo


def _orb_entry_time(lo_time: datetime, exact_time: datetime, name_a: str, name_b: str, angle: int, orb: float) -> datetime | None:
    """Find time when |sep - angle| == orb before exact_time, by scanning backwards."""
    # start search window: up to 48h before exact
    start = exact_time - timedelta(hours=48)
    if start < lo_time:
        start = lo_time
    # coarse hourly check
    t = exact_time
    step = timedelta(hours=-1)
    prev_time = None
    prev_sep = None
    # walk backwards hourly
    cur = exact_time
    while cur >= start:
        pos = _positions_at(cur)
        sep = _angular_sep(pos[name_a]["lon"], pos[name_b]["lon"])
        if prev_sep is not None:
            # check if orb crossing between prev and cur
            if (abs(prev_sep - angle) - orb) * (abs(sep - angle) - orb) <= 0:
                # bisect between prev and cur
                lo, hi = cur, prev_time
                for _ in range(30):
                    mid = lo + (hi - lo) / 2
                    mid_pos = _positions_at(mid)
                    sep_mid = _angular_sep(mid_pos[name_a]["lon"], mid_pos[name_b]["lon"])
                    if abs(abs(sep_mid - angle) - orb) < 1e-6:
                        return mid
                    if (abs(sep_mid - angle) - orb) * (abs(sep - angle) - orb) <= 0:
                        hi = mid
                    else:
                        lo = mid
                return lo
        prev_time = cur
        prev_sep = sep
        cur += step
    return None


def _build_row(when: datetime, name_a: str, name_b: str, aspect_code: str, angle: int) -> Dict[str, Any]:
    pos = _positions_at(when)
    pa = pos[name_a]
    pb = pos[name_b]
    sun = pos["Sun"]
    rashi1 = pa["abbr"]
    rashi2 = pb["abbr"]
    rashis = f"{rashi1}-{rashi2}"
    relations = _relations(pa["sign_idx"], pb["sign_idx"], angle if isinstance(aspect_code, int) else 0)
    combust = _combust(pa, sun["lon"], name_a) or _combust(pb, sun["lon"], name_b)
    retro = pa["retro"] or pb["retro"]
    winner = _winner(pa, pb, name_a, name_b)
    weekday = when.strftime("%A")
    return {
        "date": when.date().isoformat(),
        "weekday": weekday,
        "time": when.strftime("%H:%M"),
        "pl1": name_a,
        "aspect": str(aspect_code),
        "pl2": name_b,
        "rashi1": pa["sign"],
        "rashi2": pb["sign"],
        "rashis": rashis,
        "relations": relations,
        "combust": bool(combust),
        "retro": bool(retro),
        "winner": winner,
        "muhurta": "",
    }


def get_aspects(start_date: date, end_date: date) -> List[Dict[str, Any]]:
    """Return exact sidereal aspects with Moon included for the date range.

    Scans hourly and refines to minute precision via bisection.
    Includes KSc/KSp orb-entry rows.
    """
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    if isinstance(end_date, str):
        end_date = date.fromisoformat(end_date)
    if end_date < start_date:
        raise ValueError("end_date must be >= start_date")

    planets = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
               "Uranus", "Neptune", "Pluto", "Rahu", "Ketu"]

    # build hourly timeline
    start_dt = datetime.combine(start_date, time(0, 0))
    end_dt = datetime.combine(end_date + timedelta(days=1), time(0, 0)) - timedelta(minutes=1)
    times = []
    cur = start_dt
    while cur <= end_dt:
        times.append(cur)
        cur += timedelta(hours=1)

    rows: List[Dict[str, Any]] = []
    seen = set()

    # pre-cache positions for speed
    pos_cache: Dict[datetime, Dict[str, Any]] = {}

    def get_pos(dt_: datetime) -> Dict[str, Any]:
        if dt_ not in pos_cache:
            pos_cache[dt_] = _positions_at(dt_)
        return pos_cache[dt_]

    # main scan
    for i in range(len(times) - 1):
        t0 = times[i]
        t1 = times[i + 1]
        pos0 = get_pos(t0)
        pos1 = get_pos(t1)
        for ia in range(len(planets)):
            for ib in range(ia + 1, len(planets)):
                name_a = planets[ia]
                name_b = planets[ib]
                if name_a not in pos0 or name_b not in pos0:
                    continue
                lon0_a = pos0[name_a]["lon"]
                lon0_b = pos0[name_b]["lon"]
                lon1_a = pos1[name_a]["lon"]
                lon1_b = pos1[name_b]["lon"]
                sep0 = _angular_sep(lon0_a, lon0_b)
                sep1 = _angular_sep(lon1_a, lon1_b)
                for angle in ASPECT_ANGLES:
                    diff0 = sep0 - angle
                    diff1 = sep1 - angle
                    # exact at start
                    if abs(diff0) < 0.05:
                        key = (t0.date(), t0.hour, name_a, name_b, angle)
                        if key not in seen:
                            rows.append(_build_row(t0, name_a, name_b, angle, angle))
                            seen.add(key)
                    # crossing
                    if diff0 * diff1 < 0:
                        root = _find_exact_between(t0, t1, pos0, pos1, name_a, name_b, angle)
                        if root:
                            # round to minute
                            root_min = root.replace(second=0, microsecond=0)
                            key = (root_min.date(), root_min.hour, root_min.minute, name_a, name_b, angle)
                            if key not in seen:
                                rows.append(_build_row(root_min, name_a, name_b, angle, angle))
                                seen.add(key)
                                # orb entry
                                orb = ANGLE_ORB_MAP.get(angle, DEFAULT_ORB)
                                entry = _orb_entry_time(t0, root_min, name_a, name_b, angle, orb)
                                if entry:
                                    entry_min = entry.replace(second=0, microsecond=0)
                                    entry_code = "KSp" if angle == 0 else "KSc"
                                    entry_key = (entry_min.date(), entry_min.hour, entry_min.minute, name_a, name_b, entry_code)
                                    if entry_key not in seen:
                                        # relations for entry use actual aspect angle for context
                                        e_row = _build_row(entry_min, name_a, name_b, entry_code, angle)
                                        # keep aspect code as KSc/KSp
                                        e_row["aspect"] = entry_code
                                        rows.append(e_row)
                                        seen.add(entry_key)

    rows.sort(key=lambda r: (r["date"], r["time"], r["pl1"], r["pl2"]))
    return rows
