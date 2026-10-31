"""Ashtakavarga: Bhinnashtakavarga (BAV) and Sarvashtakavarga (SAV).

Classical BPHS benefic places, cross-checked against VedAstro's Ashtakavarga.cs
(docs/VEDASTRO_INGEST_2026-10-31.md). Sidereal Lahiri, whole signs, sign 0 =
Aries: the conventions of sbc.natal. Descriptive only: no scores or thresholds.

Two variants (spec .internal/specs/2026-10-31-ashtakavarga-design.md):

    classical   8 contributors (7 planets + Lagna), cells 0-8, SAV total 337
    seven       the 7 planets only, cells 0-7, SAV total 292; for anchors whose
                Lagna is unreliable (approximate time or no real birth place)
"""

from __future__ import annotations

import datetime as dt
from functools import cache

from sbc import cities, natal
from sbc.engine import ANCHORS, _julday, _utc_from_local
from sbc.helio_aspects import IST, _jd
from sbc.nakshatra import RASHIS
from sbc.planets import positions

PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
CONTRIBUTORS = PLANETS + ("Lagna",)

# BENEFIC_PLACES[planet][contributor]: houses counted from the contributor's sign
# (its own sign = 1) where the contributor gives the planet a bindu.
BENEFIC_PLACES: dict[str, dict[str, tuple[int, ...]]] = {
    "Sun": {
        "Sun": (1, 2, 4, 7, 8, 9, 10, 11), "Moon": (3, 6, 10, 11),
        "Mars": (1, 2, 4, 7, 8, 9, 10, 11), "Mercury": (3, 5, 6, 9, 10, 11, 12),
        "Jupiter": (5, 6, 9, 11), "Venus": (6, 7, 12),
        "Saturn": (1, 2, 4, 7, 8, 9, 10, 11), "Lagna": (3, 4, 6, 10, 11, 12),
    },
    "Moon": {
        "Sun": (3, 6, 7, 8, 10, 11), "Moon": (1, 3, 6, 7, 10, 11),
        "Mars": (2, 3, 5, 6, 9, 10, 11), "Mercury": (1, 3, 4, 5, 7, 8, 10, 11),
        "Jupiter": (1, 4, 7, 8, 10, 11, 12), "Venus": (3, 4, 5, 7, 9, 10, 11),
        "Saturn": (3, 5, 6, 11), "Lagna": (3, 6, 10, 11),
    },
    "Mars": {
        "Sun": (3, 5, 6, 10, 11), "Moon": (3, 6, 11),
        "Mars": (1, 2, 4, 7, 8, 10, 11), "Mercury": (3, 5, 6, 11),
        "Jupiter": (6, 10, 11, 12), "Venus": (6, 8, 11, 12),
        "Saturn": (1, 4, 7, 8, 9, 10, 11), "Lagna": (1, 3, 6, 10, 11),
    },
    "Mercury": {
        "Sun": (5, 6, 9, 11, 12), "Moon": (2, 4, 6, 8, 10, 11),
        "Mars": (1, 2, 4, 7, 8, 9, 10, 11), "Mercury": (1, 3, 5, 6, 9, 10, 11, 12),
        "Jupiter": (6, 8, 11, 12), "Venus": (1, 2, 3, 4, 5, 8, 9, 11),
        "Saturn": (1, 2, 4, 7, 8, 9, 10, 11), "Lagna": (1, 2, 4, 6, 8, 10, 11),
    },
    "Jupiter": {
        "Sun": (1, 2, 3, 4, 7, 8, 9, 10, 11), "Moon": (2, 5, 7, 9, 11),
        "Mars": (1, 2, 4, 7, 8, 10, 11), "Mercury": (1, 2, 4, 5, 6, 9, 10, 11),
        "Jupiter": (1, 2, 3, 4, 7, 8, 10, 11), "Venus": (2, 5, 6, 9, 10, 11),
        "Saturn": (3, 5, 6, 12), "Lagna": (1, 2, 4, 5, 6, 7, 9, 10, 11),
    },
    "Venus": {
        "Sun": (8, 11, 12), "Moon": (1, 2, 3, 4, 5, 8, 9, 11, 12),
        "Mars": (3, 5, 6, 9, 11, 12), "Mercury": (3, 5, 6, 9, 11),
        "Jupiter": (5, 8, 9, 10, 11), "Venus": (1, 2, 3, 4, 5, 8, 9, 10, 11),
        "Saturn": (3, 4, 5, 8, 9, 10, 11), "Lagna": (1, 2, 3, 4, 5, 8, 9, 11),
    },
    "Saturn": {
        "Sun": (1, 2, 4, 7, 8, 10, 11), "Moon": (3, 6, 11),
        "Mars": (3, 5, 6, 10, 11, 12), "Mercury": (6, 8, 9, 10, 11, 12),
        "Jupiter": (5, 6, 11, 12), "Venus": (6, 11, 12),
        "Saturn": (3, 5, 6, 11), "Lagna": (1, 3, 4, 6, 10, 11),
    },
}

