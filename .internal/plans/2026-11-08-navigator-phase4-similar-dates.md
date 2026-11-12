# Navigator Phase 4: Similar Past Dates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use beads-superpowers:subagent-driven-development (recommended) or beads-superpowers:executing-plans to implement this plan task-by-task. Each Task becomes a bead (`bd create -t task --parent <epic-id>`). Steps within tasks use checkbox (`- [ ]`) syntax for human readability.

**Goal:** For each upcoming high-scoring date of a profile, show at least 5 past dates with the most similar blended natal and sky signature, with their market outcomes, in the Navigator tab.

**Architecture:** `sbc/navigator/signature.py` computes natal similarity and the blend. `sbc/navigator/analogs.py` picks targets and analogs, then computes outcomes and the random comparison. A new route in `navigator_bp.py` serves the results, and `navigator.js` renders them.

**Tech Stack:** Python 3.11, numpy, Flask, plain JS. The existing `sbc.analogs`, `sbc.fingerprint`, and Phase 1 `sbc.navigator` modules.

Spec: `.internal/specs/2026-11-08-navigator-phase4-similar-dates-design.md` (read it, including Stress Test Results).

## Global Constraints

- Run tests with `C:/Users/Owner/OneDrive/Documents/Trading/SBC_Tool/venv/Scripts/python -m pytest`. Load env with `set -a; . ./.env; set +a`.
- Tests touch only `navigator_test`. Never print connection values.
- Commit on `feature/astrotrade-navigator`. Do not push. Never use git stash.
- `ANALOG_VERSION = "nav-analog-1"`. Weights:
    - Natal: 0.8 contacts + 0.2 dasha.
    - Dasha: 0.6 Antardasha match + 0.4 Pratyantar match. No Mahadasha.
    - Blend: 0.5 natal + 0.5 sky.
    - Never fitted to returns.
- Selection:
    - High-scoring is an integer score of 61 or more, over the next N sessions (default 30, allowed 5-60).
    - Top-5 fallback, with ties going to the earlier date.
    - Exclude analogs within 30 calendar days of the target. Spacing of at least 5 sessions. Top 10. Fewer than 5 means "too few analogs".
- Outcomes (raw, no costs):
    - Next-5 is open to the open 5 sessions later, as in Phase 1 `oo_5`. Drawdown is over the same window.
    - Eligibility requires the exit open to be on or before the last session before the target.
- Random comparison: 1,000 draws with seed 1729, same size and spacing, share with win ratio greater than or equal to the analogs'.
- Cost and privacy:
    - One computation at a time, otherwise 429. Cache of the last 8 results.
    - No natal longitudes, birth data or `chart_hash` in responses.
- Page and labels:
    - Every target says "anecdotal: N analogs, not a tested signal".
    - `textContent` only, no new CDN, no sideways page scroll at 375px.
- Plan snippets are unrun. Verify every name against the repo before relying on it.
- `test_every_route_has_a_ui_caller_or_is_listed` is a known pre-existing failure on `/api/briefing_summary` and `/health` only.

---

### Task 1: Natal signature and blended similarity

**Files:**
- Create: `sbc/navigator/signature.py`
- Test: `tests/test_navigator_signature.py`

**Interfaces:**
- Consumes:
    - `sbc.navigator.weights` (ASPECTS, ORB, TRANSIT_BODIES).
    - `sbc.navigator.ephemeris.build_sky` and `SkyTable`.
    - `sbc.navigator.profile.natal_points`.
    - `sbc.yogas.vimshottari`.
    - `sbc.analogs.similarity` and `SkyArrays`.
