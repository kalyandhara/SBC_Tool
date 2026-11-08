"""Phase 4: similar past dates for a profile's upcoming high-scoring sessions.

Descriptive research, not a tested signal. Similarity weights live in
sbc.navigator.signature (ANALOG_VERSION). Outcomes are raw (no costs). Missing data
is None ("n/a") and never filled.

Timing: an analog at session i is eligible only if its exit open (session i+5) is on
or before the last session before the target, so i + 5 <= L. This matches Phase 1's
open-to-open `oo_5` window. sbc.analogs.History.usable_before uses a close-to-close
window, so the rule is restated here rather than reused.

Upcoming sessions come from sbc.market_holidays (NSE holiday list; weekends only for
years it does not cover, disclosed in the notes).
"""
from __future__ import annotations

import bisect
import datetime as dt
from dataclasses import dataclass

import numpy as np

from sbc import analogs as SA
from sbc import market_holidays as MH
from sbc.navigator import scoring as S
from sbc.navigator import signature as G
from sbc.navigator.ephemeris import build_sky
from sbc.navigator.profile import Profile, natal_points

HORIZON = 5
SPACING = 5
TOP_N = 10
MIN_ANALOGS = 5
EXCLUDE_DAYS = 30
HIGH_SCORE = 61
FALLBACK_TARGETS = 5
SEED, DRAWS = 1729, 1000
ERA_MIN_DAYS = 730
TOO_FEW = "too few analogs"
NO_HIGH = "no high-scoring date in this window"
# The 11 CNX sector indices with data, excluding CNXBANK (CNXMEDIA, CNXHEALTH and
# CNXOILGAS have no rows in market.db).
SECTORS = ["CNXFIN", "CNXIT", "CNXPHARMA", "CNXAUTO", "CNXFMCG", "CNXMETAL", "CNXENERGY",
           "CNXREALTY", "CNXPSUBANK", "CNXINFRA", "CNXCONSUM"]
NOTES = [
    "Descriptive research, not a tested signal: no walk-forward test of analogs exists yet.",
    "Similarity is hand-set (nav-analog-1): 0.5 natal (0.8 contacts + 0.2 dasha) + 0.5 sky; never fitted.",
    "Next-5 return is open to open, 5 sessions, as in the backtest. Returns are raw, with no costs.",
    "Max drawdown runs from the analog-day open through each session's low or close up to the exit open.",
    "An analog is used only if its exit open is on or before the last session before the target.",
    "Analogs within 30 calendar days of the target are excluded; kept analogs are at least 5 sessions apart.",
    "Forward scores use Phase 1 scoring with neutral Vol, because the VIX close before the day is unknown.",
    "Upcoming sessions use the NSE holiday list in sbc.market_holidays.",
    "Bank Nifty and sector data end 2026-10-29 and most sectors start in 2011; India VIX starts 2008-03. "
    "Missing values show as n/a and are never filled.",
    "Random share: the fraction of 1,000 random draws (seed 1729) of the same size and spacing from the "
    "eligible pool whose win ratio was at least as high. No significance claim.",
    "Era-matched random share and baseline use the same procedure on pool sessions dated between the oldest "
    "and newest analog (widened to at least 2 years); the all-eras figures mix market regimes.",
]


def _ord(day: str) -> int:
    return dt.date.fromisoformat(day).toordinal()


def _f(x) -> float | None:
    x = float(x)
    return x if np.isfinite(x) else None


def next_sessions(last: str, n: int) -> list[str]:
    out, d = [], dt.date.fromisoformat(last)
    while len(out) < n:
        d = MH.next_trading_day(d, inclusive=False)
        out.append(d.isoformat())
    return out


def pick_targets(days, scores) -> tuple[str, list[int]]:
    scores = [int(s) for s in scores]
    high = [i for i, s in enumerate(scores) if s >= HIGH_SCORE]
    if high:
        return "high_scoring", high
    best = sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:FALLBACK_TARGETS]
    return "top_scores", sorted(best)


