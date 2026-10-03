"""Walk-forward test of the analog engine on NIFTY.

For every session from START onward, the engine forecasts that session as a
live user would have: it finds analogs only among sessions whose h-day outcome
was complete by the previous close, takes the top TOP_K (thinned), and leans
the way their average outcome beat the drift of every eligible session:

    signal = sign(mean(analog forward returns) - mean(all eligible forward returns))

Variants weight the tiers differently, to see which layer of the sky (if any)
carries information. A control picks the same number of analogs at random
from the same pool; it should show no edge.

The signals are graded by sbc.rule_validation.grade, the harness used for the
rules, so the numbers are directly comparable.
"""

from __future__ import annotations

import datetime as dt

import numpy as np

from sbc import analogs as an
from sbc import fingerprint_store
from sbc import rule_validation as rv
from sbc import stats as st

START = "2012-01-01"  # leaves 4+ years of history for the first searches
ERA_SPLIT = "2021-01-01"

VARIANTS = {
    "analog_overall": an.TIER_WEIGHTS,
    "analog_slow": {"slow": 1.0, "medium": 0.0, "fast": 0.0},
    "analog_medium": {"slow": 0.0, "medium": 1.0, "fast": 0.0},
    "analog_fast": {"slow": 0.0, "medium": 0.0, "fast": 1.0},
}
CONTROL = "analog_random"

DESCRIPTIONS = {
    "analog_overall": "Top-30 analogs on the blended sky (slow .35 / medium .35 / fast .30)",
    "analog_slow": "Top-30 analogs on the slow tier only (Jupiter, Saturn, nodes, outers)",
    "analog_medium": "Top-30 analogs on the medium tier only (Sun, Mercury, Venus, Mars)",
    "analog_fast": "Top-30 analogs on the fast tier only (Moon, panchang, KP lords)",
    CONTROL: "30 random eligible sessions (control; should show no edge)",
}


def track_record(variant: str, horizon: int) -> dict | None:
    """Walk-forward grade of one variant/horizon from the newest analog_validation report."""
    from sbc import research_reports

    r = research_reports.result("analog_validation", f"analog_{variant}", horizon)
    if r is None:
        return None
    keys = ("n", "hit_rate", "baseline", "excess", "p", "q", "verdict", "eras", "years_right", "years")
    return {"report": r["_file"], "sample": r["_sample"], **{k: r.get(k) for k in keys}}


def _era(date: str) -> str:
    return "2012-2020" if date < ERA_SPLIT else "2021-2026"


def walk_forward(history: an.History, start: str = START, k: int = an.TOP_K,
                 horizons=an.HORIZONS) -> tuple[dict, dict]:
    """({variant: {h: signal per session}}, {variant: {h: best similarity per session}})."""
    n = len(history.dates)
    first = int(np.searchsorted(history.dates, start))
    names = [*VARIANTS, CONTROL]
    signals = {v: {h: np.zeros(n, dtype=int) for h in horizons} for v in names}
    best = {v: {h: np.full(n, np.nan) for h in horizons} for v in VARIANTS}
    fwd_known = {h: np.isfinite(history.fwd[h]) for h in horizons}

    for i in range(max(first, 1), n):
        entry = i - 1
        pool_n = history.usable_before(entry, min(horizons))
        if pool_n < 2 * k:
            continue
        target = an._slice_rows(history.sky, i, i + 1)
        tiers = an.tier_similarity(target, an._slice(history.sky, pool_n))
        far = np.abs(history.ordinals[:pool_n] - history.ordinals[i]) > an.EXCLUDE_DAYS
        rng = np.random.default_rng(i)
        for h in horizons:
            n_u = history.usable_before(entry, h)
            eligible = fwd_known[h][:n_u] & far[:n_u]
            candidates = np.where(eligible)[0]
            if len(candidates) < 2 * k:
                continue
            fwd = history.fwd[h]
            base = fwd[candidates].mean()
            for name, weights in VARIANTS.items():
                overall = an.blend({t: v[:n_u] for t, v in tiers.items()}, weights)
                idx, _ = an.select(overall, candidates, None, k)
                signals[name][h][i] = int(np.sign(fwd[idx].mean() - base))
                best[name][h][i] = overall[candidates].max()
            pick = rng.choice(candidates, size=k, replace=False)
            signals[CONTROL][h][i] = int(np.sign(fwd[pick].mean() - base))
    return signals, best


def run(n_perm: int = st.N_PERMUTATIONS, start: str = START) -> dict:
    history = an.load_nifty_history()
    signals, best = walk_forward(history, start)
    entries = [{"name": name, "kind": "directional", "source": "sbc.analogs",
                "description": DESCRIPTIONS[name], "signal": signals[name]}
               for name in signals]
    results = rv.grade(history.dates, history.closes, entries, an.HORIZONS, n_perm,
                       start=start, era=_era)
    first = int(np.searchsorted(history.dates, start))
    similarity = {
        name: {str(h): {"median_best": float(np.nanmedian(best[name][h][first:])),
                        "max_best": float(np.nanmax(best[name][h][first:]))}
               for h in an.HORIZONS}
        for name in VARIANTS
    }
    return {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "fingerprint_version": fingerprint_store.current_version(),
        "sample": {"first": history.dates[first], "last": history.dates[-1],
                   "sessions": len(history.dates) - first},
        "horizons": list(an.HORIZONS),
        "n_permutations": n_perm,
        "k": an.TOP_K,
        "best_similarity": similarity,
        "results": results,
    }
