"""Event anchors and clusters for the sector rotation study (phase 1).

Core events, each a dict {"date", "event"} with IST dates from the existing generators:
Mercury retrograde starts (sbc.stations), solar and lunar eclipses and Jupiter/Saturn sign
ingresses (sbc.transit_almanac). Pure functions only; grading lives elsewhere.
"""

from __future__ import annotations

import bisect
import datetime as dt
from collections import Counter

import numpy as np

from sbc import incremental as inc
from sbc import stations
from sbc import stats as st
from sbc import transit_almanac as ta

CLUSTER_GAP = 20  # sessions; events closer than this merge into one cluster
SLOW_PLANETS = ("Jupiter", "Saturn")
ECLIPSE_EVENT = {"Solar": "SOLAR_ECLIPSE", "Lunar": "LUNAR_ECLIPSE"}


def anchor_session(sessions: list[str], day: str) -> int | None:
    """Index of the first session on or after `day`, or None if past the last session."""
    i = bisect.bisect_left(sessions, day)
    return i if i < len(sessions) else None


def cluster(anchors: list[int], gap: int = CLUSTER_GAP) -> list[list[int]]:
    """Group sorted anchor indices so that consecutive members are < gap sessions apart."""
    out: list[list[int]] = []
    for a in sorted(anchors):
        if out and a - out[-1][-1] < gap:
            out[-1].append(a)
        else:
            out.append([a])
    return out


def mercury_events(rows: list[dict]) -> list[dict]:
    """One MERCURY_RETROGRADE_START per retrograde window.

    rows: station rows as sbc.stations.by_date returns them, any planets.
    window_end is the date of the next Mercury direct station, or None if none is in rows.
    """
    mercury = sorted((r for r in rows if r["planet"] == "Mercury"), key=lambda r: r["date"])
    out = []
    for i, r in enumerate(mercury):
        if r["direction"] != "retrograde":
            continue
        end = next((n["date"] for n in mercury[i + 1:] if n["direction"] == "direct"), None)
        out.append({"date": r["date"], "event": "MERCURY_RETROGRADE_START", "window_end": end})
    return out


def core_events(first_year: int, last_year: int) -> list[dict]:
    """Core four events from first_year through last_year, sorted by date.

    Mercury windows that start in range are kept even when they end after last_year,
    because the station lookup runs one extra year ahead to find each window's end.
    Stations are queried in 8-year chunks to stay within sbc.stations.between's 10-year limit.
    """
    rows = []
    chunk_start = first_year
    while chunk_start <= last_year + 1:
        chunk_end = min(chunk_start + 7, last_year + 1)
        stat_rows = stations.by_date(dt.date(chunk_start, 1, 1), dt.date(chunk_end, 12, 31), ("Mercury",))
        for day_rows in stat_rows.values():
            rows.extend(day_rows)
        chunk_start = chunk_end + 1
    out = [e for e in mercury_events(rows) if first_year <= int(e["date"][:4]) <= last_year]
    for year in range(first_year, last_year + 1):
        for body in ta.build(year, "sidereal")["bodies"]:
            for e in body["events"]:
                if e["type"] == "eclipse":
                    out.append({"date": e["date"], "event": ECLIPSE_EVENT[e["kind"]]})
                elif e["type"] == "ingress" and e["body"] in SLOW_PLANETS:
                    out.append({"date": e["date"], "event": f"{e['body'].upper()}_INGRESS"})
    return sorted(out, key=lambda e: (e["date"], e["event"]))


def window_return(closes: np.ndarray, anchor: int, h: int) -> float:
    """close[anchor + h] / close[anchor] - 1; NaN if out of range or either bar is missing."""
    end = anchor + h
    if anchor < 0 or end >= len(closes):
        return float("nan")
    c0, c1 = closes[anchor], closes[end]
    if not (np.isfinite(c0) and np.isfinite(c1)) or c0 <= 0:
        return float("nan")
    return float(c1 / c0 - 1.0)


def rank_sectors(returns: dict[str, float]) -> list[tuple[str, float]]:
    """Sectors with a finite return, highest first. NaN sectors are dropped; the caller counts them."""
    valid = [(s, r) for s, r in returns.items() if np.isfinite(r)]
    return sorted(valid, key=lambda kv: kv[1], reverse=True)


def relative_strength(sector_ret: float, nifty_ret: float) -> float:
    """Sector return minus NIFTY return over the same window."""
    return sector_ret - nifty_ret


