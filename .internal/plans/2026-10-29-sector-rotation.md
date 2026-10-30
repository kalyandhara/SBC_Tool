# Sector Rotation Around Planetary Events Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use beads-superpowers:subagent-driven-development (recommended) or beads-superpowers:executing-plans to implement this plan task-by-task. Each Task becomes a bead (`bd create -t task --parent <epic-id>`). Steps within tasks use checkbox (`- [ ]`) syntax for human readability.

**Goal:** For the core four planetary events, measure NSE sector index returns over T+5/T+10/T+20 sessions relative to NIFTY, grade the pre-registered confirmatory hypotheses out of sample, and publish a report plus a read-only page.

**Architecture:** Event anchors come from the existing `sbc.stations` (Mercury stations) and `sbc.transit_almanac` (eclipses, Jupiter/Saturn ingress). Sector closes come from `market.db` via `sbc.market_store`. A new pure-function module `sbc/sector_rotation.py` builds anchors, clusters, returns, ranks, and labels. Grading reuses the B-58 harness conventions: circular-shift permutations via `sbc.stats`, BH across the confirmatory family, and the incremental control test. A script writes the report and JSON. A read-only blueprint serves the JSON.

**Tech Stack:** Python, numpy, pandas, Flask blueprints, sqlite (`data/market.db`), yfinance (through `market_store`), swisseph (existing almanac), pytest.

## Global Constraints

- Sample: every NIFTY session stored in `market.db` (from 2007-09-17) to the latest session.
- Horizons: T+5, T+10, T+20 sessions from the anchor session. No other horizons.
- Clustering: events within 20 sessions of each other merge into one cluster.
- Mercury: one occurrence per retrograde window, anchored at the retrograde start station. The end date is metadata only (stress-test branch 1).
- Grader inputs: signal on day t = hypothesis direction on pre-registered anchor-window days, else 0. Forward return = sector h-session return minus NIFTY h-session return (branch 3).
- Effective sample floor: a hypothesis needs at least 8 independent out-of-sample clusters, in addition to `MIN_SIGNAL_DAYS` (branch 5). Clusters are the binding count.
- Confidence: only "High" (confirmatory pass) or "No call". No "Medium" (branch 2).
- Confirmatory list may be empty. A descriptive phase 1 with "no pre-registered edge" is a valid result (branch 4).
- Auth parity for the new endpoint is a blocking criterion (branch 6).
- Reproducibility test uses a frozen synthetic fixture. Reports record input last-session dates and a hash of the price rows (branch 7).
- Permutation: `sbc.stats` circular shift, `N_PERMUTATIONS` = 1000, `MIN_SHIFT` = 60, fixed seed.
- Minimum signal days: `sbc.stats.MIN_SIGNAL_DAYS` = 30. Below it, status is `insufficient`.
- Pass rule: q < 0.05 after BH over the confirmatory family only, same direction in both eras, AND the incremental test against market controls q < 0.05 (standing rule, `docs/GAP_ANALYSIS_PREDICTION_ENGINE_2026-10-03.md`).
- Out-of-sample era: 2021-10-01 onward. Earlier history is descriptive.
- The pre-registration is committed before the first run of `scripts/sector_rotation_report.py`.
- Endpoints are read-only and serve precomputed JSON. Query parameters are allow-listed; anything else returns 400. No SQL built from request input.
- No new credentials. Do not modify `sbc/stats.py` or the B-58 modules.

---

### Task 1: Pre-registration document

**Files:**
- Create: `docs/research/sector_rotation_preregistration_2026-10-29.md`

**Interfaces:**
- Consumes: findings in `docs/research/transit_events_preregistration_2026-10-11.md`, `docs/research/transit_event_validation_2026-10-11.json`, `docs/research/sector_validation_2026-10-03.md`
- Produces: the frozen confirmatory list (`CONFIRMATORY` in Task 5 must match it exactly), the era boundary, the forecast cutoffs, and the rotation label mapping

**Acceptance Criteria:**
- The doc lists the confirmatory hypotheses, each traceable to a prior finding in the cited docs.
- The doc fixes: events, horizons, sector set, era boundary 2021-10-01, rotation label mapping (spec section 5), forecast confidence rule, cluster rule, minimum signal days, pass rule.
- The doc states the result of the prior B-58 and sector-vedha out-of-sample runs. If no prior finding supports a directional sector hypothesis, the confirmatory list is empty and every sector result is descriptive. That is a valid outcome and must be written as such.
- The doc is committed before Task 6 runs anything.

- [ ] **Step 1: Read the prior findings**

Run: read the three cited files above in full.
Expected: you can state, per prior hypothesis, whether it passed out of sample.

- [ ] **Step 2: Write the pre-registration**

Write the doc with the fixed items above. For each confirmatory hypothesis use this row format:

