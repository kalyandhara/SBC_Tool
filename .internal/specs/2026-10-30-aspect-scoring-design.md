# Specification: Modular Aspect Set Library & Orb Tuning

## Overview
Introduce a modular aspect set library (`sbc/aspect_sets.py`) inspired by research libraries (e.g. classical & modern aspect sets with customizable orbs, energies, and polarities), enabling configurable transit scoring options in SBC workstation engines while maintaining full backwards compatibility with classical Sarvatobhadra Chakra rules.

## Objectives
1. **Configurable Aspect Library:** Define standard aspect sets (Classical 0/30/45/60/90/120/135/150/180°, Modern, Extended) with tunable orbs and energy weights.
2. **Scoring Integration:** Provide helper functions for aspect evaluation and scoring within transit analysis without disrupting existing core engines.
3. **Transparency & Testing:** Full unit test coverage verifying aspect calculations and energy weightings.

## Technical Architecture
- **`sbc/aspect_sets.py`:** Aspect definitions, orb thresholds, energy weights, and evaluation functions.
- **`tests/test_aspect_sets.py`:** Unit tests verifying aspect matching and scoring.

## Verification Plan
1. Run pytest suite (`tests/test_aspect_sets.py`, `tests/test_sector_rotation.py`, `tests/test_api.py`).

## Stress Test Results: Aspect Scoring Spec

### Resolved Decisions
- [Architecture & Integration]: Implemented as a modular, opt-in helper library (sbc/aspect_sets.py).
- [Orb Semantics]: Named aspect profiles with angle, orb, energy, and polarity.
- [Scoring Semantics]: Deterministic closest-orb priority for overlapping aspects.
- [Validation Claims]: Explicit exploratory research disclaimers.
- [Security & Risk]: Pure math geometry; zero security risk.
- [Test Coverage]: Comprehensive unit tests covering exact, boundary, and tie-breaking cases.

### Changes Made
- None to core engines; specification finalized following stress testing.

### Confidence Assessment
- Overall: High
- Areas of concern: None.
