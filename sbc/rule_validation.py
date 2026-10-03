"""Run every rule in sbc.rule_signals against NIFTY history and grade it.

For each rule and horizon (1, 5, 20 sessions) it reports the full-sample
statistic and p-value (sbc.stats), the Benjamini-Hochberg q-value across all
tests, the same statistic in each era, and the share of years in which the
rule was right on balance.

Eras: 2007-2020 is the cleaner out-of-sample period; the ad-hoc backtests in
scripts/adhoc were run on 2021+ data, so 2021-2026 may flatter a rule.

Verdict (per rule and horizon):
  edge          q < 0.05 and the effect has the same sign in both eras
  inconsistent  q < 0.05 but the eras disagree
  no edge       q >= 0.05
  insufficient  fewer than stats.MIN_SIGNAL_DAYS signal days
"""

from __future__ import annotations

import datetime as dt

import numpy as np

from sbc import fingerprint_store, market_store
from sbc import stats as st
from sbc.rule_signals import RULES, signals_for

HORIZONS = (1, 5, 20)
ERA_SPLIT = "2021-01-01"
Q_THRESHOLD = 0.05


def _era(date: str) -> str:
    return "2007-2020" if date < ERA_SPLIT else "2021-2026"


def load_history(start: str | None = None, end: str | None = None):
    """(dates, closes, fingerprints) for every NIFTY session in market.db."""
    bars = market_store.get_daily("NIFTY", start, end)
    if not bars:
        raise RuntimeError("no NIFTY bars in market.db; run scripts/refresh_market_data.py --full")
    dates = [b["date"] for b in bars]
    stored = {fp["date"]: fp for fp in fingerprint_store.get_range(dates[0], dates[-1])}
    fps = [stored.get(d) or fingerprint_store.get(d) for d in dates]
    return dates, [b["close"] for b in bars], fps


def _verdict(res: dict, eras: dict) -> str:
    if res.get("status") != "ok":
        return "insufficient"
    q = res.get("q")
    if q is None or not np.isfinite(q) or q >= Q_THRESHOLD:
        return "no edge"
    signs = {np.sign(v) for v in eras.values() if v is not None}
    return "edge" if signs == {np.sign(res["excess"])} else "inconsistent"


def run(horizons=HORIZONS, n_perm: int = st.N_PERMUTATIONS,
        start: str | None = None, end: str | None = None) -> dict:
    dates, closes, fps = load_history(start, end)
    signals = signals_for(fps)
    eras = [_era(d) for d in dates]
    years = [d[:4] for d in dates]

    results = []
    for h in horizons:
        fwd = st.forward_returns(closes, h)
        absret = np.abs(fwd)
        for rule in RULES:
            sig = signals[rule.name]
            if rule.kind == "directional":
                res = st.evaluate_directional(sig, fwd, n_perm=n_perm)
                era_stats = st.by_period(sig, fwd, eras)
                yearly = st.by_period(sig, fwd, years)
            else:
                flag = [int(bool(x)) for x in sig]
                res = st.evaluate_event(flag, fwd, n_perm=n_perm)
                era_stats = st.by_period(flag, absret, eras, st.vol_stat)
                yearly = st.by_period(flag, absret, years, st.vol_stat)
            known = [v for v in yearly.values() if v is not None]
            results.append({
                "rule": rule.name, "kind": rule.kind, "source": rule.source,
                "description": rule.description, "horizon": h, **res,
                "eras": era_stats,
                "years_right": sum(v > 0 for v in known), "years": len(known),
            })

    qs = st.bh_adjust([r.get("p", float("nan")) for r in results])
    for r, q in zip(results, qs, strict=True):
        r["q"] = q
        r["verdict"] = _verdict(r, r["eras"])

    return {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "fingerprint_version": fingerprint_store.current_version(),
        "sample": {"first": dates[0], "last": dates[-1], "sessions": len(dates)},
        "horizons": list(horizons),
        "n_permutations": n_perm,
        "results": results,
    }
