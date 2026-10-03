"""Grade the Phase 6 candidate factors (sbc.factors) on NIFTY, both tests in one report.

1. Harness (sbc.rule_validation.grade): directional factors on excess return,
   event factors on |return|; BH across this report only.
2. Beyond the market (sbc.incremental.partial_effect): the same signal after the
   12 market controls. Directional factors are tested on the signed forward
   return, event factors on |forward return|, where VIX and recent volatility
   already explain a lot, so a volatility factor has to beat them.

A factor counts in the forecast only with verdict "edge" AND beyond_market
"adds information" (sbc.forecast reads both from this report).
"""

from __future__ import annotations

import datetime as dt

import numpy as np

from sbc import factors as fx
from sbc import fingerprint_store
from sbc import incremental as inc
from sbc import market_features as mf
from sbc import rule_validation as rv
from sbc import stats as st

HORIZONS = (1, 5, 20)


def run(n_perm: int = st.N_PERMUTATIONS, horizons=HORIZONS, start: str | None = None,
        end: str | None = None) -> dict:
    dates, closes, fps = rv.load_history(start, end)
    d0 = (dt.date.fromisoformat(dates[0]) - dt.timedelta(days=1)).isoformat()
    d1 = (dt.date.fromisoformat(dates[-1]) + dt.timedelta(days=1)).isoformat()
    by_date = {fp["date"]: fp for fp in fingerprint_store.get_range(d0, d1)}
    signals = fx.signals_for(fps, lambda d: by_date.get(d) or fingerprint_store.get(d))

    entries = [{"name": f.name, "kind": f.kind, "source": "sbc.factors", "description": f.description,
                "signal": signals[f.name]} for f in fx.FACTORS]
    results = rv.grade(dates, closes, entries, horizons, n_perm)

    controls = mf.nifty_controls(dates, np.asarray(closes, dtype=float))
    extra = []
    for h in horizons:
        fwd = st.forward_returns(closes, h)
        for f in fx.FACTORS:
            sig = np.asarray([float(x) for x in signals[f.name]])
            target = fwd if f.kind == "directional" else np.abs(fwd)
            extra.append(((f.name, h), inc.partial_effect(sig, target, controls, n_perm=n_perm)))
    qs = st.bh_adjust([r.get("p", float("nan")) for _, r in extra])
    beyond = {}
    for (key, r), q in zip(extra, qs, strict=True):
        r["q"] = q
        r["verdict"] = ("insufficient" if r["status"] != "ok"
                        else "adds information" if q < 0.05 else "nothing beyond the market")
        beyond[key] = r
    for r in results:
        b = beyond[(r["rule"], r["horizon"])]
        r["beyond_market"] = {k: b.get(k) for k in ("verdict", "beta", "beta_raw", "p", "q", "n")}
        r["signal_days"] = int(sum(1 for x in signals[r["rule"]] if x))

    return {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "fingerprint_version": fingerprint_store.current_version(),
        "sample": {"first": dates[0], "last": dates[-1], "sessions": len(dates)},
        "horizons": list(horizons),
        "n_permutations": n_perm,
        "controls": list(mf.CONTROL_NAMES),
        "results": results,
    }
