"""Walk-forward band backtest with controls, placebo charts and a verdict fixed in
code before any result was seen. It must be able to say "no demonstrated edge".

Timing: entry is day T's open; T-1's close is the last input. HistVal only ever
reads scoring.forward_returns (open(t) to close(t+h-1)), whose embargo depends on
that definition. The open-to-open returns here are outcomes for band metrics and
must never be passed to hist_val.

Pure: no store import, no I/O. Results are JSON-safe (NaN becomes None).
"""
from __future__ import annotations
import datetime as dt
import math
import time
from typing import Callable, Mapping, NamedTuple, Optional
import numpy as np
import pandas as pd
from sbc import stats
from sbc.navigator import scoring as S
from sbc.navigator import weights as W
from sbc.navigator.ephemeris import SkyTable, build_sky
from sbc.navigator.profile import Profile

DEFAULT_PARAMS = {"cost_bps": 10, "n_placebo": 200, "seed": 1729, "horizons": [1, 5],
                  "min_events": 30, "min_sessions": W.HIST_MIN_YEARS * 252,
                  "n_perm": stats.N_PERMUTATIONS, "time_limit_s": 600}
EDGE, NO_EDGE = "edge candidate", "no demonstrated edge"
BAND_NAMES = [name for _, name in S.BANDS]
MIN_EVENTS = 30             # the verdict's floor; the `min_events` param only sets the label
MIN_NATAL_DAYS = 30         # natal-band days the real chart needs for its percentile to mean anything
MIN_FOLD_DAYS = 5           # band sessions with a forward return a fold needs to count
MIN_FOLDS = 3               # active folds needed before fold_pos means anything
MIN_PLACEBOS = 20           # with fewer, a 95th percentile cannot be told apart
RATE_CHECK_AFTER = 10       # charts timed before projecting the run
NOTES = [
    "The natal percentile is measured on natal-band days: sessions where the natal-only "
    "sub-score falls in the band, not the full score. The real chart needs at least 30.",
    "Excess is the band mean against the all-session mean, which includes the band itself, "
    "so it is diluted by how much of the sample the band occupies.",
    "P-values are one-sided (upside only), net of cost, then Benjamini-Hochberg adjusted "
    "across bands and horizons.",
]
SESSION_STATS = ("days", "vol", "max_dd", "hit", "win", "sharpe")
_EDGES = [hi for hi, _ in S.BANDS[:-1]]
_PLACEBO_START = dt.datetime(1950, 1, 1, tzinfo=dt.timezone.utc)
_PLACEBO_SPAN = (dt.datetime(2006, 1, 1, tzinfo=dt.timezone.utc) - _PLACEBO_START).total_seconds()
_clock = time.perf_counter


class Inputs(NamedTuple):
    profile: Profile
    ohlc: pd.DataFrame          # sessions in the index or a `date` column
    vix: Mapping[str, float]    # includes sessions before the first ohlc day
    sky: SkyTable


def count_events(mask) -> int:
    """Consecutive days are one event."""
    mask = np.asarray(mask, bool)
    return int(mask[0]) + int((mask[1:] & ~mask[:-1]).sum()) if mask.size else 0


def net(r, cost_bps):
    return r - cost_bps / 10000.0


def open_returns(opens, horizon: int) -> np.ndarray:
    """r[t] = open[t+horizon] / open[t] - 1. Outcomes only: never for hist_val."""
    opens = np.asarray(opens, float)
    out = np.full(len(opens), np.nan)
    m = len(opens) - horizon
    if m > 0:
        out[:m] = opens[horizon:] / opens[:m] - 1
    return out


def prior_returns(closes) -> np.ndarray:
    """prior[t] is the T-1 session's own return: close[t-1] / close[t-2] - 1."""
    closes = np.asarray(closes, float)
    out = np.full(len(closes), np.nan)
    out[2:] = closes[1:-1] / closes[:-2] - 1
    return out


