"""Validation of the B-39 swing-window model (sbc.swing_model), in two parts.

A. ENTRY timing, per NIFTY session. A session is "in a window" when an Earth-planet
   aspect is within orb at 09:15 IST. Signals (no look-ahead: direction uses closes
   up to the previous session, returns run from the previous close):
     directional  the trend reversal -sign(close[t-1] - close[t-11]) on window sessions
     event        window sessions -> bigger |moves|
   Graded with the Phase 2 harness (sbc.rule_validation.grade, BH within this
   report) for all windows together, each aspect type and each planet, plus the
   incremental test against the market controls. Control: the same reversal rule
   on *every* session (reversal_every_day). An astro edge has to beat it, not just
   the drift.

B. The full model as specified (window entry, confluence exit), 2008 onward:
     - against simple exits on the same entries: hold N sessions, EMA20 break, 2xATR trailing stop
     - against random entries: RANDOM_SETS sets of the same number of entries drawn from all
       sessions, same direction rule, same confluence exit. p = share of random sets whose mean
       excess is at least the model's.
   Returns are compared as excess over the drift for the bars held
   (return - direction * mean daily return * bars), because the exits hold for different lengths.
"""

from __future__ import annotations

import datetime as dt

import numpy as np

from sbc import fingerprint_store
from sbc import helio_aspects as ha
from sbc import incremental as inc
from sbc import market_features as mf
from sbc import rule_validation as rv
from sbc import stats as st
from sbc import swing_model as sm

HORIZONS = (1, 5, 20)  # the forecast's horizons, so the component can read its verdict
SCAN_START = "2007-10-01"
TRADE_START = "2008-01-01"
RANDOM_SETS = 500


# ── A. entry timing ────────────────────────────────────────────────────────

def session_windows(dates: list[str]) -> list[list[dict]]:
    """Aspects in force at 09:15 IST on each session."""
    return [ha.active_on(d) for d in dates]


def reversal(closes: np.ndarray) -> np.ndarray:
    """-sign(close[t-1] - close[t-1-TREND_BARS]); 0 where undefined."""
    out = np.zeros(len(closes))
    n = sm.TREND_BARS
    out[n + 1:] = -np.sign(closes[n:-1] - closes[:-1 - n])
    return out


def entry_entries(dates: list[str], closes: np.ndarray, active: list[list[dict]]) -> list[dict]:
    rev = reversal(closes)
    # group name -> (window field to match, value); "all" matches any window
    groups: dict[str, tuple[str, str] | None] = {"all": None}
    groups.update({f"aspect_{code}": ("aspect", code) for code in ha.ASPECTS})
    groups.update({f"planet_{planet}": ("planet", planet) for planet in ha.PLANETS})
    entries = []
    for name, match in groups.items():
        flag = np.array([bool(a) if match is None else any(x[match[0]] == match[1] for x in a)
                         for a in active])
        entries.append({"name": f"helio_{name}_reversal", "kind": "directional", "source": "sbc.helio_aspects",
                        "description": f"Trend reversal on sessions in a {name.replace('_', ' ')} window",
                        "signal": np.where(flag, rev, 0.0)})
        entries.append({"name": f"helio_{name}_volatility", "kind": "event", "source": "sbc.helio_aspects",
                        "description": f"{name.replace('_', ' ')} window -> bigger moves", "signal": flag})
    return entries


CONTROL = {"name": "reversal_every_day", "kind": "directional", "source": "control",
           "description": "10-session trend reversal on every session (no astro)"}


def part_a(dates: list[str], closes: np.ndarray, n_perm: int) -> dict:
    active = session_windows(dates)
    entries = entry_entries(dates, closes, active)
    results = rv.grade(dates, closes, entries, HORIZONS, n_perm)
    # The control is graded on its own so it isn't part of the astro BH family.
    control = rv.grade(dates, closes, [{**CONTROL, "signal": reversal(closes)}], HORIZONS, n_perm)
    controls = mf.nifty_controls(dates, closes)
    extra = []
    for h in HORIZONS:
        fwd = st.forward_returns(closes, h)
        for e in entries:
            sig = np.asarray(e["signal"], dtype=float)
            target = fwd if e["kind"] == "directional" else np.abs(fwd)
            extra.append(((e["name"], h), inc.partial_effect(sig, target, controls, n_perm=n_perm)))
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
    window_share = float(np.mean([bool(a) for a in active]))
    return {"results": results, "control": control, "window_share": window_share}


# ── B. the model as specified ──────────────────────────────────────────────

