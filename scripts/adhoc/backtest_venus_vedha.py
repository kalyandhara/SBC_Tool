"""Time-agnostic backtest of the Venus-vedha-on-Chitra/Libra hypothesis.

The research claim (astro-finance):
  * Venus vedha -> Libra : trend stabilises, volatility DROPS, mean-reversion
    (and pairs trading) works well.
  * Venus vedha -> Chitra: premium/luxury/FMCG sectors OUTPERFORM.
  * Risk (both)       : "beautiful but deceptive" moves — breakouts look
    textbook but may reverse.

We test these on real price data, pooling EVERY trading day in the sample
that has the event active (regardless of when it happened) and comparing to
the all-days baseline.

Data:
  * NIFTY 50 + a premium-FMCG basket (HUL, Nestle, Britannia, ITC).

Metrics:
  * forward return (r1/r3/r5/r10)
  * realised intraday range / volatility proxy (High-Low)/Close
  * mean-reversion: P(next-day return has opposite sign to today) when today
    was strongly up/down (the "revert" rate).
  * relative strength: FMCG basket forward return MINUS NIFTY forward return.
"""

import datetime
import os

import pandas as pd

from sbc.backtest import _julian_at_noon
from sbc.nakshatra import tithi_of
from sbc.planets import all_planets_with_natures, positions
from sbc.venus_vedha import venus_vedha_events

DATA = "data"
FMCG_FILES = {
    "HUL": "fmcg_hul.csv",
    "Nestle": "fmcg_nestle.csv",
    "Britannia": "fmcg_britannia.csv",
    "ITC": "fmcg_itc.csv",
}
HORIZONS = [1, 3, 5, 10]

_CACHE = {}


def load_csv(name):
    return pd.read_csv(os.path.join(DATA, name), parse_dates=["Date"])


def event_flags(dates):
    """Return a dict of date->{chitra,libra,librlon} flags for each date."""
    out = {}
    for d in dates:
        ds = pd.Timestamp(d).date().isoformat()
        if ds in _CACHE:
            out[ds] = _CACHE[ds]
            continue
        planets, _ = positions(_julian_at_noon(ds))
        sun = next(p for p in planets if p["name"] == "Sun")
        moon = next(p for p in planets if p["name"] == "Moon")
        t = tithi_of(sun["longitude"], moon["longitude"])
        planets = all_planets_with_natures(planets, t, sun["longitude"])
        ev = venus_vedha_events(planets)
        flag = {"chitra": False, "libra": False, "either": False}
        if ev and ev.get("active"):
            flag["chitra"] = ev["hits_chitra"]
            flag["libra"] = ev["hits_libra"]
            flag["either"] = True
        _CACHE[ds] = flag
        out[ds] = flag
    return out


def add_metrics(df):
    out = df.copy()
    out["ret"] = out["Close"].pct_change()
    out["range"] = (out["High"] - out["Low"]) / out["Close"]
    for n in HORIZONS:
        out[f"r{n}"] = out["Close"].shift(-n) / out["Close"] - 1.0
    # mean-reversion: did an up day (>+0.3%) reverse to a down next day,
    # or a down day reverse up?  (reversal rate)
    out["up_day"] = out["ret"] > 0.003
    out["down_day"] = out["ret"] < -0.003
    out["next_up"] = out["ret"].shift(-1) > 0
    out["next_down"] = out["ret"].shift(-1) < 0
    return out


def stat_row(rows, mask, label):
    s = {"label": label, "n": int(mask.sum())}
    for n in HORIZONS:
        v = rows.loc[mask, f"r{n}"].dropna()
        s[f"r{n}_avg"] = v.mean() * 100 if len(v) else float("nan")
        s[f"r{n}_win"] = (v > 0).mean() * 100 if len(v) else float("nan")
    v = rows.loc[mask, "range"].dropna()
    s["range_avg"] = v.mean() * 100 if len(v) else float("nan")
    # reversal rate on strong days
    strong_up = mask & rows["up_day"]
    rev_up = (rows.loc[strong_up, "next_down"].mean() * 100) if strong_up.sum() else float("nan")
    strong_dn = mask & rows["down_day"]
    rev_dn = (rows.loc[strong_dn, "next_up"].mean() * 100) if strong_dn.sum() else float("nan")
    s["rev_up"] = rev_up
    s["rev_dn"] = rev_dn
    return s


