"""Classical chart view for one Navigator profile: houses, dignity, combustion,
retrograde and the Vimshottari tree. Pure: no store, no Flask. Whole-sign houses
from the Lagna; sign indices 0-11 from Aries (sbc.nakshatra.RASHIS)."""
from __future__ import annotations

from typing import Any

from sbc.engine import _julday, _utc_from_local
from sbc.nakshatra import RASHIS, nakshatra_of
from sbc.navigator.profile import Profile, _require_zone, lagna_at
from sbc.planets import positions
from sbc.yogas import vimshottari

GRAHAS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
SANSKRIT = {"Sun": "Surya", "Moon": "Chandra", "Mars": "Mangal", "Mercury": "Budh",
            "Jupiter": "Guru", "Venus": "Shukra", "Saturn": "Shani", "Rahu": "Rahu", "Ketu": "Ketu"}
CODES = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me", "Jupiter": "Ju",
         "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke"}
RASHI_SA = ("Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
            "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena")
EXALTED = {"Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5, "Jupiter": 3, "Venus": 11, "Saturn": 6}
OWN = {"Sun": (4,), "Moon": (3,), "Mars": (0, 7), "Mercury": (2, 5), "Jupiter": (8, 11),
       "Venus": (1, 6), "Saturn": (9, 10)}
# (direct, retrograde) orbs in degrees; the Sun and the nodes are never combust.
COMBUST_ORB = {"Moon": (12.0, 12.0), "Mars": (17.0, 17.0), "Mercury": (14.0, 12.0),
               "Jupiter": (11.0, 11.0), "Venus": (10.0, 8.0), "Saturn": (15.0, 15.0)}
NODES = ("Rahu", "Ketu")


def dignity(planet: str, sign: int) -> str | None:
    """Exalted wins over own sign (Mercury in Kanya). Moolatrikona is out of scope."""
    if planet not in EXALTED:
        return None
    if sign == EXALTED[planet]:
        return "exalted"
    if sign == (EXALTED[planet] + 6) % 12:
        return "debilitated"
    return "own" if sign in OWN[planet] else None


def separation(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def is_combust(planet: str, lon: float, sun_lon: float, retro: bool) -> bool:
    orbs = COMBUST_ORB.get(planet)
    return orbs is not None and separation(lon, sun_lon) <= orbs[1 if retro else 0]


def bhava(sign: int, lagna_sign: int) -> int:
    return (sign - lagna_sign) % 12 + 1


def natal_detail(p: Profile) -> dict[str, dict[str, Any]]:
    _require_zone(p.tz)
    jd = _julday(_utc_from_local(p.birth_date, p.birth_time, p.tz))
    planets, _ = positions(jd)
    return {x["name"]: {"longitude": float(x["longitude"]) % 360.0, "retrograde": bool(x["retrograde"])}
            for x in planets if x["name"] in GRAHAS}


def _sign_block(lon: float) -> dict[str, Any]:
    sign = int(lon // 30)
    return {"longitude": round(lon, 4), "sign": RASHIS[sign], "sign_sa": RASHI_SA[sign],
            "sign_number": sign + 1, "degree": min(round(lon % 30, 4), 29.9999)}


def chart_view(p: Profile) -> dict[str, Any]:
    detail = natal_detail(p)
    lagna = lagna_at(p.birth_date, p.birth_time, p.tz, p.lat, p.lon) % 360.0
    lagna_sign = int(lagna // 30)
    sun = detail["Sun"]["longitude"]
    points = []
    for name in GRAHAS:
        lon = detail[name]["longitude"]
        sign = int(lon // 30)
        retro = True if name in NODES else detail[name]["retrograde"]
        nakshatra, pada = nakshatra_of(lon)
        points.append({"name": name, "sanskrit": SANSKRIT[name], "code": CODES[name],
                       **_sign_block(lon), "nakshatra": nakshatra, "pada": pada,
                       "bhava": bhava(sign, lagna_sign), "dignity": dignity(name, sign),
                       "combust": is_combust(name, lon, sun, retro), "retro": retro})
    houses = [{"house": h, "sign_number": (lagna_sign + h - 1) % 12 + 1,
               "points": [x["code"] for x in points if x["bhava"] == h]} for h in range(1, 13)]
    return {"lagna": _sign_block(lagna), "houses": houses, "points": points}


_CHILDREN = {"mahadashas": "antardashas", "antardashas": "pratyantars", "pratyantars": None}


def _nodes(items: list[dict], key: str, birth: str, today: str) -> list[dict]:
    out = []
    for item in items:
        start, end = max(item["start"][:10], birth), item["end"][:10]
        if end <= birth:
            continue
        child_key = _CHILDREN[key]
        out.append({"lord": item["lord"], "start": start, "end": end,
                    "now": start <= today < end,
                    "children": _nodes(item[child_key], child_key, birth, today) if child_key else []})
    return out


def dasha_tree(p: Profile, today: str) -> dict[str, Any]:
    moon = natal_detail(p)["Moon"]["longitude"]
    timeline = vimshottari(moon, p.birth_date, today)
    periods = _nodes(timeline["mahadashas"], "mahadashas", p.birth_date, today)
    running: dict[str, str | None] = {"maha": None, "antar": None, "pratyantar": None}
    level = periods
    for key in ("maha", "antar", "pratyantar"):
        hit = next((x for x in level if x["now"]), None)
        if hit is None:
            break
        running[key] = hit["lord"]
        level = hit["children"]
    return {"running": running, "periods": periods}