```markdown
| ID | Event | Sectors | Horizon | Direction | Source finding |
|---|---|---|---|---|---|
```

If the confirmatory list is empty, write: `Confirmatory list: empty. All sector outputs are descriptive.`

- [ ] **Step 3: Commit**

```bash
git add docs/research/sector_rotation_preregistration_2026-10-29.md
git commit -m "Pre-register sector rotation study before first run

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 2: Sector index data

**Files:**
- Modify: `sbc/market_store.py` (add to `RESEARCH_SYMBOLS` near line 49)
- Test: `tests/test_market_store.py`

**Interfaces:**
- Consumes: `market_store.refresh_daily(symbol, full=False, now=None, fetch=None) -> {"symbol", "stored"}`
- Produces: `SECTOR_SYMBOLS: dict[str, str]` mapping our symbol key (e.g. `"CNXIT"`) to yfinance ticker (e.g. `"^CNXIT"`), for the 15 sectors in the spec

**Acceptance Criteria:**
- All 15 sector symbols are registered with a yfinance ticker and an earliest date.
- `refresh_daily` with an injected fake `fetch` stores rows for each sector.
- Sector history start dates are recorded so the report can flag short histories.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_market_store.py
from sbc import market_store as ms

def test_sector_symbols_cover_the_fifteen_nse_indices():
    assert len(ms.SECTOR_SYMBOLS) == 15
    assert all(t.startswith("^CNX") for t in ms.SECTOR_SYMBOLS.values())

def test_refresh_stores_sector_rows_from_injected_fetch(tmp_db):
    fake = lambda ticker, start, end: [
        {"date": "2024-01-02", "open": 1, "high": 1, "low": 1, "close": 100.0, "volume": 0}]
    key = "CNXIT"
    out = ms.refresh_daily(key, full=True, fetch=fake)
    assert out["stored"] == 1
```

`tmp_db` is the existing market.db fixture pattern in `tests/test_market_store.py`. Reuse it; do not invent a new one.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_market_store.py -k sector -v`
Expected: FAIL with `AttributeError: module 'sbc.market_store' has no attribute 'SECTOR_SYMBOLS'`

- [ ] **Step 3: Write minimal implementation**

In `sbc/market_store.py`, add next to `RESEARCH_SYMBOLS`. Confirm the earliest-date convention against the existing entries before filling in values.

```python
SECTOR_SYMBOLS = {
    "CNXBANK": "^NSEBANK", "CNXFIN": "^CNXFIN", "CNXIT": "^CNXIT", "CNXPHARMA": "^CNXPHARMA",
    "CNXAUTO": "^CNXAUTO", "CNXFMCG": "^CNXFMCG", "CNXMETAL": "^CNXMETAL",
    "CNXENERGY": "^CNXENERGY", "CNXREALTY": "^CNXREALTY", "CNXMEDIA": "^CNXMEDIA",
    "CNXPSUBANK": "^CNXPSUBANK", "CNXINFRA": "^CNXINFRA", "CNXCONSUM": "^CNXCONSUM",
    "CNXHEALTH": "^CNXHEALTH", "CNXOILGAS": "^CNXOILGAS",
}
RESEARCH_SYMBOLS.update({k: (t, "2005-01-01") for k, t in SECTOR_SYMBOLS.items()})
```

The `^CNXCONSUM`, `^CNXHEALTH`, `^CNXOILGAS` tickers are unverified. Step 4 must confirm them.

- [ ] **Step 4: Verify tickers against yfinance**

Run: `python -c "import yfinance as yf; [print(t, len(yf.download(t, start='2020-01-01', progress=False))) for t in ['^CNXIT','^CNXCONSUM','^CNXHEALTH','^CNXOILGAS','^CNXMEDIA']]"`
Expected: a nonzero row count per ticker. Any zero-row ticker must be fixed or documented as unavailable before Task 6. Record first and last date per sector for the report.
Restriction (stress-test branch 8): this check reads row counts and first/last dates only. Do not print or summarise returns, prices, or statistics. Record the date of each pull in the pre-registration.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_market_store.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add sbc/market_store.py tests/test_market_store.py
git commit -m "Register 15 NSE sector indices for sector rotation study

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 3: Event anchors and clustering

**Files:**
- Create: `sbc/sector_rotation.py`
- Test: `tests/test_sector_rotation.py`

**Interfaces:**
- Consumes: `sbc.stations.by_date(start, end, bodies)` returns `{date: [{"planet", "direction", "date", ...}]}`; `sbc.transit_almanac.build(year, "sidereal")["bodies"]` where each body's `events` is a list of `{"date", "type": "station"|"ingress"|"eclipse", "body"?, ...}`. Eclipse events carry the eclipse kind in a field to be confirmed in Step 1.
- Produces:
  - `core_events(first_year: int, last_year: int) -> list[Event]`, where `Event = {"date": str, "event": str, "anchor": str|None}`. `event` is one of `MERCURY_STATION_START`, `MERCURY_STATION_END`, `SOLAR_ECLIPSE`, `LUNAR_ECLIPSE`, `JUPITER_INGRESS`, `SATURN_INGRESS`.
  - `anchor_session(sessions: list[str], day: str) -> int | None` returns the index of the first session on or after `day`.
  - `cluster(anchors: list[int], gap: int = 20) -> list[list[int]]` merges anchors closer than `gap` sessions.

**Acceptance Criteria:**
- One Mercury event per retrograde window, anchored at the retrograde start; the direct (end) station is metadata, not a separate event.
- Weekend and holiday event dates anchor to the next session.
- Anchors within 20 sessions form one cluster.
- Eclipses are split into solar and lunar.

- [ ] **Step 1: Confirm the eclipse and station field names**

Run: `python -c "from sbc import transit_almanac as ta; b=ta.build(2024,'sidereal')['bodies']; print({e['type'] for body in b for e in body['events']}); print([e for body in b for e in body['events'] if e['type']=='eclipse'][:2])"`
Expected: event types include `eclipse`, and eclipse rows show whether they are solar or lunar. If the kind is not in the row, read `sbc/transit_almanac.py` lines 155-175 and use the `Solar`/`Lunar` label that the code sets. Update the field name in Step 3 to match.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_sector_rotation.py
from sbc import sector_rotation as sr

SESSIONS = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-08"]  # 2024-01-06/07 weekend

def test_anchor_moves_weekend_to_next_session():
    assert sr.anchor_session(SESSIONS, "2024-01-06") == 3

def test_anchor_none_after_last_session():
    assert sr.anchor_session(SESSIONS, "2025-01-01") is None

def test_cluster_merges_within_gap():
    assert sr.cluster([0, 5, 30, 60], gap=20) == [[0, 5], [30], [60]]
    assert sr.cluster([0, 19], gap=20) == [[0, 19]]
    assert sr.cluster([0, 20], gap=20) == [[0], [20]]

def test_mercury_only_retrograde_start_and_end_are_kept():
    # Station rows follow sbc.stations.by_date: a "retrograde" station starts a
    # retrograde window, a "direct" station ends it. Other planets are ignored.
    rows = [{"planet": "Mercury", "direction": "retrograde", "date": "2024-03-01"},
            {"planet": "Mercury", "direction": "direct", "date": "2024-03-25"},
            {"planet": "Venus", "direction": "retrograde", "date": "2024-04-01"}]
    kept = sr.mercury_events(rows)
    assert [(e["event"], e["date"]) for e in kept] == [
        ("MERCURY_RETROGRADE_START", "2024-03-01"),
    ]
    assert kept[0]["window_end"] == "2024-03-25"
```

