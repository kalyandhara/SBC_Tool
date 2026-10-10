"""Rebuild third-party monthly score (B-47).

Gated on B-40 verdict. This module provides a scaffold for fitting
weights to published monthly scores using features from B-42..B-46.

Do not enable in production until score_external() shows an edge over
baseline for >=2 months.
"""

from __future__ import annotations

import datetime as dt
from typing import List, Dict

ENABLED = False  # flip to True only after B-40 verdict shows edge

def _require_enabled():
    if not ENABLED:
        raise RuntimeError(
            "B-47 is gated on B-40 verdict. "
            "Enable ENABLED=True only after third-party score beats baseline for >=2 months."
        )

def fit_monthly_weights(month: str, source: str = "third_party_monthly") -> Dict:
    """Fit linear weights to reproduce published monthly scores.

    Args:
        month: YYYY-MM
        source: external_forecasts source name

    Returns:
        dict with fitted coefficients, R², and caveat.
    """
    _require_enabled()
    from sbc.forecast_ledger import get_external
    from sbc.market_store import get_daily
    from sbc import fingerprint_store

    # Load published scores
    year, mon = map(int, month.split("-"))
    import calendar
    start = dt.date(year, mon, 1)
    end = dt.date(year, mon, calendar.monthrange(year, mon)[1])
    rows = get_external(source, start.isoformat(), end.isoformat())
    if not rows:
        raise ValueError(f"No external scores for {source} {month}")

    # Build feature matrix - placeholder
    # Features to use once B-42..B-46 are stable:
    #   station count, aspect exact count, latitude, declination, speed, ghabad flag
    X = []
    y = []
    for r in rows:
        d = dt.date.fromisoformat(r["date"])
        fp = fingerprint_store.get(d.isoformat())
        # Placeholder feature: sbc classical net
        feat = float(fp.get("sbc", {}).get("classical", {}).get("net", 0.0))
        X.append([1.0, feat])  # intercept + feature
        y.append(float(r["score"]))

    # Simple OLS placeholder
    import numpy as np
    Xmat = np.array(X)
    yvec = np.array(y)
    # Solve via least squares
    coeffs, residuals, rank, s = np.linalg.lstsq(Xmat, yvec, rcond=None)
    y_pred = Xmat @ coeffs
    ss_res = ((yvec - y_pred) ** 2).sum()
    ss_tot = ((yvec - yvec.mean()) ** 2).sum()
    r2 = 1 - ss_res / ss_tot if ss_tot else float("nan")

    return {
        "month": month,
        "source": source,
        "n": len(rows),
        "coeffs": coeffs.tolist(),
        "r2": float(r2),
        "caveat": "B-47 is gated. Model is illustrative only. Do not trade on it.",
        "gated": True,
    }

def rebuild_monthly_score(month: str, source: str = "third_party_monthly") -> List[Dict]:
    """Reproduce monthly score series using fitted weights.

    Returns list of {date, score_published, score_rebuilt}.
    """
    res = fit_monthly_weights(month, source)
    # placeholder: return empty
    return []