def print_panel(title, rows, groups):
    print("\n" + "=" * 82)
    print(title)
    print("=" * 82)
    hdr = (f"  {'group':16s} {'n':>5s} | "
           + " | ".join(f"r{n:>11}" for n in HORIZONS)
           + f" | {'range%':>7s} | {'rev_up%':>7s} {'rev_dn%':>7s}")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for g in groups:
        s = stat_row(rows, g["mask"], g["label"])
        seg = " | ".join(
            f"{s[f'r{n}_avg']:+6.2f}%/{s[f'r{n}_win']:3.0f}%" for n in HORIZONS)
        print(f"  {s['label']:16s} {s['n']:5d} | {seg}"
              f" | {s['range_avg']:7.2f} | {s['rev_up']:7.1f} {s['rev_dn']:7.1f}")


def main():
    t0 = datetime.datetime.now()

    nifty = load_csv("nifty_ohlc.csv")
    nifty = add_metrics(nifty)
    dates = nifty["Date"]
    flags = event_flags(dates)
    nifty["chitra"] = [flags[pd.Timestamp(d).date().isoformat()]["chitra"] for d in dates]
    nifty["libra"] = [flags[pd.Timestamp(d).date().isoformat()]["libra"] for d in dates]
    nifty["either"] = [flags[pd.Timestamp(d).date().isoformat()]["either"] for d in dates]

    print(f"NIFTY sample: {len(nifty)} days ({dates.min().date()} .. {dates.max().date()})")
    print(f"  Venus->Chitra days: {(nifty['chitra']).sum()}")
    print(f"  Venus->Libra days:  {(nifty['libra']).sum()}")

    all_mask = pd.Series(True, index=nifty.index)
    groups = [
        {"label": "ALL DAYS", "mask": all_mask},
        {"label": "Chitra vedha", "mask": nifty["chitra"]},
        {"label": "Libra vedha", "mask": nifty["libra"]},
        {"label": "Either", "mask": nifty["either"]},
    ]
    print_panel("NIFTY: Venus vedha effect (time-agnostic pooled)", nifty, groups)

    # --- FMCG basket relative strength ---
    print("\n" + "=" * 82)
    print("FMCG PREMIUM BASKET vs NIFTY (relative strength on event days)")
    print("=" * 82)
    basket = None
    for name, f in FMCG_FILES.items():
        df = load_csv(f)
        df = df.rename(columns={"Close": name})
        df = df[["Date", name]]
        if basket is None:
            basket = df
        else:
            basket = basket.merge(df, on="Date", how="inner")
    basket["basket_ret"] = basket[[c for c in FMCG_FILES]].mean(axis=1).pct_change()
    basket["basket_close"] = basket[[c for c in FMCG_FILES]].mean(axis=1)
    for n in HORIZONS:
        basket[f"b_r{n}"] = basket["basket_close"].shift(-n) / basket["basket_close"] - 1.0
    nifty_cols = ["Date", "Close"] + [f"r{n}" for n in HORIZONS] + ["chitra", "libra", "either"]
    merged = nifty[nifty_cols].merge(
        basket[["Date", "b_r1", "b_r3", "b_r5", "b_r10"]], on="Date", how="inner")

    # relative strength = basket forward return - nifty forward return
    for n in HORIZONS:
        merged[f"rs{n}"] = merged[f"b_r{n}"] - merged[f"r{n}"]

    print(f"\n  FMCG basket sample: {len(merged)} days")
    for lbl, col in [("ALL DAYS", "all"), ("Chitra", "chitra"),
                     ("Libra", "libra"), ("Either", "either")]:
        mask = pd.Series(True, index=merged.index) if col == "all" else merged[col]
        seg = []
        for n in HORIZONS:
            v = merged.loc[mask, f"rs{n}"].dropna()
            seg.append(f"rs{n} {v.mean()*100:+5.2f}%")
        print(f"  {lbl:12s} n={int(mask.sum()):4d}  " + "  ".join(seg))

    print(f"\nElapsed: {(datetime.datetime.now() - t0).total_seconds():.1f}s")


if __name__ == "__main__":
    main()
