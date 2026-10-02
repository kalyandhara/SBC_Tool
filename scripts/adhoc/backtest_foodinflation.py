"""Backtest SBC vedha scenarios for Food Inflation.

Scenarios (user hypothesis):
  Malefic vedhas (Saturn/Mars/Rahu) on luminaries & agri planets drive food
  inflation via scarcity, weather stress and supply shocks. Expected flow-on:
    Bullish : food commodities, fertilizer/agri-chemical stocks
    Bearish : FMCG margins / rural consumption stocks

Pair legend "X -> Y" = planet X casts a vedha ray onto the chakra cell
occupied by planet Y.

Strong Inflation  : Saturn->Moon, Saturn->Sun, Mars->Moon,
                    Mars->Jupiter, Rahu->Moon, Rahu->Mercury
Moderate          : Moon->Saturn, Moon->Mars, Sun->Saturn
Sudden Spikes     : Rahu->Sun, Rahu->Moon, Mars->Moon

Proxies:
  FOOD      = equal-weight Sugar/Wheat/Corn/Rice futures (SB=F ZW=F ZC=F ZR=F)
  FMCG      = equal-weight HindUnilever/ITC/NestleIndia/Britannia   (expect down)
  AGRICHEM  = equal-weight UPL/PIInd/Rallis/Dhanuka               (expect up)

Method: noon-IST Swiss Ephemeris positions, classical SBC vedha rays,
forward close-to-close returns at 1/3/5/7/10/20 trading days.
"""

import datetime
import os

import pandas as pd

from sbc.backtest import _julian_at_noon
from sbc.chakra import NAKSHATRA_CELL
from sbc.planets import positions
from sbc.prediction import compute_vedhas

FOOD = {
    "Sugar": ("SB=F", os.path.join("data", "food_sugar.csv")),
    "Wheat": ("ZW=F", os.path.join("data", "food_wheat.csv")),
    "Corn": ("ZC=F", os.path.join("data", "food_corn.csv")),
    "Rice": ("ZR=F", os.path.join("data", "food_rice.csv")),
}
FMCG = {
    "HindUnilever": ("HINDUNILVR.NS", os.path.join("data", "fmcg_hul.csv")),
    "ITC": ("ITC.NS", os.path.join("data", "fmcg_itc.csv")),
    "NestleIndia": ("NESTLEIND.NS", os.path.join("data", "fmcg_nestle.csv")),
    "Britannia": ("BRITANNIA.NS", os.path.join("data", "fmcg_britannia.csv")),
}
AGRICHEM = {
    "UPL": ("UPL.NS", os.path.join("data", "agch_upl.csv")),
    "PI Industries": ("PIIND.NS", os.path.join("data", "agch_piind.csv")),
    "Rallis": ("RALLIS.NS", os.path.join("data", "agch_rallis.csv")),
    "Dhanuka": ("DHANUKA.NS", os.path.join("data", "agch_dhanuka.csv")),
}

PAIR_GROUPS = {
    ("Saturn", "Moon"): "Strong Inflation",
    ("Saturn", "Sun"): "Strong Inflation",
    ("Mars", "Moon"): "Strong Inflation",
    ("Mars", "Jupiter"): "Strong Inflation",
    ("Rahu", "Moon"): "Strong Inflation",
    ("Rahu", "Mercury"): "Strong Inflation",
    ("Moon", "Saturn"): "Moderate Inflation",
    ("Moon", "Mars"): "Moderate Inflation",
    ("Sun", "Saturn"): "Moderate Inflation",
    ("Rahu", "Sun"): "Sudden Spike",
    # Rahu->Moon and Mars->Moon also belong to Sudden Spikes; handled below.
}
SPIKE_EXTRA = [("Rahu", "Moon"), ("Mars", "Moon")]
GROUPS = ["Strong Inflation", "Moderate Inflation", "Sudden Spike"]
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


def build_basket(definitions, label):
    series = {}
    for name, (symbol, cache_path) in definitions.items():
        df = load_prices(symbol, cache_path)
        if df is None or df.empty:
            print(f"{label}/{name}: NO DATA, skipping")
            continue
        s = df.set_index("Date")["Close"]
        s.name = name
        series[name] = s
    panel = pd.DataFrame(series).sort_index().ffill().dropna(how="all")
    rebased = panel / panel.iloc[0] * 100.0
    basket = rebased.mean(axis=1).rename("Close").reset_index()
    basket.columns = ["Date", "Close"]
    return panel, basket


