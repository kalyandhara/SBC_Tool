"""Validation: does the EMA 9/21 Heikin-Ashi matrix carry information?

PRE-REGISTERED before the run (frozen definitions; the report this
prints is written as-is, no tuning afterwards).  Grades the three
claims the 2026-10-27 gap analysis
(reports/mtf_ema_matrix_gap_analysis_2026-10-27.md) says the matrix
implies:

- C1 (fresh-cross follow-through): after a bar where EMA(9) crosses
  EMA(21) on HA closes, the close-to-close forward return over +1,
  +5 and +21 bars differs from random days of the same symbol.
- C2 (cross survival): P(the state 5 bars after a fresh cross still
  matches the cross direction).
- C3 (multi-timeframe alignment adds information): forward +21-bar
  returns when the daily state is bullish AND the weekly state is
  bullish vs daily-bullish alone (and the mirrored bearish reading).

Frozen scope:
- Universe: NIFTY 50 (`sbc.screener.universes.load("NIFTY 50")`).
- Frames: 1d (lookback 1500 calendar days), 1wk (700), 1h (730) -
  the deepest spans Yahoo serves; 5-15m are NOT tested (60 days is
  too thin for anything but description, per the gap analysis).
- Events: crosses on CLOSED bars; the bar's HA close is the entry;
  forward returns are close-to-close; the +21 window must fit inside
  the frame.
- Baseline: 10,000 permutations; each event is paired with a random
  day from the SAME symbol's frame (stratified), pooled mean; two-
  sided p = 2*min(P(rand>=obs), P(rand<=obs)), capped at 1.
- No parameter tuning: 9/21, +1/+5/+21, and these universes are the
  pre-registered choices.  A Bonferroni-style honest read across the
  printed cells belongs in the reading, not in re-running.

Example:
    python scripts/study_ema_ha_matrix.py
"""

import argparse
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from sbc.screener import data as screener_data  # noqa: E402
from sbc.screener.indicators import ema, heikin_ashi  # noqa: E402
from sbc.screener.universes import load  # noqa: E402

ITERS = 10_000
SEED = 42
FAST, SLOW = 9, 21
MINBARS = 22
HORIZONS = {"1d": (1, 5, 21), "1wk": (1, 2, 4), "1h": (1, 5, 21)}
LOOKBACK = {"1d": 1500, "1wk": 700, "1h": 730}


def diff_series(df_ha: pd.DataFrame) -> pd.Series:
    return (ema(df_ha["close"], FAST)
            > ema(df_ha["close"], SLOW)).astype(bool)


def events_and_outcomes(df_ha: pd.DataFrame, horizons: tuple) -> dict:
    """Cross events and random-day pools for one symbol's HA frame.

    Returns {direction: {'entry_idx': [...], 'fwd': {h: [...]}}} plus
    the full per-bar forward-return arrays under 'pool'.
    """
    diff = diff_series(df_ha).values
    closes = df_ha["close"].values
    n = len(df_ha)
    out: dict = {}
    for direction, want in (("up", True), ("down", False)):
        idx = [i for i in range(2, n - 1)
               if diff[i] == want and diff[i] != diff[i - 1]
               and i + max(horizons) < n]
        fwd = {h: [float(closes[i + h] / closes[i] - 1.0) for i in idx]
               for h in horizons}
        out[direction] = {"entry_idx": idx, "fwd": fwd}
    pool = {h: np.array([closes[i + h] / closes[i] - 1.0
                         for i in range(2, n - max(horizons))])
            for h in horizons}
    out["pool"] = pool
    out["n"] = n
    return out


