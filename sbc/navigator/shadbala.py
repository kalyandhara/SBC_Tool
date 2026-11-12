"""Shadbala (six-fold planetary strength) and Baladi Avastha, in virupas.

Follows the classical rules of Brihat Parashara Hora Shastra (ch. 27-30) as
set out in V.P. Jain, *A Text Book on Shadbala*, and B.V. Raman, *Graha and
Bhava Balas*. Positions are sidereal (Lahiri) from Swiss Ephemeris. Tests pin
the results against the worked examples in those two books.

shadbala(jd_ut, lat, lon) -> {planet: {"sthana": .., "dig": .., "kala": .., "chesta": ..,
                                       "naisargika": .., "drik": .., "total": .., "rupas": ..}}
"""

from __future__ import annotations

import math
from typing import Any

import swisseph as swe

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
_BODY = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
         "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN}

# Minimum Shadbala (virupas) each planet needs to count as strong (BPHS 27).
REQUIRED = {"Sun": 390, "Moon": 360, "Mars": 300, "Mercury": 420, "Jupiter": 390,
            "Venus": 330, "Saturn": 300}
NAISARGIKA = {"Sun": 60.0, "Moon": 51.43, "Mars": 17.14, "Mercury": 25.71,
              "Jupiter": 34.29, "Venus": 42.86, "Saturn": 8.57}
DEEP_EXALT = {"Sun": 10, "Moon": 33, "Mars": 298, "Mercury": 165, "Jupiter": 95,
              "Venus": 357, "Saturn": 200}
SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
OWN = {"Sun": {4}, "Moon": {3}, "Mars": {0, 7}, "Mercury": {2, 5}, "Jupiter": {8, 11},
       "Venus": {1, 6}, "Saturn": {9, 10}}
MOOLATRIKONA = {"Sun": (4, 0, 20), "Moon": (1, 3, 30), "Mars": (0, 0, 12), "Mercury": (5, 15, 20),
                "Jupiter": (8, 0, 10), "Venus": (6, 0, 15), "Saturn": (10, 0, 20)}
_FRIENDS = {"Sun": {"Moon", "Mars", "Jupiter"}, "Moon": {"Sun", "Mercury"},
            "Mars": {"Sun", "Moon", "Jupiter"}, "Mercury": {"Sun", "Venus"},
            "Jupiter": {"Sun", "Moon", "Mars"}, "Venus": {"Mercury", "Saturn"},
            "Saturn": {"Mercury", "Venus"}}
_ENEMIES = {"Sun": {"Venus", "Saturn"}, "Moon": set(), "Mars": {"Mercury"},
            "Mercury": {"Moon"}, "Jupiter": {"Mercury", "Venus"},
            "Venus": {"Sun", "Moon"}, "Saturn": {"Sun", "Moon", "Mars"}}
_VARGA_POINTS = {"adhimitra": 22.5, "mitra": 15.0, "sama": 7.5, "shatru": 3.75, "adhishatru": 1.875}
_MALE, _NEUTER, _FEMALE = {"Sun", "Mars", "Jupiter"}, {"Mercury", "Saturn"}, {"Moon", "Venus"}
_CHALDEAN = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
_WEEKDAY_LORD = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]   # swe.day_of_week: 0=Mon
# Baladi Avastha multipliers (hand-set, part of the nav-2 weights): infant, youth, adult, old, dead.
AVASTHA = [("Bala", 0.25), ("Kumara", 0.5), ("Yuva", 1.0), ("Vriddha", 0.125), ("Mrita", 0.0)]


def _norm(x: float) -> float:
    return x % 360.0


