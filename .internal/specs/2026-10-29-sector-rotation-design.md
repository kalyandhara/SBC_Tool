# Sector Rotation Around Planetary Events: Design

Date: 2026-10-29
Status: approved in brainstorming; awaiting written-spec review
Source requirement: "Enhanced Requirement: Sector Rotation Analysis Around Planetary Events" (pasted by user)

## 1. Purpose

For each core planetary event occurrence, measure how the NSE sector indices behaved over the following sessions, relative to NIFTY. Report which sectors lead, how consistently they lead, and whether any of this holds out of sample. The illustrative numbers in the source requirement are not results and are not to be reproduced.

## 2. Scope (phase 1)

In scope:
- Core four events, anchored to the first NIFTY session on or after the event date:
  - Mercury retrograde windows, one occurrence per window, anchored at the retrograde start station; the direct (end) station is metadata only (`sbc/stations.py`). Start and end are about 15 sessions apart, so the cluster rule would otherwise merge them
  - Solar and lunar eclipses (`sbc/transit_almanac.py`)
  - Jupiter sign ingress (`sbc/transit_almanac.py`)
  - Saturn sign ingress (`sbc/transit_almanac.py`)
- 15 NSE sector indices from the requirement (NIFTY BANK, FIN SERVICE, IT, PHARMA, AUTO, FMCG, METAL, ENERGY, REALTY, MEDIA, PSU BANK, INFRASTRUCTURE, CONSUMER DURABLES, HEALTHCARE, OIL & GAS)
- Horizons T+5, T+10, T+20 sessions from the anchor session

Out of scope (phase 1):
- Constituent stock rankings ("Top Stocks Within Top Sectors"). Deferred to phase 2, after sector-level results are graded.
- Mars/Saturn/Pluto aspects and other almanac events. Not included in the core four.
- Any live trading signal or recommendation.

## 3. Data

- Sector index daily history downloaded via yfinance (`^CNXIT`, `^CNXPHARMA`, `^CNXAUTO`, and so on) and cached in `data/market.db` using `sbc/market_store.py` (`refresh_daily`). NIFTY is already stored.
- Each sector records the first and last date it has data. Sectors with short histories are flagged in the report.
- Prices are the close series used by the existing pipeline. Splits and bonus issues are not a concern at index level.

## 4. Metrics

| Metric | Definition |
|---|---|
| Sector return | close(anchor + h) / close(anchor) - 1, for h in {5, 10, 20} |
| NIFTY return | Same window, NIFTY |
| Relative strength | Sector return minus NIFTY return |
| Rank table | Sectors ordered by sector return, per event and horizon |
| Top-5 appearance rate | Share of occurrences where the sector ranks in the top 5 of 15 |
| Consistency score | Top-5 appearance rate, with the occurrence count shown beside it |
| Beat-NIFTY probability | Share of occurrences where relative strength > 0 |
| Event effect | Mean daily excess return (sector minus NIFTY) on event-window days (+/- 10 sessions around each anchor), graded by `sbc.stats.evaluate_directional` with its circular-shift p-value. Replaces Pearson correlation (branch 4) |
| Volatility | Standard deviation of the sector's daily returns over the window |
| Win rate | Beat-NIFTY probability (same as above) |
| Sharpe ratio | Mean daily excess return / std of daily excess return, over the window, not annualised |
| Sector breadth | Phase 1: not computed and not shown on any chart. Added in phase 2 with constituent data (branch 8) |
| Sector participation | Share of the 15 sectors with a positive return over the same window |
| Rotation pattern | Mapping in section 5 |

## 5. Rotation pattern mapping (proposed, needs review)

Sector groupings used for the rotation pattern label:
- Defensive: FMCG, Pharma, Healthcare, Consumer Durables
- Growth: IT, Media, Auto
- Risk-On: Bank, Financial Services, Realty, Metal, Infrastructure, PSU Bank
- Neutral: Energy, Oil & Gas

Label rule: a rotation pattern is "Defensive" when the top-5 sectors are mostly Defensive, and so on. Ties are reported as "Mixed". The mapping is fixed in the pre-registration and is a stated classification, not a finding. The matrix is descriptive, and the top-5 sector list is shown beside each label (branch 9).

## 6. Statistical protocol

- A pre-registration doc is committed before the first run. It fixes events, horizons, sector set, the confirmatory hypothesis list, the era boundary, and the pass rule. Convention follows `docs/research/transit_events_preregistration_2026-10-11.md`.
- Confirmatory hypotheses come only from prior B-58 and sector-validation findings, never from the new sector results (branch 7).
- Era split: out-of-sample = 2021-10-01 onward; everything earlier is descriptive history. Each sector's out-of-sample signal-day count is reported.
- Grading: reuse `sbc.stats.evaluate_directional` and `evaluate_event` unchanged. Circular-shift null (`np.roll`, MIN_SHIFT 60 sessions, 1000 permutations, fixed seed). The custom random-date baseline is dropped (branch 3).
- Clustering: events within 20 sessions of each other merge into one cluster before grading. The permutation shifts whole clusters. Raw and cluster counts are both reported (branch 2).
- Multiple testing: Benjamini-Hochberg across the confirmatory tests only.
- Pass rule (confirmatory only): a sector passes only if its out-of-sample result has q < 0.05 in the pre-registered direction. Rank tables, appearance rates and beat-NIFTY probabilities have no direction and are never graded (branch 1).
- Minimum sample: `sbc.stats.MIN_SIGNAL_DAYS` (30 signal days). Below it, the result is "insufficient" and not ranked. The spec's earlier 8-occurrence figure is withdrawn (branch 3).
- Descriptive outputs (rank tables, heatmaps, rotation matrix, leadership forecast) are labelled descriptive and carry the raw and cluster counts.
- Leadership forecast confidence is fixed by the pre-registration (branch 5, revised in the plan stress-test): "High" = passes the confirmatory test out of sample; otherwise "No call". There is no "Medium" level, since any rule for it would be chosen after seeing the data. The section is labelled a historical pattern, not a trading recommendation.
- Grader inputs (plan stress-test branch 3): signal on day t = hypothesis direction on pre-registered anchor-window days, else 0. Forward return = sector h-session return minus NIFTY h-session return.
- Effective sample floor (plan stress-test branch 5): a hypothesis needs at least 8 independent out-of-sample clusters, in addition to `MIN_SIGNAL_DAYS`. Clusters are the binding count.
- The confirmatory list may be empty. A descriptive phase 1 reporting "no pre-registered edge" is a valid result (plan stress-test branch 4).

