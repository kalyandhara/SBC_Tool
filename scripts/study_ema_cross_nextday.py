"""Does the +1-session edge after EMA 9/21 HA crosses survive controls?

PRE-REGISTERED before the run (frozen; the report prints as-is).  The
2026-10-27 matrix validation (reports/ema_ha_matrix_validation_2026-
10-27.md) found the only surviving cells were next-session returns
after DAILY fresh crosses (up +0.34%, down -0.18%, p=0.000).  This
study asks the only question that matters about that edge:

  Is the next-session drift caused by the CROSS, or does the cross
  merely tag days with a large same-day move (which continue anyway)?

Frozen design:
- Universe: NIFTY 500 constituents as of today (survivorship is
  acknowledged: today's members over-weight survivors), plus the
  ^NSEI index descriptively.
- Frames: daily, lookback 9000 calendar days (Yahoo's full history);
  symbols with fewer than 100 valid bars are skipped and counted.
- Events: EMA(9)/EMA(21) crosses on HA closes of closed bars, cross
  detected from bar 2 (the matrix module's frozen seed rule); entry
  reference = the cross bar's HA close; outcome = close-to-close
  forward +1 session (primary) and +5 (decay context).
- Controls: ALL other valid days, bucketed into deciles of their
  SAME-DAY return; the permutation matches each event with random
  control days from the SAME decile (10,000 draws, pooled mean,
  two-sided p).  If cross events lose significance against
  decile-matched controls, the edge is the move, not the cross.
- Splits (descriptive, no re-testing): up/down direction, first vs
  second half of the sample by year, and the ^NSEI index.
- Costs: the net line subtracts a 0.20% round-trip cost per trade;
  the break-even cost is reported.

Example:
    python scripts/study_ema_cross_nextday.py
"""

import argparse
import datetime as dt
import os
import sys
import time

import numpy as np
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from sbc.screener import data as screener_data  # noqa: E402
from sbc.screener.indicators import ema, heikin_ashi  # noqa: E402
from sbc.screener.universes import load  # noqa: E402

ITERS = 10_000
SEED = 42
FAST, SLOW = 9, 21
MIN_BARS = 22
MIN_VALID_BARS = 100
LOOKBACK_DAYS = 9000
COST_PCT = 0.20          # round-trip cost, % per trade, for the net line
CHUNK = 100              # symbols per yfinance call (rate-limit guard)
SLEEP_S = 2.0
DECILES = 10


def cross_events(df: pd.DataFrame) -> dict:
    """{direction: (same_day, fwd1, fwd5, year)} + control pools."""
    ha = heikin_ashi(df)
    closes = ha["close"].values
    diff = (ema(ha["close"], FAST) > ema(ha["close"], SLOW)).values
    n = len(closes)
    idx = np.arange(n)
    same_day = np.where(n > 1, closes / np.roll(closes, 1) - 1.0, 0.0)
    same_day[0] = 0.0
    fwd1 = np.full(n, np.nan)
    fwd5 = np.full(n, np.nan)
    fwd1[:-1] = closes[1:] / closes[:-1] - 1.0
    fwd5[:-5] = closes[5:] / closes[:-5] - 1.0
    years = np.array([t.year for t in df.index])
    # frozen: both horizons must be defined, so the last 5 bars are
    # excluded for events AND controls alike
    valid = (idx >= MIN_BARS) & (idx < n - 5)
    out = {"controls": {"same": same_day[valid],
                        "fwd1": fwd1[valid],
                        "fwd5": fwd5[valid],
                        "years": years[valid]}}
    for direction, want in (("up", True), ("down", False)):
        sel = valid & (diff == want) & (np.roll(diff, 1) != diff)
        sel[0] = False
        out[direction] = {"same": same_day[sel], "fwd1": fwd1[sel],
                          "fwd5": fwd5[sel], "years": years[sel]}
    return out


