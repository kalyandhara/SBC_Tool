"""Venus stations and the Sun-Venus conjunction against NIFTY swing lows (B-70).

The hypotheses, pivot definition, hit window, null, era split and pass rule were fixed in
docs/research/venus_station_preregistration_2026-10-12.md before this module existed.
Do not change them here; a different choice is a new registration.

Events: Venus retrograde (R) and direct (D) stations from sbc.stations (sidereal Lahiri,
Moshier), and geocentric Sun-Venus conjunctions (sidereal longitude difference crossing 0).
Each event sits on the first NIFTY session on or after its IST date. A pivot low is a session
whose close is the minimum of the 11 sessions centred on it. A hit is a pivot low within +-3
sessions of an event. The null shifts all events of one hypothesis by one common offset,
drawn from the offsets that keep every event inside its era.
"""

from __future__ import annotations

import bisect
import datetime as dt

import numpy as np
import swisseph as swe

from sbc import rule_validation as rv
from sbc import stations as stn
from sbc import stats as st

PREREG = "docs/research/venus_station_preregistration_2026-10-12.md"
PIVOT_HALF = 5
HIT_HALF = 3
MIN_OFFSET = 30
MAX_OFFSET = 250
MIN_EVENTS = 20
ERAS = ("2007-2020", "2021-2026")


def venus_stations(first: int, last: int) -> list[dict]:
    """Venus R and D rows from sbc.stations, in chunks under the library's ten-year limit."""
    rows: list[dict] = []
    y = first
    while y <= last:
        end = min(y + 9, last)
        rows += stn.between(dt.date(y, 1, 1), dt.date(end + 1, 1, 1), ("Venus",))
        y = end + 1
    return rows


def sidereal_diff(day: dt.date) -> float:
    """Sidereal Venus minus Sun longitude at 09:15 IST, in degrees in (-180, 180]."""
    t = dt.datetime(day.year, day.month, day.day, 9, 15) - dt.timedelta(hours=5, minutes=30)
    jd = swe.julday(t.year, t.month, t.day, t.hour + t.minute / 60)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_MOSEPH | swe.FLG_SIDEREAL
    venus = swe.calc_ut(jd, swe.VENUS, flags)[0][0]
    sun = swe.calc_ut(jd, swe.SUN, flags)[0][0]
    return (venus - sun + 180.0) % 360.0 - 180.0


def inferior_conjunctions(first: dt.date, last: dt.date) -> list[str]:
    """IST dates of Sun-Venus conjunctions: the difference crosses 0 going upward.

    Daily sampling finds the crossing; the day nearer to 0 is the event day, which is
    enough because the hit window is +-3 sessions.
    """
    out: list[str] = []
    day = first
    prev = sidereal_diff(day)
    while day < last:
        nxt = day + dt.timedelta(days=1)
        cur = sidereal_diff(nxt)
        if prev < 0 <= cur and cur - prev < 90:
            out.append((nxt if abs(cur) <= abs(prev) else day).isoformat())
        prev, day = cur, nxt
    return out


def pivot_lows(closes: np.ndarray) -> np.ndarray:
    n = len(closes)
    out = np.zeros(n, dtype=bool)
    for i in range(PIVOT_HALF, n - PIVOT_HALF):
        out[i] = closes[i] == closes[i - PIVOT_HALF: i + PIVOT_HALF + 1].min()
    return out


def event_sessions(dates: list[str], days: list[str]) -> np.ndarray:
    """Session index of each event: the first session on or after its date, in-sample only."""
    idx = set()
    for d in days:
        i = bisect.bisect_left(dates, d)
        if i < len(dates):
            idx.add(i)
    return np.array(sorted(idx), dtype=int)


def hits(pivots: np.ndarray, events: np.ndarray, lo: int, hi: int) -> int:
    """Events in [lo, hi) with a pivot low within +-HIT_HALF sessions, clipped to [lo, hi)."""
    count = 0
    for e in events:
        if lo <= e < hi and pivots[max(lo, e - HIT_HALF): min(hi, e + HIT_HALF + 1)].any():
            count += 1
    return count


def shift_null(pivots: np.ndarray, events: np.ndarray, lo: int, hi: int, n_perm: int,
               rng: np.random.Generator) -> np.ndarray:
    """Hit counts after shifting every event by one common offset, redrawn if one leaves [lo, hi)."""
    out = np.zeros(n_perm, dtype=float)
    if len(events) == 0:
        return out
    if events.min() < lo or events.max() >= hi:
        raise ValueError("events must lie inside [lo, hi) before shifting")
    offsets = np.array([k for k in range(-MAX_OFFSET, MAX_OFFSET + 1) if abs(k) >= MIN_OFFSET
                        if lo <= events.min() + k and events.max() + k < hi])
    if len(offsets) == 0:
        raise ValueError("no admissible shift keeps every event inside its era")
    for p in range(n_perm):
        out[p] = hits(pivots, events + int(rng.choice(offsets)), lo, hi)
    return out


