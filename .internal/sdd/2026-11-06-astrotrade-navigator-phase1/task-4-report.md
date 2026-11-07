# Task 4 report: Weight tables and shared ephemeris

**Status:** DONE (one concern noted below)

## Built
- `sbc/navigator/weights.py`: plan tables verbatim (WEIGHTS_VERSION "nav-1"), reformatted only. NODE_FACTOR is defined before ASPECT_WEIGHT (verified; also resolved at call time). Hand-set; nothing fitted, nothing computed against returns.
- `sbc/navigator/ephemeris.py`: `SkyTable` + `build_sky(days)` at 09:15 IST, nine bodies (Sun..Saturn, Rahu, Ketu). Plan snippet worked as written; `_julday`, `_utc_from_local`, `positions` signatures verified against repo.
- `tests/test_navigator_ephemeris.py`: 18 tests. Required three exact values; TERM_WEIGHTS sum; version pin; five non-explicit values (Jupiter SXT 24, Saturn SQ -37.5, Venus OPP -5, Mars CONJ -15, Mars TRI 10); node halving (Rahu/Ketu TRI 5.0 vs Mars TRI 10.0 with same BENEFIC, Rahu CONJ -7.5, Rahu==Ketu); DASHA/strength tables; DRUVA/UGRA names subset of `NAKSHATRAS_27`; sky shape/bodies; sky vs `positions()` (3 days, lon and retrograde).

## RED / GREEN
- RED: `ImportError: cannot import name 'weights' from 'sbc.navigator'` (collection error, before implementation).
- GREEN: 18 passed.
- Falsifiability (mutations, each restored): NODE_FACTOR 1.0 -> 1 fail; SXT .6->.5 -> 1 fail; Saturn benefic -.875->-.8 -> 1 fail; 09:15->10:15 -> 3 fail. Removing "Rohini" from DRUVA is NOT caught (subset test only checks names exist; Task 5 owns content use).
- Self-caught: first draft of the nakshatra test guarded on a wrong attribute and asserted nothing; fixed to `NAKSHATRAS_27`.
- Full suite: 1109 passed, 5 skipped, 1 failed (`test_every_route_has_a_ui_caller_or_is_listed`, known pre-existing).

## Files
sbc/navigator/weights.py, sbc/navigator/ephemeris.py, tests/test_navigator_ephemeris.py

## Bead SBC_Tool-35l
Not touched (no bd). Suggested close reason: "Weight tables (nav-1, hand-set, unfitted) and shared SkyTable/build_sky implemented; 18 tests, exact required aspect weights, node halving pinned, sky matches positions()."

## Concerns
- Tables are hand-set and need user sign-off before any real-return run.
- Ketu aspects use the same halved weight as Rahu (per plan); a Rahu/Ketu pair hitting the same point counts as one full axis.
- MOON_SIGN comment/values and DRUVA/UGRA content are judgement calls, untested beyond name validity.
- build_sky is a per-day loop; cost scales linearly with days (0.07s for tests; large ranges untimed).
