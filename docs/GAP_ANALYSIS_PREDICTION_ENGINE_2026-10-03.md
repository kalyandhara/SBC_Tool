# Gap Analysis: SBC Tool → Market Prediction Engine (2026-10-03)

Baseline: branch `fix-b15-b25` @ `60a2d04`. This is a companion to
`docs/BACKLOG_REVIEW_2026-10-01.md`. That review covers code health. This one measures
the codebase against the product goal.

## Decisions (2026-10-03)

NIFTY first · daily horizon · tiered similarity · free data only. The scheduler runs
inside `run_app.py`, and `scripts/refresh_market_data.py` also works from Windows Task Scheduler.

## Phase 0 status (branch `phase0-market-data`)

| Item | Status |
|---|---|
| `sbc/market_store.py` → `data/market.db` | ✅ NIFTY 2007-09-17→ (4,672 sessions), SENSEX 1997-07-01→ (7,207), India VIX 2008-03-03→ (4,553). No invalid bars; the large daily moves are real events (2008, 2009, 2020) |
| FII/DII cash flows | 🟡 NSE's free endpoint returns the **latest session only**. The history builds up daily from 2026-10-01. A free archive for backfill is still open |
| Breadth (A/D), PCR | ⬜ not started; no free history source found yet |
| EOD refresh | ✅ `run_app.py` loop, after 16:30 IST on trading days, retries until that day's FII/DII figures land. `scripts/refresh_market_data.py [--full]` for manual or Task Scheduler runs |
| Freshness | ✅ `GET /api/engine/market/freshness` (holiday-aware). UI badge not added yet |
| Legacy CSV cache never backfilled its head | ✅ fixed in `sbc/market_data.py`; `data/nifty_ohlc.csv` now starts 2007 |
| B-10 placeholder research routes | ✅ the 10 routes, `research/` and `research_bp` are removed; the real dash-named routes stay |
| NIFTY before 2007 | ⬜ yfinance starts 2007-09-17. niftyindices.com archives would add 1995–2007 (optional) |

## Phase 1 status (branch `phase1-fingerprint`)

| Item | Status |
|---|---|
| `sbc/fingerprint.py` | ✅ one call → every factor at 09:15 IST: 12 bodies (9 grahas + Uranus/Neptune/Pluto) with sign, nakshatra, pada, speed, retro, stationary, combust, dignity; angular aspects with orb and applying flag; Vedic drishti; panchang (tithi, yoga, karana, Vishti, weekday lord, hora lord); KP asc/Moon star and sub lords; SBC NIFTY vedha net (classical, all-three); Bradley; eclipse distance |
| Tiers | ✅ slow / medium / fast on every planet, aspect (tier of the faster planet) and feature |
| `feature_vector()` | ✅ 460 named, tiered numbers (143 slow / 195 medium / 122 fast); fixed order across dates |
| `data/fingerprints.db` | ✅ 16,801 days, 1990-01-01 → 2035-12-31, built in 13 s; rows versioned by `engine_version.module_version("sbc.fingerprint")` |
| Validation | ✅ 2020-12-21 Jupiter–Saturn conjunction (orb 0.07°); retrograde shares Mercury 19.2%, Venus 7.3%, Mars 9.7%, Jupiter 30.5%, Saturn 36.2%; Vishti 13.3% (8 of 60 karanas); 2009-07-22 solar eclipse; Vishti matches `sbc.bhadra` |
| API | ✅ `GET /api/engine/fingerprint?date=&vector=1`, `GET /api/engine/fingerprint/status` |
| Not yet | ⬜ station dates as events, graha yuddha, declination (G8, after the stats harness) |

## Phase 2 status (branch `phase2-stats`)

