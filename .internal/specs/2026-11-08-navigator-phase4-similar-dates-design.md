# AstroTrade Navigator Phase 4: Similar Past Dates

Date: 2026-11-08. Brainstorming bead: SBC_Tool-kt7. Builds on Phase 1 (`2026-11-06-astrotrade-navigator-phase1-design.md`) on branch `feature/astrotrade-navigator`. Status: design approved by the user.

## Goal

For each upcoming high-scoring date of a profile, show at least 5 past dates with the most similar astro signature and what the market did then. This is the user's key enhancement from the original brief. It is descriptive research, not a tested signal.

## Upcoming dates

- Score the next 30 Nifty trading sessions after the last market date, for the selected profile, with the Phase 1 scoring. Use the repo's market calendar and holidays and say which module is used.
- **High-scoring** means an integer score of 61 or more.
- **No high-scoring date:** if none of the 30 reaches 61, take the 5 highest-scoring sessions instead. Ties go to the earlier date. The response and page say "no high-scoring date in this window".
- Forward scores use neutral Vol, as in Phase 1, and say so.

## Similarity (hand-set, version `nav-analog-1`, never fitted)

All parts are on a 0 to 1 scale.

**Natal similarity:**
- **Contacts, weight 0.8:** weighted Jaccard of the two days' active transit contacts to the profile's natal points. A contact is a key (planet, natal point, aspect) using the Phase 1 aspect set, orb and bodies. Its weight is the Phase 1 orb factor: 1 at exact, 0 at the orb edge. Weighted Jaccard is the sum of minimums over the sum of maximums. If both days have no contacts, the value is 1.
- **Dasha, weight 0.2:** 0.6 if the Antardasha lords match, plus 0.4 if the Pratyantar lords match. The Mahadasha is left out, because it lasts years and would make analogs cluster by era.
- **Moon:** no separate Moon component. The sky part already carries the Moon, so a natal Moon term would count it twice.

**Sky similarity:** `sbc.analogs.similarity(...)["overall"]`, unchanged. Fingerprints for future dates come from `sbc.fingerprint`; historical ones come from the existing history.

**Blended:** 0.5 × natal + 0.5 × sky.

Every weight lives in one module with `ANALOG_VERSION = "nav-analog-1"`, pinned by a test. Any change bumps the version and is disclosed.

## Eligible past dates

- **Pool:** Nifty sessions. A session qualifies only if its full outcome window had closed by the last close before the target. Concretely, its open 5 sessions later must be on or before the last session before the target. Reuse the rule in `sbc.analogs.History.usable_before`, adapted so the definitions match exactly.
- **Exclusions:** sessions within 30 calendar days of the target are excluded.
- **Spacing:** analogs are thinned to at least 5 sessions apart, keeping the most similar, as `sbc.analogs` does.
- **Count:** the top 10 by blended similarity. If fewer than 5 remain, the target says "too few analogs" and shows none.
- **Era check:** each target reports the median age in years of its analogs, so clustering by era is visible.

## Per-analog outcomes

These use the analog's own date. All returns are raw: no costs, because nothing is traded.

| Field | Definition |
|---|---|
| Nifty day return | Nifty open-to-close on the analog date |
| Bank Nifty day return | CNXBANK open-to-close on the analog date |
| VIX change | India VIX close on the analog date against the previous session's close, in percent |
| Top 5 sectors | The 11 CNX sector indices (excluding CNXBANK) ranked by open-to-close return that day. Sectors with no bar that day are listed as missing, and the top 5 is taken from those present. |
| Next-5 return | Nifty open of the analog date to the Nifty open 5 sessions later. This matches Phase 1's `oo_5` and is labelled "open to open, 5 sessions, as in the backtest". |
| Max drawdown (next 5) | Worst fall within the same window: from the analog-day open through each session's low or close in the window, up to the exit open |

Missing data is shown as "n/a" and is never filled.

