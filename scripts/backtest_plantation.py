"""Backtest SBC vedha scenarios for Coffee/Tea plantation commodities.

Scenarios (user hypothesis):
  Vedha = obstruction / impact / reversal energy on the Sarvatobhadra Chakra.
  Positive vedha -> bullishness; negative vedha -> bearishness;
  dual vedha -> volatility + trend reversal.

Plantation-sensitive grahas: Moon (agri demand), Venus (plantation crops),
Mercury (trade/export), Saturn (weather/supply), Jupiter (expansion),
Rahu (shocks/speculation).

Pair legend "X -> Y" = planet X casts a vedha ray onto the chakra cell
occupied by planet Y.

Strong Bullish   : Moon->Venus, Jupiter->Venus, Mercury->Venus, Venus->Moon
Moderate Bullish : Jupiter->Moon, Mercury->Moon, Moon->Jupiter
Volatile/Reversal: Saturn->Moon, Saturn->Venus, Rahu->Venus, Rahu->Moon

Method:
  - Daily planetary positions at noon IST (Swiss Ephemeris, Lahiri).
  - Classical-school vedha rays via sbc.prediction.compute_vedhas.
  - Signal day T; forward close-to-close returns over 1/3/5/7 trading days.
"""

import datetime
import os

import pandas as pd

from sbc.chakra import NAKSHATRA_CELL
from sbc.planets import positions
from sbc.prediction import compute_vedhas
from sbc.backtest import _julian_at_noon

SYMBOLS = {
    "Coffee (KC=F)": ("KC=F", os.path.join("data", "coffee_kc.csv")),
    "Tea (McLeodRussel.NS proxy)": ("MCLEODRUSS.NS", os.path.join("data", "tea_mcleod.csv")),
}

PAIR_GROUPS = {
    ("Moon", "Venus"): "Strong Bullish",
    ("Jupiter", "Venus"): "Strong Bullish",
    ("Mercury", "Venus"): "Strong Bullish",
    ("Venus", "Moon"): "Strong Bullish",
    ("Jupiter", "Moon"): "Moderate Bullish",
    ("Mercury", "Moon"): "Moderate Bullish",
    ("Moon", "Jupiter"): "Moderate Bullish",
    ("Saturn", "Moon"): "Volatile/Reversal",
    ("Saturn", "Venus"): "Volatile/Reversal",
    ("Rahu", "Venus"): "Volatile/Reversal",
    ("Rahu", "Moon"): "Volatile/Reversal",
}
GROUPS = ["Strong Bullish", "Moderate Bullish", "Volatile/Reversal"]
HORIZONS = [1, 3, 5, 7]


def load_prices(symbol, cache_path):
    """Daily OHLC via yfinance with local CSV cache (same pattern as market_data)."""
    if os.path.exists(cache_path):
        df = pd.read_csv(cache_path, parse_dates=["Date"])
        last = df["Date"].max().date()
        if last >= datetime.date.today() - datetime.timedelta(days=4):
            return df
    else:
        df = None
    import yfinance as yf
    fetch_start = "2021-08-01"
    if df is not None and not df.empty:
        fetch_start = (df["Date"].max().date() + datetime.timedelta(days=1)).isoformat()
    new = yf.download(symbol, start=fetch_start,
                      end=(datetime.date.today() + datetime.timedelta(days=1)).isoformat(),
                      progress=False, auto_adjust=False)
    if new is not None and not new.empty:
        if isinstance(new.columns, pd.MultiIndex):
            new.columns = [c[0] for c in new.columns]
        new = new.reset_index()
        new["Date"] = pd.to_datetime(new["Date"]).dt.tz_localize(None)
        new = new[["Date", "Open", "High", "Low", "Close", "Volume"]]
        df = new if df is None or df.empty else (
            pd.concat([df, new]).drop_duplicates("Date").sort_values("Date"))
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        df.to_csv(cache_path, index=False)
    return df