def eligible_mask(dates, target_date: str, horizon: int = HORIZON) -> np.ndarray:
    last = bisect.bisect_left(list(dates), target_date) - 1
    return np.arange(len(dates)) + horizon <= last


def select_analogs(sim, dates, target_date: str, k: int = TOP_N) -> tuple[list[int], str | None]:
    """Best-first, eligible, outside the exclusion window, thinned to SPACING sessions.
    Reuses sbc.analogs._thin; sbc.analogs.select is not used because its threshold
    mode and TOP_K of 30 do not match this spec."""
    kept, note, _ = _select(sim, dates, target_date, k)
    return kept, note


def _select(sim, dates, target_date: str, k: int = TOP_N):
    """select_analogs plus the eligible, outside-exclusion pool indices it computed."""
    t = _ord(target_date)
    far = np.array([abs(t - _ord(d)) > EXCLUDE_DAYS for d in dates])
    cand = np.where(eligible_mask(dates, target_date) & far)[0]
    if not len(cand):
        return [], TOO_FEW, cand
    scores = np.asarray(sim, float)[cand]
    order = np.argsort(-scores, kind="stable")
    kept = [int(cand[j]) for j in SA._thin(order, cand, SPACING, k)]
    if len(kept) < MIN_ANALOGS:
        return [], TOO_FEW, cand
    return kept, None, cand


def era_window(analog_dates) -> tuple[str, str]:
    """Oldest..newest analog date, widened symmetrically to at least ERA_MIN_DAYS."""
    lo, hi = min(_ord(d) for d in analog_dates), max(_ord(d) for d in analog_dates)
    extra = ERA_MIN_DAYS - (hi - lo)
    if extra > 0:
        lo, hi = lo - extra // 2, hi + (extra - extra // 2)
    return dt.date.fromordinal(lo).isoformat(), dt.date.fromordinal(hi).isoformat()


def era_pool(dates, pool, window) -> np.ndarray:
    pool = np.asarray(pool, int)
    return np.array([i for i in pool if window[0] <= dates[i] <= window[1]], dtype=int)


def _ret(o, c) -> float | None:
    return _f(c / o - 1) if np.isfinite(o) and np.isfinite(c) and o else None


def outcomes(i: int, prices: dict) -> dict:
    o, c, lo = prices["open"], prices["close"], prices["low"]
    n = len(o)
    vix = prices["vix_close"]
    vix_change = None
    if i > 0 and np.isfinite(vix[i]) and np.isfinite(vix[i - 1]) and vix[i - 1]:
        vix_change = _f((vix[i] / vix[i - 1] - 1) * 100)
    present, missing = [], []
    for s in SECTORS:
        r = _ret(prices["sector_open"][s][i], prices["sector_close"][s][i])
        (missing.append(s) if r is None else present.append((s, r)))
    present.sort(key=lambda x: (-x[1], x[0]))
    next5 = drawdown = None
    if i + HORIZON < n:
        exit_open = o[i + HORIZON]
        window = np.r_[lo[i:i + HORIZON], c[i:i + HORIZON], exit_open]
        if np.isfinite(o[i]) and np.isfinite(window).all():
            next5 = _f(exit_open / o[i] - 1)
            drawdown = min(0.0, float(window.min() / o[i] - 1))
    return {"nifty_day": _ret(o[i], c[i]),
            "bank_day": _ret(prices["bank_open"][i], prices["bank_close"][i]),
            "vix_change_pct": vix_change,
            "sectors_top5": [{"symbol": s, "return": r} for s, r in present[:5]],
            "sectors_missing": missing,
            "next5": next5, "drawdown": drawdown}


def random_draws(pool_next5, n, spacing, observed_win, seed=SEED, draws=DRAWS, positions=None):
    """(share, short): share of draws with win ratio >= observed_win; `short` counts
    draws where spacing left fewer than n sessions."""
    vals = np.asarray(pool_next5, float)
    pos = np.arange(len(vals)) if positions is None else np.asarray(positions)
    ok = np.isfinite(vals)
    vals, pos = vals[ok], pos[ok]
    if not len(vals) or n <= 0:
        return None, draws
    rng = np.random.default_rng(seed)
    hits = short = 0
    for _ in range(draws):
        kept = SA._thin(rng.permutation(len(vals)), pos, spacing, n)
        short += len(kept) < n
        win = float((vals[kept] > 0).mean()) if kept else 0.0
        hits += win >= observed_win - 1e-12
    return hits / draws, short


