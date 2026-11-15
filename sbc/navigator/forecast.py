"""Forward day ranking for a Navigator profile (Phase 3).

Scores every trading session after the last market close with the Phase 1
pipeline. Market inputs stop at the last close: Volatility is neutral for
every forward day and Historical Validation uses only past sessions, so a
forward score is mostly astrological. It is research output, not a forecast
of returns, and nothing here has been validated out of sample.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np

from sbc import market_holidays as MH
from sbc.navigator import scoring as S
from sbc.navigator.analogs import Market, next_sessions
from sbc.navigator.ephemeris import build_sky
from sbc.navigator.profile import Profile

WINDOWS = (30, 90, 365)
TOP_N = 20
NOTES = [
    "Forward scores use market data only up to the last close. Volatility is neutral "
    "for every forward day; Historical Validation uses past sessions only.",
    "Rankings are research output from hand-set weights (nav-1), not validated predictions.",
    "Top trading dates are the highest scores in the window; stay-away dates are the lowest. "
    "Ties go to the earlier date.",
]


def sessions_for(window_days: int, last: str) -> list[str]:
    """Trading sessions in the next `window_days` calendar days after `last`."""
    end = dt.date.fromisoformat(last) + dt.timedelta(days=window_days)
    out = []
    for d in next_sessions(last, window_days):   # at most one session per calendar day
        if dt.date.fromisoformat(d) > end:
            break
        out.append(d)
    return out


def rank(days: list[str], scores: list[int], n: int = TOP_N) -> tuple[list[int], list[int]]:
    """Indices of the top-n and bottom-n scores; ties go to the earlier date."""
    idx = range(len(scores))
    top = sorted(idx, key=lambda i: (-scores[i], i))[:n]
    low = sorted(idx, key=lambda i: (scores[i], i))[:n]
    return top, low


def build(profile: Profile, market: Market, window_days: int = 30) -> dict[str, Any]:
    if window_days not in WINDOWS:
        raise ValueError("window must be 30, 90 or 365")
    dates, n = list(market.dates), len(market.dates)
    future = sessions_for(window_days, dates[-1])
    m = len(future)
    sky = build_sky(dates + future)
    nan = np.full(m, np.nan)
    opens = np.r_[market.prices["open"], nan]
    closes = np.r_[market.prices["close"], nan]
    vix = {d: c for d, c in market.vix.items() if d != dates[-1]}   # neutral Vol, as in Phase 1
    series = S.score_series(sky, profile, opens, closes, vix)
    scores = [int(s) for s in series.score[n:]]
    rows = [{"date": d, "score": s, "band": S.band_of(s), "action": S.action_of(S.band_of(s))}
            for d, s in zip(future, scores, strict=True)]
    top, low = rank(future, scores)
    counts = {b: 0 for _, b in S.BANDS}
    for score in scores:
        counts[S.band_of(score)] += 1
    notes = list(NOTES)
    uncovered = sorted({d[:4] for d in future if not MH.is_covered(dt.date.fromisoformat(d))})
    if uncovered:
        notes.append(f"No NSE holiday list for {', '.join(uncovered)}: weekends only are skipped.")
    return {"window_days": window_days, "data_asof": dates[-1], "sessions": rows,
            "top": [rows[i] for i in top], "stay_away": [rows[i] for i in low],
            "band_counts": counts, "notes": notes}
