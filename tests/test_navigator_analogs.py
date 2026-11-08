"""Phase 4 analog selection, outcomes and random comparison: exact values on fixtures."""
import datetime as dt

import numpy as np
import pytest

from sbc.navigator import analogs as A

DATES = [(dt.date(2024, 1, 1) + dt.timedelta(days=i)).isoformat() for i in range(40)]


def _prices():
    o = 100.0 + np.arange(40)
    c = o + 0.5
    lo = o - 1.0
    lo[12] = 100.0       # deepest low inside the window of analog 10
    lo[15] = 50.0        # the exit day's low is outside the window
    vix = np.full(40, 20.0)
    vix[10], vix[9] = 22.0, 20.0
    vix[20] = np.nan
    secs = {s: (np.full(40, 100.0), np.full(40, 100.0)) for s in A.SECTORS}
    for k, s in enumerate(A.SECTORS):
        secs[s][1][10] = 100.0 + k        # sector k returns k% on day 10
    secs["CNXCONSUM"][0][10] = np.nan     # missing that day
    return {"open": o, "close": c, "low": lo,
            "bank_open": np.full(40, 200.0), "bank_close": np.r_[np.full(10, 200.0), 210.0, np.full(29, np.nan)],
            "vix_close": vix,
            "sector_open": {s: v[0] for s, v in secs.items()},
            "sector_close": {s: v[1] for s, v in secs.items()}}


def test_sectors_are_the_eleven_cnx_without_bank():
    assert len(A.SECTORS) == 11 and "CNXBANK" not in A.SECTORS


def test_outcomes_exact():
    out = A.outcomes(10, _prices())
    assert out["nifty_day"] == pytest.approx(110.5 / 110 - 1, abs=1e-15)
    assert out["bank_day"] == pytest.approx(210 / 200 - 1, abs=1e-15)
    assert out["vix_change_pct"] == pytest.approx((22 / 20 - 1) * 100, abs=1e-12)
    assert out["next5"] == pytest.approx(115 / 110 - 1, abs=1e-15)
    assert out["drawdown"] == pytest.approx(100 / 110 - 1, abs=1e-15)
    assert out["sectors_missing"] == ["CNXCONSUM"]
    present = [s for s in A.SECTORS if s != "CNXCONSUM"]
    expect = sorted(present, key=lambda s: -A.SECTORS.index(s))[:5]
    assert [r["symbol"] for r in out["sectors_top5"]] == expect
    assert out["sectors_top5"][0]["return"] == pytest.approx(A.SECTORS.index(expect[0]) / 100)


def test_outcomes_na_never_filled():
    p = _prices()
    out = A.outcomes(20, p)     # VIX missing on the day, bank missing
    assert out["vix_change_pct"] is None and out["bank_day"] is None
    assert A.outcomes(21, p)["vix_change_pct"] is None   # previous close missing
    assert A.outcomes(0, p)["vix_change_pct"] is None
    end = A.outcomes(35, p)     # exit open beyond the data
    assert end["next5"] is None and end["drawdown"] is None


def test_drawdown_zero_when_never_below_open():
    p = _prices()
    p["low"] = p["open"] + 0.1
    assert A.outcomes(3, p)["drawdown"] == 0.0


def test_eligibility_cutoff_exact():
    target = DATES[30]          # last session before it is index 29
    m = A.eligible_mask(DATES, target)
    assert m[24] and not m[25]
    assert m.sum() == 25
    # a target one session later moves the cutoff by exactly one
    assert A.eligible_mask(DATES, DATES[31]).sum() == 26
    future = A.eligible_mask(DATES, "2030-01-01")
    assert future.sum() == 35 and future[34] and not future[35]


def test_select_spacing_exclusion_and_top10():
    dates = [(dt.date(2020, 1, 1) + dt.timedelta(days=i)).isoformat() for i in range(200)]
    sim = np.linspace(0, 1, 200)            # most similar near the end
    idx, note = A.select_analogs(sim, dates, dates[199])
    assert note is None and len(idx) == 10
    pos = sorted(idx)
    assert min(np.diff(pos)) >= 5
    target_ord = dt.date.fromisoformat(dates[199]).toordinal()
    assert all(target_ord - dt.date.fromisoformat(dates[i]).toordinal() > 30 for i in idx)
    assert max(idx) == 168      # 199 - 31 is the nearest allowed, also eligible (168+5 <= 198)
    assert list(idx) == sorted(idx, reverse=True)  # best first


def test_select_too_few():
    dates = DATES
    idx, note = A.select_analogs(np.ones(40), dates, "2024-02-20")
    # excluded from 2024-01-21 (index 20) on; 0..19 spaced 5 apart gives only 4
    assert len(idx) == 0 and note == "too few analogs"


