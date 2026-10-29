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
    """
    stat_rows = stations.by_date(dt.date(first_year, 1, 1), dt.date(last_year + 1, 12, 31), ("Mercury",))
    rows = [r for day in stat_rows.values() for r in day]
    out = [e for e in mercury_events(rows) if int(e["date"][:4]) <= last_year]
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
    "CNXPHARMA": "Defensive", "CNXFMCG": "Defensive", "CNXHEALTH": "Defensive", "CNXCONSUM": "Defensive",
    "CNXIT": "Growth", "CNXMEDIA": "Growth", "CNXAUTO": "Growth",
    "CNXBANK": "Risk-On", "CNXFIN": "Risk-On", "CNXREALTY": "Risk-On", "CNXMETAL": "Risk-On",
    "CNXINFRA": "Risk-On", "CNXPSUBANK": "Risk-On",
    "CNXENERGY": "Neutral", "CNXOILGAS": "Neutral",
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