def matched_control_mean(mask, prior, fwd) -> float:
    """Non-band sessions in the same decile of the T-1 session's return, weighted
    by the band's sessions in each decile."""
    mask, prior, fwd = np.asarray(mask, bool), np.asarray(prior, float), np.asarray(fwd, float)
    ok = np.isfinite(prior) & np.isfinite(fwd)
    if not ok.any():
        return float("nan")
    decile = np.digitize(prior, np.quantile(prior[ok], np.linspace(.1, .9, 9)))
    means, weights = [], []
    for d in range(10):
        here = ok & (decile == d)
        band, control = (here & mask).sum(), here & ~mask
        if band and control.any():
            means.append(fwd[control].mean())
            weights.append(band)
    return float(np.average(means, weights=weights)) if means else float("nan")


def verdict(b: Mapping, is_sample: bool) -> str:
    """Spec rule. Missing or NaN evidence fails. A sample chart never qualifies."""
    q, pct, folds = b.get("q"), b.get("natal_pct"), b.get("fold_pos")
    natal_days = b.get("natal_band_days")
    ok = (q is not None and pct is not None and folds is not None
          and natal_days is not None and natal_days >= MIN_NATAL_DAYS
          and q < .10 and bool(b["beats_control"]) and pct >= 95
          and b["events"] >= MIN_EVENTS and folds >= .60)
    return EDGE if ok and not is_sample else NO_EDGE


def percentile(real: float, placebos) -> Optional[float]:
    """Share of placebos strictly below the real chart, 0-100. Placebos with no
    sessions in the band are dropped; None if too few remain."""
    placebos = np.asarray(placebos, float)
    placebos = placebos[np.isfinite(placebos)]
    if not np.isfinite(real) or len(placebos) < MIN_PLACEBOS:
        return None
    return float(100.0 * np.mean(placebos < real))


def _band_index(scores) -> np.ndarray:
    return np.digitize(np.rint(np.asarray(scores, float)), _EDGES, right=True)


def _net_excess(mask, values, cost_bps) -> float:
    """In-band mean minus the mean of all sessions, then the cost of the band's trades."""
    return stats.excess_stat(np.asarray(mask, float), values) - cost_bps / 10000.0


def _p_value(mask, values, cost_bps, n_perm, seed) -> float:
    """One-sided: can this band's net excess be told from chance on the upside?
    Rotations of the gross statistic are the null, centred on zero, so an edge the
    size of the cost scores as none. Two-sided would make every idle band
    "significant" at minus the cost and flatter the BH ranks of the others."""
    observed = _net_excess(mask, values, cost_bps)
    if not np.isfinite(observed):    # shift_pvalue would report 1/(n+1) for a NaN statistic
        return float("nan")
    if observed <= 0:
        return 1.0
    return stats.shift_pvalue(np.asarray(mask, float), values,
                              lambda s, v: max(stats.excess_stat(s, v), 0.0),
                              observed, n_perm, seed)


def _max_drawdown(r) -> float:
    curve = np.concatenate(([1.0], np.cumprod(1 + r)))
    return float((curve / np.maximum.accumulate(curve) - 1).min())


def _run_totals(mask, netted) -> np.ndarray:
    """Summed net return of each run of consecutive in-band sessions."""
    runs = np.cumsum(np.concatenate(([mask[0]], mask[1:] & ~mask[:-1])))
    usable = mask & np.isfinite(netted)
    return np.bincount(runs[usable] - 1, weights=netted[usable])


def _band_row(mask, returns, prior, cost_bps, n_perm, seed, min_events) -> dict:
    netted = net(returns, cost_bps)
    picked = netted[mask & np.isfinite(netted)]
    usable = mask & np.isfinite(returns)       # tail sessions have no forward return
    events = count_events(usable)
    nan = float("nan")
    row = {"days": int(mask.sum()), "events": events, "insufficient": events < min_events,
           "mean": nan, "vol": nan, "max_dd": nan, "hit": nan, "win": nan, "sharpe": nan,
           "excess": _net_excess(mask, returns, cost_bps), "excess_vs_control": nan,
           "p": _p_value(mask, returns, cost_bps, n_perm, seed)}
    if not len(picked):
        return row
    std = picked.std()
    row.update(mean=float(picked.mean()), vol=float(std), max_dd=_max_drawdown(picked),
               hit=float((picked > 0).mean()), win=float((_run_totals(usable, netted) > 0).mean()),
               sharpe=float(picked.mean() / std * math.sqrt(252)) if std > 0 else nan)
    if prior is not None:
        # The cost falls on the band's trades only; the control is the market's own return.
        row["excess_vs_control"] = row["mean"] - matched_control_mean(mask, prior, returns)
    return row


