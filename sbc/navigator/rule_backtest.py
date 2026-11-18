"""Walk-forward test of the Today card's stance rule (rule-1) against the same rule
without its astro gate (trend-only, fixed half size). Sides are trend-Up days
(long) and trend-Down days (short); rule excess on a side is rule net P&L minus
control net P&L over that side's days, so it measures what the gate adds.
Verdict fixed in code before results; a sample chart never qualifies.
Pure: no store, no I/O. Entry at the session open; trend and VIX use the T-1 close."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, cast

import numpy as np
import pandas as pd

from sbc import stats
from sbc.navigator import backtest as B
from sbc.navigator import decision as D
from sbc.navigator import scoring as S
from sbc.navigator import weights as W
from sbc.navigator.ephemeris import SkyTable, build_sky
from sbc.navigator.profile import Profile

DEFAULT_PARAMS = {"cost_bps": 10, "n_placebo": 200, "seed": 1729, "n_perm": stats.N_PERMUTATIONS,
                  "min_sessions": W.HIST_MIN_YEARS * 252, "time_limit_s": 600}
SIDES = ("long", "short")
HORIZONS = ("oc", "oo1")
NOTES = [
    "Sides are trend-Up days (long) and trend-Down days (short). Excess is rule-1 net "
    "P&L minus the trend-only control's net P&L over the side's days.",
    "P-values are one-sided, from circular shifts of the astro gate, then Benjamini-Hochberg "
    "adjusted across sides and horizons.",
    D.SHORT_COST_NOTE,
]


def market_codes(days: list[str], closes: Any, vix: Mapping[str, float]) -> tuple[np.ndarray, np.ndarray]:
    """trend[t] in {+1, -1, 0} and vixfac[t] in {0.5, 1.0}, both from the T-1 close."""
    closes = np.asarray(closes, float)
    pcts = S.vol_percentiles_with_lead_in(list(days), dict(vix))
    trend, vixfac = np.zeros(len(days)), np.ones(len(days))
    for t in range(1, len(days)):
        trend[t] = {"Up": 1.0, "Down": -1.0}.get(D.trend_of(closes[:t]), 0.0)
        vixfac[t] = 0.5 if D._regime(float(pcts[t])) == "High" else 1.0
    return trend, vixfac


def gate(scores: Any) -> np.ndarray:
    return np.array([D.BAND_MULT.get(S.band_of(int(s)), 0.0) for s in np.rint(np.asarray(scores, float))])


def _pnl(mult: np.ndarray, sign: np.ndarray, r: np.ndarray, cost_bps: float) -> np.ndarray:
    return np.where(mult > 0, mult * (sign * r - cost_bps / 1e4), 0.0)


def _excess_series(gate_arr, trend, vixfac, r, cost_bps, sized=False):
    """Size-neutral by default: an open gate trades 1 unit against the control's 1 unit,
    so the excess isolates trade-or-stand-aside. sized=True uses the band multipliers
    against CONTROL_MULT and is reported only descriptively: in a drifting market,
    bigger size alone would look like an edge."""
    on = trend != 0
    rule_mult = (gate_arr if sized else (gate_arr > 0).astype(float)) * vixfac * on
    ctrl_mult = (D.CONTROL_MULT if sized else 1.0) * vixfac * on
    return _pnl(rule_mult, trend, r, cost_bps) - _pnl(ctrl_mult, trend, r, cost_bps)


def side_excess(gate_arr, trend, vixfac, r, cost_bps, side_mask, sized=False) -> float:
    x = _excess_series(gate_arr, trend, vixfac, r, cost_bps, sized)[side_mask]
    x = x[np.isfinite(x)]
    return float(x.mean()) if x.size else float("nan")


def side_stats(gate_arr, trend, vixfac, r, cost_bps, side_mask, n_perm, seed) -> dict[str, Any]:
    observed = side_excess(gate_arr, trend, vixfac, r, cost_bps, side_mask)
    if not np.isfinite(observed):
        p = float("nan")
    elif observed <= 0:
        p = 1.0
    else:
        p = stats.shift_pvalue(np.asarray(gate_arr, float), r,
                               lambda s, v: max(side_excess(s, trend, vixfac, v, cost_bps, side_mask), 0.0),
                               observed, n_perm, seed)
    days = int((side_mask & np.isfinite(r)).sum())
    return {"excess": observed, "p": p, "days": days, "events": B.count_events(side_mask & np.isfinite(r))}


def _folds(years, gate_arr, trend, vixfac, outcomes, cost_bps):
    folds, positive, active = [], np.zeros((2, len(outcomes))), np.zeros((2, len(outcomes)))
    for year in sorted(set(years)):
        f = years == year
        row: dict[str, Any] = {"year": year, "sessions": int(f.sum())}
        for s, side in enumerate(SIDES):
            mask = f & ((trend > 0) if side == "long" else (trend < 0))
            for h, r in enumerate(outcomes):
                value = side_excess(gate_arr, trend, vixfac, r, cost_bps, mask)
                row[f"{side}_{HORIZONS[h]}"] = value
                if int((mask & np.isfinite(r)).sum()) >= B.MIN_FOLD_DAYS and np.isfinite(value):
                    active[s, h] += 1
                    positive[s, h] += value > 0
        folds.append(row)
    with np.errstate(invalid="ignore"):
        share = np.where(active >= B.MIN_FOLDS, positive / active, np.nan)
    return folds, share, active


def _verdict(entry: Mapping[str, Any], is_sample: bool) -> str:
    q, pct, fold_pos = entry.get("q"), entry.get("pct"), entry.get("fold_pos")
    ok = (q is not None and pct is not None and fold_pos is not None and np.isfinite(q)
          and q < .10 and entry["excess"] > 0 and pct >= 95
          and entry["events"] >= B.MIN_EVENTS and fold_pos >= .60)
    return B.EDGE if ok and not is_sample else B.NO_EDGE


def run_inputs(inputs: B.Inputs, params: Mapping | None = None,
               on_progress: Callable[[int, int], None] | None = None) -> dict[str, Any]:
    p = {**DEFAULT_PARAMS, **(params or {})}
    cost, is_sample = p["cost_bps"], bool(inputs.profile.is_sample)
    days, opens, closes = B._prices(inputs.ohlc)
    start = min(p["min_sessions"], len(days))
    trend_all, vixfac_all = market_codes(days, closes, B._vix_map(inputs.vix))
    oo1 = np.full(len(opens), np.nan)
    oo1[:-1] = opens[1:] / opens[:-1] - 1
    outcomes = [(closes / opens - 1)[start:], oo1[start:]]
    trend, vixfac = trend_all[start:], vixfac_all[start:]
    years = np.array([d[:4] for d in days[start:]])

    def excesses(series) -> np.ndarray:
        g = gate(series.score[start:])
        return np.array([[side_excess(g, trend, vixfac, r, cost, (trend > 0) if side == "long" else (trend < 0))
                          for r in outcomes] for side in SIDES])

    series = B.score_for(inputs, p["min_sessions"])
    g = gate(series.score[start:])
    real = excesses(series)
    rows, pvals = {}, []
    for s, side in enumerate(SIDES):
        mask = (trend > 0) if side == "long" else (trend < 0)
        for h, r in enumerate(outcomes):
            st = side_stats(g, trend, vixfac, r, cost, mask, p["n_perm"], p["seed"] + 10 * s + h)
            rows[(side, h)] = st
            pvals.append(st["p"])
    qs = stats.bh_adjust(pvals)
    folds, fold_pos, active = _folds(years, g, trend, vixfac, outcomes, cost)

    charts = B.draw_placebos(p["n_placebo"], p["seed"])
    target, placebo, began = len(charts), [], B._clock()
    while len(placebo) < target:
        placebo.append(excesses(B.score_for(inputs._replace(profile=charts[len(placebo)]), p["min_sessions"])))
        rate = (B._clock() - began) / len(placebo)
        if len(placebo) >= B.RATE_CHECK_AFTER and rate * target > p["time_limit_s"]:
            target = max(len(placebo), int(p["time_limit_s"] / rate))
        if on_progress:
            on_progress(len(placebo), target)
    pl = np.array(placebo).reshape(len(placebo), len(SIDES), len(outcomes))

    sides: dict[str, Any] = {}
    for s, side in enumerate(SIDES):
        by_h = {}
        for h, name in enumerate(HORIZONS):
            st = rows[(side, h)]
            mask = (trend > 0) if side == "long" else (trend < 0)
            entry = {**st, "q": qs[s * len(HORIZONS) + h],
                     "sized_excess": side_excess(g, trend, vixfac, outcomes[h], cost, mask, sized=True),
                     "pct": B.percentile(real[s, h], pl[:, s, h]),
                     "fold_pos": float(fold_pos[s, h]) if np.isfinite(fold_pos[s, h]) else None,
                     "active_folds": int(active[s, h])}
            entry["verdict"] = _verdict(entry, is_sample)
            by_h[name] = entry
        best = min(by_h, key=lambda k: (by_h[k]["verdict"] != B.EDGE,
                                        by_h[k]["q"] if np.isfinite(by_h[k]["q"]) else 2.0))
        sides[side] = {"verdict": by_h[best]["verdict"], "best_horizon": best, "by_horizon": by_h}
    return cast(dict[str, Any], B.clean_json({
        "kind": "rule", "rule_version": D.RULE_VERSION, "sides": sides, "folds": folds,
        "placebo": {"n": len(placebo), "requested": p["n_placebo"], "reduced": len(placebo) < p["n_placebo"],
                    "seed": p["seed"]},
        "is_sample": is_sample, "label": B.label_for(is_sample), "notes": NOTES,
        "sessions_scored": len(days) - start, "weights_version": W.WEIGHTS_VERSION, "params": p}))


def run(profile: Profile, ohlc: pd.DataFrame, vix: Any, sky: SkyTable | None = None,
        params: Mapping | None = None,
        on_progress: Callable[[int, int], None] | None = None) -> dict[str, Any]:
    sky = sky if sky is not None else build_sky(B._prices(ohlc)[0])
    return run_inputs(B.Inputs(profile, ohlc, vix, sky), params, on_progress)
