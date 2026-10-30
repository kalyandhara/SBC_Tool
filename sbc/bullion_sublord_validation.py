"""Validation of the bullion KP sub-lord rules (B-57).

Registered in docs/research/bullion_sublord_preregistration_2026-10-11.md and amended by
docs/research/bullion_sublord_amendment_1_2026-10-11.md before any intraday data existed.
Do not change the design here; a different choice is a new registration.

Data: Dukascopy hourly BID candles (scripts/fetch_dukascopy.py), UTC converted to IST.
Each IST weekday is a session: the hourly bars from 09:00 to 23:00 IST (US daylight time)
or 24:00 IST (US standard time), kept if it has at least 10 bars. A bar starting at hour h
takes the Moon sub-lord in force at h:59:59 (segment edges floored to the hour); runs of one
lord within a session are segments.

Metrics per segment (hours = bars in the segment):
  up/down          sum of bar log returns / hours
  volatile/stable  |sum of bar log returns| / hours
each minus the mean over all segments, signed so the registered claim is positive. The
hour-of-day control repeats this with each bar demeaned by its clock hour (up/down) or
divided by its clock hour's standard deviation (volatile/stable).

Null: whole-session blocks. Each session's hourly label sequence is reassigned to another
session with the same number of bars, 10,000 times. BH across the 8 tests (4 groups x 2
metals), separately for the raw and the controlled version. A group passes for a metal if
raw q < 0.05, the effect has the claimed sign in both halves of the sample, and the
controlled q < 0.05.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path

import numpy as np

from sbc import bullion_week as bw
from sbc import stats as st

ROOT = Path(__file__).resolve().parents[1]
INTRADAY = ROOT / "data" / "intraday"
SAMPLE = ("2010-01-01", "2026-09-30")
MIN_BARS = 10
N_PERM = 10_000
GROUPS = {"up": ({"Venus", "Jupiter"}, "ret", +1), "down": ({"Sun", "Ketu", "Rahu"}, "ret", -1),
          "volatile": ({"Moon"}, "abs", +1), "stable": ({"Mars", "Saturn"}, "abs", -1)}
METALS = {"gold": "xauusd", "silver": "xagusd"}
IST = dt.timedelta(hours=5, minutes=30)


us_daylight = bw.us_daylight


def session_hours(day: dt.date) -> list[int]:
    return list(range(9, 24)) if us_daylight(day) else list(range(9, 25))


def load_bars(path: Path) -> dict[dt.datetime, float]:
    """IST bar start -> log return (close/open) of that hourly bar."""
    out = {}
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            o, c = float(r["open"]), float(r["close"])
            if o > 0 and c > 0:
                t = dt.datetime.strptime(r["time_utc"], "%Y-%m-%d %H:%M") + IST
                out[t] = float(np.log(c / o))
    return out


def lords_at_hours(day: dt.date, hours: list[int], cache: dict) -> list[str]:
    """Sub-lord in force at h:59:59 IST for each session hour h (h may be 24 = next day 00)."""
    key = day.isoformat()
    if key not in cache:
        cache[key] = [(s["a"], s["b"], s["lord"]) for s in bw.moon_day(day)[1]]
        nxt = (day + dt.timedelta(days=1)).isoformat()
        if nxt not in cache:
            cache[nxt] = [(s["a"], s["b"], s["lord"]) for s in bw.moon_day(day + dt.timedelta(days=1))[1]]
    out = []
    for h in hours:
        segs, t = (cache[key], h + 0.9997) if h < 24 else (cache[(day + dt.timedelta(days=1)).isoformat()], 0.9997)
        out.append(next(lord for a, b, lord in segs if a <= t < b))
    return out


def build_sessions(bars: dict[dt.datetime, float], lord_cache: dict) -> list[dict]:
    day = dt.date.fromisoformat(SAMPLE[0])
    end = dt.date.fromisoformat(SAMPLE[1])
    sessions = []
    while day <= end:
        if day.weekday() < 5:
            hours = session_hours(day)
            base = dt.datetime.combine(day, dt.time())
            rets, hrs = [], []
            for h in hours:
                r = bars.get(base + dt.timedelta(hours=h))
                if r is not None:
                    rets.append(r)
                    hrs.append(h)
            if len(rets) >= MIN_BARS:
                lords = lords_at_hours(day, hrs, lord_cache)
                sessions.append({"date": day.isoformat(), "hours": hrs, "ret": rets, "lords": lords})
        day += dt.timedelta(days=1)
    return sessions


def _segments(labels: np.ndarray, values: np.ndarray, sess_id: np.ndarray):
    """Runs of equal label within a session -> (label, sum of values, bar count)."""
    brk = np.r_[True, (labels[1:] != labels[:-1]) | (sess_id[1:] != sess_id[:-1])]
    starts = np.flatnonzero(brk)
    sums = np.add.reduceat(values, starts)
    counts = np.diff(np.r_[starts, len(values)])
    return labels[starts], sums, counts, sess_id[starts]


def group_stats(labels, values, sess_id, codes) -> dict[str, float]:
    lab, sums, cnt, _ = _segments(labels, values, sess_id)
    per_hour = sums / cnt
    out = {}
    for name, (members, kind, sign) in GROUPS.items():
        m = per_hour if kind == "ret" else np.abs(per_hour)
        mask = np.isin(lab, [codes[x] for x in members])
        out[name] = float(sign * (m[mask].mean() - m.mean())) if mask.any() else float("nan")
    return out


def _flatten(sessions, values_key="ret"):
    lords = sorted({x for s in sessions for x in s["lords"]} | set(bw.READING))
    codes = {l: i for i, l in enumerate(lords)}
    labels = np.concatenate([[codes[x] for x in s["lords"]] for s in sessions])
    values = np.concatenate([s[values_key] for s in sessions])
    hours = np.concatenate([s["hours"] for s in sessions])
    sess = np.concatenate([[i] * len(s["ret"]) for i, s in enumerate(sessions)])
    return labels, values, hours, sess, codes


def controlled(values: np.ndarray, hours: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(demeaned by clock hour, standardised by clock hour)."""
    dm, z = values.copy(), values.copy()
    for h in np.unique(hours):
        m = hours == h
        dm[m] = values[m] - values[m].mean()
        sd = values[m].std()
        z[m] = values[m] / sd if sd > 0 else 0.0
    return dm, z


