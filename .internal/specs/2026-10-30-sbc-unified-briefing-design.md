# Specification: SBC Workstation Unified Intelligence Briefing & Core Question Answering

## Overview
Enhance the Sarvatobhadra Chakra (SBC) Market Prediction workstation (`SBC_Tool`) to directly and transparently answer the six core trading questions demanded by systematic macro and timing workflows, while explicitly distinguishing between descriptive historical event frequencies and validated out-of-sample statistical edges.

## Core Trading Questions Addressed
1. **What planetary events are happening now?** → Real-time transit ephemeris card displaying current stations, ingress dates, and aspect matrices.
2. **What are the possible sectoral impacts in financial markets?** → Sector Heatmap & Rotation Matrix integration mapped to live sector indices.
3. **What are upcoming major events with significant bullish or bearish sectoral impact?** → Forward Calendar and Planetary Event feed highlighting upcoming ingresses, eclipses, and retrograde turns.
4. **What were the past outcomes for NIFTY and relevant sectors around these events?** → Event flow Sankey diagrams, window returns (T+5, T+10, T+20), and historical win-rate distribution tables.
5. **Which sectors are best for 6-month and 1-year investment horizons, and which sectors should be avoided?** → Explicit advisory module disclosing that medium-to-long term horizons rely on fundamentals and macro data (since astronomical models show 0/511 out-of-sample validated edge), alongside fundamental sector rotation guidance.
6. **Signal Validation Transparency:** → Persistent visual badges distinguishing *Descriptive Historical Frequencies* (experimental/exploratory) from *Validated Edges* (currently zero out-of-sample).

## Architecture & Components
- **Unified Intelligence Briefing Panel (`overview` & `sector-rotation` tabs):**
  - A summary briefing box providing synthesized answers to the 6 core questions.
  - Signal classification tags (`[DESCRIPTIVE / EXPERIMENTAL]` vs `[VALIDATED: NONE]`).
- **Backend API Integration (`sbc/api/`):**
  - Expose structured current ephemeris and core question summaries via Flask blueprints.
- **Front-End UI Updates (`static/js/` & `static/style.css`):**
  - Clean component styling with accessibility and responsive grid layout.

## Verification Plan
1. Run pytest suite (`tests/test_sector_rotation.py`, `tests/test_sector_rotation_api.py`, `tests/test_api.py`).
2. Navigate via Playwright to verify the Unified Briefing Dashboard renders correctly across tabs.

## Stress Test Results: SBC Unified Intelligence Briefing Spec

### Resolved Decisions
- [Architecture & Data Freshness]: Reused existing Flask API blueprints with graceful fallbacks.
- [Signal Transparency]: Integrated explicit disclaimer badges for descriptive vs validated signals.
- [6m/1y Horizons]: Clarified that long-term asset allocation requires fundamental macro analysis.
- [Security & Risk]: Verified safe DOM rendering and prominent educational disclaimers.
- [Performance & Scale]: Leveraged precomputed JSON to ensure zero client-side lag.
- [Test Coverage]: Added automated pytest verification for briefing data structures.

### Changes Made
- None to core architecture; specification finalized following stress testing.

### Confidence Assessment
- Overall: High
- Areas of concern: None.
