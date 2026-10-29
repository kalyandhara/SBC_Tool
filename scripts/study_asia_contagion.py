"""Study: do Indian crashes follow Asian neighbour crashes?

Grades the recurring claim (crash video 2026-10-22, Mercury video
2026-10-25: "the Indian market has fallen less than Korea/Japan/China;
history (2000, 2008) shows our markets often crash after our
neighbours do").

Definitions (frozen before the run):
- Series: India = SENSEX (market.db, 1997-07+, the only Indian series
  deep enough to cover 2000); neighbours = KOSPI (^KS11, 1996-12+),
  Nikkei (^N225, 1990+), Hang Seng (^HSI, 1990+) - repo CSV caches.
- Bear episode: a contiguous interval in which a close is >= 20% below
  its trailing 252-session high (expanding max for the first 252).
- Crash clusters: episodes whose entries are <= 63 sessions apart on
  the neighbour's own calendar are merged (dd oscillating around the
  threshold would otherwise double-count one crash).  Cluster
  attributes: first entry, deepest trough, depth.
- India "in crash" flag: India's own 252-session-high drawdown <= -15%
  on the anchor date.  India worst dd = min of its drawdown over
  [anchor - 63, anchor + 126] sessions.  Trough lag: India trough of
  its overlapping <= -20% episode minus the cluster trough.
- Baseline: 10,000 random anchor days over the joint span (same
  statistics, two-sided p).
- Lead-lag: weekly (last session per ISO week) returns; contemporaneous
  r, neighbour-leads-India r (+1 week), India's own +1 week
  autocorrelation as the honest benchmark.

Example:
    python scripts/study_asia_contagion.py
"""

import datetime
import os
import sys

import numpy as np
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from sbc import market_store  # noqa: E402
from scripts.study_mars_node_conjunction import load_series  # noqa: E402

NEIGHBOURS = ("kospi", "nikkei", "hsi")
BEAR = -0.20          # episode threshold (both sides)
INDIA_CRASH = -0.15   # India "in crash" flag threshold
WINDOW = 252          # trailing high (sessions)
AFTER = 126           # forward crash-lookahead (sessions, ~6 months)
SIDE = 63             # +-search half-window for India's worst dd
MERGE = 63            # episodes closer than this merge into one cluster
ITERS = 10_000
SEED = 42


def closes_of(rows):
    idx = pd.to_datetime([r["time"] if "time" in r else r["date"]
                          for r in rows])
    return pd.Series([r["close"] for r in rows], index=idx,
                     dtype=float).sort_index()


def dd_series(closes, window=WINDOW):
    """Drawdown vs the trailing `window`-session high (expanding early)."""
    hi = closes.cummax() if len(closes) <= window else \
        pd.concat([closes.cummax()[:window],
                   closes.rolling(window).max()[window:]])
    return closes / hi - 1.0


def episodes(dd, level=BEAR):
    """Contiguous intervals with dd <= level -> [{entry, trough, depth}]."""
    vals = dd.values
    out, start = [], None
    for i, v in enumerate(vals):
        if v <= level and start is None:
            start = i
        elif v > level and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(vals) - 1))
    eps = []
    for a, b in out:
        t = a + int(np.argmin(vals[a:b + 1]))
        eps.append({"entry": dd.index[a], "trough": dd.index[t],
                    "depth": float(vals[t]), "i_entry": a, "i_trough": t,
                    "i_end": b})
    return eps


def clusters(eps, max_gap=MERGE):
    """Merge episodes whose entries are <= max_gap sessions apart."""
    out = []
    for e in sorted(eps, key=lambda x: x["i_entry"]):
        if out and e["i_entry"] - out[-1]["i_entry"] <= max_gap:
            prev = out[-1]
            prev["i_end"] = max(prev["i_end"], e["i_end"])
            if e["depth"] < prev["depth"]:
                prev["depth"] = e["depth"]
                prev["trough"] = e["trough"]
                prev["i_trough"] = e["i_trough"]
        else:
            out.append(dict(e))
    return out


def india_pos(india_index, date_ts):
    i = india_index.searchsorted(date_ts, side="right") - 1
    return i if i >= 0 else None


