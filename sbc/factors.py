"""Phase 6 candidate factors (G8), pre-registered before any test was run.

Each factor states its direction (or "bigger moves" for events) up front, from
the traditional reading, and is admitted to the forecast only if it passes both
the sbc.stats harness and the incremental test against the market controls
(scripts/validate_factors.py). These factors form their own Benjamini-Hochberg
family, so adding them doesn't dilute or flatter the Phase 2 rule results.

  station            a planet (Mercury..Saturn) is stationary at the open  -> bigger moves
  graha_yuddha       two of Mars/Mercury/Jupiter/Venus/Saturn within 1 deg -> bigger moves
  moon_out_of_bounds Moon's declination beyond the Sun's maximum           -> bigger moves
  planet_out_of_bounds Mercury, Venus or Mars out of bounds                -> bigger moves
  ingress_window     Sun..Saturn changes sign within +/-1 day              -> bigger moves
  eclipse_day        an eclipse within 1 day                               -> bigger moves
  mercury_combust    Mercury combust (trade/communication weakened)        -> bearish
  jupiter_combust    Jupiter combust (wealth significator weakened)        -> bearish
  venus_retrograde   Venus retrograde (finance, luxury)                    -> bearish
  retrograde_cluster 3+ of Mercury..Saturn retrograde                      -> bearish
  moon_with_node     Moon within 12 deg of Rahu or Ketu                    -> bearish
  jupiter_dignity    Jupiter exalted/own +1, debilitated -1                -> as signed
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass

import swisseph as swe

from sbc import kp_ephemeris as kpe

OBLIQUITY = 23.44  # deg; the Sun's maximum declination
YUDDHA_ORB = 1.0
NODE_ORB = 12.0
WAR_PLANETS = ("Mars", "Mercury", "Jupiter", "Venus", "Saturn")
STATION_PLANETS = ("Mercury", "Venus", "Mars", "Jupiter", "Saturn")
INGRESS_PLANETS = ("Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
_DECL_BODIES = {"Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS, "Mars": swe.MARS}


@dataclass(frozen=True)
class Factor:
    name: str
    kind: str  # "directional" | "event"
    description: str
    fn: Callable[[dict, dict, dict, dict], int | bool]  # (fp, day before, day after, declinations)


def declinations(day: str) -> dict[str, float]:
    """Declination (deg) of the Moon, Mercury, Venus and Mars at 09:15 IST."""
    jd = kpe._julday_ist(dt.datetime.combine(dt.date.fromisoformat(day), dt.time(9, 15)))
    flags = swe.FLG_MOSEPH | swe.FLG_EQUATORIAL
    return {name: swe.calc_ut(jd, body, flags)[0][1] for name, body in _DECL_BODIES.items()}


def _sep(a: float, b: float) -> float:
    return abs(((a - b + 180.0) % 360.0) - 180.0)


def _graha_yuddha(fp: dict) -> bool:
    p = fp["planets"]
    return any(_sep(p[a]["longitude"], p[b]["longitude"]) < YUDDHA_ORB
               for i, a in enumerate(WAR_PLANETS) for b in WAR_PLANETS[i + 1:])


def _ingress(fp: dict, prev: dict, nxt: dict) -> bool:
    signs = lambda f: [f["planets"][n]["sign"] for n in INGRESS_PLANETS]  # noqa: E731
    return signs(prev) != signs(fp) or signs(fp) != signs(nxt)


def _eclipse_day(fp: dict) -> bool:
    e = fp["eclipse"]
    return any(v is not None and v <= 1.0 for v in (e["days_since"], e["days_to"]))


def _moon_with_node(fp: dict) -> int:
    p = fp["planets"]
    moon = p["Moon"]["longitude"]
    near = min(_sep(moon, p["Rahu"]["longitude"]), _sep(moon, p["Ketu"]["longitude"]))
    return -1 if near < NODE_ORB else 0


def _jupiter_dignity(fp: dict) -> int:
    return {"exalted": 1, "own": 1, "debilitated": -1}.get(fp["planets"]["Jupiter"]["dignity"], 0)


FACTORS: list[Factor] = [
    Factor("station", "event", "A planet (Mercury..Saturn) stationary at the open -> bigger moves",
           lambda fp, prev, nxt, dec: any(fp["planets"][n]["stationary"] for n in STATION_PLANETS)),
    Factor("graha_yuddha", "event", "Two of Mars/Mercury/Jupiter/Venus/Saturn within 1° -> bigger moves",
           lambda fp, prev, nxt, dec: _graha_yuddha(fp)),
    Factor("moon_out_of_bounds", "event", "Moon's declination beyond 23.44° -> bigger moves",
           lambda fp, prev, nxt, dec: abs(dec["Moon"]) > OBLIQUITY),
    Factor("planet_out_of_bounds", "event", "Mercury, Venus or Mars out of bounds -> bigger moves",
           lambda fp, prev, nxt, dec: any(abs(dec[n]) > OBLIQUITY for n in ("Mercury", "Venus", "Mars"))),
    Factor("ingress_window", "event", "Sun..Saturn changes sign within ±1 day -> bigger moves",
           lambda fp, prev, nxt, dec: _ingress(fp, prev, nxt)),
    Factor("eclipse_day", "event", "An eclipse within 1 day -> bigger moves",
           lambda fp, prev, nxt, dec: _eclipse_day(fp)),
    Factor("mercury_combust", "directional", "Mercury combust -> bearish",
           lambda fp, prev, nxt, dec: -1 if fp["planets"]["Mercury"]["combust"] else 0),
    Factor("jupiter_combust", "directional", "Jupiter combust -> bearish",
           lambda fp, prev, nxt, dec: -1 if fp["planets"]["Jupiter"]["combust"] else 0),
    Factor("venus_retrograde", "directional", "Venus retrograde -> bearish",
           lambda fp, prev, nxt, dec: -1 if fp["planets"]["Venus"]["retrograde"] else 0),
    Factor("retrograde_cluster", "directional", "3+ of Mercury..Saturn retrograde -> bearish",
           lambda fp, prev, nxt, dec: -1 if sum(fp["planets"][n]["retrograde"]
                                                for n in STATION_PLANETS) >= 3 else 0),
    Factor("moon_with_node", "directional", "Moon within 12° of Rahu or Ketu -> bearish",
           lambda fp, prev, nxt, dec: _moon_with_node(fp)),
    Factor("jupiter_dignity", "directional", "Jupiter exalted/own -> bullish, debilitated -> bearish",
           lambda fp, prev, nxt, dec: _jupiter_dignity(fp)),
]


def signals_for(fps: list[dict], lookup: Callable[[str], dict] | None = None) -> dict[str, list]:
    """{factor: [signal per fingerprint]}.

    Calendar neighbours (the day before and after, for the ingress window) come from
    `lookup(date)`, by default sbc.fingerprint_store.get, so a list of trading
    sessions still compares each session with the adjacent calendar days.
    """
    if lookup is None:
        from sbc import fingerprint_store
        lookup = fingerprint_store.get
    out: dict[str, list] = {f.name: [] for f in FACTORS}
    for fp in fps:
        day = dt.date.fromisoformat(fp["date"])
        before = lookup((day - dt.timedelta(days=1)).isoformat())
        after = lookup((day + dt.timedelta(days=1)).isoformat())
        dec = declinations(fp["date"])
        for f in FACTORS:
            out[f.name].append(f.fn(fp, before, after, dec))
    return out
