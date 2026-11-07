# Task 6 report: score combination, HistVal, lineage

**Status:** DONE WITH CONCERNS (code complete; concerns are decisions and notes for Task 7).
**Bead:** SBC_Tool-r14. Suggested close reason: "scoring.py adds bands, actions, combine, embargoed hist_val, exact lineage with clip adjustment lines and score_series with 253-session VIX lead-in; 48 scoring tests pass, 18 mutants killed; full suite 1201 passed, only the known route-pruning failure."

## Built
`sbc/navigator/scoring.py`: `band_of`, `action_of`, `combine`, `forward_returns`, `hist_val`, `lineage`, `ScoreSeries`, `score_series`, `day_lineage`.
- `combine` renormalises over the terms given, so the HistVal base is the other five terms at 100%.
- `hist_val` uses running per-band totals and `np.digitize`; 0.015s on 4700 days.
- `score_series` takes optional `min_sessions` (default 756) and `horizon` (default 5). Task 7's `score_for(min_sessions=)` needs the first.
- `ScoreSeries.score` is an integer array, rounded the same way as `lineage`, so the two always agree.

## Plan deviations
1. **Embargo off by one in the snippet.** The plan used `returns[:t-horizon]`, which is t'+h < t, stricter than the stated rule t'+h <= t. The code uses `t-horizon+1`, exactly the stated rule.
2. **Return definition made explicit.** `forward_returns`: `closes[t+h-1]/opens[t]-1`. A window ending at open(t+h) would need T's open on the boundary day, breaking "T-1 close is the last input". With this definition t'+h<=t ends exactly at the T-1 close. `hist_val` relies on this, so a caller passing open-to-open returns would leak T's open. `score_series` is the only producer.
3. **`vol_term` changed (terms.py, not in the brief's file list).** New `min_history` argument, default unchanged. Without it, days with 20-251 closes got a percentile instead of being neutral and flagged. It counts closes ever seen, not closes in the window: Nifty has 19 sessions with no VIX bar since 2008, and a window count would blank a year after each gap.
4. **Added beyond the interface:** `ScoreSeries.factors(i)`, `day_lineage(series, i)`, `forward_returns`. Tasks 7 and 9 need them.
5. **Frozen fixtures brought forward from Task 7.** conftest points `SBC_MARKET_DB` at an empty temp file, so DB-based real-day tests skipped silently. Added `tests/fixtures/navigator_nifty_sample.csv` (500 real rows, 2024-10-23 to 2026-10-30) and `navigator_vix_sample.csv` (750 rows, including 253 lead-in). Task 7 should reuse both; `sample_inputs` needs the VIX file.

## Lineage shape
`{score, contributions, raised, lowered}`. Each contribution line has `term, label, raw, weight, baseline, contribution, factors`. Lines sum exactly to the score; on a line with factors, baseline plus factors sum exactly to the line. Arithmetic is in integer hundredths.
- Factor contribution is `weight*raw/2`; `baseline` is `weight*50`.
- Clip: when a term's factor raws sum beyond +/-100, the term line shows the unclipped value and a separate `adjustment: true` line carries the difference. Generic, so Strength is covered as well as Transit.
- Residual goes to the largest term line, then the largest active factor. If a line only has neutral factors, a "Rounding to whole score" line is added so a neutral factor stays at 0.
- `raised`/`lowered` use the clipped value relative to 50.

## Evidence
- RED: `pytest tests/test_navigator_scoring.py` -> ImportError, cannot import name 'scoring'.
- First GREEN run: 1 failed (my tolerance: 4.375 displays as 4.38) and the 5 real-day tests skipped. Skips fixed with the fixtures above.
- GREEN: 48 passed, 0 skipped, including real days.
- Leakage on real fixture days: changing opens, closes and VIX from day 300 on leaves score, base, histval and vol identical through day 300; HistVal varies on those days; later histval does change. The T-1 close does reach day T and not earlier days (the sensitivity side). Boundary test pins t-h used and t-h+1 not used.
- Lineage on all 500 real days sums exactly (Decimal) and equals the series score; clipped real days exist in the fixture and each shows the adjustment.
- Mutation: 18 hand mutants, all killed (embargo +1/-1, return window, no clip, >= clip, short lead-in, no min_history, lead offset in factors and values, band edge, both residuals, 30-session minimum, no warm-up, HistVal in base, factor scale, raised filter, history count offset).
- Timing, synthetic 4700-day sky: score_series 0.114s, about 23s for 200 charts.
- Full suite: 1 failed, 1201 passed, 5 skipped. The failure is `test_every_route_has_a_ui_caller_or_is_listed`, the known one.
- No returns were studied, printed or used to tune anything. Fixture prices only flow through the pipeline.

## Files
- sbc/navigator/scoring.py (new)
- sbc/navigator/terms.py (`vol_term` min_history)
- tests/test_navigator_scoring.py (new)
- tests/fixtures/navigator_nifty_sample.csv, navigator_vix_sample.csv (new)

## Concerns
1. The whole-score residual can reach 0.5 points, and per spec it lands on the largest line and factor. That line can differ visibly from `weight*value`, and one factor can look up to 0.5 larger than `weight*raw/2`. A separate rounding line would be cleaner, but the spec says largest factor. User decision.
2. With real data from 2007-09, VIX starts 2008-03, so Vol is neutral and flagged until about March 2009, which overlaps the HistVal warm-up. Vol stays 50 for those days in scoring.
3. Spec metrics include open-to-open returns; HistVal uses the open-to-close window (deviation 2). Task 7 measures band returns separately and must not feed open-to-open into `hist_val`.
4. Fixture is 500 rows, so 300 sessions of VIX-free warm-up do not apply: VIX is in full from day 0. Task 7's `min_sessions=120` leakage test works as written.
5. Moon, Strength and Vol recompute per placebo. At about 23s for 200 charts this needs no cache.
