"""Run the pre-registered Crash Cluster Index test once (NIFTY primary, DJIA replication).

Registration: docs/research/crash_cluster_index_preregistration_2026-11-19.md. Every number
below (horizons, outcomes, eras, cost, iterations, seeds, placebos, pass rule) comes from it;
don't change them here. Prints a markdown results block to stdout.

    venv/Scripts/python.exe scripts/validate_crash_cluster.py
"""

import csv
import hashlib
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from sbc import crash_cluster as cc  # noqa: E402
from sbc import planetary_event_timeline as pet  # noqa: E402
from sbc.stats import bh_adjust  # noqa: E402

HORIZONS = (5, 20)
OUTCOMES = {"fwd_return": -1, "max_drawdown": -1, "realized_vol": +1}  # expected sign of excess
COST = 0.002
ERA_SPLIT = "2015-01-01"
ITERS, SEED = 10_000, 42
PLACEBO_LAGS, PLACEBO_ITERS = 20, 2_000
MIN_EPISODES = 15
ALPHA = 0.05
FILES = {"NIFTY": "data/nifty_ohlc.csv", "DJIA": "data/djia_ohlc.csv"}


def load(path):
    dates, closes = [], []
    with open(os.path.join(_ROOT, path), newline="") as f:
        for row in csv.DictReader(f):
            try:
                c = float(row["Close"])
            except (TypeError, ValueError):
                continue
            if np.isfinite(c) and c > 0:
                dates.append(row["Date"][:10])
                closes.append(c)
    return dates, np.array(closes)


def outcome(closes, name, h):
    if name == "fwd_return":
        return pet.forward_returns(closes, h)
    if name == "max_drawdown":
        return pet.max_drawdown(closes, h)
    return pet.realized_volatility(closes, h)


def era_excess(arr, labels, ev, mask):
    return pet.excess_statistic(arr, labels, ev & mask, ctrl=~ev & mask)


def tests(dates, closes, ev, iters):
    labels = pet.decile_labels(pet.same_day_returns(closes))
    d = np.array(dates)
    early, late = d < ERA_SPLIT, d >= ERA_SPLIT
    rows = []
    for name, sign in OUTCOMES.items():
        for h in HORIZONS:
            arr = outcome(closes, name, h)
            stat = pet.excess_statistic(arr, labels, ev)
            p = pet.permutation_p(arr, labels, ev, stat, iters=iters, seed=SEED)
            rows.append({"outcome": name, "h": h, "sign": sign, "excess": stat, "p": p,
                         "early": era_excess(arr, labels, ev, early),
                         "late": era_excess(arr, labels, ev, late)})
    for r, q in zip(rows, bh_adjust([r["p"] for r in rows]), strict=True):
        r["q"] = q
    return rows


def hash_events(dates, n_target, monthly):
    keys = [d[:7] if monthly else d for d in dates]
    universe = len(set(keys))
    k = max(1, round(256 * n_target / universe))
    flags = np.array([hashlib.sha256(x.encode()).digest()[0] < k for x in keys])
    return pet.episode_starts(flags)


def main():
    res = {}
    for mkt, path in FILES.items():
        dates, closes = load(path)
        out = cc.compute(dates)
        ev = out["episode_start"]
        res[mkt] = {"dates": dates, "closes": closes, "n": int(ev.sum()), "days": int(out["fire"].sum()),
                    "sessions": len(dates), "rate": {k: float(out[k].mean()) for k in ("B", "T", "W")},
                    "rows": tests(dates, closes, ev, ITERS) if ev.sum() >= MIN_EPISODES else None}

    nf, dj = res["NIFTY"], res["DJIA"]
    print("### Run output (verbatim)\n")
    for mkt, r in res.items():
        print(f"- {mkt}: {r['sessions']} sessions {r['dates'][0]}..{r['dates'][-1]}; CCI=3 on {r['days']} "
              f"sessions, {r['n']} episodes; family rates B {r['rate']['B']:.3f}, T {r['rate']['T']:.3f}, "
              f"W {r['rate']['W']:.3f}")
    print()
    grades = []
    if nf["rows"] is None or dj["rows"] is None:
        print("**Verdict: insufficient** (fewer than 15 episodes in at least one market).")
    else:
        print("| outcome | h | NIFTY excess | p | q | pre-2015 | 2015+ | DJIA excess | q | pre-2015 | 2015+ | grade |")
        print("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for a, b in zip(nf["rows"], dj["rows"], strict=True):
            s = a["sign"]
            cells = [a["early"], a["late"], b["early"], b["late"]]
            same = all(np.isfinite(x) and np.sign(x) == s for x in cells)
            cost_ok = a["outcome"] != "fwd_return" or a["excess"] <= -COST
            g = "edge" if (a["q"] < ALPHA and b["q"] < ALPHA and same and cost_ok) else "no edge"
            grades.append(g)
            print(f"| {a['outcome']} | {a['h']} | {a['excess']:+.5f} | {a['p']:.4f} | {a['q']:.4f} | "
                  f"{a['early']:+.5f} | {a['late']:+.5f} | {b['excess']:+.5f} | {b['q']:.4f} | "
                  f"{b['early']:+.5f} | {b['late']:+.5f} | {g} |")
        print(f"\n**Verdict: {'edge' if 'edge' in grades else 'no edge'}**\n")

    # Placebos (NIFTY)
    rng = np.random.default_rng(SEED)
    lags = [int(x) for x in rng.integers(180, 721, size=PLACEBO_LAGS)]
    hits = total = 0
    real_p = [r["p"] for r in nf["rows"]] if nf["rows"] else []
    for lag in lags:
        ev = cc.compute(nf["dates"], sky_offset_days=lag)["episode_start"]
        if ev.sum() < MIN_EPISODES:
            continue
        for r in tests(nf["dates"], nf["closes"], ev, PLACEBO_ITERS):
            total += 1
            hits += r["p"] < ALPHA
    print(f"- Shifted-sky placebo (NIFTY, lags {lags}): {hits}/{total} placebo tests with p < 0.05 "
          f"({100 * hits / total if total else float('nan'):.1f}%); real CCI p-values: "
          + ", ".join(f"{p:.4f}" for p in real_p))
    for monthly in (False, True):
        ev = hash_events(nf["dates"], max(nf["n"], 1), monthly)
        rows = tests(nf["dates"], nf["closes"], ev, PLACEBO_ITERS)
        tag = "monthly" if monthly else "daily"
        print(f"- Hash placebo ({tag}, {int(ev.sum())} episodes): p = "
              + ", ".join(f"{r['outcome']}/{r['h']} {r['p']:.4f}" for r in rows))


if __name__ == "__main__":
    main()