Replace the last test body before running it. Mercury retrograde start is the `retrograde` station and retrograde end is the `direct` station. Name the events so retrograde start is `MERCURY_RETROGRADE_START` and retrograde end is `MERCURY_RETROGRADE_END`. The test should assert that a `direct` station that begins a retrograde window is not counted as a start. Write this test concretely in Step 2 against the real row format from `stations.by_date`, not with the placeholder above.

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_sector_rotation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sbc.sector_rotation'`

- [ ] **Step 4: Write minimal implementation**

```python
# sbc/sector_rotation.py
"""Sector rotation around the core four planetary events (phase 1).

Pure functions only. Anchors and clusters are computed here; grading lives in Task 5.
"""
from __future__ import annotations

import bisect

CLUSTER_GAP = 20  # sessions; events closer than this merge into one cluster


def anchor_session(sessions: list[str], day: str) -> int | None:
    """Index of the first session on or after `day`, or None if past the last session."""
    i = bisect.bisect_left(sessions, day)
    return i if i < len(sessions) else None


def cluster(anchors: list[int], gap: int = CLUSTER_GAP) -> list[list[int]]:
    """Group sorted anchor indices so that consecutive members are < gap sessions apart."""
    out: list[list[int]] = []
    for a in sorted(anchors):
        if out and a - out[-1][-1] < gap:
            out[-1].append(a)
        else:
            out.append([a])
    return out
```

Add `mercury_events` and `core_events` once the Step 1 field names are confirmed. Keep each function under the field-name contract confirmed in Step 1.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_sector_rotation.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add sbc/sector_rotation.py tests/test_sector_rotation.py
git commit -m "Add sector rotation event anchors and clustering

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 4: Returns, ranks, relative strength

**Files:**
- Modify: `sbc/sector_rotation.py`
- Test: `tests/test_sector_rotation.py`

