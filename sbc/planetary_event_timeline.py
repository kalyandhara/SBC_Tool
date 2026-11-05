"""Mars-in-Pushya with Moon-in-Rohini against NIFTY forward returns (B-71).

Pure logic only. Loading NIFTY bars and the 09:15 IST sky is done by
scripts/validate_planetary_event_timeline.py. Registered in
docs/research/planetary_event_timeline_preregistration_2026-10-30.md.

Event: a run of consecutive sessions where the condition holds. The run's first
session is one event (an episode). Control: every session in the same same-day-move
decile that is not an event. Statistic: mean over events of (forward return minus
the decile control mean). Null: event labels exchanged within each decile.
"""

import numpy as np

from sbc.stats import bh_adjust

HORIZONS = (1, 5, 10, 20)
PRIMARY_HORIZON = 5
N_DECILES = 10
MIN_EPISODES = 15
N_PERMUTATIONS = 10_000
SEED = 42
ALPHA = 0.05


def is_event(planets: dict) -> bool:
    """planets: name -> planet dict from sbc.planets at 09:15 IST."""
    return planets["Mars"]["nakshatra"] == "Pushya" and planets["Moon"]["nakshatra"] == "Rohini"


def episode_starts(flags) -> np.ndarray:
    """Boolean mask marking the first session of each run of consecutive True flags."""
    flags = np.asarray(flags, dtype=bool)
    prev = np.concatenate(([False], flags[:-1]))
    return flags & ~prev


def same_day_returns(closes) -> np.ndarray:
    """r0[t] = close[t] / close[t-1] - 1; NaN on the first session."""
    c = np.asarray(closes, dtype=float)
    r0 = np.full(len(c), np.nan)
    r0[1:] = c[1:] / c[:-1] - 1.0
    return r0


def decile_labels(r0) -> np.ndarray:
    """Decile 0..9 of each finite same-day return over the whole sample; -1 where undefined."""
    r0 = np.asarray(r0, dtype=float)
    labels = np.full(len(r0), -1)
    ok = np.isfinite(r0)
    edges = np.quantile(r0[ok], np.linspace(0, 1, N_DECILES + 1)[1:-1])
    labels[ok] = np.searchsorted(edges, r0[ok], side="right")
    return labels


def forward_returns(closes, horizon: int) -> np.ndarray:
    """fwd[t] = close[t + horizon] / close[t] - 1; NaN where the window runs past the sample."""
    c = np.asarray(closes, dtype=float)
    fwd = np.full(len(c), np.nan)
    fwd[:-horizon] = c[horizon:] / c[:-horizon] - 1.0
    return fwd


def excess_statistic(fwd, labels, ev, ctrl=None) -> float:
    """Mean over events of (fwd - mean fwd of same-decile control sessions).

    ctrl defaults to every non-event session. Events with no finite forward return,
    or in a decile with no control, are dropped. NaN when nothing is left.
    """
    ev = np.asarray(ev, dtype=bool)
    ctrl = ~ev if ctrl is None else np.asarray(ctrl, dtype=bool)
    total, count = 0.0, 0
    for d in range(N_DECILES):
        m = (labels == d) & np.isfinite(fwd)
        e = m & ev
        c = m & ctrl
        if e.any() and c.any():
            total += float((fwd[e] - fwd[c].mean()).sum())
            count += int(e.sum())
    return total / count if count else float("nan")


def permutation_p(fwd, labels, ev, observed: float, iters: int = N_PERMUTATIONS,
                  seed: int = SEED) -> float:
    """Two-sided p from a decile-preserving permutation of event labels.

    Each permutation draws the same number of events per decile from all sessions in
    that decile with a finite forward return. p = (hits + 1) / (iters + 1).
    """
    if not np.isfinite(observed):
        return float("nan")
    rng = np.random.default_rng(seed)
    ev = np.asarray(ev, dtype=bool)
    ok = np.isfinite(fwd) & (labels >= 0)
    pools = {d: np.flatnonzero(ok & (labels == d)) for d in range(N_DECILES)}
    counts = {d: int((ev & ok & (labels == d)).sum()) for d in range(N_DECILES)}
    hits = 0
    for _ in range(iters):
        perm = np.zeros(len(fwd), dtype=bool)
        for d, k in counts.items():
            if k:
                perm[rng.choice(pools[d], size=k, replace=False)] = True
        if abs(excess_statistic(fwd, labels, perm)) >= abs(observed) - 1e-12:
            hits += 1
    return (hits + 1) / (iters + 1)


def event_path(closes, starts, before: int = 5, after: int = 20) -> np.ndarray:
    """One row per event: closes from -before to +after sessions, scaled so the event close = 100.

    Rows run past the sample edge are NaN.
    """
    c = np.asarray(closes, dtype=float)
    rows = []
    for i in np.flatnonzero(starts):
        row = np.full(before + after + 1, np.nan)
        lo, hi = i - before, i + after
        src = c[max(lo, 0):min(hi, len(c) - 1) + 1]
        row[max(0, -lo):max(0, -lo) + len(src)] = src / c[i] * 100.0
        rows.append(row)
    return np.array(rows) if rows else np.empty((0, before + after + 1))


def grade(n_episodes: int, p: float, q: float, same_sign: bool) -> str:
    """Registered rule: needs MIN_EPISODES, p < ALPHA, q < ALPHA and the same sign in both eras."""
    if n_episodes < MIN_EPISODES:
        return "insufficient"
    if p < ALPHA and q < ALPHA and same_sign:
        return "edge"
    return "no edge"


def benjamini_hochberg(pvalues) -> list[float]:
    """BH-adjusted q-values across one family (thin wrapper over sbc.stats)."""
    return bh_adjust(pvalues)