CLASSICAL_TOTALS = {"Sun": 48, "Moon": 49, "Mars": 39, "Mercury": 54,
                    "Jupiter": 56, "Venus": 52, "Saturn": 39}
SAV_CLASSICAL_TOTAL = 337

for _planet, _total in CLASSICAL_TOTALS.items():
    if sum(len(h) for h in BENEFIC_PLACES[_planet].values()) != _total:
        raise RuntimeError(f"Ashtakavarga table for {_planet} does not sum to {_total}")


def _check_sign(name: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value < 12:
        raise ValueError(f"{name}: sign index 0-11 required, got {value!r}")


def bav(signs: dict[str, int], lagna_sign: int | None = None) -> dict[str, list[int]]:
    """{planet: 12 bindu counts} from each contributor's sign; no Lagna row if lagna_sign is None."""
    for planet in PLANETS:
        _check_sign(planet, signs.get(planet))
    origins = {p: signs[p] for p in PLANETS}
    if lagna_sign is not None:
        _check_sign("Lagna", lagna_sign)
        origins["Lagna"] = lagna_sign
    out = {}
    for planet in PLANETS:
        row = [0] * 12
        for contributor, start in origins.items():
            for house in BENEFIC_PLACES[planet][contributor]:
                row[(start + house - 1) % 12] += 1
        out[planet] = row
    return out


def sav(bav_result: dict[str, list[int]]) -> list[int]:
    """Sarvashtakavarga: the 7 BAV rows summed sign by sign."""
    return [sum(bav_result[p][s] for p in PLANETS) for s in range(12)]


MODES = ("auto", "classical", "seven")

# A Lagna needs an exact time AND a real birth place: sbc.natal falls back to
# Mumbai for every anchor. Anything not listed is unreliable, so a new anchor
# fails safe.
LAGNA_RELIABLE = {"india": "exact official time, Indian place"}


def _check_anchor(anchor: str) -> None:
    if anchor not in ANCHORS:
        raise ValueError(f"unknown anchor: {anchor!r}")


def _time_approximate(anchor: str) -> bool:
    return "time approximate" in ANCHORS[anchor]["note"].lower()


def resolve_mode(anchor: str, lagna_mode: str = "auto") -> tuple[str, bool, str]:
    """(mode, lagna_reliable, lagna_reason); `auto` drops the Lagna when it is unreliable."""
    _check_anchor(anchor)
    if lagna_mode not in MODES:
        raise ValueError(f"lagna_mode must be one of {MODES}, got {lagna_mode!r}")
    if anchor in LAGNA_RELIABLE:
        reliable, reason = True, LAGNA_RELIABLE[anchor]
    elif _time_approximate(anchor):
        reliable, reason = False, "birth time approximate"
    else:
        reliable, reason = False, "no birth place"
    if lagna_mode == "auto":
        lagna_mode = "classical" if reliable else "seven"
    return lagna_mode, reliable, reason


@cache
def _ambiguous(anchor: str) -> tuple[tuple[str, tuple[str, str]], ...]:
    # Two samples are enough: no contributor moves 30 degrees in a day, and a
    # retrograde planet cannot cross a sign boundary and come back within 24 h.
    # positions() directly, not natal.chart, so natal's shared cache is untouched.
    if not _time_approximate(anchor):
        return ()
    a = ANCHORS[anchor]

    def signs_at(hhmm: str) -> dict[str, int]:
        planets, _ayanamsa = positions(_julday(_utc_from_local(a["date"], hhmm, a["tz"])))
        return {p["name"]: p["sign_index"] for p in planets}

    start, end = signs_at("00:00"), signs_at("23:59")
    return tuple((p, (RASHIS[start[p]], RASHIS[end[p]]))
                 for p in PLANETS if start[p] != end[p])


def ambiguous_contributors(anchor: str) -> dict[str, list[str]]:
    """{planet: [sign at 00:00, sign at 23:59]} for planets changing sign on an approximate birth day."""
    _check_anchor(anchor)
    return {p: list(pair) for p, pair in _ambiguous(anchor)}


TRANSIT_TIME = dt.time(9, 15)  # NSE open, the transit_natal.active_on convention
TRANSIT_TIME_LABEL = "09:15 IST"


def _planet_signs(detail: list[dict]) -> dict[str, int]:
    return {p["name"]: p["sign_index"] for p in detail if p["name"] in PLANETS}


def _tables(signs: dict[str, int], lagna_sign: int | None) -> dict:
    rows = bav(signs, lagna_sign)
    return {"max_per_sign": 8 if lagna_sign is not None else 7, "bav": rows, "sav": sav(rows)}


def natal_ashtakavarga(anchor: str, lagna_mode: str = "auto") -> dict:
    """BAV/SAV for an anchor's natal chart, with how far its Lagna can be trusted."""
    mode, reliable, reason = resolve_mode(anchor, lagna_mode)
    signs = _planet_signs(natal.chart_detail(anchor))
    lagna = int(natal.lagna_longitude(anchor) // 30) if mode == "classical" else None
    return {"mode": mode, "lagna_reliable": reliable, "lagna_reason": reason,
            "ambiguous_contributors": ambiguous_contributors(anchor),
            **_tables(signs, lagna)}


def chart_ashtakavarga(date: str, time: str, tz: str, city: str,
                       lagna_mode: str = "classical") -> dict:
    """BAV/SAV for a hand-given birth moment (book fixtures); `auto` needs an anchor."""
    if lagna_mode not in ("classical", "seven"):
        raise ValueError("lagna_mode must be 'classical' or 'seven' for a hand-given chart")
    if cities.resolve(city) is None:
        raise ValueError(f"unknown city: {city!r}")
    signs = _planet_signs(natal.chart_detail(date, time, tz))
    lagna = int(natal.lagna_longitude(date, time, tz, city) // 30)         if lagna_mode == "classical" else None
    return {"mode": lagna_mode, **_tables(signs, lagna),
            "planet_signs": {p: RASHIS[s] for p, s in signs.items()},
            "lagna_sign": RASHIS[lagna] if lagna is not None else None}


def transit_scores(anchor: str, date: dt.date, lagna_mode: str = "auto") -> dict:
    """Natal BAV/SAV plus, for each of the 7 planets, the bindus of the sign it transits at 09:15 IST."""
    if not isinstance(date, dt.date):
        raise TypeError(f"date must be a datetime.date, got {type(date).__name__}")
    natal_av = natal_ashtakavarga(anchor, lagna_mode)
    planets, _ayanamsa = positions(_jd(dt.datetime.combine(date, TRANSIT_TIME, IST)))
    transit = {}
    for p in planets:
        if p["name"] in PLANETS:
            s = p["sign_index"]
            transit[p["name"]] = {"sign": RASHIS[s], "sign_index": s,
                                  "bav_points": natal_av["bav"][p["name"]][s],
                                  "sav_points": natal_av["sav"][s]}
    return {"date": date.isoformat(), "transit_time": TRANSIT_TIME_LABEL,
            "natal": natal_av, "transit": transit}