def permuted(observed: float, pools: list[np.ndarray], counts: list[int],
             rng: np.random.Generator) -> float:
    """Two-sided p: redraw `counts[i]` random days from pools[i] per
    iteration, pooled mean vs observed."""
    if not counts or sum(counts) == 0:
        return float("nan")
    means = np.empty(ITERS)
    for it in range(ITERS):
        vals = []
        for pool, k in zip(pools, counts):
            if k:
                pick = rng.integers(0, len(pool), size=k)
                vals.append(pool[pick])
        means[it] = np.concatenate(vals).mean() if vals else np.nan
    p_ge = float((means >= observed).mean())
    p_le = float((means <= observed).mean())
    return min(1.0, 2 * min(p_ge, p_le))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=os.path.join(
        "reports", "ema_ha_matrix_validation_2026-10-27.md"))
    args = parser.parse_args()

    symbols = load("NIFTY 50")
    rng = np.random.default_rng(SEED)
    lines = ["# EMA 9/21 HA matrix - pre-registered validation",
             "",
             "Frozen before the run (module docstring).  Universe NIFTY 50; "
             "crosses on closed HA candles; forward returns close-to-close; "
             "baseline = 10,000 stratified permutations, two-sided p.",
             ""]

    for tf, horizons in HORIZONS.items():
        raw, errs = screener_data.batch(symbols, tf,
                                        lookback_days=LOOKBACK[tf])
        if not raw:
            lines.append(f"## {tf}: no data")
            continue
        ha_frames = {s: heikin_ashi(df) for s, df in raw.items()}
        per_sym = {s: events_and_outcomes(f, horizons)
                   for s, f in ha_frames.items()}
        lines.append(f"## {tf} - C1: fresh-cross follow-through "
                     f"({len(raw)} symbols)")
        lines.append("")
        lines.append("| direction | h | events | mean % | random mean % | p |")
        lines.append("|---|---|---|---|---|---|")
        for direction in ("up", "down"):
            for h in horizons:
                obs_vals = []
                pools, counts = [], []
                for s in raw:
                    ev = per_sym[s][direction]
                    obs_vals.extend(ev["fwd"][h])
                    pools.append(per_sym[s]["pool"][h])
                    counts.append(len(ev["fwd"][h]))
                if not obs_vals:
                    continue
                obs = float(np.mean(obs_vals))
                p = permuted(obs, pools, counts, rng)
                rand = float(np.mean([np.mean(p_) for p_ in pools
                                      if len(p_)]))
                lines.append(
                    f"| {'cross up' if direction == 'up' else 'cross down'} "
                    f"| +{h} | {len(obs_vals)} | {obs * 100:+.2f} "
                    f"| {rand * 100:+.2f} | {p:.3f} |")
        lines.append("")

        # C2: survival 5 bars after a fresh cross
        for direction in ("up", "down"):
            surv, tot = 0, 0
            want = direction == "up"
            for s in raw:
                diff = diff_series(ha_frames[s]).values
                for i in per_sym[s][direction]["entry_idx"]:
                    if i + 5 < len(diff):
                        tot += 1
                        surv += int(bool(diff[i + 5]) == want)
            if tot:
                lines.append(f"- C2 survival ({'up' if want else 'down'}): "
                             f"{surv}/{tot} = {surv / tot * 100:.1f}% still "
                             f"{'bullish' if want else 'bearish'} 5 bars "
                             f"after the cross")
        lines.append("")

        if tf == "1d":
            # C3: alignment conditioning (daily x weekly state)
            wk_raw, _ = screener_data.batch(symbols, "1wk", lookback_days=700)
            wk_state = {}
            for s, dfw in wk_raw.items():
                hw = heikin_ashi(dfw)
                if len(hw) >= MINBARS:
                    wk_state[s] = bool(diff_series(hw).iloc[-1])
            lines.append("## C3: daily+weekly alignment vs daily alone "
                         "(+21 sessions)")
            lines.append("")
            lines.append("| conditioning | days | mean % | p |")
            lines.append("|---|---|---|---|")
            groups = {"daily bullish": [], "daily+weekly bullish": [],
                      "daily bearish": [], "daily+weekly bearish": []}
            pools_c = {"daily bullish": [], "daily+weekly bullish": [],
                       "daily bearish": [], "daily+weekly bearish": []}
            for s, dfh in ha_frames.items():
                d = diff_series(dfh).values
                closes = dfh["close"].values
                n = len(closes)
                pool = np.array([closes[i + 21] / closes[i] - 1.0
                                 for i in range(2, n - 21)])
                for i in range(2, n - 21):
                    if d[i]:
                        groups["daily bullish"].append(
                            closes[i + 21] / closes[i] - 1.0)
                        pools_c["daily bullish"].append(pool)
                        if wk_state.get(s, d[i]) is True:
                            groups["daily+weekly bullish"].append(
                                closes[i + 21] / closes[i] - 1.0)
                            pools_c["daily+weekly bullish"].append(pool)
                    else:
                        groups["daily bearish"].append(
                            closes[i + 21] / closes[i] - 1.0)
                        pools_c["daily bearish"].append(pool)
                        if wk_state.get(s, d[i]) is False:
                            groups["daily+weekly bearish"].append(
                                closes[i + 21] / closes[i] - 1.0)
                            pools_c["daily+weekly bearish"].append(pool)
            for label, vals in groups.items():
                if len(vals) < 30:
                    continue
                obs = float(np.mean(vals))
                pooled = (np.concatenate(pools_c[label])
                          if pools_c[label] else np.array([]))
                p = permuted(obs, [pooled], [len(vals)], rng)
                lines.append(f"| {label} | {len(vals)} | {obs * 100:+.2f} "
                             f"| {p:.3f} |")
            lines.append("")

    if errs:
        lines.append(f"Download errors: {len(errs)} symbols skipped "
                     f"(first few: {list(errs.items())[:3]})")
    lines.append("")
    lines.append("Reading: a cell is interesting only if it survives the "
                 "honest read across the printed cells; the matrix's "
                 "value as a DISPLAY does not depend on any of these "
                 "cells being significant, only its value as a SIGNAL "
                 "does.")
    report = "\n".join(lines) + "\n"
    print(report)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(f"saved: {args.out}")


if __name__ == "__main__":
    main()
