"""Natal inputs. Rejects bad input; never defaults. `_utc_from_local` silently
falls back to Kolkata, so tz is validated here first."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import swisseph as swe

from sbc.engine import _julday, _utc_from_local
from sbc.planets import positions

_OUTER = ("Uranus", "Neptune", "Pluto")


@dataclass(frozen=True)
class Profile:
    label: str
    is_sample: bool
    # Birth data is sensitive: kept out of repr so logs and tracebacks stay clean.
    birth_date: str = field(repr=False)
    birth_time: str = field(repr=False)
    tz: str = field(repr=False)
    lat: float = field(repr=False)
    lon: float = field(repr=False)


_TIME_RE = re.compile(r"[0-9]{2}:[0-9]{2}(:[0-9]{2})?")
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_MIN_DATE, _MAX_DATE = dt.date(1800, 1, 1), dt.date(2100, 12, 31)


def _num(v) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError
    return float(v)


def _parse(d: dict):
    """Raises ValueError (or KeyError) on any problem; caller discards details."""
    bd, bt, tz = d["birth_date"], d["birth_time"], d["tz"]
    if not all(isinstance(x, str) for x in (bd, bt, tz)) or not tz:
        raise ValueError
    if not _DATE_RE.fullmatch(bd) or not _TIME_RE.fullmatch(bt):
        raise ValueError
    date = dt.date.fromisoformat(bd)
    if not (_MIN_DATE <= date <= _MAX_DATE):
        raise ValueError
    time = dt.time.fromisoformat(bt)
    zone = ZoneInfo(tz)
    naive = dt.datetime.combine(date, time)
    first = naive.replace(tzinfo=zone, fold=0)
    if first.utcoffset() != naive.replace(tzinfo=zone, fold=1).utcoffset():
        raise ValueError  # ambiguous (fold)
    back = first.astimezone(dt.timezone.utc).astimezone(zone).replace(tzinfo=None)
    if back != naive:
        raise ValueError  # nonexistent (DST gap)
    lat, lon = _num(d["lat"]), _num(d["lon"])
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError
    sample = d.get("is_sample", False)
    if not isinstance(sample, bool):
        raise ValueError
    label = d.get("label", "Unnamed")
    if (not isinstance(label, str) or len(label) > 80 or "<" in label or ">" in label
            or any(unicodedata.category(c).startswith("C") for c in label)):
        raise ValueError
    return label, date.isoformat(), time.strftime("%H:%M:%S"), tz, lat, lon, sample


def validate(d: dict) -> Profile:
    """Return a Profile or raise ValueError("invalid birth data").

    The raise happens outside the except block so no exception context
    (which would hold the raw input) is attached.
    """
    bad = False
    try:
        label, date, time, tz, lat, lon, sample = _parse(d)
    except (KeyError, ValueError, TypeError, OSError, OverflowError,
            ZoneInfoNotFoundError):
        bad = True
    if bad:
        raise ValueError("invalid birth data")
    return Profile(label, sample, date, time, tz, lat, lon)


def _require_zone(tz) -> None:
    """_utc_from_local silently falls back to Kolkata; refuse unknown tz first."""
    ok = False
    if isinstance(tz, str) and tz:
        try:
            ZoneInfo(tz)
            ok = True
        except (ValueError, OSError, ZoneInfoNotFoundError):
            pass
    if not ok:
        raise ValueError("invalid birth data")


def lagna_at(date, time, tz, lat, lon) -> float:
    _require_zone(tz)
    jd = _julday(_utc_from_local(date, time, tz))
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return float(swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)[1][0] % 360.0)


def natal_points(p: Profile) -> dict[str, float]:
    _require_zone(p.tz)
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