def main():
    india_rows = market_store.get_daily("SENSEX", "1990-01-01")
    india = closes_of(india_rows)
    print("# Asia->India contagion study (pre-registered)")
    print(f"\nIndia: SENSEX {india.index[0].date()} .. "
          f"{india.index[-1].date()} (n={len(india)}); neighbours from "
          f"repo CSV caches. Bear episode = >=20% below the trailing "
          f"252-session high; episodes <=63 sessions apart merge into "
          f"one crash cluster; India crash flag = <= -15%; baseline = "
          f"10,000 random anchor days over the joint span.")

    india_dd = dd_series(india)
    india_eps = clusters(episodes(india_dd))
    n = len(india)
    dd_arr = india_dd.values
    rng = np.random.default_rng(SEED)

    lows = np.full(n, np.nan)
    for i in range(SIDE, n - AFTER):
        lows[i] = dd_arr[i - SIDE:i + AFTER + 1].min()
    crash_ahead = np.full(n, np.nan)
    for i in range(n - AFTER):
        crash_ahead[i] = float(dd_arr[i:i + AFTER + 1].min() <= INDIA_CRASH)
    valid = ~np.isnan(lows)

    def rand_stat(anchor_idx):
        k = len(anchor_idx)
        picks = rng.choice(np.where(valid)[0], size=(ITERS, k),
                           replace=True)
        obs_low = float(np.nanmean(lows[anchor_idx]))
        mean_lows = np.nanmean(lows[picks], axis=1)
        p_le = float((mean_lows <= obs_low).mean())
        p_low = min(1.0, 2 * min(p_le, 1 - p_le))
        obs_crash = float(np.nanmean(crash_ahead[anchor_idx]))
        mean_crash = np.nanmean(crash_ahead[picks], axis=1)
        p_ge = float((mean_crash >= obs_crash).mean())
        p_crash = min(1.0, 2 * min(p_ge, 1 - p_ge))
        return float(mean_lows.mean()), p_low, float(mean_crash.mean()), \
            p_crash

    print("\nToday's scoreboard (close-basis drawdown from the running "
          "high since 2026-01-01):")
    tables = {}
    for label, s in (("SENSEX", india),) + tuple(
            (a, closes_of(load_series(a, datetime.date(2025, 1, 1),
                                      datetime.date.today())))
            for a in NEIGHBOURS + ("nifty",)):
        hi = s[s.index >= "2026-01-01"].cummax()
        print(f"  {label:8s} high {hi.max():>9,.0f} -> last "
              f"{s.iloc[-1]:>9,.0f} = {(s.iloc[-1] / hi.max() - 1) * 100:+.1f}%")
        if label in NEIGHBOURS:
            tables[label] = closes_of(load_series(
                label, datetime.date(1990, 1, 1), datetime.date.today()))

    fwd_hdr = "| fwd21 | fwd63 | fwd126 |"
    for asset in NEIGHBOURS:
        s = tables[asset]
        dd = dd_series(s)
        eps = [e for e in clusters(episodes(dd))
               if india_pos(india.index, e["trough"]) is not None
               and india_pos(india.index, e["trough"]) > SIDE]
        print(f"\n## {asset}: {len(eps)} crash clusters after "
              f"{india.index[0].date()}\n")
        print("| entry | trough | depth | India in crash? | India worst dd "
              "( -63/+126 ) | India trough lag |" + fwd_hdr)
        print("|---" * 9 + "|")
        anchors = []
        for e in eps:
            i = india_pos(india.index, e["trough"])
            if i is None or i + AFTER >= n:
                continue
            anchors.append(i)
            worst = india_dd.iloc[max(0, i - SIDE):i + AFTER + 1].min()
            in_crash = india_dd.iloc[i] <= INDIA_CRASH
            lag = "-"
            overl = [x for x in india_eps
                     if x["entry"] <= e["trough"] <=
                     india.index[x["i_end"]]]
            if overl:
                it = min(overl, key=lambda x: x["depth"])
                days = (it["trough"] - e["trough"]).days
                lag = f"{days:+d} d"
            fwd = {h: (india.iloc[i + h] / india.iloc[i] - 1) * 100.0
                   if i + h < n else float("nan") for h in (21, 63, 126)}
            print(f"| {e['entry'].date()} | {e['trough'].date()} "
                  f"| {e['depth'] * 100:.0f}% "
                  f"| {'yes' if in_crash else 'no'} "
                  f"| {worst * 100:.0f}% | {lag} "
                  f"| {fwd[21]:+.1f}% | {fwd[63]:+.1f}% "
                  f"| {fwd[126]:+.1f}% |")
        if anchors:
            rl, p_l, rc, p_c = rand_stat(np.array(anchors))
            print(f"\n  anchors n={len(anchors)}: mean worst-India-dd "
                  f"{lows[anchors].mean() * 100:.1f}% vs random "
                  f"{rl * 100:.1f}% (p={p_l:.3f}); India <= -15% within "
                  f"126 sessions after {np.nanmean(crash_ahead[anchors]) * 100:.0f}% "
                  f"of anchors vs random {rc * 100:.0f}% (p={p_c:.3f})")

    print("\n## Weekly lead-lag (last session per ISO week, weekly "
          "returns)\n")
    print("| pair | contemporaneous r | neighbour -> India (+1w) r | "
          "India own (+1w) r |")
    print("|---|---|---|---|")
    for asset in NEIGHBOURS + ("nifty",):
        s = closes_of(load_series(asset, datetime.date(1990, 1, 1),
                                  datetime.date.today()))
        wk = pd.concat([s.rename("nb"), india.rename("in_")],
                       axis=1).resample("W-FRI").last().dropna()
        r_nb = wk["nb"].pct_change()
        r_in = wk["in_"].pct_change()
        print(f"| {asset} -> SENSEX | {r_nb.corr(r_in):+.2f} "
              f"| {r_nb.shift(1).corr(r_in):+.2f} "
              f"| {r_in.shift(1).corr(r_in):+.2f} |")


if __name__ == "__main__":
    main()
