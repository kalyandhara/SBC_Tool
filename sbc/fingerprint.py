"""Astro fingerprint: every astrological factor for one market day, in one place.

`fingerprint(day)` snapshots the sky at the NSE open (09:15 IST) and returns a
JSON-safe dict built from the existing calculators:

  planets   Sun..Ketu (Lahiri, sbc.planets) plus Uranus, Neptune, Pluto:
            longitude, ecliptic latitude (Sara; 0 for the mean nodes), sign,
            nakshatra (27-star), pada, speed, retrograde, stationary,
            combust, dignity
  aspects   angular aspects (sbc.market_events angles/orbs) with orb and
            applying/separating
  drishti   Vedic sign aspects (7th + special) and same-sign conjunctions
  panchang  tithi, paksha, tithi group, yoga, karana, Vishti (Bhadra),
            weekday, weekday lord, hora lord at the open
  kp        ascendant and Moon star/sub lords at the open (NSE Mumbai,
            sbc.kp_ephemeris), Moon sub-lord house-set strength
  sbc       NIFTY-anchor vedha net per school (classical, allthree)
  bradley   Bradley barometer value (sbc.bradley)
  eclipse   days since the last / to the next solar or lunar eclipse

Every planet, aspect and field carries a tier, which the analog search uses
to compare dates layer by layer:

  slow    Jupiter, Saturn, Rahu, Ketu, Uranus, Neptune, Pluto
  medium  Sun, Mercury, Venus, Mars (and eclipses)
  fast    Moon, panchang, KP lords, SBC nets

An aspect belongs to the tier of its faster planet, since that planet is
what makes and breaks it. `feature_vector(fp)` flattens a fingerprint into
named, tiered numbers.
"""

from __future__ import annotations

import bisect
import datetime as dt
import math
from functools import lru_cache

import swisseph as swe

from sbc import kp_ephemeris as kpe
from sbc.bradley import bradley_score
from sbc.engine import _anchor_nakshatra
from sbc.market_events import ASPECT_ANGLES, ASPECT_ORBS
from sbc.nakshatra import GROUP_OF_TITHI, NAKSHATRAS_27, RASHIS, paksha_of
from sbc.planets import COMBUST_ORB, DEBIL, EXALT, positioned_planets
from sbc.prediction import analyze, compute_vedhas

OPEN_TIME = "09:15"
ANCHOR = "nifty"
# sbc.chakra.vedha_cells implements two schools; "kp" would silently fall back to classical.
SCHOOLS = ("classical", "allthree")

GRAHAS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
OUTERS = (("Uranus", swe.URANUS), ("Neptune", swe.NEPTUNE), ("Pluto", swe.PLUTO))
BODIES = GRAHAS + tuple(name for name, _ in OUTERS)

TIER = {
    "Moon": "fast",
    "Sun": "medium", "Mercury": "medium", "Venus": "medium", "Mars": "medium",
    "Jupiter": "slow", "Saturn": "slow", "Rahu": "slow", "Ketu": "slow",
    "Uranus": "slow", "Neptune": "slow", "Pluto": "slow",
}
TIERS = ("slow", "medium", "fast")
_TIER_RANK = {"slow": 0, "medium": 1, "fast": 2}

# Mean daily motion (deg/day); a planet under 10% of it is treated as stationary.
MEAN_SPEED = {
    "Sun": 0.9856, "Moon": 13.176, "Mercury": 1.383, "Venus": 1.2, "Mars": 0.524,
    "Jupiter": 0.083, "Saturn": 0.0335, "Rahu": 0.053, "Ketu": 0.053,
    "Uranus": 0.0117, "Neptune": 0.006, "Pluto": 0.004,
}
STATIONARY_FRACTION = 0.10

STAR_SPAN = 360.0 / 27.0
YOGA_SPAN = 360.0 / 27.0
LORDS = ("Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury")
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

ECLIPSE_RANGE = (1980, 2045)


def _sep(a: float, b: float) -> float:
    return abs(((a - b + 180.0) % 360.0) - 180.0)


def _dignity(name: str, sign_idx: int) -> str:
    if EXALT.get(name) == sign_idx:
        return "exalted"
    if DEBIL.get(name) == sign_idx:
        return "debilitated"
    if kpe.SIGN_LORD[sign_idx] == name:
        return "own"
    return "neutral"