def grade(pivots: np.ndarray, events: np.ndarray, lo: int, hi: int, n_perm: int,
          rng: np.random.Generator) -> dict:
    ev = events[(events >= lo) & (events < hi)]
    n = len(ev)
    if n == 0:
        return {"n": 0, "hits": 0, "rate": None, "null_mean": None, "lift": None, "p": None}
    h = hits(pivots, ev, lo, hi)
    null_rate = shift_null(pivots, ev, lo, hi, n_perm, rng) / n
    rate = h / n
    p = float((np.sum(null_rate >= rate) + 1) / (n_perm + 1))
    return {"n": n, "hits": h, "rate": rate, "null_mean": float(null_rate.mean()),
            "lift": rate - float(null_rate.mean()), "p": p}


def window_report(dates: list[str], closes: np.ndarray, pivots: np.ndarray, rows: list[dict]) -> dict:
    """Retrograde windows (R to the next D) as the deck counted them. Reported, not graded."""
    wins = []
    directs = [r["date"] for r in rows if r["direction"] == "direct"]
    for r in (r for r in rows if r["direction"] == "retrograde"):
        later = [d for d in directs if d > r["date"]]
        if not later:
            continue
        a = bisect.bisect_left(dates, r["date"])
        b = bisect.bisect_left(dates, later[0])
        if a >= len(dates) or b >= len(dates) or b <= a:
            continue
        seg = closes[a: b + 1]
        wins.append({"start": r["date"], "end": dates[b], "sessions": b - a + 1,
                     "pivot_inside": bool(pivots[a: b + 1].any()),
                     "range_pct": (float(seg.max() / seg.min()) - 1) * 100})
    if not wins:
        return {"windows": [], "with_pivot": 0, "total": 0}
    length = int(np.median([w["sessions"] for w in wins]))
    rolling = [(closes[j: j + length].max() / closes[j: j + length].min() - 1) * 100
               for j in range(0, len(closes) - length, 5)]
    return {"windows": wins,
            "with_pivot": sum(w["pivot_inside"] for w in wins),
            "total": len(wins),
            "median_sessions": length,
            "median_range_pct": float(np.median([w["range_pct"] for w in wins])),
            "normal_median_range_pct": float(np.median(rolling))}


def forward_returns(closes: np.ndarray, events: np.ndarray) -> dict:
    out = {}
    for h in (1, 5, 20):
        vals = [closes[e + h] / closes[e] - 1 for e in events if e + h < len(closes)]
        out[str(h)] = float(np.mean(vals) * 100) if vals else None
    return out


def run(n_perm: int = st.N_PERMUTATIONS, seed: int = 20261012) -> dict:
    dates, close_list, _ = rv.load_history()
    closes = np.asarray(close_list, dtype=float)
    first, last = dt.date.fromisoformat(dates[0]), dt.date.fromisoformat(dates[-1])
    rows = [r for r in venus_stations(first.year, last.year)
            if first <= dt.date.fromisoformat(r["date"]) <= last]
    conj = [d for d in inferior_conjunctions(first, last) if first <= dt.date.fromisoformat(d) <= last]
    station_days = [r["date"] for r in rows]
    events = {"h1_venus_station": event_sessions(dates, station_days),
              "h2_venus_inferior_conjunction": event_sessions(dates, conj)}
    pivots = pivot_lows(closes)
    rng = np.random.default_rng(seed)
    split = bisect.bisect_left(dates, rv.ERA_SPLIT)
    era_bounds = {ERAS[0]: (0, split), ERAS[1]: (split, len(dates))}

    results = []
    for name, ev in events.items():
        full = grade(pivots, ev, 0, len(dates), n_perm, rng)
        eras = {e: grade(pivots, ev, *era_bounds[e], n_perm, rng) for e in ERAS}
        results.append({"name": name, "events": int(len(ev)), **full, "eras": eras})
    qs = st.bh_adjust([r["p"] if r["p"] is not None else 1.0 for r in results])
    for r, q in zip(results, qs):
        r["q"] = float(q)
        era_ok = all(r["eras"][e]["lift"] is not None and r["eras"][e]["lift"] > 0
                     and r["eras"][e]["p"] < 0.05 for e in ERAS)
        if r["events"] < MIN_EVENTS:
            r["verdict"] = "underpowered"
        elif r["q"] < 0.05 and era_ok:
            r["verdict"] = "pass"
        else:
            r["verdict"] = "no edge"
    return {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "preregistration": PREREG,
        "sample": {"first": dates[0], "last": dates[-1], "sessions": len(dates)},
        "n_permutations": n_perm,
        "seed": seed,
        "event_counts": {"venus_stations": len(station_days), "inferior_conjunctions": len(conj)},
        "results": results,
        "deck_claims": window_report(dates, closes, pivots, rows),
        "forward_returns_pct": {name: forward_returns(closes, ev) for name, ev in events.items()},
    }