def random_share(pool_next5, n, spacing, observed_win, seed=SEED, draws=DRAWS, positions=None):
    return random_draws(pool_next5, n, spacing, observed_win, seed, draws, positions)[0]


def summarize(rows, pool_next5, share, short, era=None) -> dict:
    nx = np.array([r["outcomes"]["next5"] for r in rows if r["outcomes"]["next5"] is not None], float)
    dd = np.array([r["outcomes"]["drawdown"] for r in rows if r["outcomes"]["drawdown"] is not None], float)
    pool = np.asarray(pool_next5, float)
    pool = pool[np.isfinite(pool)]
    return {
        "n": len(rows), "n_with_outcome": int(len(nx)),
        "win_ratio": float((nx > 0).mean()) if len(nx) else None,
        "mean_next5": float(nx.mean()) if len(nx) else None,
        "median_next5": float(np.median(nx)) if len(nx) else None,
        "mean_drawdown": float(dd.mean()) if len(dd) else None,
        "baseline": {"n": int(len(pool)),
                     "win_ratio": float((pool > 0).mean()) if len(pool) else None,
                     "mean_next5": float(pool.mean()) if len(pool) else None},
        "random_share": share, "random_short_draws": int(short),
        "median_age_years": float(np.median([r["age_years"] for r in rows])) if rows else None,
        "label": f"anecdotal: {len(rows)} analogs, not a tested signal",
        "era_random_share": era["random_share"] if era else None,
        "era_baseline": era["baseline"] if era else None,
        "era_window": {"start": era["window"][0], "end": era["window"][1]} if era else None,
        "era_note": ((era["note"] or "") + (" " if era["note"] else "") + (
            f"Analogs are mostly from {era['window'][0]} to {era['window'][1]}; compare with the "
            "era-matched figures, because the all-eras pool mixes market regimes.")) if era else None,
    }


@dataclass
class Market:
    dates: list[str]
    prices: dict           # aligned arrays for outcomes()
    vix: dict              # every INDIAVIX close by date, for scoring


def load_market() -> Market:
    """Nifty sessions up to the last close, with Bank Nifty, VIX and sectors aligned (NaN if absent)."""
    from sbc import market_store as M
    bars = [b for b in M.get_daily("NIFTY")]
    while bars and bars[-1]["close"] is None:
        bars.pop()
    if not bars:
        raise M.MarketDataMissing("no NIFTY bars")
    dates = [b["date"][:10] for b in bars]
    pos = {d: i for i, d in enumerate(dates)}

    def col(rows, key):
        out = np.full(len(dates), np.nan)
        for r in rows:
            i = pos.get(r["date"][:10])
            if i is not None and r[key] is not None:
                out[i] = r[key]
        return out
    vix_rows = M.get_daily("INDIAVIX")
    bank = M.get_daily("CNXBANK")
    sec = {s: M.get_daily(s) for s in SECTORS}
    prices = {"open": col(bars, "open"), "close": col(bars, "close"), "low": col(bars, "low"),
              "bank_open": col(bank, "open"), "bank_close": col(bank, "close"),
              "vix_close": col(vix_rows, "close"),
              "sector_open": {s: col(r, "open") for s, r in sec.items()},
              "sector_close": {s: col(r, "close") for s, r in sec.items()}}
    vix = {r["date"][:10]: r["close"] for r in vix_rows
           if r["close"] is not None and r["date"][:10] <= dates[-1]}
    return Market(dates, prices, vix)


def _history_sky(dates):
    hist = SA.load_nifty_history()
    if hist.sky.dates[:len(dates)] != list(dates):
        raise ValueError("fingerprint history does not align with market sessions")
    return SA._slice(hist.sky, len(dates))


