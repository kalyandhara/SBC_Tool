"""Moon-sign signal check for the Trading Signals panel.

    check(bars, multi_tf=True, regime=False, gap_filter=False) -> {rows, summary, rolling, gap_control}

The signal: the Moon's sidereal sign at 09:15 IST on session t gives a bullish or bearish call
(sbc.config.RASHI_TREND) for session t+1's close against session t's close. The filters
reproduce the old /api/backtest/moon options:

  multi_tf    keep a day only if the Monday-of-week Moon sign gives the same call
  regime      skip the 1st and 15th of the month
  gap_filter  keep a day only if session t+1 OPENS in the called direction. This uses
              t+1's open, which isn't known when the call is made: look-ahead. The summary
              reports the "follow the opening gap" control on the same days so its share
              of the hit rate is visible.

The summary always sets the hit rate next to a base rate: the share of all sessions in the
period that moved in the more common direction (what "always guess that direction" scores),
with an exact two-sided binomial p-value of the hits against it.
"""

from __future__ import annotations

import datetime as dt
import math
from zoneinfo import ZoneInfo

from sbc.config import RASHI_TREND
from sbc.market_data import moon_rashi

IST = ZoneInfo("Asia/Kolkata")
ROLLING = 40


def _binom_two_sided(k: int, n: int, p: float) -> float:
    if n == 0:
        return float("nan")
    pk = math.comb(n, k) * p ** k * (1 - p) ** (n - k)
    total = 0.0
    for i in range(n + 1):
        pi = math.comb(n, i) * p ** i * (1 - p) ** (n - i)
        if pi <= pk * (1 + 1e-9):
            total += pi
    return min(1.0, total)


def _direction(a: float, b: float) -> str | None:
    return "bullish" if b > a else "bearish" if b < a else None


def check(bars: list[dict], multi_tf: bool = True, regime: bool = False, gap_filter: bool = False,
          rashi_at=moon_rashi) -> dict:
    """bars: oldest-first dicts with date (YYYY-MM-DD), open, high, low, close."""
    rows, sign_cache = [], {}

    def sign_on(day: dt.date) -> str:
        if day not in sign_cache:
            sign_cache[day] = rashi_at(dt.datetime.combine(day, dt.time(9, 15), tzinfo=IST))
        return sign_cache[day]

    for i in range(len(bars) - 1):
        day = dt.date.fromisoformat(bars[i]["date"])
        sign = sign_on(day)
        expected = RASHI_TREND.get(sign)
        if expected is None:
            continue
        if multi_tf and RASHI_TREND.get(sign_on(day - dt.timedelta(days=day.weekday()))) != expected:
            continue
        if regime and day.day in (1, 15):
            continue
        prev_close, nxt = float(bars[i]["close"]), bars[i + 1]
        gap = _direction(prev_close, float(nxt["open"]))
        if gap_filter and gap != expected:
            continue
        actual = _direction(prev_close, float(nxt["close"]))
        if actual is None:
            continue
        rows.append({"date": bars[i]["date"], "scored": nxt["date"], "sign": sign, "expected": expected,
                     "actual": actual, "match": expected == actual, "gap": gap})

    moves = [_direction(float(a["close"]), float(b["close"])) for a, b in zip(bars, bars[1:])]
    moves = [m for m in moves if m]
    up_share = sum(m == "bullish" for m in moves) / len(moves) if moves else float("nan")
    base = max(up_share, 1 - up_share) if moves else float("nan")
    n, hits = len(rows), sum(r["match"] for r in rows)
    hit_rate = hits / n if n else float("nan")
    p = _binom_two_sided(hits, n, base) if n and moves else float("nan")
    gap_hits = sum(r["gap"] == r["actual"] for r in rows)
    rolling = []
    for k in range(ROLLING, n + 1):
        window = rows[k - ROLLING:k]
        rolling.append({"date": window[-1]["scored"], "hit_rate": sum(r["match"] for r in window) / ROLLING})

    if not n:
        verdict = "No sessions passed the filters."
    elif p < 0.05 and hit_rate > base:
        verdict = "Above the base rate (p < 0.05). One test, uncorrected: confirm out of sample before relying on it."
    elif hit_rate > base:
        verdict = "Above the base rate, but within chance (p ≥ 0.05)."
    else:
        verdict = "Not above the base rate."
    if gap_filter and n:
        verdict += " The gap filter uses the next session's open, which isn't known at signal time."
    def clean(x):
        return None if isinstance(x, float) and math.isnan(x) else x

    return {
        "rows": rows,
        "rolling": rolling,
        "rolling_window": ROLLING,
        "summary": {"sessions": len(bars), "samples": n, "hits": hits, "hit_rate": clean(hit_rate),
                    "up_share": clean(up_share), "base_rate": clean(base), "p_value": clean(p),
                    "verdict": verdict},
        "gap_control": {"hit_rate": gap_hits / n if n else None,
                        "note": "Same days, predicting that the close follows the opening gap."},
    }
