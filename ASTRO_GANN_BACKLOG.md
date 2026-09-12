Goal (one sentence)  
Build a production‑grade Python pipeline that generates forward Navamsa (D‑9) time series at configurable granularity (hour/minute during market hours), derives KP/SBC rule‑based intraday triggers (Tier‑1/Tier‑2/Pure‑Set/Regime‑Shift/Reversal), exports CSV/XLSX outputs, and includes validation/backtest against historical NIFTY and BANKNIFTY intraday data.

Deliverables (explicit, testable)
Codebase (Python) with modular components: ephemeris, divisional mapping, SBC/KP primitives, rule engine, temporal tiler, exporter, and tests.

PoC outputs for one sample month: navamsa_monthly.csv and intraday_triggers.csv (minute or 5‑minute resolution as configured).

Validation report comparing generated triggers to historical intraday price moves (metrics: precision, recall, avg move in first 5 candles, false positive rate for Rahu windows).

Documentation: README, rule specification (canonicalized from your report), deployment/run instructions, and acceptance criteria.

Packaging & scheduler: CLI to run generation for arbitrary date ranges and a scheduled job example (cron / Prefect / Airflow).

Optional: lightweight web UI or notebook to preview outputs.

Inputs you must provide or confirm before work starts
Ayanamsha to use (e.g., KP Ayanamsha, Lahiri) — confirm exact string.

Ephemeris preference: skyfield (DE440) or pyswisseph/swisseph — confirm.

Canonical rule spec: a single document enumerating every rule referenced in the attached report (A‑11, A‑12, A‑13, A‑14, v12.2, v14, DL flags, pure‑set alarm definitions, hora weighting, vargottama rules, nadi multipliers, confirmation thresholds such as 15 NIFTY points). If not available, allocate time to extract and formalize rules from the provided report.

Historical intraday price data (NIFTY and BANKNIFTY) at 1‑minute or 5‑minute resolution for at least 12 months; provide access method (S3, local CSV, database).

Reference Navamsa examples (a small set of validated charts) to unit‑test divisional mapping.

Compute environment: target OS, Python version, CPU/RAM constraints, and whether GPU is available (not required).

Acceptance thresholds: e.g., reversal candidate precision ≥ X%, average first‑5‑candle move ≥ Y points, maximum false positive rate Z% for Tier‑1 signals.

Security / compliance constraints (if pipeline will access trading accounts or PII).

Technical requirements and architecture (must‑have)
Language & packaging: Python 3.10+, poetry or pipenv.

Ephemeris: skyfield with DE440 (preferred) or pyswisseph if KP compatibility required. Lock ephemeris version and record DE file used.

Core libraries: pandas, numpy, pytz, dateutil, openpyxl/xlsxwriter, pytest. Optional: numba for speed.

Rule engine: deterministic, unit‑tested functions for each rule; rules must be parameterized (weights, thresholds) via a YAML/JSON config.

Temporal tiler: vectorized batch ephemeris calls for many timestamps; detect and record exact transition timestamps for sub‑lord changes.

Divisional mapping: accurate Navamsa mapping function with unit tests against reference charts.

Hora & aspect geometry: compute planetary aspects to hora lords and apply weighting rules.

Export format: CSV and Excel with metadata header (ayanamsha, ephemeris version, generation timestamp).

Validation harness: script to compute first‑5‑candle move and produce summary metrics and confusion matrix.

Logging & reproducibility: deterministic outputs given same inputs; log ephemeris file hash, code commit hash, and config used.

Performance: minute‑level generation for one month should complete within a reasonable time (target: < 2 hours on a 4‑core machine). If not, provide optimization plan.

Tests: unit tests for mapping, sub‑lord detection, and rule outputs; integration test that produces sample CSVs.

Rule codification (how to convert your report into code)
Canonicalize each rule: For every named rule (A‑11, A‑12, A‑13, A‑14, v12.2, v14, N‑3, N‑5, etc.) produce:

Rule ID (string), description, inputs, outputs, parameters, default values, and unit tests.

Thresholds: encode the 15‑point confirmation rule, Rahu‑window half‑size rule, hora weighting (0.3 slot weight), and Nadi multipliers (e.g., Neer 1.05×).

Edge cases: retrograde planets, exact boundary conditions when a planet is exactly on a nakshatra/pada/sub boundary — define tie‑break rules.

Validation & backtest plan (explicit)
For each generated trigger:

Extract the next five 1‑minute or 5‑minute candles from historical price data.

Compute net move in predicted direction; mark trigger as validated if move ≥ configured threshold (default 15 NIFTY points).

Produce metrics: precision, recall, average move, median move, and distribution of time‑to‑target.

Special checks: Rahu windows — compute give‑back rate (percentage of gains reversed within X minutes).

Produce a short report with charts (score over time, trigger density, hit/miss examples).

Timeline & milestones (recommended)
Week 0: Kickoff, confirm inputs, lock ayanamsha/ephemeris, gather data.

Week 1: Ephemeris baseline + divisional mapping + unit tests.

Week 2: SBC/KP primitives + sub‑lord detection + temporal tiler.

