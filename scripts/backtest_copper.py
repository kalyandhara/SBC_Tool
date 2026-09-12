"""Backtest SBC vedha scenarios for Copper.

Scenarios (user hypothesis):
  Mars vedha = #1 copper trigger (metal demand); Sun -> infra/power;
  Mercury -> trade/pricing; Saturn -> heavy industry; Rahu -> spikes;
  Moon -> short inventory cycles.

Pair legend "X -> Y" = planet X casts a vedha ray onto the chakra cell
occupied by planet Y.

Strong Bullish        : Mars->Sun, Mars->Mercury, Sun->Mars,
                        Mercury->Mars, Saturn->Mars, Mars->Saturn
Moderate Bullish      : Sun->Mercury, Mercury->Sun, Jupiter->Sun
Sudden Bullish Spikes : Rahu->Mars, Rahu->Mercury, Rahu->Sun

Proxies:
  COPPER   = COMEX copper futures HG=F
  HC       = Hindustan Copper (HINDCOPPER.NS) - Indian copper miner
  FCX      = Freeport-McMoRan (FCX) - global copper major

Method: noon-IST Swiss Ephemeris positions, classical SBC vedha rays,
forward close-to-close returns at 1/3/5/7/10/20 trading days.
"""

import datetime
import os

import pandas as pd

from sbc.chakra import NAKSHATRA_CELL
from sbc.planets import positions
from sbc.prediction import compute_vedhas
from sbc.backtest import _julian_at_noon

INSTRUMENTS = {
    "Copper HG": ("HG=F", os.path.join("data", "copper_hg.csv")),
    "HindCopper": ("HINDCOPPER.NS", os.path.join("data", "copper_hindcop.csv")),
    "FCX": ("FCX", os.path.join("data", "copper_fcx.csv")),
}

PAIR_GROUPS = {
    ("Mars", "Sun"): "Strong Bullish",
    ("Mars", "Mercury"): "Strong Bullish",
    ("Sun", "Mars"): "Strong Bullish",
    ("Mercury", "Mars"): "Strong Bullish",
    ("Saturn", "Mars"): "Strong Bullish",
    ("Mars", "Saturn"): "Strong Bullish",
    ("Sun", "Mercury"): "Moderate Bullish",
    ("Mercury", "Sun"): "Moderate Bullish",
    ("Jupiter", "Sun"): "Moderate Bullish",
    ("Rahu", "Mars"): "Sudden Spike",
    ("Rahu", "Mercury"): "Sudden Spike",
    ("Rahu", "Sun"): "Sudden Spike",
    # Moon-target short-term demand pairs (section 6 of the hypothesis)
    ("Mars", "Moon"): "Short-Term Moon",
    ("Sun", "Moon"): "Short-Term Moon",
    ("Mercury", "Moon"): "Short-Term Moon",
}
GROUPS = ["Strong Bullish", "Moderate Bullish", "Sudden Spike", "Short-Term Moon"]
HORIZONS = [1, 3, 5, 7, 10, 20]


def load_prices(symbol, cache_path):
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
    out = df.copy()
    for n in horizons:
        out[f"r{n}"] = out["Close"].shift(-n) / out["Close"] - 1.0
    return out


def stats_block(rows, label, n):
    s = rows[f"r{n}"].dropna()
    if s.empty:
        return None
    return {"label": label, "n": len(s), "avg": s.mean() * 100,
            "med": s.median() * 100, "win": (s > 0).mean() * 100,
            "abs_avg": s.abs().mean() * 100}


def print_table(title, blocks):
    print(f"\n  {title}")
    for n in HORIZONS:
        print(f"\n    -- {n}-day forward return --")
        print(f"    {'scenario':34s} {'n':>5s} {'avg%':>7s} {'med%':>7s} {'win%':>6s} {'|avg|%':>7s}")
        for b in blocks[n]:
            if b is None:
                continue
            print(f"    {b['label']:34s} {b['n']:5d} {b['avg']:7.2f} {b['med']:7.2f} "
                  f"{b['win']:6.1f} {b['abs_avg']:7.2f}")


def compute_flags(date_list):
    pair_f = {pair: [] for pair in PAIR_GROUPS}
    dual = []
    for i, ds in enumerate(date_list):
        try:
            active = active_vedha_pairs(ds)
        except Exception as exc:
            print(f"astro error {ds}: {exc}")
            active = set()
        pairs_today = [p for p in PAIR_GROUPS if p in active]
        for pair in pairs_today:
            pair_f[pair].append(i)
        if len(pairs_today) >= 2:
            dual.append((ds, pairs_today))
    return pair_f, dual


def main():
    t0 = datetime.datetime.now()

    loaded = {}
    for name, (symbol, cache_path) in INSTRUMENTS.items():
        df = load_prices(symbol, cache_path)
        if df is None or df.empty:
            print(f"{name}: NO DATA, skipping")
            continue
        loaded[name] = df

    primary_name = next((k for k in INSTRUMENTS if k in loaded), None)
    dates = [d.date().isoformat() for d in loaded[primary_name]["Date"]]

    def entries_for(pair_f):
        blocks = [("ALL DAYS (baseline)", None)]
        for g in GROUPS:
            idx = sorted({i for p, lst in pair_f.items()
                          if PAIR_GROUPS[p] == g for i in lst})
            blocks.append((f"[ANY {g}]", idx))
        for p, idx in pair_f.items():
            blocks.append((f"{p[0]} -> {p[1]} [{PAIR_GROUPS[p]}]", idx))
        return blocks

    all_dual = []
    for name, df in loaded.items():
        pair_f, dual = compute_flags([d.date().isoformat() for d in df["Date"]])
        all_dual.append((name, dual))
        rdf = forward_returns(df)
        blocks = entries_for(pair_f)
        resolved = [("ALL DAYS (baseline)", list(range(len(df))))]
        for lbl, idx in blocks[1:]:
            resolved.append((lbl, idx if idx is not None else list(range(len(df)))))
        print(f"\n{'=' * 78}")
        print_table(f"{name} ({INSTRUMENTS[name][0]})", 
                    {n: [stats_block(rdf.iloc[idx], b, n) for b, idx in resolved]
                     for n in HORIZONS})

    name, dual = all_dual[0]
    print(f"\n{'=' * 78}\nDual-signal days ({name}, >=2 scenario pairs): {len(dual)}")
    for ds, pairs in dual[:10]:
        print("  " + ds + ": " + ", ".join(a + "->" + b for a, b in pairs))
    if len(dual) > 10:
        print(f"  ... and {len(dual) - 10} more")

    print(f"\nElapsed: {(datetime.datetime.now() - t0).total_seconds():.1f}s")


if __name__ == "__main__":
    main()