**Interfaces:**
- Consumes: `closes: dict[str, np.ndarray]` aligned to NIFTY sessions (NaN where missing); `anchor: int`; `h: int`
- Produces:
  - `window_return(closes: np.ndarray, anchor: int, h: int) -> float` = close[anchor+h]/close[anchor] - 1, NaN if out of range or missing.
  - `rank_sectors(returns: dict[str, float]) -> list[tuple[str, float]]` sorted descending, NaN sectors excluded and counted in the caller.
  - `relative_strength(sector_ret: float, nifty_ret: float) -> float`

**Acceptance Criteria:**
- Known-answer arithmetic on a synthetic series.
- NaN and out-of-range windows return NaN, never zero.
- Ranks exclude NaN sectors.

- [ ] **Step 1: Write the failing test**

```python
import numpy as np
import pytest
from sbc import sector_rotation as sr

def test_window_return_known_answer():
    c = np.array([100.0, 101.0, 102.0, 110.0])
    assert sr.window_return(c, anchor=0, h=3) == pytest.approx(0.10)

def test_window_return_out_of_range_is_nan():
    c = np.array([100.0, 101.0])
    assert np.isnan(sr.window_return(c, anchor=1, h=5))

def test_window_return_missing_bar_is_nan():
    c = np.array([100.0, np.nan, 102.0])
    assert np.isnan(sr.window_return(c, anchor=0, h=1))  # end bar missing
    assert sr.window_return(c, anchor=0, h=2) == pytest.approx(0.02)  # end bar present

def test_rank_excludes_nan_and_orders_descending():
    r = {"IT": 0.062, "PHARMA": 0.054, "AUTO": float("nan"), "BANK": 0.035}
    assert [s for s, _ in sr.rank_sectors(r)] == ["IT", "PHARMA", "BANK"]

def test_relative_strength_is_difference():
    assert sr.relative_strength(0.072, 0.023) == pytest.approx(0.049)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sector_rotation.py -k "window or rank or relative" -v`
Expected: FAIL with `AttributeError: module 'sbc.sector_rotation' has no attribute 'window_return'`

- [ ] **Step 3: Write minimal implementation**

```python
import numpy as np

def window_return(closes: np.ndarray, anchor: int, h: int) -> float:
    end = anchor + h
    if anchor < 0 or end >= len(closes):
        return float("nan")
    c0, c1 = closes[anchor], closes[end]
    if not (np.isfinite(c0) and np.isfinite(c1)) or c0 <= 0:
        return float("nan")
    return float(c1 / c0 - 1.0)

def rank_sectors(returns: dict[str, float]) -> list[tuple[str, float]]:
    valid = [(s, r) for s, r in returns.items() if np.isfinite(r)]
    return sorted(valid, key=lambda kv: kv[1], reverse=True)

def relative_strength(sector_ret: float, nifty_ret: float) -> float:
    return sector_ret - nifty_ret
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_sector_rotation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sbc/sector_rotation.py tests/test_sector_rotation.py
git commit -m "Add sector window returns, ranks and relative strength

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 5: Grading (confirmatory and descriptive)

**Files:**
- Modify: `sbc/sector_rotation.py`
- Test: `tests/test_sector_rotation.py`

**Interfaces:**
- Consumes: `sbc.stats.evaluate_directional(signal, fwd, n_perm, seed, min_n) -> dict` (keys include `status`, `n`, `excess`, `p`, and the era fields); `sbc.stats.bh_adjust(pvalues) -> list[float]`; `sbc.rule_validation` incremental control helper used by B-58 (locate it in Step 1).
- Produces:
  - `CONFIRMATORY: list[dict]` = the list from the pre-registration in Task 1, exactly. Each entry `{"id", "event", "sector", "h", "direction"}`.
  - `grade_confirmatory(hypotheses, signals_by_id, fwd_by_h, era_mask) -> list[dict]` returns per-hypothesis `{id, status, q, passed}`.
  - `descriptive_summary(rows) -> dict` returns rank counts, appearance rate, beat-NIFTY share, and occurrence counts (raw and cluster). Never carries `q` or `passed`.

**Acceptance Criteria:**
- `CONFIRMATORY` matches the pre-registration row for row (a test compares them).
- A hypothesis passes only if q < 0.05 after BH across the confirmatory family, same direction in both eras, and the incremental test q < 0.05.
- Descriptive output has no `q`, `p`, or `passed` keys.
- Sectors below `MIN_SIGNAL_DAYS` return `insufficient`.

- [ ] **Step 1: Locate the incremental control helper**

Run: `grep -n "incremental" sbc/rule_validation.py sbc/swing_validation.py | head`
Expected: a function name and signature used by `transit_event_validation.py`. Use that same function. Do not write a new one.

- [ ] **Step 2: Write the failing tests**

```python
from sbc import sector_rotation as sr

