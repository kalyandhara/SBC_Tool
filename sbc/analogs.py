"""Analog search: past market days whose sky most resembles a target day.

Similarity is computed per tier (sbc.fingerprint.TIER) and then blended:

  planets   for each planet in the tier, the mean of: same sign, same
            nakshatra, longitude closeness (1 at 0°, 0 at 30° or more) and,
            for planets that can retrograde, the same direction of motion
  aspects   Jaccard overlap of the tier's aspect sets (both empty = 1)
  fast      also tithi closeness, yoga, weekday lord, hora lord and the KP
            Moon / ascendant sub lords

  slow   = 0.7 planets + 0.3 aspects
  medium = 0.6 planets + 0.4 aspects
  fast   = 0.4 Moon + 0.2 aspects + 0.4 panchang/KP
  overall = TIER_WEIGHTS-weighted mean of the three (0..1; "90% similar" = 0.90)

Analogs are trading days with a complete forward-return window *before the
target's entry* (the previous close), so a search for any past date uses only
what was knowable then. Consecutive days share most of the sky, so analogs
are thinned to at least MIN_SPACING sessions apart, keeping the most similar.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from numpy.typing import ArrayLike

from sbc import fingerprint as fpm
from sbc import stats as st
from sbc.market_events import ASPECT_ANGLES

TIER_WEIGHTS = {"slow": 0.35, "medium": 0.35, "fast": 0.30}
HORIZONS = (1, 5, 20)
MIN_SIMILARITY = 0.90
MIN_ANALOGS = 10   # fewer than this above the threshold -> fall back to the top K
TOP_K = 30
MIN_SPACING = 5    # sessions between kept analogs
EXCLUDE_DAYS = 30  # calendar days around the target that can't be its own analog

_BODIES = fpm.BODIES
_RETRO_CAPABLE = np.array([b not in ("Sun", "Moon", "Rahu", "Ketu") for b in _BODIES])
_ASPECT_KEYS = [(a, b, asp) for a, b in fpm._PAIRS for asp in ASPECT_ANGLES]
_ASPECT_INDEX = {k: i for i, k in enumerate(_ASPECT_KEYS)}
_LORD_INDEX = {lord: i for i, lord in enumerate(fpm.LORDS)}


def _tier_mask(tier: str) -> np.ndarray:
    return np.array([fpm.TIER[b] == tier for b in _BODIES])


def _aspect_tier_mask(tier: str) -> np.ndarray:
    return np.array([fpm._pair_tier(a, b) == tier for a, b, _ in _ASPECT_KEYS])


@dataclass
class SkyArrays:
    """Fingerprints of many dates as aligned numpy arrays (row = date)."""
    dates: list[str]
    lon: np.ndarray      # (N, B) degrees
    sign: np.ndarray     # (N, B)
    nak: np.ndarray      # (N, B)
    retro: np.ndarray    # (N, B) bool
    aspects: np.ndarray  # (N, K) bool
    tithi: np.ndarray    # (N,)
    yoga: np.ndarray
    wd_lord: np.ndarray
    hora_lord: np.ndarray
    moon_sub: np.ndarray
    asc_sub: np.ndarray

    @classmethod
    def from_fingerprints(cls, fps: list[dict]) -> SkyArrays:
        n, b = len(fps), len(_BODIES)
        lon = np.zeros((n, b))
        sign = np.zeros((n, b), dtype=np.int8)
        nak = np.zeros((n, b), dtype=np.int8)
        retro = np.zeros((n, b), dtype=bool)
        aspects = np.zeros((n, len(_ASPECT_KEYS)), dtype=bool)
        cols = {k: np.zeros(n, dtype=np.int16) for k in
                ("tithi", "yoga", "wd_lord", "hora_lord", "moon_sub", "asc_sub")}
        for i, fp in enumerate(fps):
            for j, name in enumerate(_BODIES):
                p = fp["planets"][name]
                lon[i, j], sign[i, j], nak[i, j], retro[i, j] = (
                    p["longitude"], p["sign"], p["nakshatra"], p["retrograde"])
            for a in fp["aspects"]:
                aspects[i, _ASPECT_INDEX[(a["a"], a["b"], a["aspect"])]] = True
            pan, kp = fp["panchang"], fp["kp"]
            cols["tithi"][i] = pan["tithi"]
            cols["yoga"][i] = pan["yoga"]
            cols["wd_lord"][i] = _LORD_INDEX[pan["weekday_lord"]]
            cols["hora_lord"][i] = _LORD_INDEX[pan["hora_lord"]]
            cols["moon_sub"][i] = _LORD_INDEX[kp["moon_sublord"]]
            cols["asc_sub"][i] = _LORD_INDEX[kp["asc_sublord"]]
        return cls([fp["date"] for fp in fps], lon, sign, nak, retro, aspects, **cols)


_MASKS = {t: (_tier_mask(t), _aspect_tier_mask(t)) for t in fpm.TIERS}


def _planet_score(target: SkyArrays, pool: SkyArrays, body_mask: np.ndarray) -> np.ndarray:
    ang = np.abs(((pool.lon[:, body_mask] - target.lon[0, body_mask] + 180) % 360) - 180)
    parts = [
        (pool.sign[:, body_mask] == target.sign[0, body_mask]).astype(float),
        (pool.nak[:, body_mask] == target.nak[0, body_mask]).astype(float),
        np.clip(1 - ang / 30.0, 0, 1),
    ]
    score = sum(parts)
    count = np.full(body_mask.sum(), 3.0)
    retro_cols = _RETRO_CAPABLE[body_mask]
    if retro_cols.any():
        same = (pool.retro[:, body_mask] == target.retro[0, body_mask]).astype(float)
        score = score + same * retro_cols
        count = count + retro_cols
    result: np.ndarray = (score / count).mean(axis=1)
    return result


def _jaccard(target: SkyArrays, pool: SkyArrays, key_mask: np.ndarray) -> np.ndarray:
    t = target.aspects[0, key_mask]
    p = pool.aspects[:, key_mask]
    inter = (p & t).sum(axis=1)
    union = (p | t).sum(axis=1)
    return np.where(union == 0, 1.0, inter / np.maximum(union, 1))


def tier_similarity(target: SkyArrays, pool: SkyArrays) -> dict[str, np.ndarray]:
    """Similarity (0..1) of one target row against every pool row, per tier."""
    out = {}
    for tier in fpm.TIERS:
        bodies, keys = _MASKS[tier]
        planets = _planet_score(target, pool, bodies)
        aspects = _jaccard(target, pool, keys)
        if tier == "slow":
            out[tier] = 0.7 * planets + 0.3 * aspects
        elif tier == "medium":
            out[tier] = 0.6 * planets + 0.4 * aspects
        else:
            tithi_gap = np.abs(((pool.tithi - target.tithi[0] + 15) % 30) - 15)
            extras = np.mean([
                1 - tithi_gap / 15.0,
                pool.yoga == target.yoga[0],
                pool.wd_lord == target.wd_lord[0],
                pool.hora_lord == target.hora_lord[0],
                pool.moon_sub == target.moon_sub[0],
                pool.asc_sub == target.asc_sub[0],
            ], axis=0)
            out[tier] = 0.4 * planets + 0.2 * aspects + 0.4 * extras
    return out


def blend(tiers: dict[str, np.ndarray], weights: dict[str, float] | None = None) -> np.ndarray:
    """Weighted mean of tier similarities (weights need not sum to 1)."""
    weights = weights or TIER_WEIGHTS
    total = sum(weights.values())
    out = np.zeros_like(next(iter(tiers.values())), dtype=float)
    for t, w in weights.items():
        if w:
            out = out + w * tiers[t]
    return out / total


def similarity(target: SkyArrays, pool: SkyArrays,
               weights: dict[str, float] | None = None) -> dict[str, np.ndarray]:
    """Per-tier and overall similarity of one target row against every pool row."""
    tiers = tier_similarity(target, pool)
    return {**tiers, "overall": blend(tiers, weights)}


def select(overall: np.ndarray, candidates: np.ndarray, min_similarity: float | None = MIN_SIMILARITY,
           k: int = TOP_K) -> tuple[np.ndarray, str]:
    """Pick analog rows from `candidates` (indices into `overall`), thinned by MIN_SPACING.

    Every candidate at or above min_similarity when there are at least MIN_ANALOGS of
    them; otherwise the K most similar.
    """
    scores = overall[candidates]
    order = np.argsort(-scores, kind="stable")
    if min_similarity is not None:
        above = order[scores[order] >= min_similarity]
        kept = _thin(above, candidates, MIN_SPACING, None)
        if len(kept) >= MIN_ANALOGS:
            return candidates[kept], "threshold"
    return candidates[_thin(order, candidates, MIN_SPACING, k)], "top_k"


def _thin(order: np.ndarray, positions: np.ndarray, spacing: int, limit: int | None) -> list[int]:
    """Walk candidates best-first, keeping those at least `spacing` sessions from any kept one."""
    kept: list[int] = []
    taken = np.zeros(int(positions.max()) + spacing + 1 if len(positions) else 1, dtype=bool)
    for i in order:
        pos = int(positions[i])
        if taken[max(0, pos - spacing + 1):pos + spacing].any():
            continue
        kept.append(int(i))
        taken[pos] = True
        if limit and len(kept) >= limit:
            break
    return kept


@dataclass
class History:
    """NIFTY sessions with their fingerprints and forward returns."""
    dates: list[str]
    closes: np.ndarray
    sky: SkyArrays
    fwd: dict[int, np.ndarray]
    ordinals: np.ndarray

    @classmethod
    def build(cls, dates: list[str], closes: ArrayLike, fps: list[dict],
              horizons: tuple[int, ...] = HORIZONS) -> History:
        closes = np.asarray(closes, dtype=float)
        return cls(dates, closes, SkyArrays.from_fingerprints(fps),
                   {h: st.forward_returns(closes, h) for h in horizons},
                   np.array([_ordinal(d) for d in dates]))

    def usable_before(self, entry_index: int, horizon: int) -> int:
        """Sessions whose h-day forward window closed by the entry close (index entry_index)."""
        # fwd[i] spans close[i-1] .. close[i+h-1]; known when i+h-1 <= entry_index
        return max(0, entry_index - horizon + 2)


@lru_cache(maxsize=2)
def _history_cached(version: str, last_date: str) -> History:
    from sbc.rule_validation import load_history
    dates, closes, fps = load_history()
    return History.build(dates, closes, fps)


def load_nifty_history() -> History:
    """NIFTY history from market.db + fingerprints.db, cached per code version and data date."""
    from sbc import fingerprint_store, market_store
    last = market_store.freshness()["series"]["NIFTY"]["last"] or ""
    return _history_cached(fingerprint_store.current_version(), last)


def find_analogs(history: History, target_fp: dict, horizon: int = 5,
                 min_similarity: float | None = MIN_SIMILARITY, k: int = TOP_K,
                 weights: dict[str, float] | None = None, cutoff: str | None = None) -> dict:
    """Analogs of `target_fp` among sessions whose `horizon`-day outcome was known before it.

    cutoff: entry date (YYYY-MM-DD); defaults to the target date. Only sessions whose
    forward window closed before the session preceding the cutoff are eligible.
    """
    cutoff = cutoff or target_fp["date"]
    entry_index = int(np.searchsorted(history.dates, cutoff)) - 1  # previous close
    n_usable = history.usable_before(entry_index, horizon) if entry_index >= 0 else 0
    fwd = history.fwd[horizon]
    target = SkyArrays.from_fingerprints([target_fp])
    sims = similarity(target, _slice(history.sky, n_usable), weights)

    eligible = np.isfinite(fwd[:n_usable])
    far = np.abs(history.ordinals[:n_usable] - _ordinal(target_fp["date"])) > EXCLUDE_DAYS
    candidates = np.where(eligible & far)[0]
    if not len(candidates):
        return {"target": target_fp["date"], "horizon": horizon, "analogs": [], "mode": "none",
                "pool": 0, "summary": None}

    idx, mode = select(sims["overall"], candidates, min_similarity, k)
    def known(h: int, i: int) -> float | None:
        """Forward return only if it was complete by the cutoff."""
        value = history.fwd[h][i]
        if not math.isfinite(value) or i >= history.usable_before(entry_index, h):
            return None
        return round(float(value), 5)

    sky, t_ord = history.sky, _ordinal(target_fp["date"])
    analogs = [{
        "date": history.dates[i],
        "age_years": round((t_ord - int(history.ordinals[i])) / 365.25, 1),
        "similarity": round(float(sims["overall"][i]), 4),
        "tiers": {t: round(float(sims[t][i]), 4) for t in fpm.TIERS},
        "same_sign": [b for j, b in enumerate(_BODIES) if sky.sign[i, j] == target.sign[0, j]],
        "same_nakshatra": [b for j, b in enumerate(_BODIES) if sky.nak[i, j] == target.nak[0, j]],
        "forward": {str(h): known(h, i) for h in history.fwd},
    } for i in idx]
    return {
        "target": target_fp["date"],
        "horizon": horizon,
        "mode": mode,
        "min_similarity": min_similarity,
        "best_similarity": round(float(sims["overall"][candidates].max()), 4),
        "pool": int(len(candidates)),
        "analogs": analogs,
        "summary": summarize(fwd[idx], fwd[:n_usable]),
    }


def summarize(analog_returns: np.ndarray, pool_returns: np.ndarray) -> dict | None:
    """What followed the analogs, against what followed every eligible session."""
    a = analog_returns[np.isfinite(analog_returns)]
    base = pool_returns[np.isfinite(pool_returns)]
    if not len(a) or not len(base):
        return None
    mu = float(base.mean())
    return {
        "n": int(len(a)),
        "mean": float(a.mean()),
        "median": float(np.median(a)),
        "q25": float(np.quantile(a, 0.25)),
        "q75": float(np.quantile(a, 0.75)),
        "up_share": float((a > 0).mean()),
        "base_mean": mu,
        "base_up_share": float((base > 0).mean()),
        "excess": float(a.mean() - mu),
        "lean": int(np.sign(a.mean() - mu)),
    }


_ARRAY_FIELDS = ("lon", "sign", "nak", "retro", "aspects", "tithi", "yoga", "wd_lord",
                 "hora_lord", "moon_sub", "asc_sub")


def _slice_rows(sky: SkyArrays, start: int, stop: int) -> SkyArrays:
    return SkyArrays(sky.dates[start:stop], *(getattr(sky, f)[start:stop] for f in _ARRAY_FIELDS))


def _slice(sky: SkyArrays, n: int) -> SkyArrays:
    return _slice_rows(sky, 0, n)


def _ordinal(date: str) -> int:
    return dt.date.fromisoformat(date).toordinal()