def band_stats(scores, returns, prior=None, cost_bps=10, n_perm=stats.N_PERMUTATIONS,
               seed=0, min_events=30) -> dict:
    """Per-band metrics net of cost. `excess` is net of the all-session mean; `p`
    is circular-shift on that. `hit` is the share of positive sessions, `win` the
    share of positive events. Drawdown is meaningful for one-session returns only."""
    returns = np.asarray(returns, float)
    index = _band_index(scores)
    return {name: _band_row(index == k, returns, prior, cost_bps, n_perm, seed + k, min_events)
            for k, name in enumerate(BAND_NAMES)}


def _prices(ohlc: pd.DataFrame):
    days = ohlc["date"] if "date" in ohlc.columns else ohlc.index
    return [str(d)[:10] for d in days], ohlc["open"].to_numpy(float), ohlc["close"].to_numpy(float)


def _vix_map(vix) -> dict:
    return vix.to_dict() if isinstance(vix, pd.Series) else dict(vix)


def score_for(inputs: Inputs, min_sessions: int = 756) -> S.ScoreSeries:
    """Score every session. The VIX map's earlier sessions are the Vol lead-in;
    days without that history are neutral and flagged in their factors."""
    days, opens, closes = _prices(inputs.ohlc)
    if days != list(inputs.sky.days):
        raise ValueError("ohlc sessions must match sky.days")
    return S.score_series(inputs.sky, inputs.profile, opens, closes, _vix_map(inputs.vix),
                          min_sessions=min_sessions)


def natal_subscore(series: S.ScoreSeries) -> np.ndarray:
    """Mean of Transit, Dasha and Strength; Moon and Vol are common to all charts."""
    return (series.terms["transit"] + series.terms["dasha"] + series.terms["strength"]) / 3.0


def draw_placebos(n: int, seed: int) -> list[Profile]:
    """Births uniform over 1950-2005 with random locations. Each draw depends only
    on its position, so a shortened run is a prefix of the full one."""
    out = []
    for when, lat, lon in np.random.default_rng(seed).random((n, 3)):
        at = _PLACEBO_START + dt.timedelta(seconds=int(when * _PLACEBO_SPAN))
        out.append(Profile("placebo", True, at.strftime("%Y-%m-%d"), at.strftime("%H:%M:%S"),
                           "UTC", float(lat * 120 - 60), float(lon * 360 - 180)))
    return out


def _excess_table(scores, outcomes, start, cost_bps) -> np.ndarray:
    """Net excess by band and horizon on the scored sessions."""
    index = _band_index(scores)[start:]
    return np.array([[_net_excess(index == k, r[start:], cost_bps) for r in outcomes]
                     for k in range(len(BAND_NAMES))])


def _run_placebos(inputs, p, start, outcomes, on_progress):
    """Same score_series and same statistic as the real chart. Returns the full and
    natal excess tables (chart, band, horizon) and the disclosure fields."""
    charts = draw_placebos(p["n_placebo"], p["seed"])
    target = len(charts)
    full, natal = [], []
    done, elapsed = 0, 0.0
    began = _clock()
    while done < target:
        series = score_for(inputs._replace(profile=charts[done]), p["min_sessions"])
        full.append(_excess_table(series.score, outcomes, start, p["cost_bps"]))
        natal.append(_excess_table(natal_subscore(series), outcomes, start, p["cost_bps"]))
        done += 1
        elapsed = _clock() - began
        rate = elapsed / done
        if done >= RATE_CHECK_AFTER and rate * target > p["time_limit_s"]:
            target = max(done, int(p["time_limit_s"] / rate))
        if on_progress:
            on_progress(done, target)
    shape = (done, len(BAND_NAMES), len(outcomes))
    info = {"n": done, "requested": p["n_placebo"], "reduced": done < p["n_placebo"],
            "seconds": elapsed, "seed": p["seed"]}
    return np.array(full).reshape(shape), np.array(natal).reshape(shape), info


