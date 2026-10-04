"""Statistics for judging astro signals against what the market does anyway.

Everything here compares a signal with the *unconditional* market over the
same days, because NIFTY drifts upward: a rule that is "bullish" every day
gets a 53% hit rate for free.

  forward_returns     close-to-close return over the next h sessions
  evaluate_directional  signal in {-1, 0, +1}: excess return, hit rate vs baseline, p-value
  evaluate_event        boolean flag: does the market move more (|return|) on flagged days?
  bh_adjust             Benjamini-Hochberg q-values for many tests at once
  by_period             the same statistic per year / per era

P-values come from a circular-shift permutation test: the signal series is
rotated against the return series by a random offset. Rotation keeps the
autocorrelation of both series (a slow-planet signal lasts months; h-day
returns overlap), which an ordinary t-test or shuffle would ignore and so
overstate significance.

Entry is the previous close: the ephemeris is known in advance, so a signal
for day t is available before day t opens.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
from numpy.typing import ArrayLike

MIN_SIGNAL_DAYS = 30
N_PERMUTATIONS = 1000
MIN_SHIFT = 60  # sessions; rotations shorter than this barely decorrelate anything


def forward_returns(closes: ArrayLike, horizon: int) -> np.ndarray:
    """r[t] = close[t+h-1] / close[t-1] - 1; NaN where the window runs off either end."""
    c = np.asarray(closes, dtype=float)
    out = np.full(len(c), np.nan)
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    if len(c) > horizon:
        out[1:len(c) - horizon + 1] = c[horizon:] / c[:len(c) - horizon] - 1.0
    return out


def shift_pvalue(signal: np.ndarray, values: np.ndarray, stat: Callable[[np.ndarray, np.ndarray], float],
                  observed: float, n_perm: int, seed: int) -> float:
    n = len(signal)
    if n <= 2 * MIN_SHIFT:
        return float("nan")
    rng = np.random.default_rng(seed)
    shifts = rng.integers(MIN_SHIFT, n - MIN_SHIFT, size=n_perm)
    extreme = 0
    for k in shifts:
        s = stat(np.roll(signal, int(k)), values)
        if np.isfinite(s) and abs(s) >= abs(observed):
            extreme += 1
    return (extreme + 1) / (n_perm + 1)


def excess_stat(signal: np.ndarray, fwd: np.ndarray) -> float:
    valid = np.isfinite(fwd)
    mask = valid & (signal != 0)
    if not mask.any():
        return float("nan")
    mu = fwd[valid].mean()
    return float(np.mean(signal[mask] * (fwd[mask] - mu)))


def evaluate_directional(signal: ArrayLike, fwd: ArrayLike, n_perm: int = N_PERMUTATIONS,
                         seed: int = 0, min_n: int = MIN_SIGNAL_DAYS) -> dict:
    """Score a directional signal (+1 bullish, -1 bearish, 0 no call) against forward returns.

    excess    mean of signal * (return - unconditional mean) over signal days:
              > 0 means the calls beat the market's own drift
    hit_rate  share of signal days whose return has the called sign
    baseline  the hit rate a constant guess of the same calls would get
              (P(up) for each bullish call, P(down) for each bearish one)
    """
    s = np.asarray(signal, dtype=float)
    r = np.asarray(fwd, dtype=float)
    valid = np.isfinite(r)
    mask = valid & (s != 0)
    n = int(mask.sum())
    out: dict = {"n": n, "n_long": int((mask & (s > 0)).sum()), "n_short": int((mask & (s < 0)).sum())}
    if n < min_n:
        return {**out, "status": "insufficient"}
    p_up = float((r[valid] > 0).mean())
    hits = np.sign(r[mask]) == s[mask]
    baseline = np.where(s[mask] > 0, p_up, 1.0 - p_up).mean()
    observed = excess_stat(s, r)
    long_mask, short_mask = mask & (s > 0), mask & (s < 0)
    return {
        **out,
        "status": "ok",
        "excess": observed,
        "hit_rate": float(hits.mean()),
        "baseline": float(baseline),
        "mean_long": float(r[long_mask].mean()) if long_mask.any() else None,
        "mean_short": float(r[short_mask].mean()) if short_mask.any() else None,
        "mean_all": float(r[valid].mean()),
        "p": shift_pvalue(s, r, excess_stat, observed, n_perm, seed),
    }


def vol_stat(flag: np.ndarray, absret: np.ndarray) -> float:
    valid = np.isfinite(absret)
    on, off = valid & (flag != 0), valid & (flag == 0)
    if not on.any() or not off.any():
        return float("nan")
    return float(absret[on].mean() - absret[off].mean())


def evaluate_event(flag: ArrayLike, fwd: ArrayLike, n_perm: int = N_PERMUTATIONS,
                   seed: int = 0, min_n: int = MIN_SIGNAL_DAYS) -> dict:
    """Do flagged days move more than unflagged ones? Compares mean |return|."""
    f = np.asarray(flag, dtype=float)
    r = np.asarray(fwd, dtype=float)
    valid = np.isfinite(r)
    n = int((valid & (f != 0)).sum())
    if n < min_n or n > valid.sum() - min_n:
        return {"n": n, "status": "insufficient"}
    absret = np.abs(r)
    observed = vol_stat(f, absret)
    on, off = valid & (f != 0), valid & (f == 0)
    return {
        "n": n,
        "status": "ok",
        "abs_on": float(absret[on].mean()),
        "abs_off": float(absret[off].mean()),
        "vol_ratio": float(absret[on].mean() / absret[off].mean()),
        "mean_on": float(r[on].mean()),
        "excess": observed,
        "p": shift_pvalue(f, absret, vol_stat, observed, n_perm, seed),
    }


def bh_adjust(pvalues: ArrayLike) -> list[float]:
    """Benjamini-Hochberg q-values (NaN p-values stay NaN and are not counted)."""
    p = np.asarray(pvalues, dtype=float)
    q = np.full(len(p), np.nan)
    idx = np.where(np.isfinite(p))[0]
    m = len(idx)
    if not m:
        return q.tolist()
    order = idx[np.argsort(p[idx])]
    ranked = p[order] * m / np.arange(1, m + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    q[order] = np.minimum(ranked, 1.0)
    return q.tolist()


def by_period(signal: ArrayLike, fwd: ArrayLike, periods: Sequence[str],
              stat: Callable[[np.ndarray, np.ndarray], float] = excess_stat) -> dict[str, float | None]:
    """The statistic computed separately within each period label (e.g. year or era)."""
    s = np.asarray(signal, dtype=float)
    r = np.asarray(fwd, dtype=float)
    labels = np.asarray(periods)
    out: dict[str, float | None] = {}
    for label in sorted(set(periods)):
        m = labels == label
        value = stat(s[m], r[m])
        out[str(label)] = value if np.isfinite(value) else None
    return out

