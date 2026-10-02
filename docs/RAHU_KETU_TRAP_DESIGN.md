# Rahu / Ketu Trap Calendar – Design Document

## Objective
Build a backtestable, industry-wise daily trap detection engine for Rahu/Ketu transits and pipeline results to executive dashboard.

## Core Concept
Rahu/Ketu are shadow nodes. When they:
1. Occupy nakshatras ruled by industry ruling planets
2. Form vedha/aspect with sector anchor nakshatra
3. Coincide with Moon in inauspicious nakshatra / Tithi
4. Align with planetary debilitation / enemy positions

→ Trap score increases → high probability of false breakouts / reversal / distribution traps.

## Architecture

### Modules
1. **rahu_ketu_trap.engine**
   - `RahuKetuTrapEngine`
   - Inputs: date range, industries config, anchor mapping
   - Outputs: daily trap matrix, scores, flags

2. **rahu_ketu_trap.config**
   - Industry → ruling planet mapping
   - Industry → birth nakshatra / anchor date mapping
   - Trap rule weights

3. **rahu_ketu_trap.backtest**
   - Historical price data loader
   - Trap signal → next day return correlation
   - Metrics: win rate, avg drawdown, precision/recall

4. **rahu_ketu_trap.pipeline**
   - Daily batch job
   - Cache results in SQLite
   - Expose API

5. **API / UI Integration**
   - Flask endpoint `/api/rahu_ketu_trap_calendar`
   - Dashboard tab: Executive → Rahu/Ketu Trap Calendar
   - Calendar heatmap: industry x date, trap severity

## Trap Scoring Logic v1

Score = w1*NodeProximity + w2*Vedha + w3*MoonConjunction + w4*Tithi + w5*AyanamsaDrift

Where:
- NodeProximity: angular distance Rahu/Ketu to sector ruling planet < 5° → +3
- Vedha: Rahu/Ketu forms vedha with sector anchor nakshatra lord → +2
- MoonConjunction: Moon in Rahu/Ketu nakshatra or same sign → +2
- Tithi: Krishna Paksha 8-14 → +1
- Ayanamsa drift penalty if node speed anomaly → +1

Trap Levels:
0-2 → GREEN
3-5 → AMBER
6-8 → ORANGE
9+ → RED 🚨

## Data Sources
- Planetary positions: swisseph via sbc.planets.positions
- Industry mapping: sbc.config.SECTOR_NAME_MAP + custom RULING_PLANET_MAP
- Price data: sbc.market_data / yfinance cache
- Backtest data: existing backtest.db

## Backtestability
- Rule weights configurable via JSON
- Walk-forward validation
- Output metrics: precision, recall, avg trap day return, max drawdown

## Dashboard Integration
- New tab "Rahu/Ketu Trap Calendar"
- Monthly heatmap: industries rows, dates columns, color by trap level
- Drill-down: daily trap details per industry
- Export CSV / JSON

## Implementation Phases
Phase 1: Engine + config + scoring
Phase 2: Backtest harness
Phase 3: API endpoint
Phase 4: Dashboard UI tab
Phase 5: Pipeline + caching