def test_confirmatory_list_matches_preregistration():
    # Expected rows are copied from docs/research/sector_rotation_preregistration_2026-10-29.md
    import re, pathlib
    doc = pathlib.Path("docs/research/sector_rotation_preregistration_2026-10-29.md").read_text(encoding="utf-8")
    if "Confirmatory list: empty" in doc:
        assert sr.CONFIRMATORY == []
    else:
        ids = re.findall(r"^\| (\S+) \|", doc, flags=re.M)
        assert [h["id"] for h in sr.CONFIRMATORY] == [i for i in ids if i != "ID"]

def test_descriptive_summary_has_no_pass_fields():
    rows = [{"sector": "IT", "event": "SOLAR_ECLIPSE", "h": 5, "ret": 0.01, "nifty": 0.0,
             "cluster": 0, "rank": 1}]
    out = sr.descriptive_summary(rows)
    assert not ({"q", "p", "passed"} & set(out))

def test_insufficient_below_minimum_signal_days():
    import numpy as np
    res = sr.grade_confirmatory(
        [{"id": "T1", "event": "X", "sector": "IT", "h": 5, "direction": 1}],
        signals_by_id={"T1": np.array([1.0, 0.0, 1.0])},
        fwd_by_h={5: np.array([0.01, 0.02, -0.01])},
        era_mask=np.array([True, True, True]),
    )
    assert res[0]["status"] == "insufficient"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_sector_rotation.py -k "confirmatory or descriptive or insufficient" -v`
Expected: FAIL with `AttributeError` on `CONFIRMATORY` / `grade_confirmatory` / `descriptive_summary`

- [ ] **Step 4: Write minimal implementation**

Populate `CONFIRMATORY` from the Task 1 pre-registration (copy the rows; if empty, `CONFIRMATORY: list[dict] = []`). Then implement:

```python
from sbc import stats as st

CONFIRMATORY: list[dict] = []  # copied verbatim from the pre-registration, Task 1
Q_THRESHOLD = 0.05

def grade_confirmatory(hypotheses, signals_by_id, fwd_by_h, era_mask):
    raw = []
    for hyp in hypotheses:
        sig = signals_by_id[hyp["id"]]
        fwd = fwd_by_h[hyp["h"]]
        res = st.evaluate_directional(sig * hyp["direction"], fwd)
        raw.append({"id": hyp["id"], **res})
    ok = [r for r in raw if r.get("status") == "ok"]
    qs = st.bh_adjust([r["p"] for r in ok]) if ok else []
    q_by_id = {r["id"]: q for r, q in zip(ok, qs)}
    out = []
    for r in raw:
        q = q_by_id.get(r["id"])
        passed = bool(q is not None and q < Q_THRESHOLD)  # era and control checks added in Step 5
        out.append({**r, "q": q, "passed": passed})
    return out

def descriptive_summary(rows):
    n_raw = len(rows)
    clusters = {(r["event"], r["cluster"]) for r in rows}
    ranks = [r["rank"] for r in rows if r.get("rank") is not None]
    top5 = sum(1 for k in ranks if k <= 5)
    beat = sum(1 for r in rows if r["ret"] - r["nifty"] > 0)
    return {"n_raw": n_raw, "n_clusters": len(clusters),
            "top5_rate": top5 / len(ranks) if ranks else None,
            "beat_rate": beat / n_raw if n_raw else None}
```

Confirm `evaluate_directional` returns `p` as the key name by reading `sbc/stats.py` lines 70-100 before relying on it. If the key differs, use the real name and update the test.

- [ ] **Step 5: Add the era and control checks**

Add a failing test that a hypothesis passing BH but with an opposite sign in the out-of-sample era is `passed=False`. Then add the era sign check and the incremental-control check from Step 1 to `grade_confirmatory`, so `passed` requires all three conditions. Verify the test fails before the change and passes after.

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_sector_rotation.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add sbc/sector_rotation.py tests/test_sector_rotation.py
git commit -m "Grade sector rotation confirmatory hypotheses out of sample

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 6: Forecast confidence and rotation labels

**Files:**
- Modify: `sbc/sector_rotation.py`
- Test: `tests/test_sector_rotation.py`

**Interfaces:**
- Consumes: `GROUPS: dict[str, str]` mapping sector key to `Defensive|Growth|Risk-On|Neutral` (from the pre-registration section 5); the grading output from Task 5.
- Produces:
  - `rotation_pattern(top5: list[str]) -> tuple[str, list[str]]` returns the label and the top-5 list it was derived from. Ties are `Mixed`.
  - `forecast_confidence(row: dict) -> str` returns `High` if passed confirmatory, `Medium` if descriptive-only pass, otherwise `No call`.

**Acceptance Criteria:**
- Label is `Mixed` on a tie between groups.
- Confidence follows the pre-registered rule exactly.
- The top-5 list is returned with every label.

- [ ] **Step 1: Write the failing tests**

```python
def test_rotation_pattern_majority():
    label, top5 = sr.rotation_pattern(["FMCG", "PHARMA", "HEALTH", "IT", "AUTO"])
    assert label == "Defensive" and top5 == ["FMCG", "PHARMA", "HEALTH", "IT", "AUTO"]

