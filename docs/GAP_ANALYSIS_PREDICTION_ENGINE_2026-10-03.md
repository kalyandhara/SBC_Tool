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