def _folds(index, years, outcomes, horizons, cost_bps):
    """One test year per fold, from the first scored year. fold_pos[k, h] is the
    share of active folds (at least MIN_FOLD_DAYS band sessions with a forward return)
    that had positive net excess, NaN under MIN_FOLDS. Returns (folds, fold_pos, active)."""
    positive = np.zeros((len(BAND_NAMES), len(horizons)))
    active = np.zeros_like(positive)
    folds = []
    for year in sorted(set(years)):
        fold = years == year
        bands = {}
        for k, name in enumerate(BAND_NAMES):
            mask = index[fold] == k
            row = {"days": int(mask.sum())}
            for h, r in enumerate(outcomes):
                value = _net_excess(mask, r[fold], cost_bps)
                row[f"excess_{horizons[h]}"] = value
                counts = int((mask & np.isfinite(r[fold])).sum()) >= MIN_FOLD_DAYS
                if counts and np.isfinite(value):
                    active[k, h] += 1
                    positive[k, h] += value > 0
            bands[name] = row
        folds.append({"year": year, "sessions": int(fold.sum()), "bands": bands})
    with np.errstate(invalid="ignore"):
        share = np.where(active >= MIN_FOLDS, positive / active, np.nan)
    return folds, share, active


def _clean(x):
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (float, np.floating)):
        return float(x) if np.isfinite(x) else None
    return int(x) if isinstance(x, np.integer) else x


def _top_band(bands, min_events) -> int:
    """Highest band with enough events, else the highest with any days. `bands` is
    one fixed horizon's rows: a best-horizon row would let returns pick the band."""
    order = range(len(BAND_NAMES) - 1, -1, -1)
    for test in (lambda b: b["events"] >= min_events, lambda b: b["days"] > 0):
        for k in order:
            if test(bands[BAND_NAMES[k]]):
                return k
    return len(BAND_NAMES) - 1


