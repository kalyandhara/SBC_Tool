"""Combine the six terms into a daily score, with additive lineage.

Timing: entry is day T's open and T-1's close is the last input. HistVal reads
`forward_returns`, which run from a session's open to the close `horizon`
sessions later, so a session t' has closed by T-1 exactly when t'+horizon <= T.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Mapping
import numpy as np
from sbc.navigator import terms as T
from sbc.navigator import weights as W
from sbc.navigator.profile import Profile, natal_points

BANDS = [(20, "No Trading"), (40, "Very Defensive"), (60, "Normal"),
         (80, "High Probability"), (100, "Exceptional Setup")]
ACTIONS = {"Exceptional Setup": "Trade Aggressively", "High Probability": "Trade Normally",
           "Normal": "Reduce Position Size", "Very Defensive": "Stay Cash",
           "No Trading": "Avoid Market Entirely"}
TERM_LABELS = {"transit": "Transit", "moon": "Moon", "dasha": "Dasha",
               "strength": "Planet Strength (partial)", "histval": "Historical band rank",
               "vol": "Volatility"}
VOL_WINDOW = 252
VOL_LEAD_IN = VOL_WINDOW + 1    # the T-1 close plus the full window before it
_BAND_EDGES = [hi for hi, _ in BANDS[:-1]]
_MIN_BAND_SESSIONS = 30
_NEUTRAL = 50.0


def band_of(score: int) -> str:
    return next(name for hi, name in BANDS if score <= hi)


def action_of(band: str) -> str:
    return ACTIONS[band]


def combine(terms: Mapping[str, np.ndarray]) -> np.ndarray:
    """Weighted sum, renormalised over the terms given. Without histval this is
    the HistVal base, so HistVal never feeds on itself."""
    unknown = set(terms) - set(W.TERM_WEIGHTS)
    if unknown:
        raise ValueError(f"unknown terms: {sorted(unknown)}")
    used = [k for k in W.TERM_WEIGHTS if k in terms]
    total = sum(W.TERM_WEIGHTS[k] for k in used)
    return sum(W.TERM_WEIGHTS[k] * np.asarray(terms[k], float) for k in used) / total


def forward_returns(opens, closes, horizon: int) -> np.ndarray:
    """returns[t] = closes[t+horizon-1] / opens[t] - 1; NaN if not yet closed."""
    opens, closes = np.asarray(opens, float), np.asarray(closes, float)
    out = np.full(len(opens), np.nan)
    m = len(opens) - horizon + 1
    if m > 0:
        with np.errstate(divide="ignore", invalid="ignore"):
            out[:m] = closes[horizon - 1:] / opens[:m] - 1
    return out


def _hist_val(base, returns, horizon, min_sessions):
    """(values, known): `known` marks days with a real rank, not the neutral 50."""
    base, returns = np.asarray(base, float), np.asarray(returns, float)
    if len(base) != len(returns):
        raise ValueError("base and returns must be the same length")
    n = len(base)
    out, known = np.full(n, _NEUTRAL), np.zeros(n, bool)
    bands = np.digitize(np.rint(base), _BAND_EDGES, right=True)
    valid = np.isfinite(returns)
    clean = np.where(valid, returns, np.nan)
    valid_before = np.concatenate(([0], np.cumsum(valid)))
    # Running per-band totals: index u covers sessions before u.
    in_band = [(bands == k) & valid for k in range(len(BANDS))]
    band_count = [np.concatenate(([0], np.cumsum(m))) for m in in_band]
    band_sum = [np.concatenate(([0.0], np.cumsum(np.where(m, returns, 0.0)))) for m in in_band]
    for t in range(max(min_sessions, horizon), n):
        usable = t - horizon + 1      # sessions t' with t'+horizon <= t
        k = bands[t]
        count = band_count[k][usable]
        if count < _MIN_BAND_SESSIONS:
            continue
        mean = band_sum[k][usable] / count
        out[t] = 100.0 * np.count_nonzero(clean[:usable] < mean) / valid_before[usable]
        known[t] = True
    return out, known


def hist_val(base_scores, returns, horizon: int, min_sessions: int) -> np.ndarray:
    """Rank of the current band's past mean return among all past returns, 0-100.
    Day t uses t' only if t'+horizon <= t, and `returns` must be fully known by
    the close of t'+horizon-1 (see forward_returns). Neutral 50 in the warm-up or
    with under 30 past sessions in the band."""
    return _hist_val(base_scores, returns, horizon, min_sessions)[0]


def _cents(x: float) -> int:
    return int(round(x * 100))


def _factor_lines(term, rows, weight, cents_due):
    """Factors in score points. baseline + factors == cents_due, with any residual
    on the largest active factor."""
    lines, cents = [], []
    for f in rows:
        lines.append({**f, "weight": weight})
        cents.append(_cents(weight * f["raw"] / 2.0))
    residual = cents_due - _cents(weight * _NEUTRAL) - sum(cents)
    active = [i for i, f in enumerate(lines) if not f.get("neutral")]
    if active:
        cents[max(active, key=lambda i: abs(cents[i]))] += residual
    elif residual:
        lines.append({"term": term, "label": "Rounding to whole score",
                      "raw": 0.0, "weight": weight, "adjustment": True})
        cents.append(residual)
    for line, c in zip(lines, cents):
        line["contribution"] = c / 100
    return lines


def lineage(terms_at_day: Mapping[str, float], factors: list[dict]) -> dict:
    """Displayed values add up exactly: lines to the score, and for each line with
    factors, its neutral baseline plus factors to the line."""
    values = {k: float(terms_at_day[k]) for k in W.TERM_WEIGHTS}
    score = int(np.rint(combine({k: np.array([v]) for k, v in values.items()})[0]))
    grouped = {k: [f for f in factors if f["term"] == k] for k in W.TERM_WEIGHTS}
    lines, cents = [], []
    for k, weight in W.TERM_WEIGHTS.items():
        raw_sum = sum(f["raw"] for f in grouped[k])
        clipped = abs(raw_sum) > 100.0
        shown = _NEUTRAL + raw_sum / 2.0 if clipped else values[k]
        lines.append({"term": k, "label": TERM_LABELS[k], "raw": shown if clipped else values[k],
                      "weight": weight, "baseline": weight * _NEUTRAL})
        cents.append(_cents(weight * shown))
        if clipped:
            lines.append({"term": k, "label": f"{TERM_LABELS[k]} clip to +/-100 adjustment",
                          "raw": values[k] - shown, "weight": weight, "adjustment": True,
                          "factors": []})
            cents.append(_cents(weight * values[k]) - cents[-1])
    terms_only = [i for i, line in enumerate(lines) if not line.get("adjustment")]
    largest = max(terms_only, key=lambda i: abs(cents[i]))
    cents[largest] += score * 100 - sum(cents)
    for line, c in zip(lines, cents):
        line["contribution"] = c / 100
        if not line.get("adjustment"):
            line["factors"] = _factor_lines(line["term"], grouped[line["term"]], line["weight"], c)
    moves = [{"term": k, "label": TERM_LABELS[k], "delta": round(w * (values[k] - _NEUTRAL), 2),
              "size": w * (values[k] - _NEUTRAL)} for k, w in W.TERM_WEIGHTS.items()]
    moves.sort(key=lambda m: -abs(m["size"]))
    raised = [{k: v for k, v in m.items() if k != "size"} for m in moves if m["size"] > 0]
    lowered = [{k: v for k, v in m.items() if k != "size"} for m in moves if m["size"] < 0]
    return {"score": score, "contributions": lines, "raised": raised, "lowered": lowered}


@dataclass
class ScoreSeries:
    days: list[str]
    score: np.ndarray                  # integers, as displayed and banded
    base: np.ndarray                   # the five non-HistVal terms, renormalised
    terms: dict[str, np.ndarray]
    factors: Callable[[int], list[dict]]


def _vol_with_lead_in(days, vix):
    lead = sorted(d for d in vix if d < days[0])[-VOL_LEAD_IN:]
    vol = T.vol_term(lead + list(days), vix, window=VOL_WINDOW, min_history=VOL_WINDOW)
    return vol, len(lead)


def score_series(sky, profile: Profile, opens, closes, vix: Mapping[str, float],
                 min_sessions: int = W.HIST_MIN_YEARS * 252,
                 horizon: int = W.HIST_HORIZON) -> ScoreSeries:
    """opens and closes align with sky.days, which must be sorted sessions; NaN
    marks prices not yet known."""
    days, n = sky.days, len(sky.days)
    if len(opens) != n or len(closes) != n:
        raise ValueError("opens and closes must align with sky.days")
    natal = natal_points(profile)
    transit = T.transit_term(sky, natal)
    moon = T.moon_term(sky)
    dasha = T.dasha_term(sky, natal["Moon"], profile.birth_date)
    strength = T.strength_term(sky)
    vol, lead = _vol_with_lead_in(days, vix)
    five = {"transit": transit.values, "moon": moon.values, "dasha": dasha.values,
            "strength": strength.values, "vol": vol.values[lead:]}
    base = combine(five)
    hist, known = _hist_val(base, forward_returns(opens, closes, horizon), horizon, min_sessions)
    terms = {**five, "histval": hist}
    score = np.rint(combine(terms)).astype(int)

    def factors(i):
        i = range(n)[i]
        if known[i]:
            hist_row = {"term": "histval", "raw": 2.0 * hist[i] - 100.0,
                        "label": f"Past returns for this band at percentile {hist[i]:.0f}"}
        else:
            hist_row = {"term": "histval", "raw": 0.0, "neutral": True,
                        "label": "Past return history too short, neutral value used"}
        return (transit.factors(i) + moon.factors(i) + dasha.factors(i) + strength.factors(i)
                + [hist_row] + vol.factors(i + lead))
    return ScoreSeries(list(days), score, base, terms, factors)


def day_lineage(series: ScoreSeries, i: int) -> dict:
    return lineage({k: float(v[i]) for k, v in series.terms.items()}, series.factors(i))
