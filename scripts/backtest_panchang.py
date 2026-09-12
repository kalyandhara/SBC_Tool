"""Time-agnostic backtest of the Panchanga daily-trend rule-book.

Philosophy (pooled / time-agnostic): we do NOT care *when* a day happened.
Every trading day in history is labelled with its Panchanga "Final Trend"
(Tithi+Phase -> Nakshatra modifier) and then ALL days that share a label are
pooled together, regardless of chronology.  We compare their pooled forward
close-to-close returns against the baseline (all days) to see whether the
rule itself carries a persistent edge across all time.

If "Super Bullish" days, in aggregate, deliver a higher/positive forward
return than the all-days baseline, the rule has predictive content — not
because it predicted one particular date, but because the *category* is
persistently tilted.  This is the day-zero sanity check before any
walk-forward work.
"""

import datetime
import os

import pandas as pd

from sbc.planets import positions
from sbc.backtest import _julian_at_noon
from sbc.panchang_signals import panchang_signal, tithi_bias, NAKSHATRA_MOD

NIFTY = os.path.join("data", "nifty_ohlc.csv")

HORIZONS = [1, 2, 3, 5, 10]
LABELS = ["Super Bearish", "Bearish", "Mixed/Range", "Bullish", "Super Bullish"]

# Cache of computed signals keyed by date to avoid recomputing positions twice.
_SIG_CACHE = {}


def signal_for(date_str):
    if date_str in _SIG_CACHE:
        return _SIG_CACHE[date_str]
    planets, _ = positions(_julian_at_noon(date_str))
    sig = panchang_signal(planets)
    _SIG_CACHE[date_str] = sig
    return sig


def load_nifty():
    df = pd.read_csv(NIFTY, parse_dates=["Date"])
    df = df[df["Volume"].notna()]
    return df.sort_values("Date").reset_index(drop=True)


def build_rows(df):
    """Return a DataFrame indexed like df with signal columns + forward returns."""
    rows = []
    for _, r in df.iterrows():
        d = r["Date"].date().isoformat()
        sig = signal_for(d)
        rows.append({
            "date": d,
            "close": float(r["Close"]),
            "tithi": sig["tithi"],
            "tithi_name": sig["tithi_name"],
            "paksha": sig["paksha"],
            "nakshatra": sig["nakshatra"],
            "base_bias": sig["base_bias"],
            "final_score": sig["final_score"],
            "final_label": sig["final_label"],
        })
    out = pd.DataFrame(rows)
    for n in HORIZONS:
        out[f"r{n}"] = out["close"].shift(-n) / out["close"] - 1.0
    return out


def pooled_stats(rows, mask, label):
    """Return {n days, avg%, med%, win%, |avg|%} at each horizon for mask."""
    stats = {}
    for n in HORIZONS:
        s = rows.loc[mask, f"r{n}"].dropna()
        if s.empty:
            stats[n] = None
            continue
        stats[n] = {
            "n": len(s),
            "avg": s.mean() * 100,
            "med": s.median() * 100,
            "win": (s > 0).mean() * 100,
            "abs": s.abs().mean() * 100,
        }
    return {"label": label, "count": int(mask.sum()), **stats}


def entropy_group_report(rows, by):
    """Grouped stats for a categorical column (tithi_name, paksha, nakshatra)."""
    print(f"\n  By {by}: pooled forward returns (time-agnostic)")
    for val in sorted(rows[by].dropna().unique()):
        mask = rows[by] == val
        if mask.sum() < 5:
            continue
        st = pooled_stats(rows, mask, val)
        line = f"    {val:16s} n={st['count']:4d}"
        for n in HORIZONS:
            b = st[n]
            if b is None:
                line += f"  r{n}:  -"
                continue
            line += f"  r{n}: avg {b['avg']:+6.2f}% win {b['win']:4.0f}%"
        print(line)


def main():
    t0 = datetime.datetime.now()
    df = load_nifty()
    rows = build_rows(df)
    n_days = len(rows)
    print(f"NIFTY trading days: {n_days}  ({rows['date'].iloc[0]} .. {rows['date'].iloc[-1]})")

    # --- Baseline (all days) ---
    print("\n" + "=" * 78)
    print("BASELINE & FINAL-TREND POOLED RETURNS (time-agnostic)")
    print("=" * 78)
    base = pooled_stats(rows, pd.Series(True, index=rows.index), "ALL DAYS")
    for n in HORIZONS:
        b = base[n]
        print(f"  ALL DAYS      r{n}: avg {b['avg']:+6.2f}%  med {b['med']:+6.2f}%  "
              f"win {b['win']:4.0f}%  n={b['n']}")

    for label in LABELS:
        mask = rows["final_label"] == label
        st = pooled_stats(rows, mask, label)
        if st["count"] == 0:
            continue
        print(f"\n  {label}  (n={st['count']})")
        for n in HORIZONS:
            b = st[n]
            if b is None:
                print(f"    r{n}: no data")
                continue
            print(f"    r{n}: avg {b['avg']:+6.2f}%  med {b['med']:+6.2f}%  "
                  f"win {b['win']:4.0f}%  |avg| {b['abs']:5.2f}%")

    # --- Directional signal quality: did "Bullish/Super Bullish" beat "Bearish/Super Bearish"? ---
    print("\n" + "=" * 78)
    print("DIRECTIONAL EDGE (long bullish bucket, hypothetical short bearish bucket)")
    print("=" * 78)
    for n in HORIZONS:
        bull_mask = rows["final_score"] >= +1
        bear_mask = rows["final_score"] <= -1
        bull = rows.loc[bull_mask, f"r{n}"].dropna()
        bear = rows.loc[bear_mask, f"r{n}"].dropna()
        spread = bull.mean() - bear.mean()
        hit = ((bull > 0).mean() + (bear < 0).mean()) / 2.0
        print(f"  r{n}: bull avg {bull.mean()*100:+6.2f}% (n={len(bull)})  "
              f"bear avg {bear.mean()*100:+6.2f}% (n={len(bear)})  "
              f"spread {spread*100:+6.2f}%  direction-hit {hit*100:4.0f}%")

    # --- Composition reports ---
    print("\n" + "=" * 78)
    print("COMPOSITION / GRANULAR BREAKDOWNS")
    print("=" * 78)
    entropy_group_report(rows, "paksha")
    entropy_group_report(rows, "tithi_name")
    entropy_group_report(rows, "nakshatra")

    # --- Distribution of final labels ---
    print("\n" + "=" * 78)
    print("FINAL-TREND LABEL DISTRIBUTION")
    print("=" * 78)
    vc = rows["final_label"].value_counts()
    for label in LABELS:
        print(f"  {label:16s} {int(vc.get(label, 0)):5d}  "
              f"({vc.get(label, 0) / n_days * 100:4.1f}%)")

    print(f"\nElapsed: {(datetime.datetime.now() - t0).total_seconds():.1f}s")


if __name__ == "__main__":
    main()