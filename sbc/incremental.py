"""Does an astro signal tell us anything the market itself didn't already?

Two questions, answered on the same NIFTY sessions:

1. Partial effect. Regress the h-session forward return on the market
   controls (sbc.market_features) and the astro signal together. The astro
   coefficient is what the signal adds *beyond* trend, volatility, VIX,
   weekday and turn-of-month. Its p-value comes from rotating the astro
   signal against everything else (circular shift, as in sbc.stats), so
   persistent signals aren't flattered.

2. Out-of-sample skill of the controls alone. A yearly walk-forward OLS
   (fit on sessions whose outcome was known before the year starts, predict
   the year) shows whether the market-side variables forecast anything; if
   even they don't, an astro edge on top of them would be surprising.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import ArrayLike

from sbc import stats as st

MIN_ROWS = 500


def _design(controls: np.ndarray) -> np.ndarray:
    """Standardized controls plus an intercept; constant columns dropped."""
    mu = controls.mean(axis=0)
    sd = controls.std(axis=0)
    keep = sd > 0
    z = (controls[:, keep] - mu[keep]) / sd[keep]
    return np.column_stack([np.ones(len(z)), z])


def _residualizer(x: np.ndarray) -> Callable[[np.ndarray], np.ndarray]:
    q, _ = np.linalg.qr(x)
    return lambda v: v - q @ (q.T @ v)


def partial_effect(signal: ArrayLike, fwd: ArrayLike, controls: ArrayLike,
                   n_perm: int = st.N_PERMUTATIONS, seed: int = 0) -> dict:
    """Effect of `signal` on `fwd` after the controls, with a circular-shift p-value.

    beta     return per unit of signal (for a ±1 signal: half the long-minus-short gap)
    beta_raw the same without controls, to show how much the controls absorb
    """
    s = np.asarray(signal, dtype=float)
    y = np.asarray(fwd, dtype=float)
    x = np.asarray(controls, dtype=float)
    rows = np.isfinite(y) & np.isfinite(x).all(axis=1) & np.isfinite(s)
    n = int(rows.sum())
    if n < MIN_ROWS or np.nanstd(s[rows]) == 0:
        return {"n": n, "status": "insufficient"}
    s, y, x = s[rows], y[rows], x[rows]
    resid = _residualizer(_design(x))
    ry = resid(y)

    def beta(sig):
        rs = resid(sig)
        var = rs @ rs
        return float(rs @ ry / var) if var > 0 else float("nan")

    observed = beta(s)
    sc = s - s.mean()
    raw = float(sc @ (y - y.mean()) / (sc @ sc))
    p = st.shift_pvalue(s, y, lambda sig, _y: beta(sig), observed, n_perm, seed)
    return {"n": n, "status": "ok", "beta": observed, "beta_raw": raw, "p": p}


def _with_intercept(m: np.ndarray, mu: np.ndarray, sd: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(m)), (m - mu) / sd])


def controls_walk_forward(dates: list[str], fwd: ArrayLike, controls: ArrayLike, horizon: int,
                          first_year: int = 2012) -> dict:
    """Yearly refit OLS of fwd on controls; out-of-sample hit rate and R² vs the drift."""
    y = np.asarray(fwd, dtype=float)
    x = np.asarray(controls, dtype=float)
    years = np.array([int(d[:4]) for d in dates])
    ok = np.isfinite(y) & np.isfinite(x).all(axis=1)
    preds = np.full(len(y), np.nan)
    drift = np.full(len(y), np.nan)
    for year in range(first_year, years.max() + 1):
        test = ok & (years == year)
        if not test.any():
            continue
        first_test = int(np.argmax(years == year))
        train = ok.copy()
        train[max(0, first_test - horizon + 1):] = False  # outcome known before the year starts
        if train.sum() < MIN_ROWS:
            continue
        mu, sd = x[train].mean(axis=0), x[train].std(axis=0)
        sd[sd == 0] = 1.0
        coef, *_ = np.linalg.lstsq(_with_intercept(x[train], mu, sd), y[train], rcond=None)
        preds[test] = _with_intercept(x[test], mu, sd) @ coef
        drift[test] = y[train].mean()
    mask = np.isfinite(preds)
    if not mask.any():
        return {"status": "insufficient"}
    yt, pt, dt_ = y[mask], preds[mask], drift[mask]
    calls = np.sign(pt - dt_)
    p_up = float((yt > 0).mean())
    return {
        "status": "ok",
        "n": int(mask.sum()),
        "hit_rate": float((np.sign(yt) == calls)[calls != 0].mean()),
        "baseline": float(np.where(calls > 0, p_up, 1 - p_up)[calls != 0].mean()),
        "oos_r2": float(1 - ((yt - pt) ** 2).sum() / ((yt - dt_) ** 2).sum()),
        "excess": float(np.mean(calls * (yt - yt.mean()))),
    }


def run(n_perm: int = st.N_PERMUTATIONS, horizons: tuple[int, ...] = (1, 5, 20)) -> dict:
    """Partial-effect test of every rule and analog variant, plus the controls' own skill."""
    import datetime as dt

    from sbc import analog_validation as av
    from sbc import analogs as an
    from sbc import fingerprint_store
    from sbc import market_features as mf
    from sbc.rule_signals import RULES, signals_for

    history = an.load_nifty_history()
    dates, closes = history.dates, history.closes
    controls = mf.nifty_controls(dates, closes)
    fps = fingerprint_store.get_range(dates[0], dates[-1])
    by_date = {fp["date"]: fp for fp in fps}
    rule_signals = signals_for([by_date.get(d) or fingerprint_store.get(d) for d in dates])
    analog_signals, _ = av.walk_forward(history)
    analog_start = int(np.searchsorted(dates, av.START))

    entries = [(r.name, r.description, {h: np.asarray(rule_signals[r.name], dtype=float) for h in horizons})
               for r in RULES]
    for name, by_h in analog_signals.items():
        masked = {}
        for h in horizons:
            sig = by_h[h].astype(float)
            sig[:analog_start] = np.nan  # no walk-forward forecast before START
            masked[h] = sig
        entries.append((name, av.DESCRIPTIONS[name], masked))

    results, skill = [], {}
    for h in horizons:
        fwd = st.forward_returns(closes, h)
        skill[str(h)] = controls_walk_forward(dates, fwd, controls, h)
        for name, desc, by_h in entries:
            res = partial_effect(by_h[h], fwd, controls, n_perm=n_perm)
            results.append({"rule": name, "description": desc, "horizon": h, **res})
    qs = st.bh_adjust([r.get("p", float("nan")) for r in results])
    for r, q in zip(results, qs, strict=True):
        r["q"] = q
        r["verdict"] = ("insufficient" if r["status"] != "ok"
                        else "adds information" if q < 0.05 else "nothing beyond the market")
    return {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "fingerprint_version": fingerprint_store.current_version(),
        "controls": list(mf.CONTROL_NAMES),
        "sample": {"first": dates[0], "last": dates[-1], "sessions": len(dates)},
        "n_permutations": n_perm,
        "horizons": list(horizons),
        "controls_skill": skill,
        "results": results,
    }
