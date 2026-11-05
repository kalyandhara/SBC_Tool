"""Empirical study: does an astrological filter pick better EMA 9/21 crosses than chance?

Design (frozen before the run; the report prints as-is):
- Universe: NIFTY daily OHLC (data/nifty_ohlc.csv).
- Technical event: Heikin-Ashi EMA 9/21 cross on a closed bar i.
- Trade: enter at close[i], exit at close[i+1] (T+1). Bull cross = long, bear cross = short.
- Astro bias: sign of the SBC engine's daily `net` score for the session being traded
  (bar i+1's date, 09:15 IST). Planetary positions are deterministic, so this uses no
  price information from the future. >0 bullish, <0 bearish, 0/None neutral.
- Confirmed event: bull cross with bullish bias, or bear cross with bearish bias.
- Costs: 0.20% round-trip is subtracted from each trade's mean for the net line.
- Control: 10,000 random same-size subsets of the SAME crosses (seed 42). The p-value is
  the share of random subsets whose mean return >= the confirmed subset's mean. A filter
  that adds nothing looks like a random subset.

Limits (stated, not hidden):
- This tests the FILTER against chance. It is NOT the decile-matched same-day-return
  control, which asks whether the cross itself matters. That control is still to do.
- One index, one filter definition, no multiple-testing correction. Descriptive only;
  the research corpus has 0/511 out-of-sample passes. Not financial advice.
"""

import os
import sys

import numpy as np
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from sbc.confluence_engine import confluence_signal, detect_ma_cross, net_trade_return  # noqa: E402
from sbc.screener.indicators import ema, heikin_ashi  # noqa: E402

COST_PCT = 0.20
ITERS = 10_000
SEED = 42
FAST, SLOW = 9, 21


def engine_bias(date_iso: str) -> int:
    """Sign of the SBC engine's net score for a session: +1 bullish, -1 bearish, 0 neutral."""
    from sbc.engine import build_response
    net = build_response(date_iso, "09:15", "Asia/Kolkata", "nifty", "classical").get("net")
    if net is None or net == 0:
        return 0
    return 1 if net > 0 else -1


def permutation_p(all_rets: np.ndarray, k: int, observed_mean: float,
                  iters: int = ITERS, seed: int = SEED) -> float:
    """Share of random size-k subsets of all_rets whose mean >= observed_mean."""
    if k == 0 or k > len(all_rets):
        return float("nan")
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(all_rets, size=k, replace=False).mean() for _ in range(iters)])
    return float((means >= observed_mean).mean())


def _row(label: str, rets: np.ndarray, p: float | None = None) -> None:
    if len(rets) == 0:
        print(f"  {label}: no events")
        return
    mean = float(rets.mean())
    tail = "" if p is None or np.isnan(p) else f"  p(random>=this)={p:.3f}"
    print(f"  {label}: N={len(rets):3d}  gross={mean * 100:+.2f}%  "
          f"net={net_trade_return(mean, COST_PCT) * 100:+.2f}%  "
          f"win={np.mean(rets > 0) * 100:.1f}%{tail}")


def run_confluence_study(csv_path: str = os.path.join(_ROOT, "data", "nifty_ohlc.csv"),
                         bias_fn=engine_bias) -> dict | None:
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return None
    df = pd.read_csv(csv_path)
    df.columns = [c.lower() for c in df.columns]
    dates = pd.to_datetime(df["date"]).dt.date.astype(str).values
    ha = heikin_ashi(df)
    crosses = detect_ma_cross(ema(ha["close"], FAST).values, ema(ha["close"], SLOW).values)
    closes = df["close"].values

    events = {"bull": [], "bear": []}  # (fwd return in trade direction, confirmed?)
    for i in range(len(closes) - 1):
        if crosses[i] == 0:
            continue
        fwd = closes[i + 1] / closes[i] - 1.0
        bias = bias_fn(dates[i + 1])
        if crosses[i] == 1:
            ok = confluence_signal(1, float(bias)) == "BUY"
            events["bull"].append((fwd, ok))
        else:
            ok = confluence_signal(-1, float(bias)) == "SELL"
            events["bear"].append((-fwd, ok))

    print("\nASTRO-TECHNICAL CONFLUENCE STUDY  (NIFTY daily, HA EMA 9/21, trade = close[i] -> close[i+1])")
    print("Descriptive only. 0/511 out-of-sample passes in the research corpus. Not financial advice.")
    print(f"Cost: {COST_PCT}% round-trip.  Permutations: {ITERS:,}, seed {SEED}.\n")

    out = {}
    for side, label in (("bull", "Bull crosses (long)"), ("bear", "Bear crosses (short)")):
        rets = np.array([r for r, _ in events[side]])
        conf = np.array([r for r, ok in events[side] if ok])
        rest = np.array([r for r, ok in events[side] if not ok])
        p = permutation_p(rets, len(conf), float(conf.mean())) if len(conf) else float("nan")
        print(f"{label}")
        _row("all crosses (raw)    ", rets)
        _row("astro-confirmed      ", conf, p)
        _row("astro-not-confirmed  ", rest)
        print()
        out[side] = {"n_all": len(rets), "n_confirmed": len(conf), "p": p,
                     "mean_all": float(rets.mean()) if len(rets) else None,
                     "mean_confirmed": float(conf.mean()) if len(conf) else None}
    return out


if __name__ == "__main__":
    run_confluence_study()
