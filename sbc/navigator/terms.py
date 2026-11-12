"""Daily term calculators. Each maps a raw score to 0-100 by (raw + 100) / 2.

`Term.raw` is left unclipped so a day's factors always sum to it exactly; only
`values` is clipped. Natal-dependent terms run once per placebo chart, so they
are vectorised over the shared SkyTable and factor lists are built on demand.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any
from dataclasses import dataclass

import numpy as np

from sbc import nakshatra as N
from sbc.navigator import weights as W
from sbc.planets import COMBUST_ORB, DEBIL, EXALT
from sbc.yogas import vimshottari

STRENGTH_NOTE = "partial: no Shadbala/Avastha yet"
STRENGTH_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
ASPECT_NAMES = {"CONJ": "conjunct", "SXT": "sextile", "SQ": "square",
                "TRI": "trine", "OPP": "opposite"}
_RASHIS = np.array(N.RASHIS)
_SIGN_POINTS = np.array([W.MOON_SIGN[i] for i in range(12)], float)
_NAK_NAMES = np.array(N.NAKSHATRAS_27 + ["Abhijit"])
_NAK_POINTS = np.array([W.MOON_NAKSHATRA_DRUVA if n in W.DRUVA
                        else W.MOON_NAKSHATRA_UGRA if n in W.UGRA else 0.0
                        for n in _NAK_NAMES])
_LEVELS = (("maha", "antardashas"), ("antar", "pratyantars"), ("pratyantar", None))
_MIN_VOL_HISTORY = 20


@dataclass
class Term:
    values: np.ndarray
    raw: np.ndarray
    factors: Callable[[int], list[dict]]


def _scale(raw: np.ndarray) -> np.ndarray:
    return np.asarray((np.clip(raw, -100, 100) + 100) / 2)


def _lon(x: np.ndarray) -> np.ndarray:
    """Longitude in [0, 360); a tiny negative would otherwise % to exactly 360."""
    x = np.mod(x, 360.0)
    return np.where(x >= 360.0, 0.0, x)


def _sep(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.asarray(np.abs((a - b + 180.0) % 360.0 - 180.0))


def _sign_index(lon: np.ndarray) -> np.ndarray:
    return (np.floor(lon).astype(int) // 30) % 12


def _nakshatra_index(lon: np.ndarray) -> np.ndarray:
    """Vector form of sbc.nakshatra.nakshatra_of; 27 is Abhijit."""
    idx = np.minimum(np.floor_divide(lon, N.NAKSHATRA_SPAN).astype(int), 26)
    return np.where((lon >= N.ABHIJIT_START) & (lon < N.ABHIJIT_END), 27, idx)


def _transit_contrib(sky_lon: np.ndarray, points: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """sky_lon (bodies, days), points (points,), weights (bodies, points, aspects).
    Returns contributions shaped (bodies, points, aspects, days)."""
    sep = _sep(sky_lon[:, None, :], points[None, :, None])
    angles = np.array(list(W.ASPECTS.values()))[None, None, :, None]
    orb = np.clip(1 - np.abs(sep[:, :, None, :] - angles) / W.ORB, 0, 1)
    return np.asarray(weights[..., None] * orb)


def transit_term(sky: Any, natal: Mapping[str, float]) -> Term:
    bodies, names, codes = W.TRANSIT_BODIES, list(natal), list(W.ASPECTS)
    lon = np.array([sky.lon[b] for b in bodies], float)
    points = np.array([natal[p] for p in names], float)
    weights = np.array([[[W.ASPECT_WEIGHT(b, p, c) for c in codes] for p in names]
                        for b in bodies], float)
    raw = _transit_contrib(lon, points, weights).sum(axis=(0, 1, 2))

    def factors(i):
        i = range(lon.shape[1])[i]
        c = _transit_contrib(lon[:, i:i + 1], points, weights)[..., 0]
        return [{"term": "transit", "raw": float(c[b, p, a]),
                 "label": f"{bodies[b]} {ASPECT_NAMES[codes[a]]} natal {names[p]}"}
                for b, p, a in zip(*np.nonzero(c))]
    return Term(_scale(raw), raw, factors)


def moon_term(sky: Any) -> Term:
    moon, sun = _lon(sky.lon["Moon"]), _lon(sky.lon["Sun"])
    elong = _lon(moon - sun)
    phase = W.MOON_PHASE * np.cos(np.radians(elong - 90.0))
    tithi = np.minimum(np.floor_divide(elong, 12.0).astype(int) + 1, 30)
    rikta = np.isin(tithi, list(N.TITHI_GROUPS["Rikta"]))
    nanda = np.isin(tithi, list(N.TITHI_GROUPS["Nanda"]))
    tithi_pts = rikta * W.MOON_TITHI_RIKTA + nanda * W.MOON_TITHI_NANDA
    sign = _sign_index(moon)
    sign_pts = _SIGN_POINTS[sign]
    nak = _nakshatra_index(moon)
    nak_pts = _NAK_POINTS[nak]
    raw = phase + tithi_pts + sign_pts + nak_pts

    def factors(i):
        side = "waxing" if elong[i] < 180.0 else "waning"
        group = "rikta" if rikta[i] else "nanda"
        star = "fixed" if nak_pts[i] > 0 else "fierce"
        parts = [(f"Moon phase ({side})", phase[i]),
                 (f"Tithi {tithi[i]} ({group} group)", tithi_pts[i]),
                 (f"Moon in {_RASHIS[sign[i]]}", sign_pts[i]),
                 (f"Moon in {_NAK_NAMES[nak[i]]} ({star} star group)", nak_pts[i])]
        return [{"term": "moon", "label": lbl, "raw": float(r)} for lbl, r in parts if r]
    return Term(_scale(raw), raw, factors)


def _flatten_periods(timeline):
    """{level: (start times, lord names)}, each sorted, from one vimshottari call."""
    rows: dict[str, list[tuple[Any, Any]]] = {level: [] for level, _ in _LEVELS}
    def walk(periods, depth):
        level, child = _LEVELS[depth]
        for p in periods:
            rows[level].append((p["start"], p["lord"]))
            if child:
                walk(p[child], depth + 1)
    walk(timeline["mahadashas"], 0)
    return {k: (np.array([s for s, _ in v], "datetime64[us]"), np.array([lbl for _, lbl in v]))
            for k, v in rows.items()}


def dasha_term(sky: Any, moon_natal_lon: float, birth_date: str) -> Term:
    timeline = vimshottari(moon_natal_lon, birth_date, sky.days[0])
    days = np.array(sky.days, "datetime64[D]").astype("datetime64[us]")
    periods = _flatten_periods(timeline)
    end = np.datetime64(timeline["mahadashas"][-1]["end"], "us")
    covered = (days >= periods["maha"][0][0]) & (days < end)
    lords, parts = {}, {}
    for level, _ in _LEVELS:
        starts, names = periods[level]
        at = np.clip(np.searchsorted(starts, days, side="right") - 1, 0, len(names) - 1)
        lords[level] = names[at]
        pts = np.array([W.DASHA_LORD[n] * W.DASHA_LEVELS[level] for n in names])
        parts[level] = np.where(covered, pts[at], 0.0)
    raw = np.sum(list(parts.values()), axis=0)
    period_name = {"maha": "main period", "antar": "sub-period", "pratyantar": "minor period"}

    def factors(i):
        if not covered[i]:
            return [{"term": "dasha", "label": "Date outside dasha timeline",
                     "raw": 0.0, "neutral": True}]
        return [{"term": "dasha", "label": f"{lords[lvl][i]} {period_name[lvl]}",
                 "raw": float(parts[lvl][i])} for lvl, _ in _LEVELS]
    return Term(_scale(raw), raw, factors)


def strength_term(sky: Any) -> Term:
    sun = sky.lon["Sun"]
    parts = []
    for planet in STRENGTH_PLANETS:
        lon = _lon(sky.lon[planet])
        sign = _sign_index(lon)
        parts.append((f"{planet} exalted", (sign == EXALT[planet]) * W.STRENGTH_EXALTED))
        parts.append((f"{planet} debilitated", (sign == DEBIL[planet]) * W.STRENGTH_DEBILITATED))
        if planet in COMBUST_ORB:     # the Sun has no entry, so it cannot combust itself
            near = _sep(lon, sun) < COMBUST_ORB[planet]
            parts.append((f"{planet} combust", near * W.STRENGTH_COMBUST))
        parts.append((f"{planet} retrograde", sky.retro[planet] * W.STRENGTH_RETRO))
    raw = np.sum([c for _, c in parts], axis=0)

    def factors(i):
        return [{"term": "strength", "label": lbl, "raw": float(c[i]), "note": STRENGTH_NOTE}
                for lbl, c in parts if c[i]]
    return Term(_scale(raw), raw, factors)


def vol_term(days: list[str], vix_by_day: Mapping[str, float], window: int = 252, min_history: int = _MIN_VOL_HISTORY) -> Term:
    """Percentile of the T-1 close among the `window` closes before it, so the
    entry day's own value can never reach day T's score. Neutral until
    `min_history` closes exist before T-1; gaps in the series do not restart it."""
    n = len(days)
    vix = np.array([vix_by_day.get(d, np.nan) for d in days], float)
    vix[~np.isfinite(vix)] = np.nan
    values, pcts = np.full(n, 50.0), np.full(n, np.nan)
    closes_before = np.concatenate(([0], np.cumsum(~np.isnan(vix))))
    for i in range(1, n):
        last = vix[i - 1]
        if np.isnan(last) or closes_before[i - 1] < min_history:
            continue
        past = vix[max(0, i - 1 - window):i - 1]
        past = past[~np.isnan(past)]
        if len(past) < _MIN_VOL_HISTORY:
            continue
        pcts[i] = 100.0 * (np.sum(past < last) + .5 * np.sum(past == last)) / len(past)
        values[i] = 100.0 - pcts[i]
    raw = 2.0 * values - 100.0

    def factors(i):
        if np.isnan(pcts[i]):
            return [{"term": "vol", "label": "India VIX unavailable, neutral value used",
                     "raw": 0.0, "neutral": True}]
        return [{"term": "vol", "raw": float(raw[i]),
                 "label": f"India VIX prior close at percentile {pcts[i]:.0f}"}]
    return Term(values, raw, factors)