def main():
    t0 = datetime.datetime.now()

    _, food = build_basket(FOOD, "FOOD")
    _, fmcg = build_basket(FMCG, "FMCG")
    _, agch = build_basket(AGRICHEM, "AGRICHEM")

    dates = [d.date().isoformat() for d in food["Date"]]
    def compute_flags(date_list):
        pair_f = {pair: [] for pair in PAIR_GROUPS}
        spike_f = []
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
            if any(p in active for p in SPIKE_EXTRA):
                spike_f.append(i)
            if len(pairs_today) >= 2:
                dual.append((ds, pairs_today))
        return pair_f, spike_f, dual

    pair_flags, spike_flags, dual_days = compute_flags(dates)

    def entries_for(df, include_pairs=True, extra=None):
        blocks = [("ALL DAYS (baseline)", list(range(len(df))))]
        if include_pairs:
            for g in GROUPS:
                if g == "Sudden Spike":
                    idx = sorted(set(spike_flags) |
                                 set(pair_flags[("Rahu", "Moon")]) |
                                 set(pair_flags[("Mars", "Moon")]))
                    blocks.append((f"[ANY {g}]", idx))
                    continue
                idx = sorted({i for p, lst in pair_flags.items()
                              if PAIR_GROUPS[p] == g for i in lst})
                blocks.append((f"[ANY {g}]", idx))
            for p, idx in pair_flags.items():
                tag = PAIR_GROUPS[p]
                if p in SPIKE_EXTRA:
                    tag += " +Spike"
                blocks.append((f"{p[0]} -> {p[1]} [{tag}]", idx))
        else:
            for g in GROUPS:
                if g == "Sudden Spike":
                    idx = sorted(set(spike_flags) |
                                 set(pair_flags[("Rahu", "Moon")]) |
                                 set(pair_flags[("Mars", "Moon")]))
                    blocks.append((f"[ANY {g}]", idx))
                    continue
                idx = sorted({i for p, lst in pair_flags.items()
                              if PAIR_GROUPS[p] == g for i in lst})
                blocks.append((f"[ANY {g}]", idx))
        for lbl, idx in (extra or []):
            blocks.append((lbl, idx))
        return blocks

    def render(df, title, blocks):
        rdf = forward_returns(df)
        print(f"\n{'=' * 78}\n{title}  days={len(df)}")
        print_table(title, {n: [stats_block(rdf.iloc[idx], b, n) for b, idx in blocks]
                            for n in HORIZONS})

    render(food, "FOOD BASKET (Sugar/Wheat/Corn/Rice)", entries_for(food))

    # FMCG / agri-chem trade on NSE calendar -> recompute signal indices on their own axes
    fmcg_flags, fmcg_spike, _ = compute_flags([d.date().isoformat() for d in fmcg["Date"]])
    agch_flags, agch_spike, _ = compute_flags([d.date().isoformat() for d in agch["Date"]])

    def group_entries(pair_f, spike_f):
        blocks = [("ALL DAYS (baseline)", list(range(1)))]
        for g in GROUPS:
            if g == "Sudden Spike":
                idx = sorted(set(spike_f) |
                             set(pair_f[("Rahu", "Moon")]) |
                             set(pair_f[("Mars", "Moon")]))
                blocks.append((f"[ANY {g}]", idx))
                continue
            idx = sorted({i for p, lst in pair_f.items()
                          if PAIR_GROUPS[p] == g for i in lst})
            blocks.append((f"[ANY {g}]", idx))
        return blocks

    fmcg_blocks = group_entries(fmcg_flags, fmcg_spike)
    fmcg_blocks[0] = ("ALL DAYS (baseline)", list(range(len(fmcg))))
    render(fmcg, "FMCG BASKET (HUL/ITC/Nestle/Britannia) - hypothesis: BEARISH", fmcg_blocks)

    agch_blocks = group_entries(agch_flags, agch_spike)
    agch_blocks[0] = ("ALL DAYS (baseline)", list(range(len(agch))))
    render(agch, "AGRI-CHEM BASKET (UPL/PIInd/Rallis/Dhanuka) - hypothesis: BULLISH", agch_blocks)

    print(f"\n{'=' * 78}\nDual-signal days (>=2 scenario pairs): {len(dual_days)}")
    for ds, pairs in dual_days[:10]:
        print("  " + ds + ": " + ", ".join(a + "->" + b for a, b in pairs))
    if len(dual_days) > 10:
        print(f"  ... and {len(dual_days) - 10} more")

    print(f"\nElapsed: {(datetime.datetime.now() - t0).total_seconds():.1f}s")


if __name__ == "__main__":
    main()