def test_rotation_pattern_tie_is_mixed():
    label, _ = sr.rotation_pattern(["FMCG", "IT"])
    assert label == "Mixed"

def test_confidence_no_call_by_default():
    assert sr.forecast_confidence({"passed": False}) == "No call"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_sector_rotation.py -k "rotation or confidence" -v`
Expected: FAIL with `AttributeError`

- [ ] **Step 3: Write minimal implementation**

```python
from collections import Counter

GROUPS = {
    "PHARMA": "Defensive", "FMCG": "Defensive", "HEALTH": "Defensive", "CONSUM": "Defensive",
    "IT": "Growth", "MEDIA": "Growth", "AUTO": "Growth",
    "BANK": "Risk-On", "FIN": "Risk-On", "REALTY": "Risk-On", "METAL": "Risk-On",
    "INFRA": "Risk-On", "PSUBANK": "Risk-On",
    "ENERGY": "Neutral", "OILGAS": "Neutral",
}

def rotation_pattern(top5: list[str]) -> tuple[str, list[str]]:
    counts = Counter(GROUPS[s] for s in top5 if s in GROUPS)
    if not counts:
        return "Mixed", top5
    (label, n), *rest = counts.most_common()
    if rest and rest[0][1] == n:
        return "Mixed", top5
    return label, top5

def forecast_confidence(row: dict) -> str:
    # Stress-test branch 2: no "Medium". Only a confirmatory pass earns a label.
    return "High" if row.get("passed") else "No call"
```

There is no "Medium" level (stress-test branch 2). Descriptive leads appear in the descriptive tables without a confidence label.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_sector_rotation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sbc/sector_rotation.py tests/test_sector_rotation.py
git commit -m "Add sector rotation pattern labels and forecast confidence

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 7: Report script and JSON

**Files:**
- Create: `scripts/sector_rotation_report.py`
- Create: `reports/sector_rotation_<YYYY-MM-DD>.md` and `.json` (generated, not hand-written)
- Test: `tests/test_sector_rotation.py`

**Interfaces:**
- Consumes: everything from Tasks 2-6; `market_store.get_daily(symbol, start, end) -> list[{"date","close",...}]`
- Produces: `build(n_perm: int = st.N_PERMUTATIONS, seed: int = 0) -> dict` returning the full result, plus the CLI `python scripts/sector_rotation_report.py`. The JSON schema: `{"generated", "preregistration", "era_boundary", "events": [...], "descriptive": {...}, "confirmatory": [...], "coverage": {sector: {first, last, sessions}}}`.

**Acceptance Criteria:**
- Report and JSON carry raw and cluster counts for every event and sector.
- Report states the confirmatory list (or "empty") and the pre-registration commit hash.
- Sectors below the minimum are `insufficient`, not ranked as findings.
- The run is reproducible: same seed, same JSON.
- The run fails if the pre-registration file is missing or uncommitted.

- [ ] **Step 1: Write the failing test**

```python
def test_build_is_reproducible_with_fixed_seed(frozen_fixture):
    # frozen_fixture: a synthetic market fixture checked into tests/fixtures/ (stress-test branch 7).
    # Never the live market.db, which changes daily.
    from scripts import sector_rotation_report as rep
    a = rep.build(n_perm=50, seed=0, source=frozen_fixture)
    b = rep.build(n_perm=50, seed=0, source=frozen_fixture)
    assert a == b

def test_build_refuses_without_preregistration(monkeypatch, tmp_path):
    from scripts import sector_rotation_report as rep
    monkeypatch.setattr(rep, "PREREG", tmp_path / "missing.md")
    import pytest
    with pytest.raises(FileNotFoundError):
        rep.build(n_perm=10)
```

If `scripts/` is not importable as a package in this repo, check how `tests/test_transit_event_validation.py` imports `scripts/validate_transit_events.py` and follow that exactly.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sector_rotation.py -k build -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

Implement `build` by calling Tasks 2-6 in order: load NIFTY and sector closes from `market_store.get_daily`, align them to NIFTY sessions, build core events, anchor and cluster, compute returns for each horizon, run `grade_confirmatory` over `CONFIRMATORY`, compute `descriptive_summary`, and assemble the result dict. Raise `FileNotFoundError` on a missing pre-registration. Write the `.md` and `.json` outputs with the date in the filename. Keep the function under the file-size limit used by sibling scripts; split helpers into `sbc/sector_rotation.py` if needed.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_sector_rotation.py -v`
Expected: PASS

- [ ] **Step 5: Generate the report**

