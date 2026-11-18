"""The Today card's stance rule, fixed before any result was seen (rule-1).

Timing: T is the session the card is for, chosen from the IST clock. Every input
is as of the T-1 close: rows dated T or later are never read, so a partial bar for
T cannot leak in. Change any constant here: bump RULE_VERSION and disclose it."""
from __future__ import annotations

import datetime as dt
from bisect import bisect_left
from collections.abc import Mapping
from typing import Any

import numpy as np

from sbc.navigator import scoring as S
from sbc.market_holidays import is_trading_day, next_trading_day

RULE_VERSION = "rule-1"
SESSION_CLOSE = dt.time(15, 30)
TREND_FAST, TREND_SLOW = 20, 50
VIX_WINDOW, VIX_HIGH_PCT = 252, 80.0
LONG, SHORT, ASIDE = "Long bias", "Short bias", "Stand aside"
BAND_MULT = {"Exceptional Setup": 1.0, "High Probability": 0.75, "Normal": 0.5}
CONTROL_MULT = 0.5
SHORT_COST_NOTE = ("Shorts are charged the same 10 bps round trip as longs. Futures roll, "
                   "option premium and margin are not modelled.")


def session_for(now_ist: dt.datetime) -> dt.date:
    today = now_ist.date()
    if is_trading_day(today) and now_ist.time() < SESSION_CLOSE:
        return today
    return next_trading_day(today, inclusive=False)


def previous_trading_day(day: str) -> str:
    d = dt.date.fromisoformat(day) - dt.timedelta(days=1)
    while not is_trading_day(d):
        d -= dt.timedelta(days=1)
    return d.isoformat()


def trend_of(closes: Any) -> str:
    """Closes up to and including T-1."""
    c = np.asarray(closes, float)
    if len(c) < TREND_SLOW or not np.isfinite(c[-TREND_SLOW:]).all():
        return "Mixed"
    last, fast, slow = c[-1], c[-TREND_FAST:].mean(), c[-TREND_SLOW:].mean()
    if last > fast > slow:
        return "Up"
    if last < fast < slow:
        return "Down"
    return "Mixed"


def _regime(pct: float) -> str:
    return "Unknown" if np.isnan(pct) else ("High" if pct >= VIX_HIGH_PCT else "Normal")


def vix_regime(days_before_t: list[str], t: str, vix: Mapping[str, float]) -> str:
    """Same percentile the score's Vol term uses for session t (T-1 close, session-day window)."""
    pcts = S.vol_percentiles_with_lead_in(list(days_before_t) + [t], {d: v for d, v in vix.items() if d < t})
    return _regime(float(pcts[-1]))


def inputs_before(days: list[str], closes: Any, vix: Mapping[str, float], t: str) -> dict[str, Any]:
    """`days` sorted ascending ISO dates; `closes` aligned with `days`. When stale (T-1
    missing) the VIX regime is "Unknown", matching the score's neutral Vol term."""
    k = bisect_left(days, t)
    if k == 0:
        return {"t_minus_1": None, "stale": True, "trend": "Mixed", "vix": "Unknown"}
    t1 = days[k - 1]
    stale = t1 < previous_trading_day(t)
    # Stale: the score drops the last row's VIX, so its Vol term is neutral; the regime agrees.
    return {"t_minus_1": t1, "stale": stale, "trend": trend_of(np.asarray(closes, float)[:k]),
            "vix": "Unknown" if stale else vix_regime(days[:k], t, vix)}


def stance(band: str, trend: str, vix: str) -> dict[str, Any]:
    if band not in BAND_MULT:
        side = ASIDE
    elif trend == "Up":
        side = LONG
    elif trend == "Down":
        side = SHORT
    else:
        side = ASIDE
    mult = 0.0 if side == ASIDE else BAND_MULT[band] * (0.5 if vix == "High" else 1.0)
    return {"stance": side, "multiplier": mult, "band": band, "trend": trend, "vix": vix,
            "rule_version": RULE_VERSION}


def control(trend: str, vix: str) -> dict[str, Any]:
    """The rule without its astro gate: trend alone at a fixed half size."""
    side = {"Up": LONG, "Down": SHORT}.get(trend, ASIDE)
    mult = 0.0 if side == ASIDE else CONTROL_MULT * (0.5 if vix == "High" else 1.0)
    return {"stance": side, "multiplier": mult}