def _excess(trades: list[dict], drift: float) -> np.ndarray:
    return np.array([t["return"] - t["direction"] * drift * t["bars"] for t in trades])


def _stats(trades: list[dict], drift: float) -> dict:
    if not trades:
        return {"n": 0}
    r = np.array([t["return"] for t in trades])
    x = _excess(trades, drift)
    return {"n": len(trades), "mean_return": float(r.mean()), "win_rate": float((r > 0).mean()),
            "mean_excess": float(x.mean()), "mean_bars": float(np.mean([t["bars"] for t in trades])),
            "mean_mae": float(np.mean([t["mae"] for t in trades])),
            "confluence_share": float(np.mean([t["exit_reason"] == "confluence" for t in trades]))}


def part_b(bars: sm.Bars, n_sets: int = RANDOM_SETS, seed: int = 0) -> dict:
    windows = ha.scan(SCAN_START, bars.dates[-1])
    first = bars.session_on_or_after(TRADE_START) or 0
    drift = float(np.mean(bars.close[first + 1:] / bars.close[first:-1] - 1))
    out: dict = {"windows": len(windows), "drift_per_bar": drift, "models": {}}
    cache: dict[tuple, dict | None] = {}

    def cached(e: int, direction: int, rule: str, need: int = 3, hold: int = 10) -> dict | None:
        key = (e, direction, rule, need, hold)
        if key not in cache:
            cache[key] = sm.trade(bars, e, direction, rule, need, hold)
        return cache[key]

    usable = [w for w in windows if w["entry_date"] >= TRADE_START]
    rng = np.random.default_rng(seed)
    eligible = np.arange(max(first, sm.TREND_BARS), len(bars.close) - sm.MAX_HOLD)
    for need in (3, 2):
        swings = [s for s in sm.swing_windows(usable, bars, need) if s["exit_reason"] != "open"]
        entries = [(bars.dates.index(s["entry_session"]), s["direction"]) for s in swings]
        model = _stats(swings, drift)
        median_bars = int(np.median([s["bars"] for s in swings])) if swings else 10
        baselines = {
            f"hold {median_bars} (model's median)": [cached(e, d, "hold", hold=median_bars) for e, d in entries],
            "hold 10": [cached(e, d, "hold", hold=10) for e, d in entries],
            "EMA20 break": [cached(e, d, "ema20") for e, d in entries],
            "2xATR trailing stop": [cached(e, d, "atr_stop") for e, d in entries],
        }
        base_stats = {k: _stats([t for t in v if t], drift) for k, v in baselines.items()}
        random_list: list[float] = []
        for _ in range(n_sets):
            pick = np.sort(rng.choice(eligible, size=min(len(entries), len(eligible)), replace=False))
            maybe = [cached(int(e), sm.direction_at(bars, int(e)), "confluence", need) for e in pick]
            trades = [t for t in maybe if t and t["exit_reason"] != "open"]
            random_list.append(float(_excess(trades, drift).mean()) if trades else 0.0)
        random_means = np.array(random_list)
        p = float((np.sum(random_means >= model.get("mean_excess", np.inf)) + 1) / (n_sets + 1)) if swings else None
        label = "strict (3 of 3)" if need == 3 else "2 of 3"
        out["models"][label] = {
            "model": model, "baselines": base_stats,
            "random": {"sets": n_sets, "mean": float(random_means.mean()),
                       "p5": float(np.quantile(random_means, 0.05)), "p95": float(np.quantile(random_means, 0.95)),
                       "p_value": p},
            "verdict": ("insufficient" if model.get("n", 0) < st.MIN_SIGNAL_DAYS
                        else "timing adds value" if p is not None and p < 0.05 else "no better than random entries"),
            "trades": swings,
        }
    return out


def run(n_perm: int = st.N_PERMUTATIONS, n_sets: int = RANDOM_SETS) -> dict:
    dates, close_list, _fps = rv.load_history()
    closes = np.asarray(close_list, dtype=float)
    bars = sm.Bars.nifty()
    a = part_a(dates, closes, n_perm)
    b = part_b(bars, n_sets)
    return {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "fingerprint_version": fingerprint_store.current_version(),
        "sample": {"first": dates[0], "last": dates[-1], "sessions": len(dates)},
        "horizons": list(HORIZONS),
        "n_permutations": n_perm,
        "orb": ha.ORB,
        "results": a["results"],
        "control": a["control"],
        "window_share": a["window_share"],
        "model": b,
    }