def active_vedha_pairs(date_str, _cache={}):
    """Set of (source -> target) planet pairs whose vedha ray hits the target's cell."""
    if date_str in _cache:
        return _cache[date_str]
    planets, _ = positions(_julian_at_noon(date_str))
    vedha_map, _ = compute_vedhas(planets, school="classical")
    cell_of = {p["name"]: NAKSHATRA_CELL.get(p["nakshatra"]) for p in planets}
    active = set()
    for src, hits in vedha_map.items():
        hit_cells = {(h["row"], h["col"]) for h in hits}
        for tgt, tcell in cell_of.items():
            if tgt != src and tcell and tcell in hit_cells:
                active.add((src, tgt))
    _cache[date_str] = active
    return active


def forward_returns(df, horizons=HORIZONS):
    """Attach forward close-to-close return columns r1/r3/r5/r7."""
    out = df.copy()
    for n in horizons:
        out[f"r{n}"] = out["Close"].shift(-n) / out["Close"] - 1.0
    return out


def stats_block(rows, label, n):
    s = rows[f"r{n}"].dropna()
    if s.empty:
        return None
    return {
        "label": label,
        "n": len(s),
        "avg": s.mean() * 100,
        "med": s.median() * 100,
        "win": (s > 0).mean() * 100,
        "abs_avg": s.abs().mean() * 100,
    }


def print_table(title, blocks):
    print(f"\n  {title}")
    hdr = f"    {'scenario':38s} {'n':>5s} {'avg%':>7s} {'med%':>7s} {'win%':>6s} {'|avg|%':>7s}"
    for n in HORIZONS:
        print(f"\n    -- {n}-day forward return --")
        print(hdr)
        for b in blocks[n]:
            if b is None:
                continue
            print(f"    {b['label']:38s} {b['n']:5d} {b['avg']:7.2f} {b['med']:7.2f} "
                  f"{b['win']:6.1f} {b['abs_avg']:7.2f}")


def run_symbol(name, symbol, cache_path):
    df = load_prices(symbol, cache_path)
    if df is None or df.empty:
        print(f"\n{name}: NO PRICE DATA")
        return
    dates = [d.date().isoformat() for d in df["Date"]]
    df = forward_returns(df)

    pair_flags = {pair: [] for pair in PAIR_GROUPS}
    group_flags = {g: [] for g in GROUPS}
    dual_days = []
    for i, ds in enumerate(dates):
        try:
            active = active_vedha_pairs(ds)
        except Exception as exc:
            print(f"  astro error on {ds}: {exc}")
            active = set()
        pairs_today = [p for p in PAIR_GROUPS if p in active]
        for pair in pairs_today:
            pair_flags[pair].append(i)
            group_flags[PAIR_GROUPS[pair]].append(i)
        if len(pairs_today) >= 2:
            dual_days.append((ds, pairs_today))

    all_rows = {"r%d" % n: df["r%d" % n] for n in HORIZONS}

    def blocks_for(indices_by_day, label_fn):
        per_h = {n: [] for n in HORIZONS}
        for label, idx_list in indices_by_day:
            for n in HORIZONS:
                rows = df.iloc[idx_list] if idx_list else df.iloc[0:0]
                per_h[n].append(stats_block(rows, label, n))
        return per_h

    # baseline
    baseline = {n: [stats_block(df, "ALL DAYS (baseline)", n)] for n in HORIZONS}
    print(f"\n{'=' * 78}\n{name}  ({symbol})  days: {len(df)}")
    print_table("Baseline (all trading days)", baseline)

    for g in GROUPS:
        entries = [(p[0] + " -> " + p[1], idx) for p, idx in pair_flags.items()
                   if PAIR_GROUPS[p] == g]
        entries.append((f"[ANY {g}]", group_flags[g]))
        print_table(f"{g} scenarios", blocks_for(entries, None))

    print(f"\n  Dual-vedha days (>=2 scenario pairs active): {len(dual_days)}")
    for ds, pairs in dual_days[:10]:
        pretty = ", ".join(a + "->" + b for a, b in pairs)
        print(f"    {ds}: {pretty}")
    if len(dual_days) > 10:
        print(f"    ... and {len(dual_days) - 10} more")


if __name__ == "__main__":
    t0 = datetime.datetime.now()
    for name, (symbol, cache_path) in SYMBOLS.items():
        run_symbol(name, symbol, cache_path)
    print(f"\nElapsed: {(datetime.datetime.now() - t0).total_seconds():.1f}s")