Week 3: Rule engine implementation + trigger export.

Week 4: Validation harness + backtest on one month; produce PoC outputs and report.

Week 5: Optimization, packaging, docs, and handover.
(Adjust timeline if minute‑level generation or additional rule formalization is required.)

Acceptance criteria (must pass)
Navamsa mapping matches reference examples for all test cases.

Triggers exported in required CSV/XLSX format with metadata.

Validation report runs and produces metrics; at least one Tier‑1 signal must match the historical rule behavior in the attached report for the sample month.

Code is unit‑tested and reproducible; README explains how to run end‑to‑end.

Operational & production notes
Version control: push to Git repo; tag releases.

Reproducibility: store ephemeris DE file and record its checksum.

Monitoring: log generation times, trigger counts, and validation metrics.

Extensibility: design rule engine so new rules can be added via config without code changes.

Security: do not store credentials in code; use environment variables for data access.

Example prompt summary (one paragraph you can paste to an engineer or task agent)
Build a Python pipeline that computes planetary longitudes using skyfield (DE440) with KP Ayanamsha, maps to Navamsa (D‑9) at minute resolution during market hours, detects sub‑lord transitions and vargottama flags, applies the KP/SBC rule set (A‑11/A‑12/A‑13/A‑14, v12.2, v14, hora weighting, Rahu windows, pure‑set alarms) to emit intraday triggers (Tier‑1/Tier‑2/Pure‑Set/Regime‑Shift/Reversal), exports navamsa_monthly.csv and intraday_triggers.csv with metadata, and runs a validation/backtest against provided NIFTY/BANKNIFTY intraday data using the 15‑point first‑5‑candle confirmation rule. Deliver code, unit tests, a validation report, and deployment instructions within five weeks. Use parameterized YAML for rule thresholds and ensure reproducibility by recording ephemeris and code hashes.


# AstroGann Pro – Enhancement Backlog

## Vision
Integrate Astro & Gann indicators into SBC Tool Trading Signals and Astro-Technical chart to deliver high-accuracy swing/positional setups with astro-vedha confluence.

## Epics

### 1. Gann Precision Zones
**Goal:** Gann’s Price Action Studies + Natural Laws of Vibration for swing/positional entry/exit.
- Purple & Red levels for high-probability initiation/target zones
- Black levels for stop-loss & trailing SL
- Asset types: stocks, indices, commodities
- UI: overlay levels on Nifty sector chart, toggle on/off

### 2. Gann Turbo Zones / Bramhastra – Options Trading
- Green lines = trade initiation zones
- Dotted line = target/profit booking
- Automatic 1% SL
- Dynamic high-probability zones for index/stock options
- Integration with NIFTY/BANK NIFTY options expiry calendar

### 3. Gann Momentum Analyzer
- Dynamic price levels for long/short trigger and target
- Customizable visuals: colors, line styles, table position
- Swing & positional across stocks/indices/commodities

### 4. Gann Apex Reversal Suite
- Dynamic reversal signals
- Automated target & stop-loss calculations
- Comprehensive data visualization
- Use cases: swing, day, positional

### 5. Gann Harmonic Vibrations
- Swing High/Low inputs for harmonic vibration levels
- Dynamic vibration levels for support/resistance
- Visual representation with lines/labels
- Customizable swing points

### 6. Gann Harmonic Opens
- Weekly/Monthly/Quarterly/Yearly opens calculation
- Buy above / Sell below levels
- Customizable tables/charts
- Swing/day/positional

### 7. Expiry Range Indicator
- Accurately forecast expiry day support/resistance
- Eliminate false breakouts
- Works for Nifty/Bank Nifty/options
- Backtested strategy

### 8. Gann Time Navigator Pro
- Intraday time cycles for reversal timing
- Auto plot high-probability reversal times
- Works on all timeframes
- Intraday scalping/day trading

### 9. AstroCycle Pro
- Intraday reversals based on Mercury & Moon cycles
- Auto-generated time bars
- Entry rules above/below bar with SL/target
- Scalpers & day traders

### 10. Gann Turbo Cycles / Gann Time Pulse / Gann Intraday Pro
- Auto-generated time cycles for intraday reversals
- Simple trade setup: enter above/below time cycle bar
- Time-based scalping
- Scalper Pro: buy above green, sell below red, blue SL, black targets

### 11. Astro Scalper X
- Planetary cycles for intraday precision
- Buy above blue, sell below black
- Yellow SL, red/green targets
- Index & stock astro timing

### 12. Gann Mega Trend X / SAP Swing Master / Gann Annual Pulse
- Monthly/Annual trend change levels
- Buy above trend change, sell below
- Swing & positional
- Yearly trend reversal zones

### 13. Gann Wave Levels
- Dynamic support/resistance from previous day OHLC
- Bullish/bearish levels generation
- Intraday & swing

### 14. Gann Lightning Scalper
- High-speed intraday scalping levels
- Instant buy/sell signals
- Forex, commodities, stocks

## Backlog Items – User Stories