def permutation_test(sessions, n_perm=N_PERM, seed=0) -> dict:
    labels, raw, hours, sess, codes = _flatten(sessions)
    dm, z = controlled(raw, hours)
    variants = {"raw": (raw, raw), "controlled": (dm, z)}  # (values for up/down, values for vol)
    lengths = np.array([len(s["ret"]) for s in sessions])
    starts = np.r_[0, np.cumsum(lengths)[:-1]]

    def stats_for(lab):
        out = {}
        for v, (ret_vals, vol_vals) in variants.items():
            a = group_stats(lab, ret_vals, sess, codes)
            b = group_stats(lab, vol_vals, sess, codes)
            out[v] = {g: (a[g] if GROUPS[g][1] == "ret" else b[g]) for g in GROUPS}
        return out

    observed = stats_for(labels)
    rng = np.random.default_rng(seed)
    # Flat bar positions of each session, grouped by session length (the permutation strata).
    strata = [starts[lengths == n][:, None] + np.arange(n) for n in np.unique(lengths)]
    ge = {v: {g: 0 for g in GROUPS} for v in variants}
    for _ in range(n_perm):
        perm_labels = labels.copy()
        for pos in strata:
            perm_labels[pos] = labels[pos[rng.permutation(len(pos))]]
        s = stats_for(perm_labels)
        for v in variants:
            for g in GROUPS:
                if s[v][g] >= observed[v][g]:
                    ge[v][g] += 1
    p = {v: {g: (ge[v][g] + 1) / (n_perm + 1) for g in GROUPS} for v in variants}
    mid = sessions[len(sessions) // 2]["date"]
    halves = {}
    for name, part in (("first", [s for s in sessions if s["date"] < mid]), ("second", [s for s in sessions if s["date"] >= mid])):
        lb, rv, hr, ss, cd = _flatten(part)
        halves[name] = group_stats(lb, rv, ss, cd)
    seg_lab, _, _, _ = _segments(labels, raw, sess)
    counts = {g: int(np.isin(seg_lab, [codes[x] for x in GROUPS[g][0]]).sum()) for g in GROUPS}
    return {"observed": observed, "p": p, "halves": halves, "split": mid, "segments": counts,
            "total_segments": int(len(seg_lab)), "bars": int(len(raw)), "sessions": len(sessions)}


def run(n_perm: int = N_PERM, intraday_dir: Path = INTRADAY) -> dict:
    lord_cache: dict = {}
    per_metal = {}
    for metal, stem in METALS.items():
        path = intraday_dir / f"{stem}_1h.csv"
        if not path.exists():
            raise FileNotFoundError(f"{path} missing; run scripts/fetch_dukascopy.py")
        sessions = build_sessions(load_bars(path), lord_cache)
        per_metal[metal] = permutation_test(sessions, n_perm)
        meta = intraday_dir / f"{stem}_1h.meta.json"
        per_metal[metal]["data"] = json.loads(meta.read_text()) if meta.exists() else None
    for v in ("raw", "controlled"):
        keys = [(m, g) for m in METALS for g in GROUPS]
        qs = st.bh_adjust([per_metal[m]["p"][v][g] for m, g in keys])
        for (m, g), q in zip(keys, qs):
            per_metal[m].setdefault("q", {}).setdefault(v, {})[g] = q
    rows = []
    for m in METALS:
        r = per_metal[m]
        for g in GROUPS:
            both = r["halves"]["first"][g] > 0 and r["halves"]["second"][g] > 0
            ok = r["q"]["raw"][g] < 0.05 and both and r["q"]["controlled"][g] < 0.05
            rows.append({"metal": m, "group": g, "lords": sorted(GROUPS[g][0]), "segments": r["segments"][g],
                         "effect": r["observed"]["raw"][g], "p": r["p"]["raw"][g], "q": r["q"]["raw"][g],
                         "first_half": r["halves"]["first"][g], "second_half": r["halves"]["second"][g],
                         "controlled_effect": r["observed"]["controlled"][g],
                         "controlled_q": r["q"]["controlled"][g], "verdict": "PASS" if ok else "no edge"})
    return {"generated": dt.datetime.now().isoformat(timespec="seconds"), "sample": SAMPLE,
            "n_permutations": n_perm, "preregistration": [
                "docs/research/bullion_sublord_preregistration_2026-10-11.md",
                "docs/research/bullion_sublord_amendment_1_2026-10-11.md"],
            "metals": {m: {k: v for k, v in per_metal[m].items() if k in ("sessions", "bars", "total_segments", "split", "data")}
                       for m in METALS},
            "results": rows}