def _sep(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _sidereal(jd: float, ayanamsa: int = swe.SIDM_LAHIRI) -> dict[str, Any]:
    swe.set_sid_mode(ayanamsa)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    out: dict[str, Any] = {}
    for name, body in _BODY.items():
        xx, _ = swe.calc_ut(jd, body, flags)
        trop, _ = swe.calc_ut(jd, body, swe.FLG_SWIEPH | swe.FLG_SPEED)
        out[name] = {"lon": xx[0] % 360.0, "speed": xx[3], "trop_lon": trop[0], "trop_lat": trop[1]}
    return out


# ---- varga signs ---------------------------------------------------------------------
def varga_sign(lon: float, d: int) -> int:
    sign, deg = int(lon // 30) % 12, lon % 30
    odd = sign % 2 == 0           # Aries (index 0) is an odd sign
    if d == 1:
        return sign
    if d == 2:                    # Hora: Sun's hora is Leo, Moon's is Cancer
        first = deg < 15
        return 4 if (odd == first) else 3
    if d == 3:
        return (sign + 4 * int(deg // 10)) % 12
    if d == 7:
        start = sign if odd else (sign + 6) % 12
        return (start + int(deg // (30 / 7))) % 12
    if d == 9:
        return (sign * 9 + int(deg // (30 / 9))) % 12
    if d == 12:
        return (sign + int(deg // 2.5)) % 12
    if d == 30:
        if odd:
            for limit, s in ((5, 0), (10, 10), (18, 8), (25, 2), (30, 6)):
                if deg < limit:
                    return s
        for limit, s in ((5, 1), (12, 5), (20, 11), (25, 9), (30, 7)):
            if deg < limit:
                return s
    raise ValueError(f"unsupported varga D{d}")


def _relationship(planet: str, other: str, signs: dict[str, int]) -> str:
    natural = 1 if other in _FRIENDS[planet] else (-1 if other in _ENEMIES[planet] else 0)
    dist = (signs[other] - signs[planet]) % 12 + 1
    temporal = 1 if dist in (2, 3, 4, 10, 11, 12) else -1
    total = natural + temporal
    return {2: "adhimitra", 1: "mitra", 0: "sama", -1: "shatru", -2: "adhishatru"}[total]


def saptavargaja(planet: str, lon: float, signs: dict[str, int]) -> float:
    total = 0.0
    for d in (1, 2, 3, 7, 9, 12, 30):
        s = varga_sign(lon, d)
        # Moolatrikona counts for the whole sign in the rasi chart, as in V.P. Jain's worked example.
        if d == 1 and s == MOOLATRIKONA[planet][0]:
            total += 45.0
        elif s in OWN[planet]:
            total += 30.0
        else:
            total += _VARGA_POINTS[_relationship(planet, SIGN_LORD[s], signs)]
    return total


# ---- the six balas -----------------------------------------------------------------------
def uchcha(planet: str, lon: float) -> float:
    debil = (DEEP_EXALT[planet] + 180) % 360
    return _sep(lon, debil) / 3.0


def ojayugma(planet: str, lon: float) -> float:
    total = 0.0
    for d in (1, 9):
        odd = varga_sign(lon, d) % 2 == 0
        if (planet in ("Moon", "Venus")) != odd:
            total += 15.0
    return total


def kendradi(lon: float, asc: float) -> float:
    house = (int(lon // 30) - int(asc // 30)) % 12 + 1
    if house in (1, 4, 7, 10):
        return 60.0
    if house in (2, 5, 8, 11):
        return 30.0
    return 15.0


def drekkana(planet: str, lon: float) -> float:
    part = int((lon % 30) // 10)
    want = 0 if planet in _MALE else (1 if planet in _NEUTER else 2)
    return 15.0 if part == want else 0.0


def dig(planet: str, lon: float, asc: float, mc: float) -> float:
    weak = {"Jupiter": asc + 180, "Mercury": asc + 180, "Sun": mc + 180, "Mars": mc + 180,
            "Saturn": asc, "Moon": mc, "Venus": mc}[planet]
    return _sep(lon, weak % 360) / 3.0


def drishti(angle: float) -> float:
    """Aspect value in virupas cast across `angle` degrees (aspected minus aspecting)."""
    a = angle % 360
    if a < 30 or a >= 300:
        return 0.0
    if a < 60:
        return (a - 30) / 2
    if a < 90:
        return a - 60 + 15
    if a < 120:
        return (120 - a) / 2 + 30
    if a < 150:
        return 150 - a
    if a < 180:
        return (a - 150) * 2
    return (300 - a) / 2


def _special(planet: str, angle: float) -> float:
    a = angle % 360
    if planet == "Mars" and (90 <= a < 120 or 210 <= a < 240):
        return 15.0
    if planet == "Jupiter" and (120 <= a < 150 or 240 <= a < 270):
        return 30.0
    if planet == "Saturn" and (60 <= a < 90 or 270 <= a < 300):
        return 45.0
    return 0.0


def _benefic(planet: str, moon_waxing: bool, mercury_benefic: bool = True) -> bool:
    if planet == "Moon":
        return moon_waxing
    if planet == "Mercury":
        return mercury_benefic
    return planet in ("Jupiter", "Venus")


def mercury_is_benefic(pos: dict[str, Any], moon_waxing: bool) -> bool:
    """Mercury takes the nature of its sign-mates: malefic when malefics outnumber benefics there."""
    sign = int(pos["Mercury"]["lon"] // 30)
    mates = [p for p in PLANETS if p != "Mercury" and int(pos[p]["lon"] // 30) == sign]
    good = sum(_benefic(p, moon_waxing) for p in mates)
    return good >= len(mates) - good


def drik(target: str, pos: dict[str, Any], moon_waxing: bool, mercury_benefic: bool = True) -> float:
    total = 0.0
    for src in PLANETS:
        if src == target:
            continue
        angle = pos[target]["lon"] - pos[src]["lon"]
        value = drishti(angle) + _special(src, angle)
        total += value if _benefic(src, moon_waxing, mercury_benefic) else -value
    return total / 4.0


_MEAN = {"Sun": (280.46646, 0.98564736), "Mercury": (252.25084, 4.09233880),
         "Venus": (181.97973, 1.60213047), "Mars": (355.45332, 0.52403304),
         "Jupiter": (34.40438, 0.08308676), "Saturn": (50.07571, 0.03345969)}


def _mean_lon(name: str, jd: float, ayan: float) -> float:
    l0, n = _MEAN[name]
    return _norm(l0 + n * (jd - 2451545.0) - ayan)


def chesta(planet: str, true_lon: float, jd: float, ayan: float) -> float:
    if planet in ("Sun", "Moon"):
        return 0.0
    mean_sun = _mean_lon("Sun", jd, ayan)
    if planet in ("Mercury", "Venus"):
        seeghrochcha, mean_planet = _mean_lon(planet, jd, ayan), mean_sun
    else:
        seeghrochcha, mean_planet = mean_sun, _mean_lon(planet, jd, ayan)
    mid = (mean_planet + true_lon) / 2
    if abs(mean_planet - true_lon) > 180:
        mid = _norm(mid + 180)
    kendra = _norm(seeghrochcha - mid)
    if kendra > 180:
        kendra = 360 - kendra
    return kendra / 3.0


# ---- Kala bala ------------------------------------------------------------------------------
def _sun_events(jd: float, lat: float, lon: float) -> tuple[float, float, float]:
    """(previous sunrise, sunset after it, next sunrise) around jd, in UT."""
    geopos = (lon, lat, 0.0)
    flags = swe.BIT_DISC_CENTER
    rise = swe.rise_trans(jd - 1.0, swe.SUN, swe.CALC_RISE | flags, geopos)[1][0]
    while True:
        nxt = swe.rise_trans(rise + 0.01, swe.SUN, swe.CALC_RISE | flags, geopos)[1][0]
        if nxt > jd:
            break
        rise = nxt
    sset = swe.rise_trans(rise + 0.01, swe.SUN, swe.CALC_SET | flags, geopos)[1][0]
    return rise, sset, nxt


_RAMAN_BASE_JD = 2434376.5      # 1951-12-31 00:00 UT
# Weekday order for the year and month lords, fixed so both books' worked examples agree.
_ABDA_FROM_TUESDAY = ["Venus", "Saturn", "Sun", "Moon", "Mars", "Mercury", "Jupiter"]


def _raman_ahargana(jd_local: float) -> int:
    """Raman's ahargana (Graha and Bhava Balas, Table I): 174 on 1951-12-31, one per civil day."""
    return int(math.floor(jd_local + 0.5) - math.floor(_RAMAN_BASE_JD + 0.5)) + 174


def kala(pos: dict[str, Any], jd: float, lat: float, lon: float, tz_hours: float) -> dict[str, float]:
    rise, sset, nxt = _sun_events(jd, lat, lon)
    is_day = jd < sset
    # Nathonnatha: apparent solar time, distance from midnight in hours.
    lmt_hours = ((jd + 0.5) % 1.0) * 24 + lon / 15.0
    apparent = (lmt_hours + swe.time_equ(jd) * 24) % 24
    from_midnight = min(apparent, 24 - apparent)
    night = 60.0 * (12 - from_midnight) / 12
    out = dict.fromkeys(PLANETS, 0.0)
    for p in PLANETS:
        if p == "Mercury":
            out[p] += 60.0
        elif p in ("Moon", "Mars", "Saturn"):
            out[p] += night
        else:
            out[p] += 60.0 - night
    # Paksha
    elong = _norm(pos["Moon"]["lon"] - pos["Sun"]["lon"])
    angle = elong if elong <= 180 else 360 - elong
    merc = mercury_is_benefic(pos, _norm(pos["Moon"]["lon"] - pos["Sun"]["lon"]) < 180)
    for p in PLANETS:
        benefic = p in ("Jupiter", "Venus", "Moon") or (p == "Mercury" and merc)
        value = angle / 3.0 if benefic else 60.0 - angle / 3.0
        out[p] += 2 * value if p == "Moon" else value
    # Tribhaga
    out["Jupiter"] += 60.0
    if is_day:
        third = int((jd - rise) / ((sset - rise) / 3))
        out[["Mercury", "Sun", "Saturn"][min(third, 2)]] += 60.0
    else:
        third = int((jd - sset) / ((nxt - sset) / 3))
        out[["Moon", "Venus", "Mars"][min(third, 2)]] += 60.0
    # Abda, Masa, Vara and Hora lords (vara runs from sunrise).
    vara = _WEEKDAY_LORD[swe.day_of_week(rise + lon / 360.0 + 0.25)]
    ahar = _raman_ahargana(jd + tz_hours / 24.0)
    abda = _ABDA_FROM_TUESDAY[((ahar // 360) * 3 + 1) % 7]
    masa = _ABDA_FROM_TUESDAY[((ahar // 30) * 2 + 1) % 7]
    day_len = (sset - rise) if is_day else (nxt - sset)
    start = rise if is_day else sset
    hour = int((jd - start) / (day_len / 12)) + (0 if is_day else 12)
    hora = _CHALDEAN[(_CHALDEAN.index(vara) + hour) % 7]
    out[abda] += 15.0
    out[masa] += 30.0
    out[vara] += 45.0
    out[hora] += 60.0
    # Ayana: declination of each planet.
    eps = swe.calc_ut(jd, swe.ECL_NUT)[0][0]
    for p in PLANETS:
        ra_dec = swe.cotrans((pos[p]["trop_lon"], pos[p]["trop_lat"], 1.0), -eps)
        kranti = ra_dec[1]
        if p in ("Moon", "Saturn"):
            value = (24 - kranti) / 48 * 60
        elif p == "Mercury":
            value = (24 + abs(kranti)) / 48 * 60
        else:
            value = (24 + kranti) / 48 * 60
        out[p] += 2 * value if p == "Sun" else value
    return out


def avastha(lon: float) -> tuple[str, float]:
    sign, deg = int(lon // 30), lon % 30
    idx = min(int(deg // 6), 4)
    if sign % 2 == 1:             # even signs run in reverse
        idx = 4 - idx
    return AVASTHA[idx]


def shadbala(jd: float, lat: float, lon: float, tz_hours: float = 5.5,
             ayanamsa: int = swe.SIDM_LAHIRI) -> dict[str, dict[str, Any]]:
    """Shadbala of the seven planets at UT julian day `jd` for a place (lat, lon east +).

    tz_hours is the civil offset used to date the day for the year and month lords."""
    pos = _sidereal(jd, ayanamsa)
    swe.set_sid_mode(ayanamsa)
    ayan = swe.get_ayanamsa_ut(jd)
    cusps, ascmc = swe.houses_ex(jd, lat, lon, b"P", swe.FLG_SIDEREAL)
    asc, mc = ascmc[0] % 360, ascmc[1] % 360
    signs = {p: int(pos[p]["lon"] // 30) for p in PLANETS}
    moon_waxing = _norm(pos["Moon"]["lon"] - pos["Sun"]["lon"]) < 180
    k = kala(pos, jd, lat, lon, tz_hours)
    out = {}
    for p in PLANETS:
        lp = pos[p]["lon"]
        sthana = uchcha(p, lp) + saptavargaja(p, lp, signs) + ojayugma(p, lp) + kendradi(lp, asc) + drekkana(p, lp)
        parts = {"sthana": sthana, "dig": dig(p, lp, asc, mc), "kala": k[p],
                 "chesta": chesta(p, lp, jd, ayan), "naisargika": NAISARGIKA[p],
                 "drik": drik(p, pos, moon_waxing, mercury_is_benefic(pos, moon_waxing))}
        total = sum(parts.values())
        name, factor = avastha(lp)
        out[p] = {**{key: round(v, 2) for key, v in parts.items()}, "total": round(total, 2),
                  "rupas": round(total / 60, 2), "ratio": round(total / REQUIRED[p], 3),
                  "avastha": name, "avastha_factor": factor, "lon": round(lp, 3)}
    return out
