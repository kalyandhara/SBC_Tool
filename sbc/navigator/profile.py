"""Natal inputs. Rejects bad input; never defaults. `_utc_from_local` silently
falls back to Kolkata, so tz is validated here first."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import asdict, dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import swisseph as swe

from sbc.engine import _julday, _utc_from_local
from sbc.planets import positions

_OUTER = ("Uranus", "Neptune", "Pluto")


@dataclass(frozen=True)
class Profile:
    label: str
    is_sample: bool
    birth_date: str
    birth_time: str
    tz: str
    lat: float
    lon: float


def validate(d: dict) -> Profile:
    """Return a Profile or raise a ValueError that never echoes birth data."""
    try:
        date = dt.date.fromisoformat(str(d["birth_date"])).isoformat()
        time = dt.time.fromisoformat(str(d["birth_time"])).strftime("%H:%M:%S")
        tz = str(d["tz"])
        if not tz:
            raise ValueError
        ZoneInfo(tz)
        lat, lon = float(d["lat"]), float(d["lon"])
    except (KeyError, ValueError, TypeError, OSError, ZoneInfoNotFoundError):
        raise ValueError("invalid birth data") from None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("invalid birth data")
    return Profile(str(d.get("label") or "Unnamed"), bool(d.get("is_sample")),
                   date, time, tz, lat, lon)


def lagna_at(date, time, tz, lat, lon) -> float:
    jd = _julday(_utc_from_local(date, time, tz))
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return float(swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)[1][0] % 360.0)


def natal_points(p: Profile) -> dict[str, float]:
    jd = _julday(_utc_from_local(p.birth_date, p.birth_time, p.tz))
    planets, _ = positions(jd)
    out = {x["name"]: x["longitude"] for x in planets if x["name"] not in _OUTER}
    out["Lagna"] = lagna_at(p.birth_date, p.birth_time, p.tz, p.lat, p.lon)
    return out


def chart_hash(p: Profile) -> str:
    d = asdict(p)
    d.pop("label")
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:16]


SAMPLE_PROFILE = Profile("SAMPLE (fictional chart)", True, "1980-01-15", "12:00:00",
                         "Asia/Kolkata", 19.076, 72.878)