- Produces:
    - `ANALOG_VERSION`, `W_CONTACTS = 0.8`, `W_DASHA = 0.2`, `W_ANTAR = 0.6`, `W_PRAT = 0.4`, `W_NATAL = 0.5`, `W_SKY = 0.5`.
    - `contact_matrix(sky, natal) -> (keys: list[tuple[str,str,str]], weights: np.ndarray (days, K))`. Orb factor `clip(1 - |sep - angle| / ORB, 0, 1)`, identical to `sbc.navigator.terms`.
    - `weighted_jaccard(a: np.ndarray (K,), pool: np.ndarray (N,K)) -> np.ndarray (N,)`. Sum of minimums over sum of maximums; 1 where both are all zero.
    - `dasha_lords(moon_natal_lon, birth_date, days) -> (antar: list[str], prat: list[str])`.
    - `natal_similarity(target_idx: int, contacts, antar, prat, pool_idx) -> np.ndarray`.
    - `blend(natal: np.ndarray, sky: np.ndarray) -> np.ndarray`.

**Acceptance Criteria:**
- Weighted Jaccard has exact values on hand cases: identical vectors give 1, disjoint vectors give 0, `[1,.5]` against `[.5,1]` gives 0.5, and two zero vectors give 1.
- Dasha component: both lords match gives 1.0, Antardasha only gives 0.6, Pratyantar only gives 0.4, neither gives 0.
- The contact matrix on real sky data matches a direct per-day computation of the Phase 1 transit contacts with no orb weighting.
- The weights snapshot test fails if any weight or the version changes.
- Moon has no separate natal term, and a test asserts natal = 0.8 × contacts + 0.2 × dasha exactly.

- [ ] **Step 1: Write failing tests**

```python
import numpy as np, pytest
from sbc.navigator import signature as G

@pytest.mark.parametrize("a,b,expected", [
    ([1, 0], [1, 0], 1.0), ([1, 0], [0, 1], 0.0), ([1, .5], [.5, 1], .5), ([0, 0], [0, 0], 1.0)])
def test_weighted_jaccard(a, b, expected):
    assert G.weighted_jaccard(np.array(a, float), np.array([b], float))[0] == pytest.approx(expected)

def test_weights_pinned():
    assert (G.ANALOG_VERSION, G.W_CONTACTS, G.W_DASHA, G.W_ANTAR, G.W_PRAT, G.W_NATAL, G.W_SKY) == \
        ("nav-analog-1", .8, .2, .6, .4, .5, .5)

def test_dasha_component_values():
    antar = ["Venus", "Venus", "Mars", "Mars"]; prat = ["Sun", "Moon", "Sun", "Moon"]
    contacts = np.zeros((4, 1))
    nat = G.natal_similarity(0, contacts, antar, prat, np.arange(4))
    # contacts both empty give 1, so natal = .8 + .2 * dasha
    assert nat.tolist() == pytest.approx([.8 + .2, .8 + .2 * .6, .8 + .2 * .4, .8])
```

- [ ] **Step 2: Run them; expected FAIL** (module missing).

- [ ] **Step 3: Implement**

```python
"""Natal signature similarity for Phase 4 analogs. Hand-set, never fitted."""
from __future__ import annotations
import datetime as dt
import numpy as np
from sbc.navigator import weights as W
from sbc.yogas import vimshottari

ANALOG_VERSION = "nav-analog-1"
W_CONTACTS, W_DASHA = 0.8, 0.2
W_ANTAR, W_PRAT = 0.6, 0.4
W_NATAL, W_SKY = 0.5, 0.5

def contact_matrix(sky, natal):
    keys, cols = [], []
    for planet in W.TRANSIT_BODIES:
        for point, nlon in natal.items():
            sep = np.abs((sky.lon[planet] - nlon + 180) % 360 - 180)
            for code, angle in W.ASPECTS.items():
                keys.append((planet, point, code))
                cols.append(np.clip(1 - np.abs(sep - angle) / W.ORB, 0, 1))
    return keys, np.column_stack(cols)

def weighted_jaccard(a, pool):
    mn = np.minimum(pool, a).sum(axis=1); mx = np.maximum(pool, a).sum(axis=1)
    out = np.ones(len(pool)); nz = mx > 0
    out[nz] = mn[nz] / mx[nz]
    return out

def natal_similarity(target_idx, contacts, antar, prat, pool_idx):
    c = weighted_jaccard(contacts[target_idx], contacts[pool_idx])
    a = np.array([antar[i] == antar[target_idx] for i in pool_idx], float)
    p = np.array([prat[i] == prat[target_idx] for i in pool_idx], float)
    return W_CONTACTS * c + W_DASHA * (W_ANTAR * a + W_PRAT * p)

def blend(natal, sky):
    return W_NATAL * natal + W_SKY * sky
```