def build(profile: Profile, market: Market, days: int = 30, sky_history=None,
          fingerprint_fn=None) -> dict:
    from sbc.fingerprint import fingerprint
    fingerprint_fn = fingerprint_fn or fingerprint
    dates, n = list(market.dates), len(market.dates)
    sky_history = sky_history if sky_history is not None else _history_sky(dates)
    future = next_sessions(dates[-1], days)
    all_days = dates + future
    sky = build_sky(all_days)
    nan = np.full(days, np.nan)
    opens = np.r_[market.prices["open"], nan]
    closes = np.r_[market.prices["close"], nan]
    vix = {d: c for d, c in market.vix.items() if d != dates[-1]}   # neutral Vol, as in Phase 1
    series = S.score_series(sky, profile, opens, closes, vix)
    scores = [int(s) for s in series.score[n:]]
    mode, picks = pick_targets(future, scores)

    natal = natal_points(profile)
    _, contacts = G.contact_matrix(sky, natal)
    antar, prat = G.dasha_lords(natal["Moon"], profile.birth_date, all_days)
    o = market.prices["open"]
    next5 = np.full(n, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        next5[:n - HORIZON] = o[HORIZON:] / o[:n - HORIZON] - 1
    pool_idx = np.arange(n)

    targets = []
    for k in picks:
        tdate = future[k]
        target = SA.SkyArrays.from_fingerprints([fingerprint_fn(tdate)])
        sky_sim = SA.similarity(target, sky_history)["overall"]
        nat_sim = G.natal_similarity(n + k, contacts, antar, prat, pool_idx)
        blended = G.blend(nat_sim, sky_sim)
        idx, note, pool = _select(blended, dates, tdate)
        t_ord = _ord(tdate)
        rows = [{"date": dates[i],
                 "age_years": round((t_ord - _ord(dates[i])) / 365.25, 1),
                 "similarity": round(float(blended[i]), 4),
                 "natal": round(float(nat_sim[i]), 4), "sky": round(float(sky_sim[i]), 4),
                 "outcomes": outcomes(i, market.prices)} for i in idx]
        summary = None
        if rows:
            vals = [r["outcomes"]["next5"] for r in rows if r["outcomes"]["next5"] is not None]
            win = float(np.mean([v > 0 for v in vals])) if vals else 0.0
            share, short = random_draws(next5[pool], len(vals), SPACING, win, positions=pool)
            win_era = era_window([r["date"] for r in rows])
            ep = era_pool(dates, pool, win_era)
            e_share, e_short = random_draws(next5[ep], len(vals), SPACING, win, positions=ep)
            e_note = None
            if e_share is not None and e_short:
                e_share = None
                e_note = (f"Era-matched random share unavailable: the era pool could not hold "
                          f"{len(vals)} spaced draws in {e_short} of {DRAWS} draws.")
            elif e_share is None:
                e_note = "Era-matched random share unavailable: no era outcomes to draw from."
            e_vals = next5[ep][np.isfinite(next5[ep])]
            era = {"random_share": e_share, "window": win_era, "note": e_note,
                   "baseline": {"n": int(len(e_vals)),
                                "win_ratio": float((e_vals > 0).mean()) if len(e_vals) else None,
                                "mean_next5": float(e_vals.mean()) if len(e_vals) else None}}
            summary = summarize(rows, next5[pool], share, short, era)
            if short:
                note = f"spacing could not be met in {short} of {DRAWS} random draws"
        score = scores[k]
        targets.append({"date": tdate, "score": score, "band": S.band_of(score),
                        "analogs": rows, "summary": summary, "note": note})
    notes = list(NOTES)
    if mode == "top_scores":
        notes.insert(0, NO_HIGH)
    uncovered = sorted({d[:4] for d in future if not MH.is_covered(dt.date.fromisoformat(d))})
    if uncovered:
        notes.append(f"No NSE holiday list for {', '.join(uncovered)}: weekends only are skipped.")
    return {"version": G.ANALOG_VERSION, "data_asof": dates[-1],
            "window": {"start": future[0], "end": future[-1], "sessions": days},
            "mode": mode, "targets": targets, "notes": notes}