def _outer_positions(day: dt.date) -> dict[str, tuple[float, float]]:
    """Lahiri sidereal (longitude, speed) of the outer planets at the open."""
    when = dt.datetime.combine(day, dt.time(9, 15))
    jd = kpe._julday_ist(when)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    out = {}
    for name, body in OUTERS:
        xx, _ = swe.calc_ut(jd, body, flags)
        out[name] = (xx[0] % 360.0, xx[3])
    return out


# Swiss Ephemeris ids for the latitude lookup; the mean nodes lie on the ecliptic.
_SWE_IDS = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
            "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN,
            **dict(OUTERS)}


def latitudes(day: dt.date) -> dict[str, float]:
    """Geocentric ecliptic latitude (deg) of every body at the open (B-44)."""
    jd = kpe._julday_ist(dt.datetime.combine(day, dt.time(9, 15)))
    out = {name: swe.calc_ut(jd, body, swe.FLG_MOSEPH)[0][1] for name, body in _SWE_IDS.items()}
    return {name: out.get(name, 0.0) for name in BODIES}


def _planet_record(name: str, lon: float, speed: float, sun_lon: float,
                   latitude: float = 0.0) -> dict:
    sign_idx = int(lon // 30) % 12
    star_idx = min(int(lon // STAR_SPAN), 26)
    orb = COMBUST_ORB.get(name)
    return {
        "tier": TIER[name],
        "longitude": round(lon, 4),
        "latitude": round(latitude, 4),
        "sign": sign_idx,
        "sign_name": RASHIS[sign_idx],
        "nakshatra": star_idx,
        "nakshatra_name": NAKSHATRAS_27[star_idx],
        "pada": int((lon % STAR_SPAN) // (STAR_SPAN / 4)) + 1,
        "speed": round(speed, 4),
        "retrograde": speed < 0 and name not in ("Rahu", "Ketu"),
        "stationary": abs(speed) < STATIONARY_FRACTION * MEAN_SPEED[name],
        "combust": orb is not None and _sep(lon, sun_lon) < orb,
        "dignity": _dignity(name, sign_idx),
    }


def _aspects(planets: dict[str, dict]) -> list[dict]:
    """Angular aspects between every pair (Rahu-Ketu excluded: always opposite)."""
    out = []
    names = list(planets)
    step = 0.05  # days, to tell applying from separating
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if {a, b} == {"Rahu", "Ketu"}:
                continue
            pa, pb = planets[a], planets[b]
            sep = _sep(pa["longitude"], pb["longitude"])
            sep_next = _sep(pa["longitude"] + pa["speed"] * step,
                            pb["longitude"] + pb["speed"] * step)
            for aspect, angle in ASPECT_ANGLES.items():
                orb = abs(sep - angle)
                if orb <= ASPECT_ORBS[aspect]:
                    tier = max(pa["tier"], pb["tier"], key=_TIER_RANK.__getitem__)
                    out.append({
                        "a": a, "b": b, "aspect": aspect, "orb": round(orb, 3),
                        "applying": abs(sep_next - angle) < orb, "tier": tier,
                    })
    return out


def _drishti(planets: dict[str, dict]) -> list[dict]:
    """Vedic sign aspects among the nine grahas (kp_ephemeris offsets) and same-sign pairs."""
    out = []
    for a in GRAHAS:
        sa = planets[a]["sign"]
        offsets = (6,) + kpe.SPECIAL_ASPECTS.get(a, ())
        for b in GRAHAS:
            if a == b:
                continue
            gap = (planets[b]["sign"] - sa) % 12
            tier = max(planets[a]["tier"], planets[b]["tier"], key=_TIER_RANK.__getitem__)
            if gap in offsets:
                out.append({"from": a, "to": b, "kind": "aspect", "house": gap + 1, "tier": tier})
            elif gap == 0 and a < b and {a, b} != {"Rahu", "Ketu"}:
                out.append({"from": a, "to": b, "kind": "conjunct", "house": 1, "tier": tier})
    return out


def _panchang(day: dt.date, sun_lon: float, moon_lon: float, tithi: int) -> dict:
    elong = (moon_lon - sun_lon) % 360.0
    karana = int(elong // 6.0) + 1
    vishti = 2 <= karana <= 57 and (karana - 2) % 7 == 6  # matches sbc.bhadra._is_vishti
    yoga = int(((sun_lon + moon_lon) % 360.0) // YOGA_SPAN) + 1
    open_at = dt.datetime.combine(day, dt.time(9, 15))
    return {
        "tithi": tithi,
        "paksha": paksha_of(tithi),
        "tithi_group": GROUP_OF_TITHI.get(tithi, "Purna"),
        "yoga": yoga,
        "karana": karana,
        "vishti": vishti,
        "weekday": day.weekday(),
        "weekday_name": WEEKDAYS[day.weekday()],
        "weekday_lord": kpe.WEEKDAY_LORD[day.weekday()],
        "hora_lord": kpe._hora_at(kpe.hora_schedule(day), open_at),
    }


def _kp(day: dt.date) -> dict:
    chart = kpe.chart_at(dt.datetime.combine(day, dt.time(9, 15)))
    asc = kpe.kp_point(chart["asc"])
    moon = kpe.kp_point(chart["lons"]["Moon"])
    houses = kpe.house_set_for(moon["sublord"], chart)
    return {
        "asc_sign": asc["sign_idx"],
        "asc_star_lord": asc["star_lord"],
        "asc_sublord": asc["sublord"],
        "moon_star_lord": moon["star_lord"],
        "moon_sublord": moon["sublord"],
        "moon_sub_houses": houses,
        "moon_sub_strength": kpe.house_set_strength(houses),
    }


def _sbc(planets_with_natures: list[dict]) -> dict:
    birth_star = _anchor_nakshatra(ANCHOR)
    out = {}
    for school in SCHOOLS:
        vedha_map, _ = compute_vedhas(planets_with_natures, school=school)
        analysis = analyze(planets_with_natures, vedha_map, birth_star, school)
        out[school] = {
            "net": analysis["net"],
            "benefic": round(analysis["score"]["benefic"], 3),
            "malefic": round(analysis["score"]["malefic"], 3),
        }
    return out


@lru_cache(maxsize=1)
def _eclipse_table() -> tuple[tuple[float, str], ...]:
    """(Julian day of maximum, 'solar'|'lunar') for every eclipse in ECLIPSE_RANGE."""
    start = swe.julday(ECLIPSE_RANGE[0], 1, 1, 0.0)
    end = swe.julday(ECLIPSE_RANGE[1], 12, 31, 0.0)
    found = []
    for kind, search in (("solar", swe.sol_eclipse_when_glob), ("lunar", swe.lun_eclipse_when)):
        jd = start
        while jd < end:
            _, tret = search(jd, swe.FLG_MOSEPH)
            if tret[0] >= end:
                break
            found.append((tret[0], kind))
            jd = tret[0] + 20.0
    return tuple(sorted(found))


def _eclipse(day: dt.date) -> dict:
    if not ECLIPSE_RANGE[0] <= day.year <= ECLIPSE_RANGE[1]:
        return {"days_since": None, "since_type": None, "days_to": None, "to_type": None}
    jd = kpe._julday_ist(dt.datetime.combine(day, dt.time(9, 15)))
    table = _eclipse_table()
    i = bisect.bisect_right(table, (jd, "~"))
    last = table[i - 1] if i else None
    nxt = table[i] if i < len(table) else None
    return {
        "days_since": round(jd - last[0], 2) if last else None,
        "since_type": last[1] if last else None,
        "days_to": round(nxt[0] - jd, 2) if nxt else None,
        "to_type": nxt[1] if nxt else None,
    }


def fingerprint(day: dt.date | str) -> dict:
    """All astrological factors at 09:15 IST on `day` (a date or 'YYYY-MM-DD')."""
    if isinstance(day, str):
        day = dt.date.fromisoformat(day)
    natured, _ayanamsa, sun, moon, tithi = positioned_planets(day.isoformat(), OPEN_TIME)
    sun_lon = sun["longitude"]

    lat = latitudes(day)
    planets = {p["name"]: _planet_record(p["name"], p["longitude"], p["speed"], sun_lon, lat[p["name"]])
               for p in natured}
    for name, (lon, speed) in _outer_positions(day).items():
        planets[name] = _planet_record(name, lon, speed, sun_lon, lat[name])
    planets = {name: planets[name] for name in BODIES}

    return {
        "date": day.isoformat(),
        "time": OPEN_TIME,
        "tz": "Asia/Kolkata",
        "planets": planets,
        "aspects": _aspects(planets),
        "drishti": _drishti(planets),
        "panchang": _panchang(day, sun_lon, moon["longitude"], tithi),
        "kp": _kp(day),
        "sbc": _sbc(natured),
        "bradley": bradley_score([{"name": n, "longitude": p["longitude"]}
                                  for n, p in planets.items()]),
        "eclipse": _eclipse(day),
    }


# ── flat numeric form ──────────────────────────────────────────────────────

_DIGNITY_VALUE = {"exalted": 1.0, "own": 0.5, "neutral": 0.0, "debilitated": -1.0}
_PAIRS = [(a, b) for i, a in enumerate(BODIES) for b in BODIES[i + 1:] if {a, b} != {"Rahu", "Ketu"}]


def _pair_tier(a: str, b: str) -> str:
    return max(TIER[a], TIER[b], key=_TIER_RANK.__getitem__)


def feature_vector(fp: dict) -> list[tuple[str, str, float]]:
    """(name, tier, value) for every feature, in a fixed order for all dates.

    Longitudes and cycles are encoded as sin/cos so 359° sits next to 0°;
    aspects as closeness 1 - orb/max_orb (0 when out of orb); categorical
    lords as one-hot.
    """
    out: list[tuple[str, str, float]] = []
    for name in BODIES:
        p = fp["planets"][name]
        tier = p["tier"]
        rad = math.radians(p["longitude"])
        out += [
            (f"{name}.lon_sin", tier, math.sin(rad)),
            (f"{name}.lon_cos", tier, math.cos(rad)),
            (f"{name}.retrograde", tier, float(p["retrograde"])),
            (f"{name}.stationary", tier, float(p["stationary"])),
            (f"{name}.combust", tier, float(p["combust"])),
            (f"{name}.dignity", tier, _DIGNITY_VALUE[p["dignity"]]),
        ]

    closeness = {(x["a"], x["b"], x["aspect"]): 1.0 - x["orb"] / ASPECT_ORBS[x["aspect"]]
                 for x in fp["aspects"]}
    for a, b in _PAIRS:
        tier = _pair_tier(a, b)
        for aspect in ASPECT_ANGLES:
            out.append((f"{a}-{b}.{aspect}", tier, round(closeness.get((a, b, aspect), 0.0), 4)))

    pan = fp["panchang"]
    for label, value, period in (("tithi", pan["tithi"] - 1, 30), ("yoga", pan["yoga"] - 1, 27),
                                 ("karana", pan["karana"] - 1, 60)):
        ang = 2 * math.pi * value / period
        out += [(f"panchang.{label}_sin", "fast", math.sin(ang)),
                (f"panchang.{label}_cos", "fast", math.cos(ang))]
    out.append(("panchang.vishti", "fast", float(pan["vishti"])))
    for i, wd in enumerate(WEEKDAYS[:5]):
        out.append((f"panchang.weekday_{wd}", "fast", float(pan["weekday"] == i)))
    for lord in LORDS:
        out.append((f"panchang.hora_lord_{lord}", "fast", float(pan["hora_lord"] == lord)))

    kp = fp["kp"]
    for field in ("asc_star_lord", "asc_sublord", "moon_star_lord", "moon_sublord"):
        for lord in LORDS:
            out.append((f"kp.{field}_{lord}", "fast", float(kp[field] == lord)))
    out.append(("kp.moon_sub_strength", "fast", kp["moon_sub_strength"] / 5.0))

    for school in SCHOOLS:
        out.append((f"sbc.{school}_net", "fast", fp["sbc"][school]["net"] / 10.0))
    out.append(("bradley", "slow", fp["bradley"] / 10.0))

    ecl = fp["eclipse"]
    near = min(v for v in (ecl["days_since"], ecl["days_to"], 1e9) if v is not None)
    out.append(("eclipse.proximity", "medium", math.exp(-near / 15.0)))
    return out