CONFIRMATORY: list[dict] = []  # pre-registration: "Confirmatory list: empty." Nothing is graded as a finding.
Q_THRESHOLD = 0.05
MIN_CLUSTERS = 8  # out-of-sample independent clusters with a signal day (pre-registration)


def grade_confirmatory(hypotheses: list[dict], signals_by_id: dict[str, np.ndarray],
                       fwd_by_h: dict[int, np.ndarray], era_mask: np.ndarray,
                       clusters: np.ndarray, controls: np.ndarray) -> list[dict]:
    """Grade confirmatory hypotheses. A pass needs every pre-registered condition.

    signals_by_id: 0/1 indicator per session; the hypothesis direction is applied here.
    fwd_by_h: sector minus NIFTY forward return over h sessions, per session.
    era_mask: True on out-of-sample sessions.
    clusters: cluster id per session, -1 where the session is in no cluster.
    controls: market control matrix per session, for the incremental test.
    """
    era_mask = np.asarray(era_mask, dtype=bool)
    clusters = np.asarray(clusters)
    oos, ins = era_mask, ~era_mask
    rows = []
    for hyp in hypotheses:
        sig = np.asarray(signals_by_id[hyp["id"]], dtype=float) * hyp["direction"]
        fwd = np.asarray(fwd_by_h[hyp["h"]], dtype=float)
        n_clusters = len(set(clusters[oos & (sig != 0)].tolist()) - {-1})
        oos_res = st.evaluate_directional(sig[oos], fwd[oos])
        status = oos_res["status"]
        if status == "ok" and n_clusters < MIN_CLUSTERS:
            status = "insufficient"
        inc_res = inc.partial_effect(sig, fwd, controls) if status == "ok" else {"p": None}
        rows.append({"id": hyp["id"], "status": status, "n_clusters": n_clusters,
                     "excess_oos": oos_res.get("excess"), "excess_in": st.excess_stat(sig[ins], fwd[ins]),
                     "p": oos_res.get("p"), "inc_p": inc_res.get("p")})
    # BH over the directional tests and, separately, over the incremental tests.
    for key, out in (("p", "q"), ("inc_p", "inc_q")):
        ok = [r for r in rows if r["status"] == "ok" and r[key] is not None]
        for r, q in zip(ok, st.bh_adjust([r[key] for r in ok]), strict=True):
            r[out] = q
    for r in rows:
        r["passed"] = bool(
            r["status"] == "ok"
            and r.get("q") is not None and r["q"] < Q_THRESHOLD
            and r.get("inc_q") is not None and r["inc_q"] < Q_THRESHOLD
            and r["excess_oos"] > 0 and r["excess_in"] > 0  # same direction in both eras
        )
    return rows


def descriptive_summary(rows: list[dict]) -> dict:
    """Counts and rates for descriptive tables. No p, q or pass fields by design."""
    n_raw = len(rows)
    clusters = {(r["event"], r["cluster"]) for r in rows}
    ranks = [r["rank"] for r in rows if r.get("rank") is not None]
    top5 = sum(1 for k in ranks if k <= 5)
    beat = sum(1 for r in rows if r["ret"] - r["nifty"] > 0)
    return {"n_raw": n_raw, "n_clusters": len(clusters),
            "top5_rate": top5 / len(ranks) if ranks else None,
            "beat_rate": beat / n_raw if n_raw else None}


# Rotation groups, fixed in the pre-registration ("Rotation pattern labels"). Keys are the
# sector keys from sbc.market_store.SECTOR_SYMBOLS.
GROUPS = {
    "CNXPHARMA": "Defensive", "CNXFMCG": "Defensive", "CNXCONSUM": "Defensive",
    "CNXIT": "Growth", "CNXAUTO": "Growth",
    "CNXBANK": "Risk-On", "CNXFIN": "Risk-On", "CNXREALTY": "Risk-On", "CNXMETAL": "Risk-On",
    "CNXINFRA": "Risk-On", "CNXPSUBANK": "Risk-On",
    "CNXENERGY": "Neutral",
}


def rotation_pattern(top5: list[str]) -> tuple[str, list[str]]:
    """Majority group among the top-5 sectors, or "Mixed" if no group holds more than half.

    The top-5 list is returned with the label so the label can be checked against the data.
    An unmapped sector raises KeyError rather than being dropped silently.
    """
    counts = Counter(GROUPS[s] for s in top5)
    group, n = counts.most_common(1)[0]
    if n * 2 > len(top5):
        return group, top5
    return "Mixed", top5


def forecast_confidence(row: dict) -> str:
    """High only on a confirmatory pass; otherwise No call. No Medium level (pre-registration)."""
    return "High" if row.get("passed") else "No call"