## Summary per upcoming date

- **Analog figures:** number of analogs; win ratio (share with a positive next-5 return); average and median next-5 return; average max drawdown.
- **Baseline:** the same win ratio and average for the whole eligible pool, shown next to them.
- **Random comparison:** beside the win ratio, show the share of 1,000 random draws from the eligible pool, of the same size and spacing on a fixed seed, whose win ratio was at least as high. It is plain text and makes no significance claim.
- **Label:** always "anecdotal: N analogs, not a tested signal". No p-values and no verdict.

## API

- **Route:** `GET /api/navigator/analogs?profile_id=N&days=30`. `days` is an integer from 5 to 60, otherwise 400.
- **Guard:** the existing navigator guard. Store failures return 503 with the fixed message, and an unknown profile returns 404, as elsewhere.
- **Response:**
    - `version`, `data_asof`, `window`, `mode` (`high_scoring` or `top_scores`).
    - `targets`: a list of {`date`, `score`, `band`, `analogs` (list), `summary`, `note`}.
    - `notes`: the disclosures listed above.
- **Redaction:** no `chart_hash` and no birth data.
- **Cost control:** one analog computation at a time per process, using a non-blocking lock. A second request gets 429 with a fixed message. Results are cached in memory by (profile, data date, ANALOG_VERSION, engine version, days), keeping the last 8. The response never includes natal longitudes.
- **Performance:** results are not stored in Postgres in this phase; they are computed on demand. Target under 30 seconds for 30 days with up to 30 targets on this machine. History arrays are cached in memory per data date and version. If the target cannot be met, report the measured time in the response notes rather than cutting content.

## Page

- **Section:** a "Similar past dates" section in the Navigator tab, below the score.
- **Layout:** one row per upcoming date, showing date, score and band, which expands to the analog table and summary.
- **Labels:** the anecdotal label and data caveats are always visible.
- **Rendering:** `textContent` only, no new CDN, no sideways page scroll at 375px, and tables scroll inside their wrapper.
- **States:** loading, 503 and errors show readable messages.

## Data caveats (shown in notes)

- Bank Nifty and sector data in `data/market.db` end 2026-10-29, and most sectors start in 2011. Analogs before those dates show "n/a" for those fields.
- India VIX starts 2008-03.

## Testing

- **Timing leak:** no analog's outcome window ends after the last close before the target. A test moves the cutoff and must fail if the rule is broken.
- **Weights:** pinned by snapshot. Each natal component is checked on hand-built cases with exact values: weighted Jaccard, the both-empty case, and the dasha level sums.
- **Selection:** spacing and exclusion rules; the 61 threshold and the top-5 fallback, including ties.
- **Outcomes:** exact values on fixture prices, plus the missing-sector and missing-VIX cases.
- **Determinism:** identical output on repeat.
- **API:** guard, 400, 404 and 503 behaviour; no `chart_hash`.
- **Real page:** verified in the browser before the work is called done.

## Out of scope (follow-up bead)

A walk-forward test of whether the analog average ever predicted outcomes. Until it exists, the anecdotal label stays.

## Stress Test Results: Phase 4

### Resolved Decisions
- **Dasha:** weight cut to 0.2, using Antardasha and Pratyantar only (0.6/0.4), with no Mahadasha. Each target reports the analogs' median age.
- **Moon:** no natal Moon component (it was double counted). Natal = 0.8 contacts + 0.2 dasha.
- **Random comparison:** each win ratio shows a random-draw comparison from the pool.
- **Next-5 return:** open to open, as in Phase 1's `oo_5`. Drawdown and eligibility use the same window.
- **Cost and privacy:** single-flight lock with 429, a cache of the last 8 results, timing in the notes, and no natal longitudes in responses.

### Changes Made
All five are applied above.

### Confidence Assessment
- Overall: Medium-High.
- Concern: analogs stay anecdotal until a walk-forward test of them exists.
