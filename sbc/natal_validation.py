"""Validation of the transit-to-natal model (B-53), graded the way B-39 is.

The hypotheses, groups, inputs and pass rule were fixed in
docs/research/natal_transit_preregistration_2026-10-10.md before this module existed.
Do not change them here; a different choice is a new registration.

A. ENTRY timing per NIFTY session. A session is "in a window" when a transiting planet is
   within orb of an aspect to a natal planet at 09:15 IST. The signal is B-39's trend
   reversal (sbc.swing_validation.reversal), so the two reports compare directly. Graded
   with the shared harness (sbc.swing_validation.grade_a): permutation test, BH within the
   report, the incremental test against the market controls, and the no-astro control.
B. The full swing model (entry, confluence exit) on these windows, 2008 onward, against
   simple exits and random entries (sbc.swing_validation.part_b).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable

import numpy as np

from sbc import fingerprint_store, natal
from sbc import helio_aspects as ha
from sbc import rule_validation as rv
from sbc import stats as st
from sbc import swing_model as sm
from sbc import swing_validation as sv
from sbc import transit_natal as tn

ANCHOR = "nifty"
LECTURE_ASPECTS = ("CONJ", "SQ", "SXT", "SS", "TRI")  # the five the lecture names
SOURCE = "sbc.transit_natal"


def session_contacts(chart: dict[str, float], dates: list[str]) -> list[list[dict]]:
    """Transit-to-natal contacts in force at 09:15 IST on each session."""
    return [tn.active_on(chart, d) for d in dates]


def groups(chart: dict[str, float]) -> dict[str, Callable[[dict], bool] | None]:
    """Group name -> which contacts count; None matches any contact."""
    Pred = Callable[[dict], bool]
    g: dict[str, Pred | None] = {"all": None}
    for code in ha.ASPECTS:
        g[f"aspect_{code}"] = lambda x, c=code: x["aspect"] == c  # type: ignore[return-value,misc]
    g["lecture5"] = lambda x: x["aspect"] in LECTURE_ASPECTS  # type: ignore[return-value,misc]
    for planet in tn.TRANSIT_PLANETS:
        g[f"planet_{planet}"] = lambda x, p=planet: x["planet"] == p  # type: ignore[return-value,misc]
    for point in chart:
        g[f"natal_{point}"] = lambda x, p=point: x["natal"] == p  # type: ignore[return-value,misc]
    return g


def entry_entries(closes: np.ndarray, active: list[list[dict]], chart: dict[str, float]) -> list[dict]:
    rev = sv.reversal(closes)
    entries = []
    for name, match in groups(chart).items():
        flag = np.array([bool(a) if match is None else any(match(x) for x in a) for a in active])
        label = name.replace("_", " ")
        entries.append({"name": f"natal_{name}_reversal", "kind": "directional", "source": SOURCE,
                        "description": f"Trend reversal on sessions in a transit-to-natal {label} window",
                        "signal": np.where(flag, rev, 0.0)})
        entries.append({"name": f"natal_{name}_volatility", "kind": "event", "source": SOURCE,
                        "description": f"transit-to-natal {label} window -> bigger moves", "signal": flag})
    return entries


def run(n_perm: int = st.N_PERMUTATIONS, n_sets: int = sv.RANDOM_SETS) -> dict:
    chart = natal.chart(ANCHOR)
    dates, close_list, _fps = rv.load_history()
    closes = np.asarray(close_list, dtype=float)
    bars = sm.Bars.nifty()
    active = session_contacts(chart, dates)
    a = sv.grade_a(dates, closes, entry_entries(closes, active, chart), active, n_perm)
    windows = tn.scan(chart, sv.SCAN_START, bars.dates[-1])
    b = sv.part_b(bars, n_sets, windows=windows)
    return {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "fingerprint_version": fingerprint_store.current_version(),
        "sample": {"first": dates[0], "last": dates[-1], "sessions": len(dates)},
        "horizons": list(sv.HORIZONS),
        "n_permutations": n_perm,
        "orb": ha.ORB,
        "anchor": {"key": ANCHOR, "chart": {k: round(v, 2) for k, v in chart.items()}},
        "results": a["results"],
        "control": a["control"],
        "window_share": a["window_share"],
        "model": b,
    }