def download_chunked(symbols: list[str]) -> tuple[dict, dict]:
    raw, errs = {}, {}
    for i in range(0, len(symbols), CHUNK):
        chunk = symbols[i:i + CHUNK]
        part, part_errs = screener_data.batch(chunk, "1d",
                                              lookback_days=LOOKBACK_DAYS)
        raw.update(part)
        errs.update(part_errs)
        time.sleep(SLEEP_S)
    return raw, errs


def matched_permutation(events_same, events_fwd, controls_same,
                        controls_fwd, rng) -> tuple[float, float]:
    """(two-sided p, matched-random mean) vs same-decile controls.

    Controls are grouped by decile once; draws are vectorised across
    iteration blocks (10,000 x ~77k gathers would otherwise take hours).
    """
    edges = np.quantile(controls_same, np.linspace(0, 1, DECILES + 1))[1:-1]
    ev_bins = np.digitize(events_same, edges)
    ct_bins = np.digitize(controls_same, edges)
    obs = float(np.mean(events_fwd))
    pools = [controls_fwd[ct_bins == b] for b in range(DECILES)]
    counts = [int((ev_bins == b).sum()) for b in range(DECILES)]
    pairs = [(pools[b], counts[b]) for b in range(DECILES)
             if counts[b] and len(pools[b])]
    if not pairs:
        return float("nan"), float("nan")
    means = np.empty(ITERS)
    block = 250
    done = 0
    while done < ITERS:
        m = min(block, ITERS - done)
        tot = np.zeros(m)
        cnt = 0
        for pool, k in pairs:
            pick = rng.integers(0, len(pool), size=(m, k))
            tot += pool[pick].sum(axis=1)
            cnt += k
        means[done:done + m] = tot / cnt
        done += m
    p_ge = float((means >= obs).mean())
    p_le = float((means <= obs).mean())
    return min(1.0, 2 * min(p_ge, p_le)), float(means.mean())


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=os.path.join(
        "reports", "ema_cross_nextday_validation_2026-10-28.md"))
    args = parser.parse_args()
    rng = np.random.default_rng(SEED)

    symbols = load("NIFTY 500")
    print(f"universe NIFTY 500: {len(symbols)} symbols, daily, lookback "
          f"{LOOKBACK_DAYS}d, chunks of {CHUNK}")
    raw, errs = download_chunked(symbols)
    skipped = 0
    events = {"up": {"same": [], "fwd1": [], "fwd5": [], "years": []},
              "down": {"same": [], "fwd1": [], "fwd5": [], "years": []}}
    controls = {"same": [], "fwd1": [], "fwd5": [], "years": []}
    for sym, df in raw.items():
        if len(df) < MIN_VALID_BARS:
            skipped += 1
            continue
        ev = cross_events(df)
        for k in events:
            for field in ("same", "fwd1", "fwd5", "years"):
                events[k][field].extend(ev[k][field])
        for field in ("same", "fwd1", "fwd5", "years"):
            controls[field].extend(ev["controls"][field])
    ctl = {k: np.asarray(v) for k, v in controls.items()}
    for d in events:
        events[d] = {k: np.asarray(v) for k, v in events[d].items()}
    print(f"symbols used: {len(raw) - skipped} (skipped {skipped} short); "
          f"events up {len(events['up']['fwd1'])}, down "
          f"{len(events['down']['fwd1'])}; control days {len(ctl['fwd1'])}")

    lines = ["# EMA 9/21 HA daily fresh cross - next-session study",
             "",
             "Pre-registered before the run (docstring).  Question: does "
             "the +1-session edge after a daily fresh EMA9/21 HA cross "
             "survive matching on the SAME-DAY return (i.e. is it the "
             "cross, or just big-move-day continuation)?  Universe NIFTY "
             "500 as of today (survivorship acknowledged); baseline "
             "10,000 same-decile permutations, two-sided p.",
             ""]
    lines.append("| direction | events | cross-day move % | +1d % | +1d "
                 "matched-random % | p | hit rate | +5d % | +5d p |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for direction in ("up", "down"):
        ev = events[direction]
        if not len(ev["fwd1"]):
            continue
        obs1 = float(np.mean(ev["fwd1"]))
        p1, rand1 = matched_permutation(ev["same"], ev["fwd1"], ctl["same"],
                                        ctl["fwd1"], rng)
        obs5 = float(np.mean(ev["fwd5"]))
        p5, _ = matched_permutation(ev["same"], ev["fwd5"], ctl["same"],
                                    ctl["fwd5"], rng)
        hit = float(np.mean(ev["fwd1"] > 0)) * 100
        lines.append(
            f"| cross {direction} | {len(ev['fwd1'])} "
            f"| {np.mean(ev['same']) * 100:+.2f} | {obs1 * 100:+.3f} "
            f"| {rand1 * 100:+.3f} | {p1:.3f} | {hit:.1f}% "
            f"| {obs5 * 100:+.2f} | {p5:.3f} |")
    # controls' own next-day mean for context
    lines.append(f"| all other days (unmatched) | {len(ctl['fwd1'])} | - "
                 f"| {np.mean(ctl['fwd1']) * 100:+.3f} | - | - | - | - | - |")
    lines.append("")

    # half-sample stability by year, per direction (the effect is
    # directional; pooling would dilute it)
    mid = int(np.median(np.concatenate([events["up"]["years"],
                                        events["down"]["years"]])))
    lines.append(f"Half-sample stability (split at year {mid}; +1d, "
                 f"same-decile matched):")
    for direction in ("up", "down"):
        ev = events[direction]
        for label, mask in (("first half", ev["years"] <= mid),
                            ("second half", ev["years"] > mid)):
            if mask.sum() < 30:
                continue
            obs = float(np.mean(ev["fwd1"][mask]))
            p, rand = matched_permutation(ev["same"][mask], ev["fwd1"][mask],
                                          ctl["same"], ctl["fwd1"], rng)
            lines.append(f"- cross {direction}, {label}: "
                         f"{int(mask.sum())} events, +1d {obs * 100:+.3f}% "
                         f"vs matched {rand * 100:+.3f}% (p={p:.3f})")
    lines.append("")

    # net of costs
    n_up, n_dn = len(events["up"]["fwd1"]), len(events["down"]["fwd1"])
    obs_all = (np.sum(events["up"]["fwd1"]) + np.sum(events["down"]["fwd1"])
               if n_up + n_dn else float("nan")) / (n_up + n_dn)
    net = obs_all * 100 - COST_PCT
    breakeven = obs_all * 100
    lines.append(f"Direction-pooled +1d: {obs_all * 100:+.3f}% gross; "
                 f"net of a {COST_PCT:.2f}% round trip: {net:+.3f}% per "
                 f"trade; the edge breaks even at a {breakeven:.3f}% "
                 f"round-trip cost.")
    lines.append("")

    # the index, descriptively
    idx_rows = cross_events(screener_data.history("^NSEI", "1d",
                                                  lookback_days=LOOKBACK_DAYS))
    for direction in ("up", "down"):
        ev = idx_rows[direction]
        if len(ev["fwd1"]):
            lines.append(f"- ^NSEI cross {direction}: {len(ev['fwd1'])} "
                         f"events, next-day "
                         f"{float(np.mean(ev['fwd1'])) * 100:+.3f}% "
                         f"(descriptive, n too small to test)")
    lines.append("")
    lines.append("Reading: if the matched-random column sits at the "
                 "observed value (p well above 0.05), the cross carries "
                 "nothing beyond the day's own move - the matrix stays a "
                 "display.  A surviving p means the cross timing itself "
                 "adds information; check the net-of-cost line before "
                 "caring.")
    report = "\n".join(lines) + "\n"
    print(report)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(f"saved: {args.out}")


if __name__ == "__main__":
    main()
