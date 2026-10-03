"""Out-of-sample test of the sector vedha scenarios in sbc.sector_signals.

Every scenario finding states a planet pair X -> Y (an SBC vedha ray from X onto
Y's cell), a target market, a horizon h and the historical average return on
active days. Those numbers were fitted on 2021-08 .. 2026-08 data
(scripts/adhoc/backtest_{plantation,fertilizer,foodinflation,copper}.py), so the
honest test is the history *before* 2021-08, which the fit never saw.

For each finding:
  signal  sign(claimed avg) on every target trading day the pair is active, else 0
  return  close[t+h] / close[t] - 1 (the convention the adhoc backtests used)
  graded  with sbc.stats.evaluate_directional (excess over the target's own drift,
          circular-shift p-value) separately on the out-of-sample years and on
          the fit window; BH across the out-of-sample tests.

The fit-window row is a replication check: if it doesn't reproduce the claimed
effect, the test isn't measuring what the scenario claimed.

Baskets are equal-weight averages of the components' daily returns. Prices are
unadjusted (yfinance Close, as in the adhoc backtests), so a daily move beyond
SPLIT_JUMP is treated as a split or bonus issue and neutralized.

Verdict (out-of-sample): edge (q < 0.05, right way), wrong way (q < 0.05,
opposite), no edge, insufficient (< stats.MIN_SIGNAL_DAYS signal days).
"""

from __future__ import annotations

import datetime as dt

import numpy as np

from sbc import market_store
from sbc import sector_signals as ss
from sbc import stats as st

FIT_START = "2021-08-01"
SPLIT_JUMP = 0.35
Q_THRESHOLD = 0.05

TARGETS = {
    "Copper HG=F": ["HG"], "Coffee KC=F": ["KC"], "FCX": ["FCX"], "HindCopper": ["HINDCOPPER"],
    "RCF": ["RCF"], "NFL": ["NFL"], "GNFC": ["GNFC"], "Coromandel": ["COROMANDEL"],
    "Tea proxy": ["MCLEODRUSS"],
    "Fert basket": ["CHAMBLFERT", "COROMANDEL", "GNFC", "RCF", "NFL", "DEEPAKFERT"],
    "Food basket": ["SB", "ZW", "ZC", "ZR"],
    "FMCG basket": ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA"],
    "Agri-chem basket": ["UPL", "PIIND", "RALLIS", "DHANUKA"],
}


def series(target: str) -> tuple[list[str], np.ndarray, int]:
    """(dates, index level, neutralized jumps) for a target; equal-weight daily returns for baskets."""
    members = TARGETS[target]
    rets: dict[str, dict[str, float]] = {}
    jumps = 0
    for sym in members:
        bars = market_store.get_daily(sym)
        closes = [(b["date"], b["close"]) for b in bars if b["close"] and b["close"] > 0]
        for (_, c0), (d1, c1) in zip(closes, closes[1:], strict=False):
            r = c1 / c0 - 1.0
            if abs(r) > SPLIT_JUMP:
                r, jumps = 0.0, jumps + 1
            rets.setdefault(d1, {})[sym] = r
    if not rets:
        raise market_store.MarketDataMissing(
            f"no bars for {target}; run scripts/refresh_market_data.py --research --full")
    need = 1 if len(members) == 1 else 2
    dates = [d for d in sorted(rets) if len(rets[d]) >= need]
    level = np.cumprod([1.0 + float(np.mean(list(rets[d].values()))) for d in dates])
    return dates, level, jumps


def claim_returns(level: np.ndarray, h: int) -> np.ndarray:
    """close[t+h] / close[t] - 1, NaN where the window runs off the end."""
    out = np.full(len(level), np.nan)
    if len(level) > h:
        out[:-h] = level[h:] / level[:-h] - 1.0
    return out


def findings() -> list[dict]:
    """One row per (scenario, finding) with a target we can price."""
    out = []
    for spec in ss.SCENARIOS:
        for f in spec["findings"]:
            if f["target"] not in TARGETS:
                continue
            out.append({"pair": spec["pair"], "group": spec["group"], "sector": spec["sector"],
                        "target": f["target"], "h": f["h"], "claimed_avg": f["avg"] / 100.0,
                        "claimed_win": f["win"] / 100.0, "claimed_n": f["n"],
                        "direction": 1 if f["avg"] > 0 else -1})
    return out


def _period(sig: np.ndarray, fwd: np.ndarray, mask: np.ndarray, n_perm: int) -> dict:
    s = np.where(mask, sig, 0)
    r = np.where(mask, fwd, np.nan)
    res = st.evaluate_directional(s, r, n_perm=n_perm)
    on = (s != 0) & np.isfinite(r)
    if on.any():
        res["mean_on"] = float(r[on].mean())
        res["up_share_on"] = float((r[on] > 0).mean())
    return res


def run(n_perm: int = st.N_PERMUTATIONS) -> dict:
    rows = findings()
    cache: dict[str, tuple] = {}
    results = []
    for row in rows:
        if row["target"] not in cache:
            dates, level, jumps = series(row["target"])
            active = [ss._active_pairs(d) for d in dates]
            cache[row["target"]] = (dates, level, jumps, active)
        dates, level, jumps, active = cache[row["target"]]
        sig = np.array([row["direction"] if row["pair"] in a else 0 for a in active], dtype=float)
        fwd = claim_returns(level, row["h"])
        before = np.array([d < FIT_START for d in dates])
        oos = _period(sig, fwd, before, n_perm)
        fit = _period(sig, fwd, ~before, n_perm)
        results.append({**row, "pair": f"{row['pair'][0]} -> {row['pair'][1]}",
                        "first": dates[0], "jumps_neutralized": jumps, "oos": oos, "fit": fit})

    qs = st.bh_adjust([r["oos"].get("p", float("nan")) for r in results])
    for r, q in zip(results, qs, strict=True):
        r["oos"]["q"] = q
        r["verdict"] = _verdict(r["oos"])
        r["replicates"] = (r["fit"].get("status") == "ok" and r["fit"]["excess"] > 0)
    return {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "fit_start": FIT_START,
        "n_permutations": n_perm,
        "targets": {t: {"members": m, "first": cache[t][0][0], "last": cache[t][0][-1],
                        "sessions": len(cache[t][0])} for t, m in TARGETS.items() if t in cache},
        "results": results,
    }


def _verdict(res: dict) -> str:
    if res.get("status") != "ok":
        return "insufficient"
    q = res.get("q")
    if q is None or not np.isfinite(q) or q >= Q_THRESHOLD:
        return "no edge"
    return "edge" if res["excess"] > 0 else "wrong way"
