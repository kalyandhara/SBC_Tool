# Final whole-branch review fixes: AstroTrade Navigator Phase 1

RED first: new tests failed before the code changes (occupancy, single labels/clean_json, NOTES line, score-card verdict, occupancy UI label). The percentile and verdict pins passed at once, as expected for coverage pins.

1. Verdict beside the action label (spec line 95). `/score` now returns `latest_verdict` from `store.latest_run`: run id, verdict (done runs only), status, data date, a `stale` flag when weights_version or engine version differ from the current ones, and a `text`. "no backtest yet" when there is no run. Any store failure degrades to "verdict unavailable" and the score still returns 200. chart_hash is never copied out. The score card shows the text as a tag right beside "Action label". Tests: 4 API tests (Postgres, navigator_test) and 1 page test.
2. Golden coverage: unit pins on `percentile` and `verdict` with fixed inputs, 40 placebos (n_placebo >= 20), a non-sample chart: 97.5th percentile gives "edge candidate", 92.5th gives "no demonstrated edge". No weight, gate or parameter default changed.
3. Occupancy: each band gets `occupancy = {horizon, events, insufficient}` from the first horizon, as `_top_band` does; `by_horizon` keeps per-horizon events. The UI occupancy table reads it, and its caption now says counts are for the first horizon.
4. `PIPELINE_LABEL`, `RESEARCH_LABEL` and `label_for()` live only in `sbc/navigator/backtest.py`; the blueprint uses `B.label_for`. `_clean` is now public `clean_json`, used by the blueprint.
5. NOTES gains: decile cut-points for the control come from the whole sample; they affect only the descriptive control, not the signal.
6. Spec now names `docker-compose.navigator.yml` and states the main compose file is unchanged.

Golden fixture regenerated. Disclosed reason: only additions (the `occupancy` key per band and the new NOTES line); a script confirmed every other value is unchanged.

Validation: full suite 1551 passed, 4 skipped, 1 failed (the known `test_every_route_has_a_ui_caller_or_is_listed`, on /api/briefing_summary and /health only).
