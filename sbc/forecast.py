"""One NIFTY forecast per (session, horizon): evidence first, probability second.

    forecast(day, horizon) -> {
      date, horizon, entry_date, entry_close, data_as_of, model_version, status, caveat,
      probability_up      base rate, adjusted only by *validated* components
      base                historical up share and mean return for this horizon
      expected_range      VIX-implied 68% / 95% bands and historical return quantiles
      components          every rule and analog variant: today's lean plus its verdicts
      validated           names of components that passed both tests (none so far)
      sky                 key facts from the fingerprint
      track_record        this horizon's live ledger score (sbc.daily_ledger)
    }

A component is *validated* only when its rule/analog validation verdict is
"edge" AND the incremental test says it "adds information" beyond the market
controls. Only validated components move probability_up, by their historical
conditional up share minus the base rate. With none validated, probability_up
is the base rate: the honest answer to "will NIFTY rise over the next h
sessions?" given what this tool can show.
"""

from __future__ import annotations

import datetime as dt
import math
from functools import lru_cache

import numpy as np

from sbc import analog_validation as av
from sbc import analogs as an
from sbc import fingerprint_store, market_store, research_reports
from sbc import stats as st
from sbc.market_holidays import is_trading_day
from sbc.rule_signals import RULES, signals_for

HORIZONS = (1, 5, 20)
CAVEAT = ("Research output, not investment advice. No astro component has passed validation; "
          "the probability shown is the historical base rate.")


@lru_cache(maxsize=1)
def model_version() -> str:
    from sbc.engine_version import module_version
    return module_version("sbc.forecast")


def _validated(rule: str, horizon: int, verdict_prefix: str) -> tuple[dict | None, dict | None, bool]:
    grade = research_reports.result(verdict_prefix, rule, horizon)
    extra = research_reports.result("incremental_validation", rule, horizon)
    ok = bool(grade and grade.get("verdict") == "edge"
              and extra and extra.get("verdict") == "adds information")
    return grade, extra, ok


def _summary(grade: dict | None, extra: dict | None) -> dict:
    out = {}
    if grade:
        out["validation"] = {k: grade.get(k) for k in ("verdict", "hit_rate", "baseline", "excess", "q")}
        out["validation"]["report"] = grade["_file"]
    if extra:
        out["beyond_market"] = {k: extra.get(k) for k in ("verdict", "beta", "q")}
    return out


def _sky(fp: dict) -> dict:
    p = fp["planets"]
    slow = {n: f"{p[n]['sign_name']} / {p[n]['nakshatra_name']}" + (" (R)" if p[n]["retrograde"] else "")
            for n in ("Jupiter", "Saturn", "Rahu", "Ketu")}
    exact = [f"{a['a']} {a['aspect']} {a['b']} ({a['orb']:.1f}°, {'applying' if a['applying'] else 'separating'})"
             for a in fp["aspects"] if a["orb"] <= 1.0 and "Moon" not in (a["a"], a["b"])]
    retro = [n for n in ("Mercury", "Venus", "Mars", "Jupiter", "Saturn") if p[n]["retrograde"]]
    pan, ecl = fp["panchang"], fp["eclipse"]
    eclipse = None
    for days, kind, when in ((ecl["days_to"], ecl["to_type"], "in"), (ecl["days_since"], ecl["since_type"], "ago")):
        if days is not None and days <= 14:
            eclipse = f"{kind} eclipse {days:.0f} days {when}" if when == "ago" else f"{kind} eclipse in {days:.0f} days"
    return {
        "slow_planets": slow,
        "retrograde": retro,
        "exact_aspects": exact,
        "moon": f"{p['Moon']['sign_name']} / {p['Moon']['nakshatra_name']}",
        "tithi": f"{pan['paksha']} {pan['tithi'] if pan['tithi'] <= 15 else pan['tithi'] - 15} ({pan['tithi_group']})",
        "bhadra_at_open": pan["vishti"],
        "eclipse": eclipse,
        "sbc_net": {k: v["net"] for k, v in fp["sbc"].items()},
    }


def _range(entry_close: float, horizon: int, vix: float | None, hist: np.ndarray) -> dict:
    out: dict = {"entry_close": entry_close}
    if vix and math.isfinite(vix):
        sigma = vix / 100.0 / math.sqrt(252) * math.sqrt(horizon)
        out["vix"] = vix
        out["sigma"] = sigma
        out["band_68"] = [round(entry_close * (1 - sigma), 1), round(entry_close * (1 + sigma), 1)]
        out["band_95"] = [round(entry_close * (1 - 1.96 * sigma), 1), round(entry_close * (1 + 1.96 * sigma), 1)]
    h = hist[np.isfinite(hist)]
    if len(h):
        out["historical_quantiles"] = {str(q): float(np.quantile(h, q / 100)) for q in (5, 25, 50, 75, 95)}
    return out


