# Task 2 report: targets, analog selection, outcomes, random comparison

Status: DONE_WITH_CONCERNS

## Delivered
- `sbc/navigator/analogs.py`: `next_sessions`, `pick_targets`, `eligible_mask`, `select_analogs`, `outcomes`,
  `random_draws` / `random_share`, `summarize`, `Market` + `load_market`, `build(profile, market, days=30, sky_history=None, fingerprint_fn=None)`.
- `tests/test_navigator_analogs.py`: 14 tests.

## Decisions
- Calendar: `sbc.market_holidays` (NSE list; years it does not cover fall back to weekends only, disclosed in notes).
- Eligibility restated (i+5 <= L, L = last session before target) instead of `History.usable_before`, whose window is close-to-close.
- Selection reuses `sbc.analogs._thin`; `sbc.analogs.select` not used (threshold mode, TOP_K=30 do not fit).
- Drawdown: min(0, min over sessions i..i+4 of low and close, and the exit open) / open[i] - 1. Exit day's low excluded.
- VIX change is percent vs the previous Nifty session's VIX close; missing either gives None.
- Sectors: 11 CNX indices with data (CNXMEDIA/HEALTH/OILGAS have no rows), CNXBANK excluded.
- Forward scores: `score_series` over history + future with NaN prices and the last VIX close dropped, as `_compute` does (neutral Vol).
- Random draws: permutation then `_thin` to the same size and spacing over finite pool sessions; shortfall counted and noted.
- History sky: `sbc.analogs.load_nifty_history().sky`, prefix-checked against market sessions.

## Verification
- RED: collection ImportError (module missing). GREEN: 14 passed.
- Mutations (eligibility `<` and `+1`, drawdown including exit-day low) each fail a test.
- Navigator tests: 577 passed.
- Real data (sample profile, days=30): 4.5 s cold, 2.3 s warm, identical output on repeat. Mode top_scores (no score >= 61), 5 targets.

## Concerns
- pytest isolates market.db, so the determinism/leak test uses 60 real sessions with synthetic prices and real fingerprints, not the live DB.
- Real run: first target's analogs have median age 0.85 years. They cluster in recent time, probably from the shared dasha period and slow-tier sky. The era check shows it, but it is worth a look.
- Only 5 targets were timed (no high-scoring day). 30 targets would take an estimated 10-15 s, which is not measured.

## Fix round 1
- Era-matched comparison per target: window = oldest..newest analog date, widened symmetrically to >= 730 days (`era_window`, `era_pool`). Same draws procedure (size, spacing 5, 1,000 draws, seed 1729). Summary gains `era_random_share`, `era_baseline` (n, win_ratio, mean_next5), `era_window` (start/end), `era_note` ("Analogs are mostly from <window>; compare with the era-matched figures, because the all-eras pool mixes market regimes."). If any era draw cannot meet spacing, or there are no era outcomes, `era_random_share` is None with a note. All-eras share and baseline kept; one general note added to NOTES.
- `random_draws`/`random_share` return None (not 1.0) when no analog has a next-5 value (n <= 0 or no finite pool).
- `select_analogs` now wraps `_select`, which also returns the pool indices; `build` reuses them instead of recomputing the far/eligible masks.
- RED: 7 new/changed tests failed first; GREEN: 19 passed in test_navigator_analogs.py.
- Concern: era pool uses the target's pool (eligible, outside 30 days); a tight analog cluster gives a ~2-year era, so era draws may be short on spacing and return None; not checked on real data.

## Fix round 2
- `era_window(analog_dates, first=None, last=None)`: 25th..75th percentile of analog dates (rounded to days), widened symmetrically around the midpoint to >= 730 days, then clipped to the pool's first/last date (so it never passes the last eligible session). `build` passes `dates[pool.min()]`/`dates[pool.max()]`. Note text on the summary and None behaviour unchanged; the general NOTES line now says "middle half (25th to 75th percentile)".
- RED: 3 tests failed first. New tests: outlier 15 years older than nine recent analogs (window stays within 3 years of the cluster, total <= 4 years), clip to bounds. Adjusted the "already wide" test and the build test (start <= end, since start may now exceed the oldest analog).
- GREEN: 21 passed.
- Real data (sample profile, days=30), era window / era_random_share / all-eras share:
  - 2026-11-17: 2025-04-11..2026-10-16 / 0.939 / 0.973
  - 2026-11-20: 2025-02-07..2026-10-19 / 0.777 / 0.906
  - 2026-12-10: 2025-01-13..2026-10-30 / 0.822 / 0.917
  - 2026-12-15: 2024-01-21..2026-03-10 / 0.486 / 0.548
  - 2026-12-22: 2025-01-27..2026-10-30 / 0.593 / 0.777
- Concern: the era windows are now 1.5-2.7 years, and the era shares are lower than all-eras shares, which is the intended control.