| Item | Status |
|---|---|
| `sbc/stats.py` | ✅ forward returns (prior-close entry), directional and volatility tests against the unconditional market, circular-shift permutation p-values, Benjamini–Hochberg, per-period breakdown, minimum-sample guard |
| Calibration | ✅ on synthetic data it finds a planted 20 bps/day effect and passes noise. With persistent regime signals it fires on 3.5–5% of nulls (an iid shuffle fires on 37%) |
| `sbc/rule_signals.py` | ✅ 18 existing rules as one daily NIFTY signal each, taken as stated (no fitting), plus 2 placebo controls |
| `scripts/validate_rules.py` | ✅ → `docs/research/rule_validation_2026-10-03.md` / `.json` (8 s, 1,000 permutations) |

### Result: none of the existing rules has a measurable edge on NIFTY (2007-09 → 2026-10)

- **0 of 60** rule × horizon tests pass q < 0.05. Both placebos come out clean (p 0.6–0.9).
- Closest calls are all **wrong-way**:
  - `bradley_sign`: the market did *worse* than drift when the barometer was positive (1d p 0.001, q 0.06; same sign in both eras, but right in only 7 of 20 years).
  - `reversal_calendar_bias` at 20d: q 0.14; it is bullish on 98% of days, so it is mostly a constant call.
  - `moon_gandanta` and `shukla_paksha` are not significant after correction.
- The SBC vedha net (all-three school) is bearish on 83% of days and has no edge at any horizon.
  The 2026-09-14 "actionable verdict" (20–40% exposure from net −6) had no measured basis.
- **Don't flip the wrong-way rules into new rules.** Choosing a direction after seeing the
  result is data snooping. Pre-register "contrarian Bradley" as a hypothesis and let the
  live ledger (G6) judge it.
- **Consequence for the plan:** Phase 4 must not weight these rules by assumption. The
  analog engine (Phase 3) is the remaining candidate, and it gets graded by this same
  harness before anything is labelled actionable.

### Defects found on the way
- **B-37** `school="kp"` was advertised (README "three vedha schools") but `sbc.chakra.vedha_cells`
  has no KP branch. It silently returned classical results. Removed from the fingerprint
  and the README; the UI never offered it.