Run: `python scripts/sector_rotation_report.py`
Expected: files written to `reports/` with the date. Read the Markdown and confirm the coverage table, raw/cluster counts, and the confirmatory status are present.

- [ ] **Step 6: Commit**

```bash
git add scripts/sector_rotation_report.py tests/test_sector_rotation.py reports/sector_rotation_*.md reports/sector_rotation_*.json
git commit -m "Add sector rotation report script and first run output

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 8: Read-only blueprint endpoints

**Files:**
- Create: `sbc/api/blueprints/sector_rotation_bp.py`
- Modify: `sbc/app_factory.py` (register the blueprint, following how `sectors_bp` is registered)
- Test: `tests/test_sector_rotation_api.py`

**Interfaces:**
- Consumes: the JSON written in Task 7 (`reports/sector_rotation_*.json`, newest by date)
- Produces: `GET /api/sector_rotation?event=<allow-list>&h=<5|10|20>`. Allow-list: events are the six `core_events` names plus `all`; `h` is `5|10|20`. Anything else returns 400.

**Acceptance Criteria:**
- Out-of-allow-list parameters return 400 and never reach a file path or SQL.
- The endpoint reads precomputed JSON only; it does not call `build`.
- No new public route outside `/api/sector_rotation`.
- Auth matches sibling blueprints (confirm in Step 1).

- [ ] **Step 0: Auth parity is blocking.** If the siblings require auth, add a test that asserts an unauthenticated request to `/api/sector_rotation` is rejected the same way. Task 8 does not close until that test passes.

- [ ] **Step 1: Confirm the sibling auth pattern**

Run: `grep -n "before_request\|login_required\|auth" sbc/api/blueprints/sectors_bp.py sbc/app_factory.py | head`
Expected: the pattern the sibling blueprints use. Apply the same pattern. Do not add an unauthenticated route if siblings are authenticated.

- [ ] **Step 2: Write the failing tests**

```python
def test_rejects_unknown_event(client):
    assert client.get("/api/sector_rotation?event=../../etc").status_code == 400

def test_rejects_unknown_horizon(client):
    assert client.get("/api/sector_rotation?h=7").status_code == 400

def test_serves_precomputed_json(client):
    r = client.get("/api/sector_rotation?event=all&h=5")
    assert r.status_code == 200 and "confirmatory" in r.get_json()
```

`client` is the existing Flask test client fixture used by `tests/test_api.py`. Reuse it.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_sector_rotation_api.py -v`
Expected: FAIL (404 on the new route)

- [ ] **Step 4: Write minimal implementation**

```python
# sbc/api/blueprints/sector_rotation_bp.py
import glob, json, os
from flask import Blueprint, abort, jsonify, request

sector_rotation_bp = Blueprint("sector_rotation", __name__)
EVENTS = {"MERCURY_RETROGRADE_START", "MERCURY_RETROGRADE_END", "SOLAR_ECLIPSE",
          "LUNAR_ECLIPSE", "JUPITER_INGRESS", "SATURN_INGRESS", "all"}
HORIZONS = {"5", "10", "20"}
REPORTS = os.path.join(os.path.dirname(__file__), "..", "..", "..", "reports")

@sector_rotation_bp.route("/api/sector_rotation")
def sector_rotation():
    event = request.args.get("event", "all")
    h = request.args.get("h", "5")
    if event not in EVENTS or h not in HORIZONS:
        abort(400)
    files = sorted(glob.glob(os.path.join(REPORTS, "sector_rotation_*.json")))
    if not files:
        abort(404)
    with open(files[-1], encoding="utf-8") as f:
        data = json.load(f)
    return jsonify({"event": event, "h": int(h), "data": data})
```

Register the blueprint in `sbc/app_factory.py` the same way `sectors_bp` is registered. Confirm the path resolves to the repo `reports/` folder (the `..` count depends on the file location; verify with a print in Step 5 before trusting it).

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_sector_rotation_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add sbc/api/blueprints/sector_rotation_bp.py sbc/app_factory.py tests/test_sector_rotation_api.py
git commit -m "Add read-only sector rotation API over precomputed JSON

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 9: Dashboard page

**Files:**
- Create: the page template or static file, following the existing UI pattern (locate in Step 1)
- Test: `tests/test_sector_rotation_api.py`

