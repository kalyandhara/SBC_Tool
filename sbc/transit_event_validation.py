"""Validation of transit events against NIFTY (B-58).

The hypotheses, windows, inputs and pass rule were fixed in
docs/research/transit_events_preregistration_2026-10-11.md before this module existed.
Do not change them here; a different choice is a new registration.

Events come from sbc.transit_almanac (sidereal Lahiri, mean node, IST dates). Each event
is placed on the first NIFTY session on or after its date; a window is +-k sessions around
it. Graded with the shared harness (sbc.swing_validation.grade_a): circular-shift
permutation test, BH across the report, era split, and the incremental test against the
market controls, plus B-39's no-astro reversal control.
"""

from __future__ import annotations

import bisect
import datetime as dt

import numpy as np
import swisseph as swe

from sbc import fingerprint_store
from sbc import rule_validation as rv
from sbc import stats as st
from sbc import swing_validation as sv
from sbc import transit_almanac as ta

SOURCE = "sbc.transit_almanac"
PREREG = "docs/research/transit_events_preregistration_2026-10-11.md"
MALEFICS = {"Mars", "Saturn", "Pluto"}
WINDOWS = {"h1": 3, "h3": 2, "h4": 5, "h5": 3}


def year_events(first_year: int, last_year: int) -> list[dict]:
    out = []
    for y in range(first_year, last_year + 1):
        for body in ta.build(y, "sidereal")["bodies"]:
            out.extend(body["events"])
    return out


def session_index(dates: list[str], day: str) -> int | None:
    """Index of the first session on or after `day`, or None past the sample."""
    i = bisect.bisect_left(dates, day)
    return i if i < len(dates) else None


def window_flags(dates: list[str], event_days: list[str], k: int) -> np.ndarray:
    flag = np.zeros(len(dates), dtype=bool)
    for day in event_days:
        if day < dates[0]:
            continue
        i = session_index(dates, day)
        if i is not None:
            flag[max(0, i - k): i + k + 1] = True
    return flag


def mercury_retrograde(dates: list[str]) -> np.ndarray:
    """True on sessions when Mercury's sidereal speed is negative at 09:15 IST."""
    out = np.zeros(len(dates), dtype=bool)
    for i, d in enumerate(dates):
        t = dt.datetime.fromisoformat(d + "T09:15") - dt.timedelta(hours=5, minutes=30)
        jd = swe.julday(t.year, t.month, t.day, t.hour + t.minute / 60)
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        speed = swe.calc_ut(jd, swe.MERCURY, swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED)[0][3]
        out[i] = speed < 0
    return out


def signals(dates: list[str], closes: np.ndarray, events: list[dict]) -> tuple[list[dict], np.ndarray]:
    """The five registered entries, and per-session 'inside any window' for the window share."""
    merc_stations = [e["date"] for e in events if e["type"] == "station" and e["body"] == "Mercury"]
    tense = [e["date"] for e in events if e["type"] == "aspect" and e["aspect"] in ("square", "opposition")
             and (e["body"] in MALEFICS or e["other"] in MALEFICS)]
    eclipses = [e["date"] for e in events if e["type"] == "eclipse"]
    ingress = [e["date"] for e in events if e["type"] == "ingress" and e.get("body") in ("Jupiter", "Saturn")]

    h1 = window_flags(dates, merc_stations, WINDOWS["h1"])
    h2 = mercury_retrograde(dates)
    h3 = window_flags(dates, tense, WINDOWS["h3"])
    h4 = window_flags(dates, eclipses, WINDOWS["h4"])
    h5 = window_flags(dates, ingress, WINDOWS["h5"])
    rev = sv.reversal(closes)
    entries = [
        {"name": "h1_mercury_station_volatility", "kind": "event", "source": SOURCE,
         "description": "within 3 sessions of a Mercury station -> bigger moves", "signal": h1},
        {"name": "h2_mercury_retrograde_down", "kind": "directional", "source": SOURCE,
         "description": "Mercury retrograde at 09:15 IST -> weaker returns", "signal": np.where(h2, -1.0, 0.0)},
        {"name": "h3_tense_mars_saturn_pluto_volatility", "kind": "event", "source": SOURCE,
         "description": "within 2 sessions of a square/opposition involving Mars, Saturn or Pluto -> bigger moves",
         "signal": h3},
        {"name": "h4_eclipse_volatility", "kind": "event", "source": SOURCE,
         "description": "within 5 sessions of an eclipse -> bigger moves", "signal": h4},
        {"name": "h5_jupiter_saturn_ingress_reversal", "kind": "directional", "source": SOURCE,
         "description": "trend reversal within 3 sessions of a Jupiter/Saturn sign change",
         "signal": np.where(h5, rev, 0.0)},
    ]
    counts = {"mercury_stations": len(merc_stations), "tense_aspects": len(tense),
              "eclipses": len(eclipses), "jupiter_saturn_ingresses": len(ingress)}
    shares = {e["name"]: float(np.mean(np.asarray(e["signal"]) != 0)) for e in entries}
    return entries, h1 | h2 | h3 | h4 | h5, counts, shares


def run(n_perm: int = st.N_PERMUTATIONS) -> dict:
    dates, close_list, _fps = rv.load_history()
    closes = np.asarray(close_list, dtype=float)
    events = year_events(int(dates[0][:4]), int(dates[-1][:4]))
    entries, any_flag, counts, shares = signals(dates, closes, events)
    a = sv.grade_a(dates, closes, entries, [[1] if f else [] for f in any_flag], n_perm)
    return {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "preregistration": PREREG,
        "fingerprint_version": fingerprint_store.current_version(),
        "sample": {"first": dates[0], "last": dates[-1], "sessions": len(dates)},
        "horizons": list(sv.HORIZONS),
        "n_permutations": n_perm,
        "event_counts": counts,
        "signal_share": shares,
        "results": a["results"],
        "control": a["control"],
        "window_share": a["window_share"],
    }