## 7. Outputs

- `scripts/sector_rotation_report.py`: runs the pipeline, writes the outputs below.
- `sbc/sector_rotation.py`: the computation module. Pure functions for returns, ranks, relative strength, correlation, grading. Imported by the script and the blueprint.
- `reports/sector_rotation_<YYYY-MM-DD>.md` and `reports/sector_rotation_<YYYY-MM-DD>.json`.
- New blueprint page (following `sectors_bp` and `research_bp`), read-only over the precomputed JSON (branch 6):
  - Sector performance heatmap (per event, colour scale from dark green to dark red, per the requirement)
  - Rotation matrix table
  - Event x sector grid with average T+5, T+10 and T+20 returns
  - Radar chart per event, five dimensions in phase 1: return, volatility, win rate, Sharpe, participation. The chart states the dimension count (branch 8)
  - Sector rotation wheel and event -> sector -> NIFTY Sankey (presentational, drawn from the JSON)
- Security (branch 6): endpoints serve precomputed JSON only and never recompute on request. Query parameters are limited to an allow-list (event type, horizon, sector code); anything else returns 400. Market data reaches SQL only through parameterised `market_store` functions. All strings are HTML-escaped by the template engine. The endpoints follow the same auth pattern as sibling blueprints, with no new public route. No new credentials are needed.
- The effect table and the leadership forecast appear in the report and on the page, always with their graded status and the disclaimer from section 6.

## 8. Error handling

- A sector with no data for an event's window is skipped for that event and the skip is counted in the report.
- Events falling on non-trading days use the next NIFTY session (no silent shift).
- If yfinance returns incomplete data, the refresh reports the gap and the analysis runs on what is stored; it does not fill gaps with zeros.

## 9. Testing

- Unit tests for return and relative-strength arithmetic on a small synthetic series with known answers.
- Test that anchor mapping matches the next-session rule (weekend and holiday events).
- Test that the circular-shift null is reproducible under a fixed seed.
- Test that sectors below `MIN_SIGNAL_DAYS` are not ranked and not graded.
- Test that clusters merge events within 20 sessions and that permutation shifts move whole clusters.
- Test that only confirmatory items can carry a pass or fail status.
- Test that the forecast confidence follows the pre-registered rule, and that out-of-range endpoint parameters return 400.

## 10. Open items

- Confirm the rotation pattern mapping in section 5 before the pre-registration is committed.
- The implementation plan (`.internal/plans/2026-10-29-sector-rotation.md`) carries the full stress-test record for the changes above.
- Write the pre-registration doc (confirmatory list, era boundary, cutoffs) before any run.
- Phase 2 (stocks and breadth) gets its own design once phase 1 is graded.

## Stress Test Results: Sector Rotation Around Planetary Events

### Resolved Decisions
- Pass rule (branch 1): only pre-registered directional hypotheses can pass; rankings are descriptive.
- Independence (branch 2): events within 20 sessions merge into clusters; permutation shifts whole clusters; raw and cluster counts reported.
- Null and minimum (branch 3): reuse `sbc.stats` circular-shift harness and 30-signal-day minimum; custom baseline and 8-occurrence minimum withdrawn.
- Correlation (branch 4): Pearson replaced with mean excess return on event-window days, graded with a p-value.
- Leadership forecast (branch 5): confidence from pre-registered out-of-sample cutoffs; "No call" default; historical-pattern label.
- Security (branch 6): read-only precomputed JSON, allow-listed parameters, parameterised queries, autoescape, existing auth pattern.
- Era and provenance (branch 7): hypotheses only from prior findings; out-of-sample from 2021-10; earlier history descriptive.
- Breadth (branch 8): five-dimension radar in phase 1; breadth in phase 2.
- Rotation labels (branch 9): mapping fixed in pre-registration; matrix descriptive; top-5 list shown beside each label.

### Changes Made
- Sections 4, 5, 6, 7, 9 and 10 of this spec updated to match the resolutions above.

### Deferred / Parking Lot
- Phase 2 constituent-stock analysis and breadth.
- Mars/Saturn/Pluto aspects and other almanac events.

### Confidence Assessment
- Overall: Medium. The statistical protocol is now aligned with the existing harness, but the sector data has not been checked yet: index history lengths are unverified, and the yfinance series may have gaps or differ from NSE official values.
- Areas of concern: the out-of-sample era (2021-10 onward) is roughly five years, so the confirmatory tests will have few independent clusters per event type. Expect many sectors to return "insufficient" or "no edge", which is a valid outcome.
