"""Backtest SBC vedha scenarios for the Fertilizer sector.

Scenarios (user hypothesis):
  Fertilizer stocks (Chambal, Coromandel, GNFC, RCF, NFL, Deepak Fertilizers)
  respond to SBC vedhas involving the sector's planetary rulers:
    Agri demand -> Moon/Jupiter | Subsidies -> Sun | Chemical mfg -> Saturn
    Trade/distribution -> Mercury | Monsoon -> Moon | Input costs -> Saturn/Mars

Pair legend "X -> Y" = planet X casts a vedha ray onto the chakra cell
occupied by planet Y.

Strong Bullish        : Moon->Jupiter, Sun->Jupiter, Mercury->Jupiter,
                        Jupiter->Moon, Jupiter->Sun      (window 5-12d)
Moderate Bullish      : Moon->Sun, Mercury->Moon, Mercury->Sun (window 3-8d)
Reversal (Bear->Bull) : Saturn->Jupiter, Saturn->Sun,
                        Rahu->Jupiter, Rahu->Sun         (volatility then rally)

Method:
  - Daily planetary positions at noon IST (Swiss Ephemeris, Lahiri).
  - Classical-school vedha rays via sbc.prediction.compute_vedhas.
  - Signal day T; forward close-to-close returns over 1/3/5/7/10 trading days.
  - Per-stock group stats + full pair breakdown on an equal-weight basket.
"""

import datetime
import os

import pandas as pd

from sbc.backtest import _julian_at_noon
from sbc.chakra import NAKSHATRA_CELL
from sbc.planets import positions
from sbc.prediction import compute_vedhas

STOCKS = {
    "Chambal Fert": ("CHAMBLFERT.NS", os.path.join("data", "fert_chambal.csv")),
    "Coromandel": ("COROMANDEL.NS", os.path.join("data", "fert_coromandel.csv")),
    "GNFC": ("GNFC.NS", os.path.join("data", "fert_gnfc.csv")),
    "RCF": ("RCF.NS", os.path.join("data", "fert_rcf.csv")),
    "NFL": ("NFL.NS", os.path.join("data", "fert_nfl.csv")),
    "Deepak Fert": ("DEEPAKFERT.NS", os.path.join("data", "fert_deepak.csv")),
}

PAIR_GROUPS = {
    ("Moon", "Jupiter"): "Strong Bullish",
    ("Sun", "Jupiter"): "Strong Bullish",
    ("Mercury", "Jupiter"): "Strong Bullish",
    ("Jupiter", "Moon"): "Strong Bullish",
    ("Jupiter", "Sun"): "Strong Bullish",
    ("Moon", "Sun"): "Moderate Bullish",
    ("Mercury", "Moon"): "Moderate Bullish",
    ("Mercury", "Sun"): "Moderate Bullish",
    ("Saturn", "Jupiter"): "Reversal(Bear>Bull)",
    ("Saturn", "Sun"): "Reversal(Bear>Bull)",
    ("Rahu", "Jupiter"): "Reversal(Bear>Bull)",
    ("Rahu", "Sun"): "Reversal(Bear>Bull)",
}
GROUPS = ["Strong Bullish", "Moderate Bullish", "Reversal(Bear>Bull)"]
HORIZONS = [1, 3, 5, 7, 10]


def load_prices(symbol, cache_path):
    """Daily OHLC via yfinance with local CSV cache."""
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
    for n in HORIZONS:
        print(f"\n    -- {n}-day forward return --")
        print(f"    {'scenario':40s} {'n':>5s} {'avg%':>7s} {'med%':>7s} {'win%':>6s} {'|avg|%':>7s}")
        for b in blocks[n]:
            if b is None:
                continue
            print(f"    {b['label']:40s} {b['n']:5d} {b['avg']:7.2f} {b['med']:7.2f} "
                  f"{b['win']:6.1f} {b['abs_avg']:7.2f}")


def signal_indices(dates):
    """Map pairs/groups -> list of positional indices for the shared date axis."""
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
    return pair_flags, group_flags, dual_days


def main():
    t0 = datetime.datetime.now()

    # Load all stocks and align to a common date axis
    series = {}
    for name, (symbol, cache_path) in STOCKS.items():
        df = load_prices(symbol, cache_path)
        if df is None or df.empty:
            print(f"{name}: NO PRICE DATA, skipping")
            continue
        s = df.set_index("Date")["Close"]
        s.name = name
        series[name] = s
    if not series:
        print("No price data at all.")
        return
    panel = pd.DataFrame(series).sort_index().ffill().dropna(how="all")

    # Equal-weight basket (rebased to 100)
    rebased = panel / panel.iloc[0] * 100.0
    basket_df = rebased.mean(axis=1).rename("Basket").reset_index()
    basket_df.columns = ["Date", "Close"]

    # Astro signals on the basket's date axis (shared by all stocks)
    dates = [d.date().isoformat() for d in panel.index]
    pair_flags, group_flags, dual_days = signal_indices(dates)

    def blocks_for(df, entries):
        per_h = {n: [] for n in HORIZONS}
        for label, idx_list in entries:
            rows = df.iloc[idx_list] if idx_list else df.iloc[0:0]
            for n in HORIZONS:
                per_h[n].append(stats_block(rows, label, n))
        return per_h

    basket = forward_returns(basket_df)

    print("=" * 78)
    print("FERTILIZER SECTOR BASKET (equal-weight: " +
          ", ".join(series.keys()) + ")")
    print(f"days: {len(panel)}  ({panel.index.min().date()} .. {panel.index.max().date()})")

    print_table("Baseline (all trading days)",
                blocks_for(basket, [("ALL DAYS (baseline)", list(range(len(basket))))]))

    for g in GROUPS:
        entries = [(p[0] + " -> " + p[1], idx) for p, idx in pair_flags.items()
                   if PAIR_GROUPS[p] == g]
        entries.append((f"[ANY {g}]", group_flags[g]))
        print_table(f"{g} scenarios", blocks_for(basket, entries))

    print(f"\n  Dual-vedha days (>=2 scenario pairs): {len(dual_days)}")
    for ds, pairs in dual_days[:10]:
        print(f"    {ds}: " + ", ".join(a + "->" + b for a, b in pairs))
    if len(dual_days) > 10:
        print(f"    ... and {len(dual_days) - 10} more")

    # Per-stock group-level stats
    for name in series:
        sdf = panel[[name]].reset_index()
        sdf.columns = ["Date", "Close"]
        sdf = forward_returns(sdf)
        print(f"\n{'-' * 78}\n{name}: group-level results")
        blocks = [("ALL DAYS", list(range(len(sdf))))]
        blocks += [(f"[ANY {g}]", group_flags[g]) for g in GROUPS]
        print_table("vs baseline", blocks_for(sdf, blocks))

    print(f"\nElapsed: {(datetime.datetime.now() - t0).total_seconds():.1f}s")


if __name__ == "__main__":
    main()