def test_pick_targets_threshold():
    assert A.pick_targets(["a", "b", "c"], [61, 60, 75]) == ("high_scoring", [0, 2])


def test_pick_targets_top5_ties_to_earlier():
    scores = [50, 55, 55, 40, 55, 55, 55, 60]
    mode, idx = A.pick_targets([str(i) for i in range(8)], scores)
    assert mode == "top_scores" and idx == [1, 2, 4, 5, 7]


def test_next_sessions_skip_holidays():
    # 2026-11-10 is Diwali Balipratipada, 2026-11-14/15 a weekend
    assert A.next_sessions("2026-11-06", 4) == ["2026-11-09", "2026-11-11", "2026-11-12", "2026-11-13"]


def test_random_share_bounds_and_seed():
    rng = np.random.default_rng(0)
    pool = rng.normal(0, 1, 500)
    a = A.random_share(pool, 10, 5, 0.6)
    assert a == A.random_share(pool, 10, 5, 0.6)
    assert 0.0 <= a <= 1.0
    assert A.random_share(pool, 10, 5, 0.0) == 1.0
    assert A.random_share(np.ones(500), 10, 5, 1.0) == 1.0
    assert A.random_share(-np.ones(500), 10, 5, 0.1) == 0.0


def test_random_share_none_without_outcomes():
    assert A.random_draws(np.ones(50), 0, 5, 0.0) == (None, 1000)
    assert A.random_draws(np.full(50, np.nan), 5, 5, 0.0)[0] is None
    assert A.random_share(np.ones(50), 0, 5, 0.0) is None


def test_era_window_exact_and_widened():
    # span 2025-01-01..2025-01-31 = 30 days; widened to 730 days: 700 extra, 350 each side
    assert A.era_window(["2025-01-31", "2025-01-01", "2025-01-15"]) == ("2024-01-17", "2026-01-16")
    # already wider than 2 years: p25..p75 of two dates is 2020-07-01..2023-07-01 (approx), unchanged by widening
    lo, hi = A.era_window(["2020-01-01", "2024-01-01"])
    assert "2020-01-01" < lo and hi < "2024-01-01" and (_d(hi) - _d(lo)).days >= 730


def _d(s):
    import datetime as dt
    return dt.date.fromisoformat(s)


def test_era_window_ignores_old_outlier():
    recent = [f"2026-{m:02d}-15" for m in range(1, 10)]  # nine within 8 months
    w = A.era_window(["2011-06-01"] + recent)
    assert (_d(recent[0]) - _d(w[0])).days <= 3 * 365
    assert (_d(w[1]) - _d(recent[-1])).days <= 3 * 365
    assert (_d(w[1]) - _d(w[0])).days <= 4 * 365


def test_era_window_clipped_to_bounds():
    w = A.era_window(["2025-01-01", "2025-01-15"], first="2024-12-01", last="2025-02-01")
    assert w == ("2024-12-01", "2025-02-01")


def test_era_pool_filters_by_date_inclusive():
    dates = ["2020-01-01", "2020-06-01", "2021-01-01", "2022-01-01"]
    assert A.era_pool(dates, np.array([0, 1, 2, 3]), ("2020-06-01", "2021-01-01")).tolist() == [1, 2]


def test_select_returns_the_pool_mask_it_used():
    dates = [(dt.date(2023, 1, 2) + dt.timedelta(days=i)).isoformat() for i in range(200)]
    idx, note, pool = A._select(np.arange(200, dtype=float), dates, dates[199])
    far = np.array([abs(dt.date.fromisoformat(dates[199]).toordinal() - dt.date.fromisoformat(d).toordinal()) > 30
                    for d in dates])
    assert pool.tolist() == np.where(A.eligible_mask(dates, dates[199]) & far)[0].tolist()


def test_random_draws_respect_spacing_and_disclose_shortfall():
    share, short = A.random_draws(np.ones(20), 10, 5, 0.5, draws=10)
    assert short == 10 and share == 1.0   # 20 sessions cannot hold 10 spaced 5 apart