- **B-38** `sbc.backtest._nakshatra_bullish` lists `"Uttara Phalguni"`, but the codebase spells
  it `"U.Phalguni"`, so that star never fires (left unchanged; the rule isn't in the tested set).

## Phase 3 status (branch `phase3-analogs`)

| Item | Status |
|---|---|
| `sbc/analogs.py` | ✅ tiered similarity (per planet: sign, nakshatra, longitude within 30°, direction; aspect sets by Jaccard; fast tier adds tithi, yoga, weekday/hora lord, KP sub lords), blended overall score, top-K or ≥ threshold, analogs ≥ 5 sessions apart, **no lookahead** (only sessions whose outcome was complete by the previous close) |
| Walk-forward (`sbc/analog_validation.py`, `scripts/validate_analogs.py`) | ✅ every session 2012-01 → 2026-10 (3,622) forecast from its top-30 analogs, graded by the Phase 2 harness → `docs/research/analog_validation_2026-10-03.md` |
| API | ✅ `GET /api/engine/analogs?date=&horizon=1|5|20&variant=overall|slow|medium|fast&k=&min_similarity=`; each response carries the walk-forward track record and `status: experimental` |
| Analog Lab tab | ✅ Advanced analysis → Analog Lab: outcome stats against all sessions, the setting's track record, and an analogs table (age, tier similarities, shared signs, +1/+5/+20 outcomes). Checked at desktop and phone width |

### Result: no analog variant has an edge, and "90% similar" days don't exist

- **Whole-sky similarity tops out at 60%** over 2007–2026 (median best match 45%). Nothing
  comes near 90%, because 12 bodies don't repeat their configuration within decades. The
  engine therefore reports the actual best-match similarity and uses the top 30. The 90%
  threshold remains available and falls back to top-K.
- **0 of 15** variant × horizon tests show an edge. The random-analog control is clean.
- The near-misses (whole sky and slow tier at 5/20d, q 0.16) are wrong-way and turn out
  to be a **recency confound**: their analogs are a median 0.4–1.0 years old, because the slow
  sky barely changes within a year. "Follow the analogs" then means "follow the trailing
  trend", which mean-reverted in 2012–2020. That isn't an astrological effect.
- The cross-year variants (medium and fast tiers, analogs a median 5–6 years old) are the
  real "same sky, same market" test. They show nothing (hit rate 49–50% vs 50% by chance).

### What this means for Phases 4–5
Neither the rules nor the analogs earn weight in a forecast on this evidence. Options to
decide on before Phase 4:
1. Build the forecast/ledger anyway as an **honest research instrument**: it shows the evidence
   and the track record, and keeps scoring live forecasts in case something emerges out of sample.
2. Add the market-side inputs (VIX regime, FII/DII flows, trend) as **controls**: test whether
   any astro factor adds information *beyond* them, the only way an astro edge could hide here.
3. Pre-register specific hypotheses (e.g. contrarian Bradley) and let the live ledger judge.

## Phase 4 status (branch `phase4-forecast`) — options 1 + 2

| Item | Status |
|---|---|
| `sbc/market_features.py` | ✅ 12 controls known at the previous close: trailing 5/20/60 returns, 20-day realized vol, 200-day MA gap, log VIX and its 5-day change, weekday, turn-of-month. FII/DII is excluded until it has history |
| `sbc/incremental.py` + `scripts/validate_incremental.py` | ✅ partial regression of each astro signal on forward returns *after* the controls, with circular-shift p-values (2.5% false positives on synthetic noise); yearly walk-forward OLS of the controls alone |
| `sbc/forecast.py` | ✅ one contract per (session, horizon): probability (base rate unless a component is validated), VIX-implied 68/95% bands and historical quantiles, every rule/analog lean with both verdicts, key sky facts, live track record, model version |
| `sbc/daily_ledger.py` | ✅ freezes 1/5/20-session forecasts before 09:15 IST (live / late / backfill), scores them from `market.db` (Brier against the base rate, plus each component's live hit rate); runs in the `run_app.py` loop. First live forecast frozen for 2026-10-05 |
| API | ✅ `GET /api/engine/forecast?date=&horizon=`, `GET /api/engine/forecast/ledger?horizon=&kind=` |

### Result: nothing astro adds information beyond market conditions, and the controls don't predict either

- **0 of 75** signal × horizon tests add information after the controls
  (`docs/research/incremental_validation_2026-10-03.md`). Bradley's wrong-way effect shrinks
  once trend is controlled for, so it was partly a trend echo.
- The controls alone have **negative out-of-sample R²** at 1, 5 and 20 sessions: simple
  market state doesn't forecast NIFTY's direction better than its drift either. Daily NIFTY
  direction is close to unpredictable from public, slow-moving information. That is the
  bar any astro factor has to clear.
- So the forecast's probability is the **base rate** (5 Oct 2026: 52.9% / 55.9% / 59.9% up
  over 1 / 5 / 20 sessions), and its useful content is the **range** (VIX-implied) and the
  **evidence** behind each component. The ledger now builds the live record that a
  pre-registered hypothesis would need.

## Phase 5 status (branch `phase5-calendar`)

| Item | Status |
|---|---|
| `sbc/forward_calendar.py` | ✅ next 1–8 weeks: next-session forecast (1/5/20), VIX-implied range at each week's end, per-day sky events (ingresses, slow-planet nakshatra changes, stations, exact aspects < 1°, eclipses, new/full Moon), rule lean counts, analog-set leans, volatility flags. Markdown, HTML and JSON |
| Weekly schedule | ✅ the `run_app.py` loop writes `reports/calendar/forward_calendar_<Saturday>.{md,html,json}` from Saturday 08:00 IST, once a week, after topping up `fingerprints.db` (purge stale + build missing). It catches up if the server was down. `scripts/forward_calendar.py --weekly` does the same from Task Scheduler |
| Evidence card (G9) | ✅ top of Executive Overview (`/api/engine/forecast/card`). It shows 1/5/20-session chance of a rise against the base rate, 68/95% ranges, live record (Brier vs base rate), sky facts, and every component's lean with its historical and beyond-market verdicts. It uses the ledger's frozen copy when one exists. The old vedha outlook is relabelled "unvalidated", and so is the "Actionable Investment Directive" |
| Forward Calendar tab | ✅ Advanced analysis: weekly range + day-by-day table, "open as page", and links to the stored weekly copies |
| API | ✅ `GET /api/engine/forecast/card`, `GET /api/engine/calendar?start=&weeks=&format=json\|html\|md`, `GET /api/engine/calendar/reports[/<file>]` (only files the store lists are served) |
| Not done | Monthly automatic re-validation (the `scripts/validate_*.py` runs take minutes; still manual). The async calendar job (G7) isn't needed: a 4-week build takes ~2 s. Pushing reports out (email) was left out, because it needs your consent per send |

## Phase 6 status (branch `phase6-factors`)

| Item | Status |
|---|---|
| G8 factors (`sbc/factors.py`) | ✅ 12 candidates, each with its direction written down before the first test: stations, graha yuddha (< 1°), Moon / planet out-of-bounds declination, ingress within ±1 day, eclipse within 1 day (all "bigger moves"), plus Mercury combust, Jupiter combust, Venus retrograde, 3+ retrogrades, Moon within 12° of a node (bearish) and Jupiter's dignity (as signed). Declination is computed in the module, so the fingerprint store needs no rebuild |
| Factor test (`sbc/factor_validation.py`, `scripts/validate_factors.py`) | ✅ harness + incremental test in one report, as its own BH family. Event factors are tested on \|return\| after the controls, so they must beat VIX and recent volatility |
| Forecast wiring | ✅ every factor is a forecast component with both verdicts. It moves the probability only if it shows an "edge" and "adds information". The daily ledger now builds each factor's live record |
| Sector test (`sbc/sector_validation.py`, `scripts/validate_sectors.py`) | ✅ 67 findings from `sbc/sector_signals.py` (copper, coffee/tea, fertilizer, food, FMCG, agri-chem), graded on the years **before** 2021-08, which the fit never saw. 23 series in `market.db` via `refresh_market_data.py --research` (US futures and NSE stocks back to 2000–2010). A sector disclaimer in the scanner now states the result |
| Sentiment / news | ⏸ not built. Free sources have no history: NSE serves FII/DII for the latest day only (accumulating in `market.db` since 2026-10-01), PCR has no free archive, and news sentiment needs a paid feed (decision 4: free only). FII/DII can enter the controls and be tested once it has ~2 years |

### Result: nothing new holds up either

- **Factors: 0 of 36** factor × horizon tests show an edge, and none adds information beyond the
  market (`docs/research/factor_validation_2026-10-03.md`). Near-misses are
  uncorrected p ≈ 0.025–0.05 out of 72 tests (36 per table), which is chance. Moon–node contact went the
  traditional way, Jupiter's dignity went the wrong way (like Bradley), and q ≥ 0.44 everywhere.
- **Sectors: 0 of 67** findings hold out of sample (`docs/research/sector_validation_2026-10-03.md`).
  The test is measuring the right thing: in the fit window it reproduces the original signal
  counts and win rates exactly (e.g. Jupiter → Sun on Hindustan Copper: 37 days, 65%; Mars →
  Saturn on copper: 69 days, 70% / 100%). Before 2021-08 the same pairs average roughly zero.
  Most of the hand-picked pairs were selection effects of a 5-year window.
- Across the project that's **0 of 253** tests: Phase 2 rules 60, analogs 15, incremental 75,
  factors 36, sectors 67.

## B-39 swing-window model (branch `b39-swing-windows`)

Heliocentric Earth–planet aspects (8 aspect types, ±2°) as ENTRY, and Gann + Fibonacci +
indicator confluence as EXIT. The full spec and results are in the backlog (B-39) and in
`docs/research/swing_validation_*.md`.
- Entry timing: 0 of 102 tests pass.
- Full model: no better than random entries (p = 0.28 strict, 0.62 for 2-of-3), and
  simple holds beat the confluence exit on the same entries.
- Running total: **0 of 355** astro tests.

## Target capability (the goal, restated as a pipeline)

```
 1. Ephemeris scan      every planet, sign, nakshatra, aspect, transit, combination (SBC + KP)
 2. Market + mood data  prices, cash-flow proxies (FII/DII, volume, breadth), sentiment (VIX, PCR, news)
 3. Astro fingerprint   one comparable feature vector per date/time
 4. Analog search       find past dates ≥90% similar to the target date
 5. Statistics          what the market did after those analogs, compared with a baseline
 6. Hypothesis          a forward forecast (direction, range, confidence) for the target date/window
 7. Delivery            on demand (UI/API) and on a schedule (calendar reports)
 8. Honesty loop        freeze forecasts → score → publish the hit rate next to every forecast
```

## Scorecard

| # | Stage | Status | What exists | Main gap |
|---|---|---|---|---|
| 1 | Ephemeris scan | 🟡 Strong but fragmented | Swiss Ephemeris positions, 81-cell SBC vedha (3 schools), KP subs/cusps/horas, nakshatra/tithi/Bhadra, ingresses, aspects, Bradley, Gann, about 15 sector rule sets | About 20 modules, each with its own output shape. No single "everything on date X" object. Rules are hard-coded heuristics |
| 2 | Market + mood data | 🔴 Thin | NIFTY daily (only **2024-08-26 → 2026-10-01**, 522 rows), 23 sector/commodity CSVs (end 2026-08-25), yfinance 5-min bars (60 days) | No long history, no auto-refresh, **no cash-flow or sentiment data**. "Sentiment" today is just Moon-sign rules |
| 3 | Astro fingerprint | 🔴 Missing | `series_cache` stores SBC verdicts, not features | No feature vector and no historical feature store |
| 4 | Analog search | 🔴 Missing | none (`grep` finds no similarity code) | The core differentiator does not exist yet |
| 5 | Statistics | 🔴 Mostly placeholder | Forecast ledger with a majority-class baseline (good). `research/astro_research.py`: all 10 functions return `"placeholder"` | No forward-return stats, significance tests or walk-forward |
| 6 | Hypothesis | 🟡 Rule-based only | `build_response` verdict, confluence blend, futurecasts, expiry range, KP intraday path | The parts aren't combined into one calibrated forecast. `unified_daily_forecast_contract` is a placeholder |
| 7 | Delivery | 🟡 On-demand only | Flask UI with about 10 tabs, KP DOCX, weekly report script | No scheduler beyond the ledger thread in `run_app.py`. No calendar/report generation job, and nothing is pushed out (email/file) |
| 8 | Honesty loop | 🟡 Started | Intraday ledger (freeze before 09:15, score after close) | Intraday only. Daily/weekly forecasts aren't ledgered. Results aren't shown beside forecasts |

## Evidence that decides the plan

The tool can't yet produce actionable conclusions, because the repo's own validation
finds **no edge so far**:

- Intraday forecast (real ephemeris KP data, 41 days): 50.8% hit rate against a 55.4%
  constant baseline. Day direction was 28/41, against a 60.8% baseline (B-21, B-33).
- Crash/turn backtest (`docs/backtest_summary.md`): 3 of 7 events, 42.9%.
- The 2026-09-14 "actionable verdict" sets 20–40% exposure from a vedha net of −6.0,
  without any measured hit rate behind that number.

That makes **stage 5 + stage 8 the critical path, not more rules**. Each new factor adds
a way to overfit ~500 bars of data. Build the measuring stick first, then let each
factor earn its weight.

## Gaps in detail, with the changes to make

### G1 · Market data depth and freshness (stage 2) — P0
- **Gap:** analog search and statistics need decades, not 2 years. Jupiter (12 y) and
  Saturn (29.5 y) configurations never repeat inside the current window.
  `scripts/fetch_history.py` asks for data from 2000, but `data/nifty_ohlc.csv` starts in
  2024-08. Sector CSVs are 5 weeks stale (B-05).
- **Change:**
  - Backfill NIFTY 50 / SENSEX daily from at least 1995 (NSE index archives; yfinance
    `^NSEI` from 2007, `^BSESN` from 1997). Store in SQLite `market.db` (`ohlc` table
    keyed by symbol+date), not one CSV per series.
  - Add India VIX (2008+), FII/DII net cash flows (NSE daily), advance/decline breadth,
    and NIFTY PCR. These are the "cash flow" and "human sentiment" inputs.
  - Optional later: a news/headline sentiment score (needs an external source; decide on cost).
  - EOD refresh job (see G7) with a freshness check that the UI shows as "data as of".

### G2 · Unified astro fingerprint (stages 1+3) — P0
- **Gap:** every module computes its own slice. Nothing can answer "how alike are dates A and B?"
- **Change:** new `sbc/fingerprint.py` → `fingerprint(date, time="09:15") -> dict` plus a
  flat numeric vector, built only from existing calculators:
  - Positions: each graha's longitude as (sin, cos), sign, nakshatra, pada, speed,
    retrograde/station flag, combustion, dignity.
  - Relations: pairwise aspect/conjunction flags with orb weighting, applying or
    separating (`market_events.planetary_aspect_events`), Rahu–Ketu axis contacts.
  - Lunar: tithi, paksha, Moon nakshatra, Bhadra, eclipse proximity.
  - SBC: vedha net per school, Janma/Karma hits. KP: day-lord/star-lord/sub-lord,
    house-set strength.
  - Derived: Bradley value, Gann/astro cycle phase.
  - Store a precomputed daily table for 1990–2035 in `data/fingerprints.db`, versioned
    with `sbc.engine_version` like the series cache (B-20).
- **Done when:** one call returns every factor for a date, and the 1990–2035 table builds
  in under 10 minutes.

### G3 · Analog ("90% similar date") engine (stage 4) — P0, new feature
- **Change:** new `sbc/analogs.py`:
  - `similarity(fp_a, fp_b, weights) -> 0..1`. Use circular distance for longitudes,
    exact match for categorical fields (sign, nakshatra, tithi), and Jaccard for aspect sets.
    Weight slow planets more for long horizons and the Moon/horas more for intraday.
  - `find_analogs(target_date, min_similarity=0.90, lookback="1995-", exclude_days=30, k=50)`.
  - For each analog, attach forward returns (+1, +5, +20, +60 trading days), max
    drawdown/run-up, VIX change, and FII flow over the same window.
- **Design decision needed:** "near-term history" and "90% similar" pull against each
  other. Recent dates share the slow planets but rarely the fast ones, and exact 90%
  matches across all factors will be rare. Two options: (a) tiered similarity (slow
  layer / medium / fast) and report each, or (b) a fixed similarity threshold with an
  automatic fallback to top-K. Recommend (a).

### G4 · Statistics and validation layer (stage 5) — P0
- **Gap:** the ten `research/astro_research.py` endpoints are placeholders (B-10).
  Nothing compares a signal to the unconditional market.
- **Change:** new `sbc/stats.py`, reused by analogs, rules and the ledger:
  - Forward-return distribution (mean, median, hit rate, quartiles) **against the
    unconditional distribution over the same years**.
  - Permutation or bootstrap p-value, an effect-size and minimum-sample guard
    (for example, hide the verdict if n < 20).
  - Multiple-testing control (Benjamini–Hochberg) whenever many factors or rules are scanned.
  - Walk-forward: fit weights on years ≤ T and test on T+1. Replace the placeholder
    `walk_forward_validation`.
  - Run every existing rule set (crash triggers, bullish/bearish futurecast,
    sector vedha, KP day bias) through this harness once, and keep only rules that beat
    the baseline out of sample.

### G5 · Unified forecast contract (stage 6) — P1
- **Change:** `sbc/forecast.py` → `forecast(date_or_range, horizon)` returns
  `{bias, probability_up, expected_range, confidence, analog_summary, top_factors,
  rule_signals, data_as_of, model_version, track_record}`.
  - Probabilities are calibrated on walk-forward results (isotonic/Platt). They are
    never raw vedha nets.
  - `expected_range` reuses `expiry_range.py` / VIX-implied moves.
  - `track_record` = live ledger hit rate and baseline for this horizon.
  - The existing verdict/confluence outputs become inputs (`rule_signals`).

### G6 · Ledger for every horizon (stage 8) — P1
- **Change:** extend `sbc/forecast_ledger.py` from intraday to daily, weekly and monthly
  horizons and to the analog forecast. Show the rolling hit rate against the baseline on
  every forecast card. Label anything that hasn't beaten the baseline "Experimental"
  (B-21).

### G7 · Scheduler and calendar generation (stage 7) — P1
- **Gap:** the only background job is the ledger thread in `run_app.py`.
- **Change:** one job runner (APScheduler inside `run_app.py`, or Windows Task Scheduler
  calling `scripts/*`), with these jobs:
  - EOD (16:30 IST): refresh market + flow data, score the ledger.
  - Pre-open (08:45 IST): freeze today's forecasts.
  - Weekly (Sat): generate the forward calendar (next 4–8 weeks: forecast, analogs,
    key transits/ingresses/eclipses) → DOCX/HTML in `reports/`.
  - Monthly: rebuild fingerprints if `engine_version` changed, and re-run walk-forward.
  - On demand: `POST /api/forecast/calendar?start=&end=` as an async job with polling
    (this also fixes B-13 timeouts).

### G8 · Factor coverage still to add (stage 1) — P2, only after G4 exists
- Station (retrograde/direct) dates, combustion windows, eclipses as events, graha
  yuddha, declination/parallels, outer planets kept consistent across modules.
- KP: confirm the RISE/FALL house convention (B-33 note), and a market-chart (NSE
  anchor) dasha.
- Add each factor only after G4 can measure it.

### G9 · Actionable output (product) — P1
- Today's "actionable verdict" turns a vedha score straight into exposure %. Change it
  to an **evidence card**: analog stats, rule signals with their measured hit rates,
  the range, data freshness and the track record. Map it to the user's own rulebook
  (`docs/risk_rulebook.md`). The engine reports evidence, and the user decides sizing.
- Every output carries "research, not investment advice" (the astro_cycles module already does).

### G10 · Platform debt that blocks the above (from the 2026-10-01 review)
B-05 stale data · B-07 cold start · B-10 placeholder research routes · B-13 fetch
timeouts / async jobs · B-16/B-17 monolith `app.py` and inline JS (the new Analog Lab
tab should live in `static/js/`) · B-36 mypy on new modules from day one.

## Phased plan

| Phase | Scope | Exit criterion |
|---|---|---|
| **0 Foundation** | G1 data backfill + `market.db`, EOD refresh job, B-05/B-10 | NIFTY/SENSEX/VIX/FII from ≥2008 in the DB; refreshed daily |
| **1 Fingerprint** | G2 | `fingerprints.db` 1990–2035; unit tests against known ephemeris dates |
| **2 Stats harness** | G4; run existing rules through it | A report showing which current rules beat the baseline out of sample |
| **3 Analogs** | G3 + Analog Lab UI tab | For any date: top analogs, forward-return stats against the baseline, p-value |
| **4 Forecast + ledger** | G5, G6 | One forecast contract; daily/weekly ledger running live |
| **5 Schedule + calendar** | G7, G9 | Weekly calendar report generated automatically; evidence cards in the UI |
| **6 Extend** | G8, sentiment/news, sectors | Each new factor admitted only via the G4 harness |

## Open decisions for you

1. **Universe:** NIFTY/SENSEX only first, or the sector baskets too?
2. **Primary horizon:** intraday, daily, weekly or monthly? This sets the similarity
   weights and the ledger.
3. **"Near-term" analog lookback:** tiered similarity (recommended) or a strict 90% threshold?
4. **Data sources:** stay on free (yfinance + NSE archives), or pay for a feed
   (FII/DII history, news sentiment)?
5. **Scheduler:** in-process APScheduler or Windows Task Scheduler?