`dasha_lords` calls `vimshottari` once and walks the antar and pratyantar boundaries with `np.searchsorted`, as `sbc.navigator.terms.dasha_term` does. Reuse its helper if one exists rather than duplicating it.

- [ ] **Step 4: Run; expected PASS.** Add the real-sky contact cross-check test.
- [ ] **Step 5: Commit**, with a message ending in the Co-Authored-By line.

### Task 2: Targets, analog selection, outcomes and random comparison

**Files:**
- Create: `sbc/navigator/analogs.py`
- Test: `tests/test_navigator_analogs.py`

**Interfaces:**
- Consumes: Task 1; `sbc.navigator.scoring.score_series`; `sbc.analogs.select`, `_thin` behaviour, `SkyArrays`, `similarity`; `sbc.fingerprint.fingerprint`; `sbc.rule_validation.load_history` or `sbc.analogs.load_nifty_history`; the repo trading calendar (find it in `sbc/market_calendar.py` or `sbc/market_holidays.py`).
- Produces:
    - `next_sessions(last: str, n: int) -> list[str]`.
    - `pick_targets(days, scores) -> (mode, list[int])`.
    - `eligible_mask(dates, target_date, horizon=5) -> np.ndarray[bool]`.
    - `outcomes(i, prices) -> dict`, where `prices` holds aligned Nifty open, close and low, CNXBANK open and close, INDIAVIX close, and the sector open and close dicts.
    - `random_share(pool_next5, n, spacing, observed_win, seed=1729, draws=1000) -> float`.
    - `build(profile, market, days=30) -> dict` in the spec's response shape.

**Acceptance Criteria:**
- Eligibility: an analog at index i is eligible only if i+5 ≤ (index of last session before target). A test moves the cutoff by one session and must fail if the rule is off by one.
- Exclusion within 30 calendar days and spacing of at least 5 sessions hold. With 10 or more eligible analogs, exactly 10 are returned. With fewer than 5, "too few analogs" is returned with an empty list.
- Targets: scores ≥ 61 are chosen. If none, the top 5 are chosen, with ties going to the earlier date and `mode="top_scores"`.
- Outcomes on fixture prices give exact values:
    - Nifty and CNXBANK day open-to-close.
    - VIX percent change against the previous close.
    - Top 5 sectors excluding CNXBANK, with missing sectors listed.
    - Next-5 open to open.
    - Drawdown from the open through lows up to the exit open.
    - n/a where data is missing, never filled.
- The random share is deterministic under its seed, in [0,1], and equals 1.0 when the observed win ratio is 0.
- The summary has n, win ratio, mean and median next-5, mean drawdown, the pool baseline, the random share, median analog age in years, and the anecdotal label.
- Determinism: identical `build` output on repeat.