1. As trader, I want Gann Precision Zones overlay on Nifty sector chart so I can see purple/red initiation zones and black SL levels.
2. As options trader, I want Gann Turbo Zones with 1% auto SL for NIFTY/BANK NIFTY expiry.
3. As swing trader, I want Momentum Analyzer dynamic levels with customizable visuals.
4. As trader, I want Apex Reversal Suite signals with auto target/SL.
5. As analyst, I want Harmonic Vibrations levels from swing high/low inputs.
6. As trader, I want Harmonic Opens for weekly/monthly/yearly opens with buy/sell levels.
7. As expiry trader, I want Expiry Range support/resistance forecast.
8. As intraday trader, I want Gann Time Navigator Pro reversal times plotted.
9. As intraday trader, I want AstroCycle Pro Mercury/Moon time bars.
10. As scalper, I want Gann Turbo Cycles/Time Pulse auto time cycle bars.
11. As intraday trader, I want Astro Scalper X planetary levels overlay.
12. As swing trader, I want Mega Trend X / Annual Pulse trend change levels.
13. As intraday/swing trader, I want Gann Wave Levels dynamic S/R.
14. As scalper, I want Gann Lightning Scalper instant signals.

## Prioritization – MoSCoW

**Must Have**
- Gann Precision Zones overlay
- Gann Time Navigator Pro intraday cycles
- AstroCycle Pro Mercury/Moon cycles
- Expiry Range Indicator

**Should Have**
- Gann Turbo Zones for options
- Gann Momentum Analyzer
- Gann Apex Reversal Suite
- Harmonic Opens

**Could Have**
- Harmonic Vibrations
- Mega Trend X / Annual Pulse
- Wave Levels
- Lightning Scalper

**Won’t Now**
- Full TradingView Pine migration – keep in SBC web app first

## Technical Notes
- Reuse existing lightweight-charts infrastructure
- Add Gann start date picker and fan toggle already scaffolded
- Vedha confluence can be combined with Gann levels for AstroGann scoring
- Persist Gann settings per sector in localStorage
- API endpoints: /api/gann/levels, /api/gann/timecycles, /api/astro/cycles

## Next Steps
1. Implement Gann Precision Zones overlay
2. Integrate AstroCycle Pro time bars
3. Add Expiry Range forecast
4. Combine Astro + Gann score into unified AstroGann Pro signal

## Financial Astrology Research Backlog

Source: *A Trader's Guide to Financial Astrology* (Pesavento/Smoleny). Use as research inspiration, not as unverified trading rules. Every method must show sample size, baseline, out-of-sample results, and limitations.

### Priority 1 – Research Foundation

1. **Astro Research Lab**
	- Status: Enhanced — canonical lunar events, volatility, one-to-one matched controls, equity curve, MAE, costs, and confidence metrics are implemented.
	- Unified event-study UI for lunar phases, planetary aspects, ingresses, retrogrades, and SBC events.
	- Inputs: market, date range, event, holding window, return/volatility measure.
	- Outputs: event count, average/median return, win rate, dispersion, max adverse excursion, baseline comparison, equity curve.

2. **Walk-Forward Validation**
	- Status: Enhanced — rolling train/test, transaction costs, regime segmentation, and fold mean-return decay are implemented.
	- Rolling train/test periods for every research rule.
	- Report in-sample versus out-of-sample performance, accuracy decay, regime results, and transaction-cost sensitivity.

3. **Canonical Market Event Model**
	- Status: MVP complete for lunar phases; aspect and ingress event types remain.
	- Shared event schema for planet pair, aspect angle, orb, applying/separating state, lunar phase, date, and source.
	- Reuse the same event data in forecasts, charts, and backtests.

### Priority 2 – Book-Inspired Studies

4. **New Moon / Full Moon Efficiency Study**
	- Compare event-window returns and volatility against normal and matched control days.
	- Support 1, 3, 5, 10, and 20 trading-day windows.

5. **Planetary Aspect Research Grid**
	- Search aspect, orb, planet pair, market, and period.
	- Show applying/separating behavior, historical samples, returns, and volatility response.

6. **Solar/Lunar Cycle Explorer**
	- Sun-sign cycle, Moon-sign cycle, Sun-Moon angular separation, synodic phase, turning points, and price overlay.

7. **Optional Bradley Barometer Overlay**
	- Experimental only; keep separate from the primary SBC score.
	- Show turning-point candidates and historical validation.

### Priority 3 – Trust and Reproducibility

8. **Regime-Aware Reports**
	- Segment results into bull, bear, high-volatility, low-volatility, and crisis regimes.

9. **Research Export**
	- Export JSON/CSV/Markdown containing rule definition, symbol, dates, event settings, holding period, assumptions, metrics, timestamp, and version.

10. **Unified Daily Forecast Contract**
	- Keep `/api/daily_confluence` as the shared source for current and forward confluence data.
	- Add cache metadata, data freshness, and calculation version.

### Guardrails

- Do not add neural-network prediction before the event-study and walk-forward layers exist.
- Do not present small-sample win rates as reliable signals.
- Keep research output separate from live recommendations.
- Display the baseline, sample size, confidence interval, and out-of-sample result beside every claimed edge.