def test_summary_fields():
    rows = [{"date": "2020-01-01", "age_years": 4.0, "outcomes": {"next5": 0.02, "drawdown": -0.01}},
            {"date": "2019-01-01", "age_years": 5.0, "outcomes": {"next5": -0.01, "drawdown": -0.03}},
            {"date": "2018-01-01", "age_years": 6.0, "outcomes": {"next5": None, "drawdown": None}}]
    s = A.summarize(rows, np.array([0.01, -0.02, 0.03, 0.0]), 0.25, 0)
    assert s["n"] == 3 and s["n_with_outcome"] == 2
    assert s["win_ratio"] == 0.5
    assert s["mean_next5"] == pytest.approx(0.005) and s["median_next5"] == pytest.approx(0.005)
    assert s["mean_drawdown"] == pytest.approx(-0.02)
    assert s["baseline"] == {"n": 4, "win_ratio": 0.5, "mean_next5": pytest.approx(0.005)}
    assert s["random_share"] == 0.25 and s["median_age_years"] == 5.0
    assert s["label"] == "anecdotal: 3 analogs, not a tested signal"
    assert s["era_random_share"] is None and s["era_baseline"] is None and s["era_window"] is None


def test_summary_era_fields_and_note():
    rows = [{"date": "2025-01-01", "age_years": 1.0, "outcomes": {"next5": 0.02, "drawdown": -0.01}}] * 2
    era = {"random_share": 0.4, "baseline": {"n": 2, "win_ratio": 0.5, "mean_next5": 0.01},
           "window": ("2024-01-01", "2026-01-01"), "note": None}
    s = A.summarize(rows, np.array([0.01]), 0.1, 0, era)
    assert s["era_random_share"] == 0.4
    assert s["era_baseline"] == {"n": 2, "win_ratio": 0.5, "mean_next5": 0.01}
    assert s["era_window"] == {"start": "2024-01-01", "end": "2026-01-01"}
    assert s["era_note"] == ("Analogs are mostly from 2024-01-01 to 2026-01-01; compare with the era-matched "
                             "figures, because the all-eras pool mixes market regimes.")


@pytest.fixture(scope="module")
def synthetic():
    """60 real NSE sessions to 2026-11-06 with synthetic prices and real skies."""
    from functools import lru_cache
    from sbc import market_holidays as MH
    from sbc.analogs import SkyArrays
    from sbc.fingerprint import fingerprint
    d, dates = dt.date(2026, 11, 6), []
    while len(dates) < 60:
        if MH.is_trading_day(d):
            dates.append(d.isoformat())
        d -= dt.timedelta(days=1)
    dates.reverse()
    fp = lru_cache(maxsize=None)(fingerprint)
    sky = SkyArrays.from_fingerprints([fp(x) for x in dates])
    rng = np.random.default_rng(7)
    o = 20000 * np.cumprod(1 + rng.normal(0, 0.01, 60))
    c = o * (1 + rng.normal(0, 0.005, 60))
    p = {"open": o, "close": c, "low": np.minimum(o, c) * 0.995,
         "bank_open": o * 2, "bank_close": c * 2, "vix_close": np.full(60, 14.0),
         "sector_open": {s: o for s in A.SECTORS}, "sector_close": {s: c for s in A.SECTORS}}
    vix = {x: 14.0 for x in dates}
    return A.Market(dates, p, vix), sky, fp


def test_build_deterministic_and_leak_free(synthetic):
    from sbc.navigator.profile import SAMPLE_PROFILE
    market, sky, fp = synthetic
    a = A.build(SAMPLE_PROFILE, market, days=5, sky_history=sky, fingerprint_fn=fp)
    b = A.build(SAMPLE_PROFILE, market, days=5, sky_history=sky, fingerprint_fn=fp)
    assert a == b
    assert a["version"] == "nav-analog-1" and a["data_asof"] == "2026-11-06"
    assert a["window"] == {"start": "2026-11-09", "end": "2026-11-16", "sessions": 5}
    assert a["mode"] in ("high_scoring", "top_scores")
    if a["mode"] == "top_scores":
        assert len(a["targets"]) == 5 and a["notes"][0] == A.NO_HIGH
    pos = {d: i for i, d in enumerate(market.dates)}
    for t in a["targets"]:
        assert "chart_hash" not in t
        assert t["analogs"], t["note"]
        assert 5 <= len(t["analogs"]) <= 10
        for an in t["analogs"]:
            assert pos[an["date"]] + 5 <= 59
            i = pos[an["date"]]
            assert an["outcomes"]["next5"] == market.prices["open"][i + 5] / market.prices["open"][i] - 1
        assert t["summary"]["label"] == f"anecdotal: {len(t['analogs'])} analogs, not a tested signal"
        assert 0.0 <= t["summary"]["random_share"] <= 1.0
        assert t["summary"]["era_window"]["start"] <= t["summary"]["era_window"]["end"]
        e = t["summary"]["era_baseline"]
        assert e is None or e["n"] <= t["summary"]["baseline"]["n"]
        assert t["summary"]["era_random_share"] is None or 0.0 <= t["summary"]["era_random_share"] <= 1.0