**Interfaces:**
- Consumes: `GET /api/sector_rotation` from Task 8
- Produces: the rendered heatmap (per the spec's colour scale), rotation matrix, event x sector grid, five-dimension radar per event, and the presentational rotation wheel and Sankey views.

**Acceptance Criteria:**
- All user-supplied and data-derived strings are HTML-escaped by the template engine. No `innerHTML` with data values.
- The radar chart labels its dimension count.
- Breadth does not appear anywhere on the page.
- Descriptive views carry raw and cluster counts. Confirmatory status is shown only where it was graded.
- The page renders without JavaScript errors and at phone width with no horizontal scroll.

- [ ] **Step 1: Locate the existing UI pattern**

Run: `grep -rln "monthly_heatmap\|sector_vedha" --include=*.html --include=*.js --include=*.jsx --include=*.tsx . | grep -v node_modules | head`
Expected: the file that renders the existing sector heatmap. Follow its structure, colour tokens and escaping approach.

- [ ] **Step 2: Write the failing browser test**

Use the Playwright tools to load the page and check for: no console errors, the heatmap rendered with the expected number of rows (15 sectors), a visible "5 dimensions" label on the radar, and no element containing "breadth".

Run the test and confirm it fails because the page does not exist yet.

- [ ] **Step 3: Implement the page**

Build the views from the Task 8 endpoint. For the heatmap, map relative strength to the colour scale in the spec (dark green strong outperformance through dark red strong underperformance). Set text with `textContent`, not `innerHTML`. Label each descriptive table "descriptive, not graded" and show counts beside every value.

- [ ] **Step 4: Run the browser test to verify it passes**

Run the Step 2 checks again. Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add <page files> tests/test_sector_rotation_api.py
git commit -m "Add sector rotation dashboard page

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 10: End-to-end verification

**Files:** none modified unless a check fails.

- [ ] **Step 1: Full test suite**

Run: `pytest tests -q`
Expected: all sector-rotation tests pass. Pre-existing failures in unrelated files (for example the modified `tests/test_natal.py` and `tests/test_route_pruning.py` in the working tree at session start) are reported as pre-existing, not as regressions. Confirm by running them on a clean checkout of `master` if needed.

- [ ] **Step 2: Confirm the pre-registration predates the run**

Run: `git log --format=%H%x20%s -- docs/research/sector_rotation_preregistration_2026-10-29.md` and `git log -1 --format=%H -- reports/sector_rotation_*.json`
Expected: the pre-registration commit is earlier than the first report commit. If not, the output is exploratory and must be labelled as such.

- [ ] **Step 3: Confirm the report states its limits**

Read the generated Markdown. Confirm it includes: the coverage table with short histories flagged, raw and cluster counts, the confirmatory status (or "empty"), the disclaimer that the leadership forecast is a historical pattern and not trading advice, and the statement that breadth is not computed.

- [ ] **Step 4: Report results honestly**

State the confirmatory outcome exactly as the report gives it. If no hypothesis passes, say so. Do not describe descriptive rankings as findings.

---

## Notes for the Executor

- Spec gap found during planning: the spec's grading omitted the incremental control test that the project's standing rule requires (Task 5). It is included here. Surface this change to the user at the plan review gate.
- Spec gap found during planning: prior out-of-sample sector-vedha results were 0 edge out of 67 findings, and B-58 is a separate prior test. The confirmatory list may therefore be empty (Task 1). That is a valid result and the plan does not assume otherwise.
### Stress Test Results: Sector Rotation Implementation Plan

#### Resolved Decisions
- Branch 1 (Mercury): one occurrence per retrograde window, anchored at start; end date is metadata.
- Branch 2 (confidence): "High" or "No call" only; "Medium" removed.
- Branch 3 (grader inputs): direction on anchor-window days; forward return = sector minus NIFTY.
- Branch 4 (empty confirmatory list): phase 1 may be descriptive; "no pre-registered edge" is valid.
- Branch 5 (sample size): floor of 8 independent out-of-sample clusters, plus 30 signal days.
- Branch 6 (security): auth parity is a blocking criterion for Task 8.
- Branch 7 (reproducibility): frozen fixture for the determinism test; reports record input dates and a data hash.
- Branch 8 (look-ahead): Task 2 check limited to counts and date range; pull dates recorded.
- Branch 9 (reflexion): coverage, depth and missed-angle pass run once; spec deviations recorded below.

#### Changes Made
- Global Constraints, Tasks 2, 3, 5 (clustering and grader notes), 6, 7 and 8 updated to match the resolutions above.

#### Deferred / Parking Lot
- Spec update: the spec still lists Mercury start and end as separate events and still has a "Medium" confidence level. Both must be brought in line with this plan before Task 1 commits the pre-registration.
- Pre-registration (Task 1) must state every rule above, including the 8-cluster floor and the grader inputs.
- Phase 2 (stocks and breadth) remains out of scope.

#### Confidence Assessment
- Overall: Medium. The statistical protocol is now explicit and bounded, but the sample is small and the confirmatory list may be empty.
- Areas of concern: few independent clusters out of sample (about 5 per event type before the floor is applied), so most hypotheses will come back "insufficient". This is an expected outcome, not a defect.

- `.internal/` is untracked in git and not ignored. The spec and this plan are not in version control. Decide whether to track them before Task 1 is committed.
- No beads were created because `bd` is not installed in this environment.
