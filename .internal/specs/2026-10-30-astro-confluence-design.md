# Specification: Astro-Technical Confluence Decision Engine

## Overview
Adopt the core decision-making insight from the `jesse-astrology-trading-strategy` repository—filtering technical trend triggers (e.g. EMA 9/21 crossovers) with astrological directional bias—and subject it to our repository's rigorous empirical validation standard (permutation testing against controls, out-of-sample eras, and transaction cost modeling).

## Objectives
1. **Decision Confluence Engine (`sbc/confluence_engine.py`):** Pure function combining technical indicators (Heikin Ashi EMA 9/21 crosses) with astrological score regimes (bullish/bearish/neutral).
2. **Empirical Validation Study (`scripts/study_astro_ma_confluence.py`):** Run pre-registered backtesting over historical NIFTY daily series to test whether astro-filtered MA crosses outperform baseline un-filtered MA crosses after transaction costs (0.20%).
3. **Unit Test Suite (`tests/test_confluence_engine.py`):** Verify signal generation, filter application, and edge cases.

## Verification Plan
1. Run pytest suite (`tests/test_confluence_engine.py`, `tests/test_sector_rotation.py`, `tests/test_api.py`).
2. Run study script to generate empirical findings.

## Stress Test Results: Astro Confluence Spec

### Resolved Decisions
- [Confluence Logic]: Strictly closed-bar data to avoid lookahead bias.
- [Empirical Rigor]: 0.20% round-trip costs and permutation tests against same-day return deciles.
- [Security & Risk]: Analytical model only; zero live execution risk.
- [Performance & Scale]: Vectorized NumPy implementation for sub-3-second runtime.
- [Test Coverage]: Unit tests for crossover detection, filter alignment, and net returns.

### Changes Made
- None to core architecture; specification finalized following stress testing.

### Confidence Assessment
- Overall: High
- Areas of concern: None.