def run_inputs(inputs: Inputs, params: Optional[Mapping] = None,
               on_progress: Optional[Callable[[int, int], None]] = None) -> dict:
    p = {**DEFAULT_PARAMS, **(params or {})}
    cost, horizons = p["cost_bps"], list(p["horizons"])
    is_sample = bool(inputs.profile.is_sample)
    series = score_for(inputs, p["min_sessions"])
    days, opens, closes = _prices(inputs.ohlc)
    start = min(p["min_sessions"], len(days))
    outcomes = [open_returns(opens, h) for h in horizons]
    scored = [r[start:] for r in outcomes]
    prior = prior_returns(closes)[start:]
    scores = series.score[start:]
    index = _band_index(scores)
    oc = net((closes / opens - 1)[start:], cost)

    per_horizon = [band_stats(scores, r, prior, cost, p["n_perm"], p["seed"] + 100 * (h + 1),
                              p["min_events"]) for h, r in enumerate(scored)]
    qs = stats.bh_adjust([row[name]["p"] for row in per_horizon for name in BAND_NAMES])
    folds, fold_pos, active = _folds(index, np.array([d[:4] for d in days[start:]]), scored, horizons, cost)

    real_full = _excess_table(series.score, outcomes, start, cost)
    real_natal = _excess_table(natal_subscore(series), outcomes, start, cost)
    natal_index = _band_index(natal_subscore(series))[start:]
    # counted on the statistic's own mask: sessions with a finite forward return
    natal_days = [np.bincount(natal_index[np.isfinite(r)], minlength=len(BAND_NAMES))
                  for r in scored]
    full, natal, placebo = _run_placebos(inputs, p, start, outcomes, on_progress)

    bands, candidates, by_band = {}, [], {}
    first_horizon = str(horizons[0])
    for k, name in enumerate(BAND_NAMES):
        by_horizon, by_band[name] = {}, {}
        for h, horizon in enumerate(horizons):
            row = per_horizon[h][name]
            pct = {"full": percentile(real_full[k, h], full[:, k, h]),
                   "natal": percentile(real_natal[k, h], natal[:, k, h])}
            by_band[name][str(horizon)] = pct
            entry = {"p": row["p"], "q": qs[h * len(BAND_NAMES) + k], "excess": row["excess"],
                     "excess_vs_control": row["excess_vs_control"],
                     "beats_control": bool(row["excess_vs_control"] > 0), "events": row["events"],
                     "insufficient": row["insufficient"], "active_folds": int(active[k, h]),
                     "fold_pos": float(fold_pos[k, h]) if np.isfinite(fold_pos[k, h]) else None,
                     "full_pct": pct["full"], "natal_pct": pct["natal"],
                     "natal_band_days": int(natal_days[h][k])}
            entry["verdict"] = verdict({**entry, "q": entry["q"] if np.isfinite(entry["q"]) else None},
                                       is_sample)
            by_horizon[str(horizon)] = entry
        # BH already covers every horizon, so the band shows its strongest one.
        best_h = min(by_horizon, key=lambda x: (by_horizon[x]["verdict"] != EDGE,
                                                by_horizon[x]["q"] if np.isfinite(by_horizon[x]["q"]) else 2.0))
        best = by_horizon[best_h]
        first = per_horizon[0][name]
        mask = index == k
        # One-session figures: at longer horizons overlapping returns make these meaningless.
        band = {"session_stats": {"horizon": first_horizon,
                                  **{key: first[key] for key in SESSION_STATS}}}
        band["mean_oc"] = float(np.nanmean(oc[mask])) if np.isfinite(oc[mask]).any() else None
        for h, horizon in enumerate(horizons):
            band[f"mean_oo_{horizon}"] = per_horizon[h][name]["mean"]
        # events, insufficient, natal_band_days, p, q and verdict all come from this one horizon
        band.update({key: best[key] for key in ("events", "insufficient", "excess_vs_control",
                                                "p", "q", "verdict", "natal_band_days")})
        band["horizon"] = best_h
        band["by_horizon"] = by_horizon
        bands[name] = band
        for horizon, entry in by_horizon.items():
            if entry["verdict"] == EDGE:
                candidates.append({"band": name, "horizon": horizon, "q": entry["q"]})

    top = BAND_NAMES[_top_band(per_horizon[0], p["min_events"])]
    placebo.update(top_band=top, horizon=first_horizon, full_pct=by_band[top][first_horizon]["full"],
                   natal_pct=by_band[top][first_horizon]["natal"], by_band=by_band)
    return _clean({
        "bands": bands, "folds": folds, "placebo": placebo,
        "verdict": EDGE if candidates else NO_EDGE, "research_grade": not is_sample,
        "notes": NOTES,
        "candidates": candidates,
        "candidate_bands": list(dict.fromkeys(c["band"] for c in candidates)), "is_sample": is_sample,
        "label": ("Sample chart: pipeline check only" if is_sample
                  else "Research-grade result with hand-set weights"),
        "sessions_scored": len(scores),
        "vol_neutral_days": int(np.sum(series.terms["vol"][start:] == 50.0)),
        "weights_version": W.WEIGHTS_VERSION, "params": p,
    })


def run(profile: Profile, ohlc: pd.DataFrame, vix, sky: Optional[SkyTable] = None,
        params: Optional[Mapping] = None,
        on_progress: Optional[Callable[[int, int], None]] = None) -> dict:
    sky = sky if sky is not None else build_sky(_prices(ohlc)[0])
    return run_inputs(Inputs(profile, ohlc, vix, sky), params, on_progress)