def forecast(day: str, horizon: int = 5, history: an.History | None = None) -> dict:
    """Forecast for NIFTY over `horizon` sessions, entering at the close before `day`."""
    if horizon not in HORIZONS:
        raise ValueError(f"horizon must be one of {HORIZONS}")
    target = dt.date.fromisoformat(day)
    if not is_trading_day(target):
        raise ValueError(f"{day} is not an NSE trading day")
    history = history or an.load_nifty_history()
    dates, closes = history.dates, history.closes
    entry_index = int(np.searchsorted(dates, day)) - 1
    if entry_index < 0:
        raise ValueError("no NIFTY history before this date")

    fwd = history.fwd[horizon]
    known = fwd[:history.usable_before(entry_index, horizon)]
    known = known[np.isfinite(known)]
    base_up = float((known > 0).mean())
    base = {"up_share": base_up, "mean": float(known.mean()), "n": int(len(known))}

    fp = fingerprint_store.get(day)
    signals = signals_for([fp])
    components, validated = [], []
    for rule in RULES:
        if rule.source == "control":
            continue
        grade, extra, ok = _validated(rule.name, horizon, "rule_validation")
        value = signals[rule.name][0]
        components.append({"name": rule.name, "kind": rule.kind, "description": rule.description,
                           "lean": int(value) if rule.kind == "directional" else None,
                           "flag": bool(value) if rule.kind == "event" else None,
                           "validated": ok, **_summary(grade, extra)})
        if ok:
            validated.append(rule.name)

    for variant, weights in av.VARIANTS.items():
        res = an.find_analogs(history, fp, horizon, None, an.TOP_K, weights=weights)
        grade, extra, ok = _validated(variant, horizon, "analog_validation")
        summary = res["summary"] or {}
        components.append({"name": variant, "kind": "directional", "description": av.DESCRIPTIONS[variant],
                           "lean": summary.get("lean", 0), "analog_excess": summary.get("excess"),
                           "analog_up_share": summary.get("up_share"),
                           "pool_up_share": summary.get("base_up_share"),
                           "best_similarity": res.get("best_similarity"), "validated": ok,
                           **_summary(grade, extra)})
        if ok:
            validated.append(variant)

    prob = base_up + sum(_adjustment(c, history, horizon, entry_index) for c in components if c["validated"])
    vix_rows = market_store.get_daily("INDIAVIX", end=dates[entry_index])
    vix = vix_rows[-1]["close"] if vix_rows else None

    from sbc import daily_ledger
    return {
        "date": day,
        "horizon": horizon,
        "entry_date": dates[entry_index],
        "entry_close": float(closes[entry_index]),
        "data_as_of": dates[-1],
        "model_version": model_version(),
        "status": "research",
        "probability_up": round(min(max(prob, 0.01), 0.99), 4),
        "base": base,
        "validated": validated,
        "confidence": "none: no validated component" if not validated else f"{len(validated)} validated component(s)",
        "expected_range": _range(float(closes[entry_index]), horizon, vix, known),
        "components": components,
        "sky": _sky(fp),
        "track_record": daily_ledger.summary(horizon),
        "caveat": CAVEAT,
    }


def _adjustment(component: dict, history: an.History, horizon: int, entry_index: int) -> float:
    """Shift in up-probability that a *validated* component justifies.

    Rules: historical up share on sessions where the rule leaned the same way, minus
    the up share of all sessions (outcomes known at entry only). Analogs: the up share
    after today's analogs minus that of the whole eligible pool.
    """
    lean = component.get("lean")
    if not lean:
        return 0.0
    if "analog_up_share" in component:
        return float(component["analog_up_share"] - component["pool_up_share"])
    n = history.usable_before(entry_index, horizon)
    dates = history.dates[:n]
    stored = {fp["date"]: fp for fp in fingerprint_store.get_range(dates[0], dates[-1])} if dates else {}
    past = signals_for([stored.get(d) or fingerprint_store.get(d) for d in dates]).get(component["name"])
    if past is None:
        return 0.0
    fwd = history.fwd[horizon][:n]
    known = np.isfinite(fwd)
    same = (np.asarray(past) == lean) & known
    if same.sum() < st.MIN_SIGNAL_DAYS:
        return 0.0
    return float((fwd[same] > 0).mean() - (fwd[known] > 0).mean())