def daily_returns(closes: np.ndarray, anchor: int, h: int) -> np.ndarray:
    """h daily returns for sessions anchor+1 .. anchor+h; NaN where a bar is out of range or missing."""
    out = np.full(h, np.nan)
    for i in range(h):
        t = anchor + 1 + i
        if 0 <= t < len(closes):
            out[i] = window_return(closes, t - 1, 1)
    return out


def volatility(rets: np.ndarray) -> float:
    """Standard deviation of the finite daily returns; NaN with fewer than two."""
    x = np.asarray(rets, dtype=float)
    x = x[np.isfinite(x)]
    return float(np.std(x, ddof=1)) if len(x) >= 2 else float("nan")


def sharpe(excess: np.ndarray) -> float:
    """Mean over std of daily excess returns, not annualised; NaN with fewer than two or zero std."""
    x = np.asarray(excess, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return float("nan")
    sd = np.std(x, ddof=1)
    return float(np.mean(x) / sd) if sd > 0 else float("nan")


def participation(returns: dict[str, float]) -> float | None:
    """Share of sectors with a finite return that is positive; None if no sector is available."""
    valid = [r for r in returns.values() if np.isfinite(r)]
    if not valid:
        return None
    return sum(1 for r in valid if r > 0) / len(valid)


HEAT_BUCKETS = ("dark_green", "light_green", "yellow", "orange", "dark_red")


def heat_bucket(z: float) -> str | None:
    """Colour bucket for a z-score of relative strength. Presentational only, not graded."""
    if not np.isfinite(z):
        return None
    if z >= 1.0:
        return "dark_green"
    if z >= 0.25:
        return "light_green"
    if z > -0.25:
        return "yellow"
    if z > -1.0:
        return "orange"
    return "dark_red"


# Capital-flow groups for the rotation wheel. The spec names the six groups but not their members;
# this mapping is a proposal, stated here, and is descriptive only.
WHEEL_GROUPS = {
    "Financials": ["CNXBANK", "CNXFIN", "CNXPSUBANK"],
    "Technology": ["CNXIT"],
    "Pharma": ["CNXPHARMA"],
    "Consumption": ["CNXFMCG", "CNXAUTO", "CNXCONSUM", "CNXREALTY"],
    "Industrials": ["CNXINFRA"],
    "Commodities": ["CNXMETAL", "CNXENERGY"],
}


def upcoming_events(events: list[dict], today: str, days: int) -> list[dict]:
    """Events dated from `today` through `today` + `days` inclusive, sorted by date.

    ISO dates compare correctly as strings, so no parsing happens per event.
    """
    end = (dt.date.fromisoformat(today) + dt.timedelta(days=days)).isoformat()
    return sorted((e for e in events if today <= e["date"] <= end), key=lambda e: (e["date"], e["event"]))


HEAT_DIRECTION = {"dark_green": "outperform", "light_green": "outperform", "yellow": "neutral",
                  "orange": "underperform", "dark_red": "underperform"}


def edge_scorecard(row: dict, confirmed: bool = False) -> dict:
    """Plain-language confidence for one event x sector x horizon cell.

    Direction comes from the heatmap bucket (no new threshold). Sample is "thin" below MIN_CLUSTERS,
    the cluster floor the pre-registration uses for grading. Validity is "Descriptive" unless the cell
    passed the confirmatory rule, and the forecast follows forecast_confidence: High or No call only.
    """
    return {
        "direction": HEAT_DIRECTION.get(row.get("heat"), "neutral"),
        "clusters": row["n_clusters"],
        "beat_rate": row.get("beat_rate"),
        "sample": "thin" if row["n_clusters"] < MIN_CLUSTERS else "adequate",
        "validity": "Confirmed" if confirmed else "Descriptive",
        "forecast": forecast_confidence({"passed": confirmed}),
    }


def event_outlook(descriptive: dict, event: str, n: int = 3) -> dict:
    """Strongest and weakest `n` sectors per horizon for one event, from the report's descriptive rows.

    The report sorts each horizon's rows by mean relative return, highest first. Descriptive only.
    Each row carries its edge_scorecard.
    """
    keep = ("sector", "n_raw", "n_clusters", "mean_relative", "beat_rate", "heat")

    def card(r: dict) -> dict:
        return {**{k: r[k] for k in keep}, "scorecard": edge_scorecard(r)}

    out = {}
    for h, rows in descriptive.get(event, {}).items():
        out[h] = {"strongest": [card(r) for r in rows[:n]],
                  "weakest": [card(r) for r in rows[::-1][:n]]}
    return out
