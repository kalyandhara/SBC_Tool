"""Validate the Mars-in-Pushya + Moon-in-Rohini timeline against NIFTY (B-71).

Run only after docs/research/planetary_event_timeline_preregistration_2026-10-30.md is
committed. Writes docs/research/planetary_event_timeline_validation_<date>.md.

    venv/Scripts/python.exe scripts/validate_planetary_event_timeline.py
"""

import datetime as dt
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from sbc import market_store  # noqa: E402
from sbc import planetary_event_timeline as pet  # noqa: E402
from sbc.planets import positioned_planets  # noqa: E402
from sbc.rule_validation import ERA_SPLIT  # noqa: E402

OUT_DIR = os.path.join(_ROOT, "docs", "research")


def _sky_flags(dates):
    flags = np.zeros(len(dates), dtype=bool)
    for i, d in enumerate(dates):
        planets, _, _, _, _ = positioned_planets(d, "09:15", "Asia/Kolkata")
        flags[i] = pet.is_event({p["name"]: p for p in planets})
    return flags


def run(out_path: str | None = None) -> str:
    bars = market_store.get_daily("NIFTY")
    dates = [b["date"] for b in bars]
    closes = np.array([b["close"] for b in bars], dtype=float)

    flags = _sky_flags(dates)
    starts = pet.episode_starts(flags)
    n_ep = int(starts.sum())
    labels = pet.decile_labels(pet.same_day_returns(closes))
    era = np.array([d < ERA_SPLIT for d in dates])

    results = {}
    for h in pet.HORIZONS:
        fwd = pet.forward_returns(closes, h)
        obs = pet.excess_statistic(fwd, labels, starts)
        p = pet.permutation_p(fwd, labels, starts, obs)
        early = pet.excess_statistic(fwd, labels, starts & era)
        late = pet.excess_statistic(fwd, labels, starts & ~era)
        results[h] = {"obs": obs, "p": p, "early": early, "late": late}

    qs = pet.benjamini_hochberg([results[h]["p"] for h in pet.HORIZONS])
    for h, q in zip(pet.HORIZONS, qs):
        r = results[h]
        r["q"] = q
        same = np.sign(r["early"]) == np.sign(r["obs"]) and np.sign(r["late"]) == np.sign(r["obs"])
        r["verdict"] = pet.grade(n_ep, r["p"], q, bool(same))

    path = pet.event_path(closes, starts)
    mean_path = np.nanmean(path, axis=0) if len(path) else np.array([])

    today = dt.date.today().isoformat()
    lines = [
        f"# Planetary event timeline validation (B-71) — {today}",
        "",
        f"Sample: {dates[0]} to {dates[-1]}, {len(dates)} NIFTY sessions. Episodes: {n_ep} "
        f"(minimum {pet.MIN_EPISODES}). Primary horizon: +{pet.PRIMARY_HORIZON}.",
        "",
        "Excess = mean forward return of events minus their decile control. Net = excess minus the 0.20% round-trip cost (long-side view).",
        "",
        "| Horizon | Mean excess | Net of 0.20% | p | q (BH) | Early era | Late era | Verdict |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for h in pet.HORIZONS:
        r = results[h]
        lines.append(
            f"| +{h} | {r['obs']*100:+.2f}% | {(r['obs']-0.002)*100:+.2f}% | "
            f"{r['p']:.4f} | {r['q']:.4f} | {r['early']*100:+.2f}% | {r['late']*100:+.2f}% | "
            f"{r['verdict']} |"
        )
    lines += ["", "Mean normalized path (event close = 100), sessions -5 to +20:", ""]
    lines.append(", ".join(f"{v:.2f}" for v in mean_path))
    text = "\n".join(lines) + "\n"

    out_path = out_path or os.path.join(OUT_DIR, f"planetary_event_timeline_validation_{today}.md")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return out_path


if __name__ == "__main__":
    print(run())