- [ ] **Step 1: Write failing tests** for each criterion above, on synthetic aligned arrays. Build a 40-session fixture with known opens, closes and lows. Assert exact numbers for one analog, such as next-5 = open[i+5]/open[i] - 1.
- [ ] **Step 2: Run; expected FAIL.**
- [ ] **Step 3: Implement** `sbc/navigator/analogs.py`:
    - Sky similarity: build `SkyArrays` for history from the existing fingerprint history, and for targets from `sbc.fingerprint.fingerprint(date)`. Call `sbc.analogs.similarity(target, pool)["overall"]`.
    - Natal similarity: Task 1 over the same history dates.
    - Combination: `G.blend`, then mask by eligibility and exclusion, then thin with spacing 5, keeping the highest. Reuse `sbc.analogs.select` and `_thin` if their contracts fit; otherwise write a small local version and say why.
    - Random comparison: draw `n` spaced sessions from the eligible pool (sample until spacing holds, with a bounded number of tries; disclose if spacing can't be met).
- [ ] **Step 4: Run; expected PASS.**
- [ ] **Step 5: Commit.**

### Task 3: API route with single-flight lock and cache

**Files:**
- Modify: `sbc/api/blueprints/navigator_bp.py`
- Test: `tests/test_navigator_api.py` (add tests)

**Interfaces:**
- Consumes: Task 2 `build`; the existing `_guard`, `_market`, profile lookup and `clean_json`.
- Produces: `GET /api/navigator/analogs?profile_id=N&days=30`.

**Acceptance Criteria:**
- The guard applies.
- `days` outside 5-60, or not an integer, gives 400 with a fixed message.
- An unknown profile gives 404. Store failure gives 503.
- A second concurrent request gets 429 with a fixed message, without blocking.
- A cached result is reused for the same (profile, data date, ANALOG_VERSION, engine version, days) and is recomputed when any of these changes. The cache holds at most 8 entries.
- The response has no `chart_hash`, birth fields or natal longitudes. The test walks the whole JSON for those keys and for the profile's coordinates as values.
- The response notes include the measured seconds and the data caveats from the spec.
- Errors are logged by exception type only.

- [ ] **Step 1: Write failing tests**, using monkeypatched `build` for lock and cache, and a real small run for redaction.
- [ ] **Step 2: Run; expected FAIL.**
- [ ] **Step 3: Implement** with a module-level `threading.Lock` and `acquire(blocking=False)`, plus an `OrderedDict` cache of size 8.
- [ ] **Step 4: Run; expected PASS.**
- [ ] **Step 5: Commit.**

### Task 4: "Similar past dates" section in the tab

**Files:**
- Modify: `static/js/navigator.js`, `templates/index.html` (bump `?v=`), `static/style.css`
- Test: `tests/test_navigator_page.py` (add tests)

**Acceptance Criteria:**
- The section sits below the score and loads `/api/navigator/analogs` for the selected profile.
- It shows the mode text, one row per target (date, score, band), and an expandable analog table with every outcome field. The summary includes the pool baseline, the random comparison sentence, median age, the anecdotal label and the data caveats.
- Next-5 is labelled "open to open, 5 sessions, as in the backtest".
- Loading, 429, 503 and error states show the server's fixed message. One request at a time; a profile switch cancels the old render.
- `textContent` only, no new CDN, and tables scroll inside their wrapper with no page scroll at 375px.
- Page tests assert the section markup and the labels, and can fail.

- [ ] **Step 1: Write failing page tests.**
- [ ] **Step 2: Run; expected FAIL.**
- [ ] **Step 3: Implement** in `navigator.js`, following the existing `navEl` and sequence-counter patterns.
- [ ] **Step 4: Run the full suite with env loaded; expected 1 known failure only.**
- [ ] **Step 5: Commit.** The controller then verifies the real page in the browser.

## Self-Review

Spec coverage:
- Targets: Task 2.
- Similarity: Task 1, with the blend in Task 2.
- Eligibility, exclusion, spacing and count: Task 2.
- Outcomes and summary: Task 2.
- Random comparison: Task 2.
- API, lock, cache and redaction: Task 3.
- Page: Task 4.
- Data caveats: Tasks 3 and 4.
- Real-page check: the controller, after Task 4.
- The analog walk-forward test is deferred to SBC_Tool-3xv.3.
