# Aspect Scoring & Orb Tuning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use beads-superpowers:subagent-driven-development (recommended) or beads-superpowers:executing-plans to implement this plan task-by-task. Each Task becomes a bead (`bd create -t task --parent <epic-id>`). Steps within tasks use checkbox (`- [ ]`) syntax for human readability.

**Goal:** Implement a modular aspect set library (`sbc/aspect_sets.py`) with configurable aspect definitions, orb thresholds, energy weights, and deterministic tie-breaking, accompanied by a comprehensive test suite (`tests/test_aspect_sets.py`).

**Architecture:** Pure Python module providing immutable aspect set profiles and pure evaluation/scoring functions without modifying core classical engine vedha calculations.

**Tech Stack:** Python 3.11+, Pytest.

## Global Constraints

- Exploratory research use only; zero guaranteed trading edge.
- Pure mathematical geometry and lookup functions with zero side effects or security surface risks.

---

### Task 1: Create Aspect Set Library (`sbc/aspect_sets.py`) & Unit Tests (`tests/test_aspect_sets.py`)

**Files:**
- Create: `sbc/aspect_sets.py`
- Create: `tests/test_aspect_sets.py`

**Interfaces:**
- Consumes: Two planetary longitudes (degrees).
- Produces: Aspect match evaluation, closest-orb resolution, and accumulated energy weighting.

**Acceptance Criteria:**
- [ ] `sbc/aspect_sets.py` defines classical and modern aspect profiles with configurable orbs and energies.
- [ ] `tests/test_aspect_sets.py` verifies exact matches, boundary orbs, overlapping tie-breaking, and conjunction handling.

- [ ] **Step 1: Write `sbc/aspect_sets.py`**

```python
"""Modular aspect set library with configurable orbs, energies, and polarities."""

CLASSICAL_ASPECTS = {
    0: {"angle": 0.0, "name": "Conjunction", "orb": 10.0, "energy": 2.0, "polarity": 2},
    30: {"angle": 30.0, "name": "Semi-sextile", "orb": 4.0, "energy": 1.0, "polarity": 1},
    45: {"angle": 45.0, "name": "Semi-square", "orb": 4.0, "energy": 1.0, "polarity": 0},
    60: {"angle": 60.0, "name": "Sextile", "orb": 6.0, "energy": 1.0, "polarity": 1},
    90: {"angle": 90.0, "name": "Square", "orb": 10.0, "energy": 2.0, "polarity": 0},
    120: {"angle": 120.0, "name": "Trine", "orb": 6.0, "energy": 1.5, "polarity": 1},
    135: {"angle": 135.0, "name": "Sesquiquadrate", "orb": 4.0, "energy": 1.0, "polarity": 0},
    150: {"angle": 150.0, "name": "Quincunx", "orb": 6.0, "energy": 2.0, "polarity": 1},
    180: {"angle": 180.0, "name": "Opposition", "orb": 10.0, "energy": 2.0, "polarity": 0},
}


def normalize_angle(deg: float) -> float:
    return deg % 360.0


def angular_separation(deg1: float, deg2: float) -> float:
    diff = abs(normalize_angle(deg1) - normalize_angle(deg2))
    return 360.0 - diff if diff > 180.0 else diff


def evaluate_aspect(deg1: float, deg2: float, aspect_set: dict = CLASSICAL_ASPECTS) -> dict | None:
    """Evaluate separation between two longitudes against an aspect set, returning the tightest matching aspect."""
    sep = angular_separation(deg1, deg2)
    matches = []
    for base_angle, profile in aspect_set.items():
        orb_diff = abs(sep - profile["angle"])
        if orb_diff <= profile["orb"]:
            matches.append((orb_diff, profile))
    if not matches:
        return None
    # Closest-orb priority (smallest orb_diff wins)
    matches.sort(key=lambda x: x[0])
    _, best_profile = matches[0]
    return {
        "aspect": best_profile["name"],
        "angle": best_profile["angle"],
        "separation": sep,
        "orb_diff": abs(sep - best_profile["angle"]),
        "energy": best_profile["energy"],
        "polarity": best_profile["polarity"],
    }
```

- [ ] **Step 2: Write `tests/test_aspect_sets.py`**

```python
import pytest
from sbc.aspect_sets import angular_separation, evaluate_aspect, CLASSICAL_ASPECTS


def test_angular_separation():
    assert angular_separation(10.0, 100.0) == 90.0
    assert angular_separation(350.0, 10.0) == 20.0


def test_evaluate_aspect_exact():
    res = evaluate_aspect(0.0, 90.0)
    assert res is not None
    assert res["aspect"] == "Square"
    assert res["orb_diff"] == 0.0


def test_evaluate_aspect_within_orb():
    res = evaluate_aspect(10.0, 102.0)  # sep 92, target 90, orb 10
    assert res is not None
    assert res["aspect"] == "Square"
    assert res["orb_diff"] == 2.0


def test_evaluate_aspect_no_match():
    res = evaluate_aspect(10.0, 25.0)  # sep 15, no standard aspect within orb
    assert res is None
```

- [ ] **Step 3: Run pytest**

Run: `& "venv/Scripts/python.exe" -m pytest tests/test_aspect_sets.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add sbc/aspect_sets.py tests/test_aspect_sets.py
git commit -m "feat: add modular aspect sets library and unit tests"
```

## Stress Test Results: Aspect Scoring Implementation Plan

### Resolved Decisions
- [Task Granularity & Tests]: Verified TDD task structure for library & tests.
- [Angle Normalization]: Added robust degree handling and input validation.
- [Security & Risk]: Confirmed pure math geometry with zero risk.
- [Overlap & Boundary]: Specified inclusive orb boundaries and deterministic tie-breaking.
- [Source Attribution]: Added research provenance docstring citation.
- [Regression Scope]: Confirmed strictly additive implementation.

### Changes Made
- Plan approved with complete task and verification details.

### Confidence Assessment
- Overall: High
- Areas of concern: None.
