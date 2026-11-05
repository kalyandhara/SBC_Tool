# Ashtakavarga Module, API and Research Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use beads-superpowers:subagent-driven-development (recommended) or beads-superpowers:executing-plans to implement this plan task-by-task. Each Task becomes a bead (`bd create -t task --parent <epic-id>`). Steps within tasks use checkbox (`- [ ]`) syntax for human readability.

**Goal:** Descriptive classical Ashtakavarga (BAV/SAV) for every anchor's natal chart, with transit lookups at 09:15 IST, served by `GET /api/ashtakavarga` and shown in a tab under "Research · unvalidated".

**Architecture:** A pure-function module `sbc/ashtakavarga.py` sits on top of `sbc.natal` and `sbc.planets.positions`. It computes live (microseconds), with no precomputed report. A thin, allow-listed Flask blueprint serves it. A vanilla-JS tab renders it with `textContent` only. One prerequisite bug fix in `sbc/engine.py` lets the bitcoin anchor build at all.

**Tech Stack:** Python 3.11+, pyswisseph (Lahiri, via `sbc.planets`), Flask blueprints, pytest, vanilla JS (no framework), plain CSS with existing tokens.

**Spec:** `.internal/specs/2026-10-31-ashtakavarga-design.md` (approved + stress-tested). Epic SBC_Tool-xro; tasks 1-7 = SBC_Tool-cah, s3c, ow8, sdc, 13w, ohb, bfl. Brainstorming bead SBC_Tool-h1z; stress-test bead SBC_Tool-a8y; prerequisite bug SBC_Tool-cah.

## Global Constraints

- Sidereal Lahiri, whole signs, sign index 0 = Aries, sign names from `sbc.nakshatra.RASHIS`: the same as `sbc.natal`.
- Descriptive only: no good/bad labels, scores or thresholds anywhere (module, API, UI).
- Transit time is **09:15 IST** on the requested date (`transit_natal.active_on` convention).
- The Lagna counts as reliable only for anchors in `LAGNA_RELIABLE = {"india": "exact official time, Indian place"}`. Every other anchor is unreliable by default.
- Contributors that change sign on an approximate anchor's birth day are **flagged, never dropped**.
- The ambiguity check must not call `natal.chart`/`natal.chart_detail` (keep natal's shared `lru_cache(64)` untouched).
- API: params `anchor`, `date`, `lagna_mode` only; any other key, value or format → `abort(400)`. Calculation failure → `sbc.api.errors.internal_error()` from inside `except` (generic JSON 500, no exception text). GET only.
- UI: no inline `<script>` or `on*=` handlers in `index.html`; all API data set via `textContent`/DOM nodes, never `innerHTML`.
- Run Python with `venv/Scripts/python.exe` (`-m pytest`).
- Git: this repo's CLAUDE.md is the **conservative profile**. The "Commit" steps below stage the files and propose the commit message; run `git commit` only if the user has authorized commits in the session. Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and cite the task's bead id.

## File Structure

| file | responsibility |
|---|---|
| `sbc/engine.py` (modify `_utc_from_local`) | accept `HH:MM[:SS]` |
| `sbc/ashtakavarga.py` (create) | tables, `bav`, `sav`, mode resolution, ambiguity, natal/chart/transit wrappers |
| `sbc/api/blueprints/ashtakavarga_bp.py` (create) | `GET /api/ashtakavarga`: validation + JSON shape |
| `sbc/app_factory.py` (modify `_blueprints`) | register the blueprint |
| `templates/index.html` (modify) | nav button, tab pane, script tag |
| `static/js/ashtakavarga.js` (create) | fetch + render the tab |
| `static/style.css` (modify, append) | `.av-*` rules |
| `tests/test_natal.py` (modify, append) | time-parser regression tests |
| `tests/test_ashtakavarga.py` (create) | module tests |
| `tests/test_ashtakavarga_api.py` (create) | endpoint tests |
| `tests/test_no_inline_js.py` (modify) | add `ashtakavarga` to the `node --check` list |

`tests/test_route_pruning.py` needs no change: the route has a UI caller (`static/js/ashtakavarga.js`), so it doesn't belong in `API_ONLY`. Task 5 temporarily adds it to `API_ONLY`; Task 6 removes it again.

---

### Task 1: Time parser accepts HH:MM:SS (bug SBC_Tool-cah)

**Files:**
- Modify: `sbc/engine.py:83-91` (`_utc_from_local`)
- Test: `tests/test_natal.py` (append)

**Interfaces:**
- Consumes: nothing new.
- Produces: `engine._utc_from_local(date_str: str, time_str: str, tz_name: str) -> datetime.datetime` (naive UTC) now accepts `"HH:MM"` or `"HH:MM:SS"`, and raises `ValueError` for anything else. `natal.chart("bitcoin")` works.

**Acceptance Criteria:**
- `_utc_from_local("2009-01-03", "18:15:05", "UTC") == datetime(2009, 1, 3, 18, 15, 5)`.
- `_utc_from_local("2026-10-30", "09:15", "Asia/Kolkata") == datetime(2026, 10, 30, 3, 45)` (unchanged behaviour).
- `"18"` and `"1:2:3:4"` raise `ValueError`.
- `natal.chart("bitcoin")` returns all 12 bodies.
- Full test suite still passes.

- [ ] **Step 0: Record the test baseline** (before any change)

Run: `venv/Scripts/python.exe -m pytest -q -p no:cacheprovider -rf 2>&1 | grep "^FAILED" > <scratchpad>/baseline-failures.txt`
Then: `bd note SBC_Tool-xro "pytest baseline before Task 1: <N> failures: <ids>"`.
Tasks 1 and 7 compare against this list. The working tree holds untracked in-progress files from other work, which may fail on their own.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_natal.py`)

```python
# ── SBC_Tool-cah: time parser accepts HH:MM:SS ─────────────────────────────

def test_utc_from_local_accepts_seconds():
    from sbc import engine
    assert engine._utc_from_local("2009-01-03", "18:15:05", "UTC") == \
        dt.datetime(2009, 1, 3, 18, 15, 5)


def test_utc_from_local_still_accepts_minutes():
    from sbc import engine
    assert engine._utc_from_local("2026-10-30", "09:15", "Asia/Kolkata") == \
        dt.datetime(2026, 10, 30, 3, 45)


@pytest.mark.parametrize("bad", ["18", "1:2:3:4"])
def test_utc_from_local_rejects_malformed(bad):
    from sbc import engine
    with pytest.raises(ValueError):
        engine._utc_from_local("2026-10-30", bad, "Asia/Kolkata")


def test_bitcoin_anchor_chart_builds():
    """The bitcoin anchor's time is 18:15:05; it used to raise 'invalid birth date/time'."""
    btc = natal.chart("bitcoin")
    assert {"Sun", "Moon", "Saturn"} <= set(btc)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_natal.py -k "utc_from_local or bitcoin" -v`
Expected: `test_utc_from_local_accepts_seconds`, `test_bitcoin_anchor_chart_builds` and the `"1:2:3:4"` case FAIL (too many values to unpack / invalid birth date/time). `"18"` already raises, so it may pass.

- [ ] **Step 3: Implement.** In `sbc/engine.py` replace the two lines

```python
    hh, mm = (int(x) for x in time_str.split(":"))
    local = datetime.datetime(y, m, d, hh, mm, tzinfo=tz)
```

with

```python
    parts = [int(x) for x in time_str.split(":")]
    if len(parts) not in (2, 3):
        raise ValueError(f"time must be HH:MM or HH:MM:SS, got {time_str!r}")
    hh, mm, ss = (parts + [0])[:3]
    local = datetime.datetime(y, m, d, hh, mm, ss, tzinfo=tz)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_natal.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full suite** (the parser is shared)

Run: `venv/Scripts/python.exe -m pytest -q`
Expected: no new failures compared with the baseline recorded before Task 1.

- [ ] **Step 6: Commit**

```bash
git add sbc/engine.py tests/test_natal.py
git commit -m "fix(engine): accept HH:MM:SS so the bitcoin anchor chart builds (SBC_Tool-cah)"
```

---

### Task 2: Ashtakavarga tables, BAV and SAV

**Files:**
- Create: `sbc/ashtakavarga.py`
- Test: `tests/test_ashtakavarga.py`

**Interfaces:**
- Consumes: nothing (pure).
- Produces:
  - `PLANETS: tuple[str, ...]` = `("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")`
  - `CONTRIBUTORS = PLANETS + ("Lagna",)`
  - `BENEFIC_PLACES: dict[str, dict[str, tuple[int, ...]]]`
  - `CLASSICAL_TOTALS: dict[str, int]`, `SAV_CLASSICAL_TOTAL = 337`
  - `bav(signs: dict[str, int], lagna_sign: int | None = None) -> dict[str, list[int]]`
  - `sav(bav_result: dict[str, list[int]]) -> list[int]`

**Acceptance Criteria:**
- Each planet's table sums to its classical total (48/49/39/54/56/52/39); a mismatch raises `RuntimeError` at import.
- All planets and the Lagna in Aries → the Sun's BAV equals the hand count `[3, 3, 3, 4, 2, 5, 4, 3, 5, 6, 7, 3]`; all in Taurus → the same row shifted by one sign.
- Classical SAV sums to 337 for any positions; 7-planet SAV sums to 292.
- For every planet and sign, classical − seven = the Lagna's contribution.
- Cells are 0..8 (classical) and 0..7 (seven).
- Bad input (missing planet, sign outside 0..11, bad Lagna) → `ValueError`.

- [ ] **Step 1: Write the failing tests** (`tests/test_ashtakavarga.py`)

```python
"""Ashtakavarga (spec .internal/specs/2026-10-31-ashtakavarga-design.md).

Sign pins (ambiguous contributors, the Raman fixture) were measured 2026-10-31
with Lahiri + Moshier via sbc.planets. A failure here after an ephemeris or
ayanamsa change is expected: re-measure and understand it, don't loosen the test.
"""

import pytest

from sbc import ashtakavarga as av

# Hand count, all planets and the Lagna in Aries: for each house 1-12, how many
# of the Sun's 8 contributor lists contain it (Sun/Mars/Saturn 1,2,4,7,8,9,10,11;
# Jupiter 5,6,9,11; Moon 3,6,10,11; Mercury 3,5,6,9,10,11,12; Lagna 3,4,6,10,11,12;
# Venus 6,7,12).
SUN_FROM_ARIES = [3, 3, 3, 4, 2, 5, 4, 3, 5, 6, 7, 3]
MIXED = {"Sun": 3, "Moon": 1, "Mars": 4, "Mercury": 4, "Jupiter": 7, "Venus": 4, "Saturn": 1}


def _all_in(sign):
    return {p: sign for p in av.PLANETS}


def test_tables_cover_every_planet_and_contributor():
    assert set(av.BENEFIC_PLACES) == set(av.PLANETS)
    for planet in av.PLANETS:
        assert set(av.BENEFIC_PLACES[planet]) == set(av.CONTRIBUTORS)
        for houses in av.BENEFIC_PLACES[planet].values():
            assert all(1 <= h <= 12 for h in houses)
            assert len(set(houses)) == len(houses)


@pytest.mark.parametrize("planet,total", [
    ("Sun", 48), ("Moon", 49), ("Mars", 39), ("Mercury", 54),
    ("Jupiter", 56), ("Venus", 52), ("Saturn", 39)])
def test_classical_totals(planet, total):
    assert sum(len(h) for h in av.BENEFIC_PLACES[planet].values()) == total


def test_sun_bav_all_in_aries_matches_hand_count():
    assert av.bav(_all_in(0), 0)["Sun"] == SUN_FROM_ARIES


def test_all_in_taurus_shifts_the_row_one_sign():
    assert av.bav(_all_in(1), 1)["Sun"] == SUN_FROM_ARIES[-1:] + SUN_FROM_ARIES[:-1]


def test_classical_sav_total_is_337():
    assert sum(av.sav(av.bav(MIXED, 10))) == av.SAV_CLASSICAL_TOTAL == 337


def test_seven_sav_total_is_292():
    # 337 minus the Lagna's 6+4+5+7+9+8+6 = 45 places
    assert sum(av.sav(av.bav(MIXED, None))) == 292


def test_classical_minus_seven_is_the_lagna_contribution():
    lagna = 10
    full, seven = av.bav(MIXED, lagna), av.bav(MIXED, None)
    for planet in av.PLANETS:
        lagna_row = [0] * 12
        for house in av.BENEFIC_PLACES[planet]["Lagna"]:
            lagna_row[(lagna + house - 1) % 12] += 1
        assert [a - b for a, b in zip(full[planet], seven[planet])] == lagna_row


def test_cell_bounds():
    for lagna, top in ((10, 8), (None, 7)):
        for row in av.bav(MIXED, lagna).values():
            assert len(row) == 12 and all(0 <= c <= top for c in row)


@pytest.mark.parametrize("signs,lagna", [
    ({p: 0 for p in av.PLANETS if p != "Moon"}, 0),
    ({**MIXED, "Sun": 12}, 0),
    (MIXED, -1),
])
def test_bav_rejects_bad_input(signs, lagna):
    with pytest.raises(ValueError):
        av.bav(signs, lagna)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_ashtakavarga.py -v`
Expected: collection error `ModuleNotFoundError: No module named 'sbc.ashtakavarga'`.

- [ ] **Step 3: Implement** `sbc/ashtakavarga.py`

```python
"""Ashtakavarga: Bhinnashtakavarga (BAV) and Sarvashtakavarga (SAV).

Classical BPHS benefic places, cross-checked against VedAstro's Ashtakavarga.cs
(docs/VEDASTRO_INGEST_2026-10-31.md). Sidereal Lahiri, whole signs, sign 0 =
Aries: the conventions of sbc.natal. Descriptive only: no scores or thresholds.

Two variants (spec .internal/specs/2026-10-31-ashtakavarga-design.md):

    classical   8 contributors (7 planets + Lagna), cells 0-8, SAV total 337
    seven       the 7 planets only, cells 0-7, SAV total 292; for anchors whose
                Lagna is unreliable (approximate time or no real birth place)
"""

from __future__ import annotations

PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
CONTRIBUTORS = PLANETS + ("Lagna",)

# BENEFIC_PLACES[planet][contributor]: houses counted from the contributor's sign
# (its own sign = 1) where the contributor gives the planet a bindu.
BENEFIC_PLACES: dict[str, dict[str, tuple[int, ...]]] = {
    "Sun": {
        "Sun": (1, 2, 4, 7, 8, 9, 10, 11), "Moon": (3, 6, 10, 11),
        "Mars": (1, 2, 4, 7, 8, 9, 10, 11), "Mercury": (3, 5, 6, 9, 10, 11, 12),
        "Jupiter": (5, 6, 9, 11), "Venus": (6, 7, 12),
        "Saturn": (1, 2, 4, 7, 8, 9, 10, 11), "Lagna": (3, 4, 6, 10, 11, 12),
    },
    "Moon": {
        "Sun": (3, 6, 7, 8, 10, 11), "Moon": (1, 3, 6, 7, 10, 11),
        "Mars": (2, 3, 5, 6, 9, 10, 11), "Mercury": (1, 3, 4, 5, 7, 8, 10, 11),
        "Jupiter": (1, 4, 7, 8, 10, 11, 12), "Venus": (3, 4, 5, 7, 9, 10, 11),
        "Saturn": (3, 5, 6, 11), "Lagna": (3, 6, 10, 11),
    },
    "Mars": {
        "Sun": (3, 5, 6, 10, 11), "Moon": (3, 6, 11),
        "Mars": (1, 2, 4, 7, 8, 10, 11), "Mercury": (3, 5, 6, 11),
        "Jupiter": (6, 10, 11, 12), "Venus": (6, 8, 11, 12),
        "Saturn": (1, 4, 7, 8, 9, 10, 11), "Lagna": (1, 3, 6, 10, 11),
    },
    "Mercury": {
        "Sun": (5, 6, 9, 11, 12), "Moon": (2, 4, 6, 8, 10, 11),
        "Mars": (1, 2, 4, 7, 8, 9, 10, 11), "Mercury": (1, 3, 5, 6, 9, 10, 11, 12),
        "Jupiter": (6, 8, 11, 12), "Venus": (1, 2, 3, 4, 5, 8, 9, 11),
        "Saturn": (1, 2, 4, 7, 8, 9, 10, 11), "Lagna": (1, 2, 4, 6, 8, 10, 11),
    },
    "Jupiter": {
        "Sun": (1, 2, 3, 4, 7, 8, 9, 10, 11), "Moon": (2, 5, 7, 9, 11),
        "Mars": (1, 2, 4, 7, 8, 10, 11), "Mercury": (1, 2, 4, 5, 6, 9, 10, 11),
        "Jupiter": (1, 2, 3, 4, 7, 8, 10, 11), "Venus": (2, 5, 6, 9, 10, 11),
        "Saturn": (3, 5, 6, 12), "Lagna": (1, 2, 4, 5, 6, 7, 9, 10, 11),
    },
    "Venus": {
        "Sun": (8, 11, 12), "Moon": (1, 2, 3, 4, 5, 8, 9, 11, 12),
        "Mars": (3, 5, 6, 9, 11, 12), "Mercury": (3, 5, 6, 9, 11),
        "Jupiter": (5, 8, 9, 10, 11), "Venus": (1, 2, 3, 4, 5, 8, 9, 10, 11),
        "Saturn": (3, 4, 5, 8, 9, 10, 11), "Lagna": (1, 2, 3, 4, 5, 8, 9, 11),
    },
    "Saturn": {
        "Sun": (1, 2, 4, 7, 8, 10, 11), "Moon": (3, 6, 11),
        "Mars": (3, 5, 6, 10, 11, 12), "Mercury": (6, 8, 9, 10, 11, 12),
        "Jupiter": (5, 6, 11, 12), "Venus": (6, 11, 12),
        "Saturn": (3, 5, 6, 11), "Lagna": (1, 3, 4, 6, 10, 11),
    },
}

CLASSICAL_TOTALS = {"Sun": 48, "Moon": 49, "Mars": 39, "Mercury": 54,
                    "Jupiter": 56, "Venus": 52, "Saturn": 39}
SAV_CLASSICAL_TOTAL = 337

for _planet, _total in CLASSICAL_TOTALS.items():
    if sum(len(h) for h in BENEFIC_PLACES[_planet].values()) != _total:
        raise RuntimeError(f"Ashtakavarga table for {_planet} does not sum to {_total}")


def _check_sign(name: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value < 12:
        raise ValueError(f"{name}: sign index 0-11 required, got {value!r}")


def bav(signs: dict[str, int], lagna_sign: int | None = None) -> dict[str, list[int]]:
    """{planet: 12 bindu counts} from each contributor's sign; no Lagna row if lagna_sign is None."""
    for planet in PLANETS:
        _check_sign(planet, signs.get(planet))
    origins = {p: signs[p] for p in PLANETS}
    if lagna_sign is not None:
        _check_sign("Lagna", lagna_sign)
        origins["Lagna"] = lagna_sign
    out = {}
    for planet in PLANETS:
        row = [0] * 12
        for contributor, start in origins.items():
            for house in BENEFIC_PLACES[planet][contributor]:
                row[(start + house - 1) % 12] += 1
        out[planet] = row
    return out


def sav(bav_result: dict[str, list[int]]) -> list[int]:
    """Sarvashtakavarga: the 7 BAV rows summed sign by sign."""
    return [sum(bav_result[p][s] for p in PLANETS) for s in range(12)]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_ashtakavarga.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add sbc/ashtakavarga.py tests/test_ashtakavarga.py
git commit -m "feat(ashtakavarga): classical BAV/SAV tables and pure bav/sav (SBC_Tool-s3c)"
```

---

### Task 3: Lagna reliability and contributors ambiguous on the birth day

**Files:**
- Modify: `sbc/ashtakavarga.py`
- Test: `tests/test_ashtakavarga.py` (append)

**Interfaces:**
- Consumes: `engine.ANCHORS`, `engine._utc_from_local` (Task 1 version), `engine._julday`, `planets.positions` (each planet dict has `"name"`, `"sign_index"`), `nakshatra.RASHIS`.
- Produces:
  - `MODES = ("auto", "classical", "seven")`
  - `LAGNA_RELIABLE: dict[str, str] = {"india": "exact official time, Indian place"}`
  - `resolve_mode(anchor: str, lagna_mode: str = "auto") -> tuple[str, bool, str]` returns `(mode, lagna_reliable, lagna_reason)`
  - `ambiguous_contributors(anchor: str) -> dict[str, list[str]]` returns `{planet: [sign at 00:00, sign at 23:59]}`
  - `_ambiguous` is an `lru_cache`d helper (tests call `.cache_clear()`).

**Acceptance Criteria:**
- `auto` resolves as follows:
  - `india` → `("classical", True, "exact official time, Indian place")`
  - `nifty`/`nse`/`bse`/`sensex`/`nyse` → `("seven", False, "birth time approximate")`
  - `bitcoin` → `("seven", False, "no birth place")`
- Every `ANCHORS` key resolves without error.
- Forced modes are honoured, and `lagna_reliable` still reports the truth.
- Unknown anchor or mode → `ValueError`.
- Ambiguous contributors:
  - nifty `{"Moon": ["Aquarius", "Pisces"]}`
  - nyse `{"Moon": ["Pisces", "Aries"]}`
  - nse `{"Mercury": ["Scorpio", "Libra"]}`
  - every other anchor `{}`
- `natal._planets.cache_info()` is unchanged by `ambiguous_contributors`.

- [ ] **Step 1: Write the failing tests** (append; move any new `import` lines to the top of the file with the existing imports)

```python
from sbc import natal
from sbc.engine import ANCHORS


@pytest.mark.parametrize("anchor,expected", [
    ("india", ("classical", True, "exact official time, Indian place")),
    ("nifty", ("seven", False, "birth time approximate")),
    ("nse", ("seven", False, "birth time approximate")),
    ("bse", ("seven", False, "birth time approximate")),
    ("sensex", ("seven", False, "birth time approximate")),
    ("nyse", ("seven", False, "birth time approximate")),
    ("bitcoin", ("seven", False, "no birth place")),
])
def test_auto_mode_per_anchor(anchor, expected):
    assert av.resolve_mode(anchor, "auto") == expected


def test_every_anchor_resolves():
    for anchor in ANCHORS:
        mode, reliable, reason = av.resolve_mode(anchor)
        assert mode in ("classical", "seven") and isinstance(reliable, bool) and reason


def test_forced_modes_are_honoured():
    assert av.resolve_mode("nifty", "classical")[:2] == ("classical", False)
    assert av.resolve_mode("india", "seven")[:2] == ("seven", True)


@pytest.mark.parametrize("anchor,mode", [("nope", "auto"), ("nifty", "both")])
def test_resolve_mode_rejects_unknown(anchor, mode):
    with pytest.raises(ValueError):
        av.resolve_mode(anchor, mode)


@pytest.mark.parametrize("anchor,expected", [
    ("nifty", {"Moon": ["Aquarius", "Pisces"]}),
    ("nyse", {"Moon": ["Pisces", "Aries"]}),
    ("nse", {"Mercury": ["Scorpio", "Libra"]}),
    ("bse", {}), ("sensex", {}), ("india", {}), ("bitcoin", {}),
])
def test_ambiguous_contributors(anchor, expected):
    assert av.ambiguous_contributors(anchor) == expected


def test_ambiguity_check_leaves_natal_cache_alone():
    av._ambiguous.cache_clear()
    before = natal._planets.cache_info()
    av.ambiguous_contributors("nifty")
    assert natal._planets.cache_info() == before


def test_ambiguous_contributors_rejects_unknown_anchor():
    with pytest.raises(ValueError):
        av.ambiguous_contributors("nope")
```

- [ ] **Step 2: Run them to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_ashtakavarga.py -v`
Expected: the new tests FAIL with `AttributeError: module 'sbc.ashtakavarga' has no attribute 'resolve_mode'` (or `ambiguous_contributors`).

- [ ] **Step 3: Implement.** Add to `sbc/ashtakavarga.py`: the imports go under `from __future__`, the code after `sav`.

```python
from functools import lru_cache

from sbc.engine import ANCHORS, _julday, _utc_from_local
from sbc.nakshatra import RASHIS
from sbc.planets import positions
```

```python
MODES = ("auto", "classical", "seven")

# A Lagna needs an exact time AND a real birth place: sbc.natal falls back to
# Mumbai for every anchor. Anything not listed is unreliable, so a new anchor
# fails safe.
LAGNA_RELIABLE = {"india": "exact official time, Indian place"}


def _check_anchor(anchor: str) -> None:
    if anchor not in ANCHORS:
        raise ValueError(f"unknown anchor: {anchor!r}")


def _time_approximate(anchor: str) -> bool:
    return "time approximate" in ANCHORS[anchor]["note"].lower()


def resolve_mode(anchor: str, lagna_mode: str = "auto") -> tuple[str, bool, str]:
    """(mode, lagna_reliable, lagna_reason); `auto` drops the Lagna when it is unreliable."""
    _check_anchor(anchor)
    if lagna_mode not in MODES:
        raise ValueError(f"lagna_mode must be one of {MODES}, got {lagna_mode!r}")
    if anchor in LAGNA_RELIABLE:
        reliable, reason = True, LAGNA_RELIABLE[anchor]
    elif _time_approximate(anchor):
        reliable, reason = False, "birth time approximate"
    else:
        reliable, reason = False, "no birth place"
    if lagna_mode == "auto":
        lagna_mode = "classical" if reliable else "seven"
    return lagna_mode, reliable, reason


@lru_cache(maxsize=None)
def _ambiguous(anchor: str) -> tuple[tuple[str, tuple[str, str]], ...]:
    # Two samples are enough: no contributor moves 30 degrees in a day, and a
    # retrograde planet cannot cross a sign boundary and come back within 24 h.
    # positions() directly, not natal.chart, so natal's shared cache is untouched.
    if not _time_approximate(anchor):
        return ()
    a = ANCHORS[anchor]

    def signs_at(hhmm: str) -> dict[str, int]:
        planets, _ayanamsa = positions(_julday(_utc_from_local(a["date"], hhmm, a["tz"])))
        return {p["name"]: p["sign_index"] for p in planets}

    start, end = signs_at("00:00"), signs_at("23:59")
    return tuple((p, (RASHIS[start[p]], RASHIS[end[p]]))
                 for p in PLANETS if start[p] != end[p])


def ambiguous_contributors(anchor: str) -> dict[str, list[str]]:
    """{planet: [sign at 00:00, sign at 23:59]} for planets changing sign on an approximate birth day."""
    _check_anchor(anchor)
    return {p: list(pair) for p, pair in _ambiguous(anchor)}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_ashtakavarga.py -v`
Expected: all PASS. If an ambiguity value differs, re-measure it before changing the test. The spec values were measured on 2026-10-31 with `natal.chart` at 00:00/23:59; a mismatch means a convention difference that needs to be understood, not a test to edit.

- [ ] **Step 5: Commit**

```bash
git add sbc/ashtakavarga.py tests/test_ashtakavarga.py
git commit -m "feat(ashtakavarga): Lagna reliability allow-list and birth-day sign ambiguity (SBC_Tool-ow8)"
```

---

### Task 4: Natal, hand-given chart and transit wrappers (Raman fixture)

**Files:**
- Modify: `sbc/ashtakavarga.py`
- Test: `tests/test_ashtakavarga.py` (append)

**Interfaces:**
- Consumes: Task 2 `bav`/`sav`, Task 3 `resolve_mode`/`ambiguous_contributors`, `natal.chart_detail(anchor_or_date, time=None, tz=None) -> list[dict]` (dicts have `name`, `sign_index`), `natal.lagna_longitude(anchor_or_date, time=None, tz=None, city=None) -> float`, `cities.resolve(name) -> dict | None`, `helio_aspects.IST` (tzinfo), `helio_aspects._jd(aware datetime) -> float`.
- Produces:
  - `TRANSIT_TIME = datetime.time(9, 15)`, `TRANSIT_TIME_LABEL = "09:15 IST"`
  - `natal_ashtakavarga(anchor: str, lagna_mode: str = "auto") -> dict` with keys `mode, lagna_reliable, lagna_reason, ambiguous_contributors, max_per_sign, bav, sav`
  - `chart_ashtakavarga(date: str, time: str, tz: str, city: str, lagna_mode: str = "classical") -> dict` with keys `mode, max_per_sign, bav, sav, planet_signs ({planet: sign name}), lagna_sign (name or None)`
  - `transit_scores(anchor: str, date: datetime.date, lagna_mode: str = "auto") -> dict` with keys `date (ISO str), transit_time ("09:15 IST"), natal (natal_ashtakavarga result), transit ({planet: {sign, sign_index, bav_points, sav_points}})`. Returning `natal` as well is a superset of the spec's per-planet dict, so the API doesn't compute it twice.

**Acceptance Criteria:**
- **Raman fixture:** for 1912-08-08 19:35 IST, Bengaluru, classical: Sun sign Cancer, Lagna Aquarius, Sun BAV in Cancer = 6. Plain asserts.
- `chart_ashtakavarga` rejects `lagna_mode="auto"` and an unknown city (`ValueError`), and never silently falls back to Mumbai.
- `natal_ashtakavarga("nifty")`: mode `seven`, `max_per_sign` 7, SAV sum 292, ambiguous Moon.
- Classical SAV sums to 337 for every anchor (the bitcoin anchor works thanks to Task 1).
- `transit_scores`:
  - planets are exactly the 7 (no Rahu/Ketu);
  - each planet's `bav_points`/`sav_points` equals the natal lookup at its `sign_index`;
  - each `sign` equals `RASHIS[sign_index]`;
  - `transit_time == "09:15 IST"`;
  - positions are computed at `_jd(datetime(date, 09:15, IST))`;
  - a non-date argument raises `TypeError`.

- [ ] **Step 1: Write the failing tests** (append; move any new `import` lines to the top of the file with the existing imports)

```python
import datetime as dt

from sbc.helio_aspects import IST, _jd
from sbc.nakshatra import RASHIS


def test_raman_sun_has_six_bindus_in_cancer():
    """B.V. Raman, Ashtakavarga System of Prediction p. 39 (cited in VedAstro's
    SunAshtakavargaYoga10Test): Sun in Cancer, 6th from Lagna, 6 bindus."""
    r = av.chart_ashtakavarga("1912-08-08", "19:35", "Asia/Kolkata", "Bengaluru", "classical")
    assert r["planet_signs"]["Sun"] == "Cancer"
    assert r["lagna_sign"] == "Aquarius"  # Cancer is the 6th sign from Aquarius
    assert r["bav"]["Sun"][RASHIS.index("Cancer")] == 6


@pytest.mark.parametrize("city,mode", [("Bengaluru", "auto"), ("Nowhere-ville", "classical")])
def test_chart_ashtakavarga_rejects_bad_input(city, mode):
    with pytest.raises(ValueError):
        av.chart_ashtakavarga("1912-08-08", "19:35", "Asia/Kolkata", city, mode)


def test_natal_nifty_is_seven_planet_with_ambiguous_moon():
    r = av.natal_ashtakavarga("nifty")
    assert (r["mode"], r["lagna_reliable"], r["max_per_sign"]) == ("seven", False, 7)
    assert r["lagna_reason"] == "birth time approximate"
    assert r["ambiguous_contributors"] == {"Moon": ["Aquarius", "Pisces"]}
    assert sum(r["sav"]) == 292 and set(r["bav"]) == set(av.PLANETS)


@pytest.mark.parametrize("anchor", sorted(ANCHORS))
def test_classical_sav_is_337_for_every_anchor(anchor):
    assert sum(av.natal_ashtakavarga(anchor, "classical")["sav"]) == 337


def test_transit_scores_are_natal_lookups():
    r = av.transit_scores("nifty", dt.date(2026, 10, 30))
    assert r["date"] == "2026-10-30" and r["transit_time"] == "09:15 IST"
    assert set(r["transit"]) == set(av.PLANETS)  # no Rahu, no Ketu
    for planet, t in r["transit"].items():
        assert t["sign"] == RASHIS[t["sign_index"]]
        assert t["bav_points"] == r["natal"]["bav"][planet][t["sign_index"]]
        assert t["sav_points"] == r["natal"]["sav"][t["sign_index"]]


def test_transit_is_computed_at_0915_ist(monkeypatch):
    calls = []
    real = av.positions

    def spy(jd):
        calls.append(jd)
        return real(jd)

    monkeypatch.setattr(av, "positions", spy)
    av.transit_scores("india", dt.date(2026, 10, 30))
    assert _jd(dt.datetime(2026, 10, 30, 9, 15, tzinfo=IST)) in calls


def test_transit_scores_rejects_non_date():
    with pytest.raises(TypeError):
        av.transit_scores("nifty", "2026-10-30")
```

- [ ] **Step 2: Run them to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_ashtakavarga.py -v`
Expected: the new tests FAIL with `AttributeError` (`chart_ashtakavarga` / `natal_ashtakavarga` / `transit_scores` missing).

- [ ] **Step 3: Implement.** Add the imports (`import datetime as dt`, `from sbc import cities, natal`, `from sbc.helio_aspects import IST, _jd`) and append:

```python
TRANSIT_TIME = dt.time(9, 15)  # NSE open, the transit_natal.active_on convention
TRANSIT_TIME_LABEL = "09:15 IST"


def _planet_signs(detail: list[dict]) -> dict[str, int]:
    return {p["name"]: p["sign_index"] for p in detail if p["name"] in PLANETS}


def _tables(signs: dict[str, int], lagna_sign: int | None) -> dict:
    rows = bav(signs, lagna_sign)
    return {"max_per_sign": 8 if lagna_sign is not None else 7, "bav": rows, "sav": sav(rows)}


def natal_ashtakavarga(anchor: str, lagna_mode: str = "auto") -> dict:
    """BAV/SAV for an anchor's natal chart, with how far its Lagna can be trusted."""
    mode, reliable, reason = resolve_mode(anchor, lagna_mode)
    signs = _planet_signs(natal.chart_detail(anchor))
    lagna = int(natal.lagna_longitude(anchor) // 30) if mode == "classical" else None
    return {"mode": mode, "lagna_reliable": reliable, "lagna_reason": reason,
            "ambiguous_contributors": ambiguous_contributors(anchor),
            **_tables(signs, lagna)}


def chart_ashtakavarga(date: str, time: str, tz: str, city: str,
                       lagna_mode: str = "classical") -> dict:
    """BAV/SAV for a hand-given birth moment (book fixtures); `auto` needs an anchor."""
    if lagna_mode not in ("classical", "seven"):
        raise ValueError("lagna_mode must be 'classical' or 'seven' for a hand-given chart")
    if cities.resolve(city) is None:
        raise ValueError(f"unknown city: {city!r}")
    signs = _planet_signs(natal.chart_detail(date, time, tz))
    lagna = int(natal.lagna_longitude(date, time, tz, city) // 30) \
        if lagna_mode == "classical" else None
    return {"mode": lagna_mode, **_tables(signs, lagna),
            "planet_signs": {p: RASHIS[s] for p, s in signs.items()},
            "lagna_sign": RASHIS[lagna] if lagna is not None else None}


def transit_scores(anchor: str, date: dt.date, lagna_mode: str = "auto") -> dict:
    """Natal BAV/SAV plus, for each of the 7 planets, the bindus of the sign it transits at 09:15 IST."""
    if not isinstance(date, dt.date):
        raise TypeError(f"date must be a datetime.date, got {type(date).__name__}")
    natal_av = natal_ashtakavarga(anchor, lagna_mode)
    planets, _ayanamsa = positions(_jd(dt.datetime.combine(date, TRANSIT_TIME, IST)))
    transit = {}
    for p in planets:
        if p["name"] in PLANETS:
            s = p["sign_index"]
            transit[p["name"]] = {"sign": RASHIS[s], "sign_index": s,
                                  "bav_points": natal_av["bav"][p["name"]][s],
                                  "sav_points": natal_av["sav"][s]}
    return {"date": date.isoformat(), "transit_time": TRANSIT_TIME_LABEL,
            "natal": natal_av, "transit": transit}
```

`dt.datetime` is a subclass of `dt.date`. A datetime passed in is combined by its date part, which is acceptable.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_ashtakavarga.py tests/test_natal.py -v`
Expected: all PASS. If the Raman test fails, stop: do not loosen it. Print the computed signs and report them. The spec recorded Lagna Aquarius 8.26° and Sun Cancer 22.98°.

- [ ] **Step 5: Commit**

```bash
git add sbc/ashtakavarga.py tests/test_ashtakavarga.py
git commit -m "feat(ashtakavarga): natal, chart and 09:15 IST transit wrappers with Raman fixture (SBC_Tool-sdc)"
```

---

### Task 5: `GET /api/ashtakavarga`

**Files:**
- Create: `sbc/api/blueprints/ashtakavarga_bp.py`
- Modify: `sbc/app_factory.py` (`_blueprints`: import + list entry)
- Modify: `tests/test_route_pruning.py` (temporary `API_ONLY` entry, removed in Task 6)
- Test: `tests/test_ashtakavarga_api.py`

**Interfaces:**
- Consumes: `av.transit_scores`, `av.MODES`, `engine.ANCHORS`, `helio_aspects.IST`, `nakshatra.RASHIS`, `sbc.api.errors.internal_error`.
- Produces: `GET /api/ashtakavarga?anchor=&date=&lagna_mode=` → 200 JSON with keys `anchor, anchor_name, anchor_note, anchors, date, transit_time, mode, lagna_reliable, lagna_reason, ambiguous_contributors, status ("experimental"), signs (12 names), natal {max_per_sign, bav, sav}, transit`. Task 6's JS reads exactly these keys.

**Acceptance Criteria:**
- The default request returns 200 for `nifty`/`seven`/`experimental`/`09:15 IST`, with 12 signs and 7 BAV rows.
- `anchor=india&date=2026-10-30&lagna_mode=classical` returns `mode=classical`, `lagna_reliable=true`, `max_per_sign=8`, `date=2026-10-30`.
- 400 for: an unknown or wrong-case anchor, a path-like anchor, a bad date, a date outside 1900-01-01..2100-12-31, a non-`YYYY-MM-DD` date, a bad mode, any unknown param.
- POST is not 200.
- A calculation exception returns 500 with a generic body that doesn't contain the exception text.

- [ ] **Step 1: Write the failing tests** (`tests/test_ashtakavarga_api.py`)

```python
"""Ashtakavarga endpoint: allow-listed params, live computation, generic errors."""

import pytest

from sbc import ashtakavarga as av

PLANETS = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}


def test_default_request(client):
    r = client.get("/api/ashtakavarga")
    assert r.status_code == 200
    body = r.get_json()
    assert (body["anchor"], body["mode"], body["status"]) == ("nifty", "seven", "experimental")
    assert body["transit_time"] == "09:15 IST" and body["lagna_reliable"] is False
    assert body["lagna_reason"] == "birth time approximate"
    assert body["ambiguous_contributors"] == {"Moon": ["Aquarius", "Pisces"]}
    assert len(body["signs"]) == 12 and "nifty" in body["anchors"]
    assert set(body["natal"]["bav"]) == PLANETS and len(body["natal"]["sav"]) == 12
    assert set(body["transit"]) == PLANETS


def test_explicit_params(client):
    r = client.get("/api/ashtakavarga?anchor=india&date=2026-10-30&lagna_mode=classical")
    assert r.status_code == 200
    body = r.get_json()
    assert (body["mode"], body["lagna_reliable"], body["date"]) == ("classical", True, "2026-10-30")
    assert body["natal"]["max_per_sign"] == 8 and sum(body["natal"]["sav"]) == 337


@pytest.mark.parametrize("qs", [
    "anchor=../../etc", "anchor=NIFTY", "anchor=", "date=2026-13-01", "date=1899-12-31",
    "date=2101-01-01", "date=20261030", "date=2026-10-30T09:15", "lagna_mode=both",
    "foo=1",
])
def test_rejects_bad_params(client, qs):
    assert client.get(f"/api/ashtakavarga?{qs}").status_code == 400


def test_post_is_not_served(client):
    assert client.post("/api/ashtakavarga").status_code != 200


def test_calculation_failure_is_a_generic_500(client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("C:/secret/path leaked")
    monkeypatch.setattr(av, "transit_scores", boom)
    r = client.get("/api/ashtakavarga")
    assert r.status_code == 500
    assert "secret" not in r.get_data(as_text=True)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_ashtakavarga_api.py -v`
Expected: FAIL; the route returns 404.

- [ ] **Step 3: Implement** `sbc/api/blueprints/ashtakavarga_bp.py`

```python
"""Ashtakavarga blueprint: live, descriptive BAV/SAV for an anchor plus 09:15 IST transits.

Parameters are allow-listed (400 otherwise); nothing from the request reaches a path, SQL or a shell.
"""

import datetime as dt

from flask import Blueprint, abort, jsonify, request

from sbc import ashtakavarga as av
from sbc.api.errors import internal_error
from sbc.engine import ANCHORS
from sbc.helio_aspects import IST
from sbc.nakshatra import RASHIS

ashtakavarga_bp = Blueprint("ashtakavarga", __name__, url_prefix="")

PARAMS = {"anchor", "date", "lagna_mode"}
DATE_MIN, DATE_MAX = dt.date(1900, 1, 1), dt.date(2100, 12, 31)


def _date(raw: str | None) -> dt.date:
    if raw is None:
        return dt.datetime.now(IST).date()
    if len(raw) != 10:
        abort(400)
    try:
        day = dt.date.fromisoformat(raw)
    except ValueError:
        abort(400)
    if not DATE_MIN <= day <= DATE_MAX:
        abort(400)
    return day


@ashtakavarga_bp.route("/api/ashtakavarga")
def ashtakavarga():
    if set(request.args) - PARAMS:
        abort(400)
    anchor = request.args.get("anchor", "nifty")
    lagna_mode = request.args.get("lagna_mode", "auto")
    if anchor not in ANCHORS or lagna_mode not in av.MODES:
        abort(400)
    day = _date(request.args.get("date"))
    try:
        res = av.transit_scores(anchor, day, lagna_mode)
    except Exception:  # noqa: BLE001 - generic 500, traceback logged by internal_error
        return internal_error("ashtakavarga calculation failed")
    n = res["natal"]
    return jsonify({
        "anchor": anchor, "anchor_name": ANCHORS[anchor]["name"],
        "anchor_note": ANCHORS[anchor]["note"], "anchors": list(ANCHORS),
        "date": res["date"], "transit_time": res["transit_time"],
        "mode": n["mode"], "lagna_reliable": n["lagna_reliable"],
        "lagna_reason": n["lagna_reason"],
        "ambiguous_contributors": n["ambiguous_contributors"],
        "status": "experimental", "signs": list(RASHIS),
        "natal": {"max_per_sign": n["max_per_sign"], "bav": n["bav"], "sav": n["sav"]},
        "transit": res["transit"],
    })
```

In `sbc/app_factory.py` `_blueprints()`: add `from sbc.api.blueprints.ashtakavarga_bp import ashtakavarga_bp` (alphabetical, before `balance_bp`), and add `ashtakavarga_bp` to the returned list right after `sector_rotation_bp`.

In `tests/test_route_pruning.py`, add to `API_ONLY` (temporary; Task 6 removes it):

```python
    # Ashtakavarga tab lands in the next task (temporary).
    "/api/ashtakavarga",
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_ashtakavarga_api.py tests/test_route_pruning.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add sbc/api/blueprints/ashtakavarga_bp.py sbc/app_factory.py tests/test_ashtakavarga_api.py tests/test_route_pruning.py
git commit -m "feat(api): read-only GET /api/ashtakavarga with allow-listed params (SBC_Tool-13w)"
```

---

### Task 6: Ashtakavarga tab under "Research · unvalidated"

**Files:**
- Modify: `templates/index.html` (nav button in `.advanced-workspace-tabs` after the `tab-swing` button; pane after the closing `</div>` of `<div id="tab-rotation" ...>`; script tag after `sector-rotation.js`)
- Create: `static/js/ashtakavarga.js`
- Modify: `static/style.css` (append)
- Modify: `tests/test_no_inline_js.py` (add `"ashtakavarga"` to the `test_extracted_scripts_parse` list)
- Modify: `tests/test_route_pruning.py` (remove the temporary entry from Task 5)

**Interfaces:**
- Consumes: the Task 5 JSON keys; header date input `#date` (`YYYY-MM-DD`); the existing tab switcher in `static/app.js` (`.nav-tab[data-tab]` toggles `.tab-pane`).
- Produces: `#tab-ashtakavarga` pane with `#av-status` and `#av-root`.

**Acceptance Criteria:**
- The tab button appears inside the Research · unvalidated menu, and clicking it loads the view.
- Controls: anchor select, Lagna-mode select (auto/classical/7 planets) and transit date; each one reloads the view.
- The banner always says "Experimental · descriptive. No validated market edge.". It adds the Lagna-exclusion reason, and one line per ambiguous contributor.
- The grid has 7 planet rows plus a SAV row × 12 signs, a `/8` or `/7` header and transit cells outlined. The transit table is headed "as of 09:15 IST".
- No `innerHTML` in `ashtakavarga.js`; `node --check` passes; `test_no_inline_js.py` and `test_route_pruning.py` pass with the `API_ONLY` entry removed.
- Stale responses (the user changes controls quickly) are ignored.
- Changing the header session date (`#date`) updates the tab, unless the tab's own date picker has been used.

- [ ] **Step 1: Update the tests first**

In `tests/test_no_inline_js.py` change the parametrize list to:

```python
@pytest.mark.parametrize("name", ["birth-city", "profiles-habits", "trading-signals", "rahu-ketu-trap", "sector-rotation", "ashtakavarga"])
```

In `tests/test_route_pruning.py` delete the two lines added in Task 5 (the comment and `"/api/ashtakavarga",`).

Append to `tests/test_ashtakavarga_api.py`:

```python
def test_ashtakavarga_tab_is_wired():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    html = (root / "templates" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "js" / "ashtakavarga.js").read_text(encoding="utf-8")
    research = html.split('class="advanced-workspace-tabs"', 1)[1].split("</details>", 1)[0]
    assert 'data-tab="tab-ashtakavarga"' in research
    assert 'id="tab-ashtakavarga"' in html and 'src="/static/js/ashtakavarga.js' in html
    assert "innerHTML" not in js and "/api/ashtakavarga" in js
```

- [ ] **Step 2: Run them to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_no_inline_js.py tests/test_route_pruning.py tests/test_ashtakavarga_api.py -v`
Expected: FAIL. The script is missing, the route is an orphan, and the tab isn't wired.

- [ ] **Step 3: Add the markup** to `templates/index.html`

Nav button: insert after the `tab-swing` button, inside `.advanced-workspace-tabs`.

```html
          <button class="nav-tab" data-tab="tab-ashtakavarga" role="tab" aria-selected="false" aria-controls="tab-ashtakavarga">
            <span class="tab-icon" aria-hidden="true">🔢</span> Ashtakavarga
          </button>
```

Pane: insert after the closing `</div>` of `<div id="tab-rotation" class="tab-pane" role="tabpanel">`.

```html
    <div id="tab-ashtakavarga" class="tab-pane" role="tabpanel">
      <section class="panel">
        <div class="panel-head">
          <h2>Ashtakavarga</h2>
          <span class="panel-sub">Classical bindus (BAV per planet, SAV total) on an anchor's natal chart, with the signs the planets transit at 09:15 IST.</span>
        </div>
        <div id="av-status" class="nifty-chart-status" role="status" aria-live="polite"></div>
        <div id="av-root" class="av-root"></div>
      </section>
    </div>
```

Script: after `<script src="/static/js/sector-rotation.js?v=1"></script>`.

```html
  <script src="/static/js/ashtakavarga.js?v=1"></script>
```

- [ ] **Step 4: Create** `static/js/ashtakavarga.js`

```javascript
// Ashtakavarga tab (spec .internal/specs/2026-10-31-ashtakavarga-design.md). Live view of
// GET /api/ashtakavarga: an anchor's natal BAV/SAV and the signs the planets transit at
// 09:15 IST. Descriptive, not validated. Every data value is set with textContent, never innerHTML.

const AV_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"];
const AV_MODES = [["auto", "Auto"], ["classical", "Classical (with Lagna)"], ["seven", "7 planets (no Lagna)"]];
const AV_STATE = { anchor: "nifty", lagna_mode: "auto", date: "", dateTouched: false };
let AV_SEQ = 0;

function avEl(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "text") node.textContent = value;
    else if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) node.appendChild(child);
  return node;
}

function avSelect(label, options, value, onChange) {
  const select = avEl("select", { "aria-label": label });
  for (const [v, text] of options) {
    const opt = avEl("option", { value: v, text });
    if (v === value) opt.selected = true;
    select.appendChild(opt);
  }
  select.addEventListener("change", () => onChange(select.value));
  return avEl("label", {}, [avEl("span", { text: `${label} ` }), select]);
}

function avDateInput(value) {
  const input = avEl("input", { type: "date", min: "1900-01-01", max: "2100-12-31", "aria-label": "Transit date" });
  input.value = value;
  input.addEventListener("change", () => {
    if (input.value) { AV_STATE.date = input.value; AV_STATE.dateTouched = true; avLoad(); }
  });
  return avEl("label", {}, [avEl("span", { text: "Transit date " }), input]);
}

function avBanner(data) {
  const lines = [];
  if (data.mode === "seven") {
    lines.push(data.lagna_reliable ? "Lagna excluded by choice." : `Lagna excluded: ${data.lagna_reason}.`);
  } else if (!data.lagna_reliable) {
    lines.push(`Lagna included by choice, but it is unreliable: ${data.lagna_reason}.`);
  }
  for (const [planet, signs] of Object.entries(data.ambiguous_contributors)) {
    lines.push(`${planet} changes sign during the birth day (${signs.join("/")}); its points may be misplaced.`);
  }
  const box = avEl("div", { class: "analog-banner", role: "note" },
    [avEl("strong", { text: "Experimental · descriptive. No validated market edge." })]);
  for (const line of lines) box.appendChild(avEl("p", { text: line }));
  return box;
}

function avGrid(data) {
  const n = data.natal;
  const head = avEl("tr", {}, [avEl("th", { text: `Planet (/${n.max_per_sign})` })]);
  data.signs.forEach((s) => head.appendChild(avEl("th", { text: s.slice(0, 3), title: s })));
  const body = avEl("tbody");
  for (const p of AV_PLANETS) {
    const row = avEl("tr", {}, [avEl("th", { text: p })]);
    n.bav[p].forEach((v, i) => {
      const cell = avEl("td", { text: String(v) });
      if (data.transit[p] && data.transit[p].sign_index === i) {
        cell.classList.add("av-transit");
        cell.title = `${p} transits ${data.signs[i]}`;
      }
      row.appendChild(cell);
    });
    body.appendChild(row);
  }
  const hi = Math.max(...n.sav);
  const lo = Math.min(...n.sav);
  const savRow = avEl("tr", { class: "av-sav" }, [avEl("th", { text: "SAV" })]);
  for (const v of n.sav) {
    const cell = avEl("td", { text: String(v) });
    cell.style.setProperty("--av-heat", (hi === lo ? 0.5 : (v - lo) / (hi - lo)).toFixed(2));
    savRow.appendChild(cell);
  }
  body.appendChild(savRow);
  return avEl("table", { class: "data-table av-grid" }, [avEl("thead", {}, [head]), body]);
}

function avTransitTable(data) {
  const cols = ["Planet", "Sign", `BAV (/${data.natal.max_per_sign})`, "SAV"];
  const head = avEl("tr", {}, cols.map((t) => avEl("th", { text: t })));
  const body = avEl("tbody");
  for (const p of AV_PLANETS) {
    const t = data.transit[p];
    body.appendChild(avEl("tr", {}, [p, t.sign, String(t.bav_points), String(t.sav_points)]
      .map((x) => avEl("td", { text: x }))));
  }
  return avEl("div", {}, [
    avEl("h3", { text: `Transits on ${data.date}, as of ${data.transit_time}` }),
    avEl("table", { class: "data-table av-transit-table" }, [avEl("thead", {}, [head]), body]),
  ]);
}

function avRender(data) {
  document.getElementById("av-root").replaceChildren(
    avEl("div", { class: "av-controls" }, [
      avSelect("Anchor", data.anchors.map((a) => [a, a]), data.anchor, (v) => { AV_STATE.anchor = v; avLoad(); }),
      avSelect("Lagna", AV_MODES, AV_STATE.lagna_mode, (v) => { AV_STATE.lagna_mode = v; avLoad(); }),
      avDateInput(data.date),
    ]),
    avEl("p", { class: "panel-sub", text: `${data.anchor_name}: ${data.anchor_note}` }),
    avBanner(data),
    avGrid(data),
    avTransitTable(data),
  );
}

async function avLoad() {
  const status = document.getElementById("av-status");
  if (!AV_STATE.date) AV_STATE.date = document.getElementById("date")?.value || "";
  const params = new URLSearchParams({ anchor: AV_STATE.anchor, lagna_mode: AV_STATE.lagna_mode });
  if (AV_STATE.date) params.set("date", AV_STATE.date);
  const seq = ++AV_SEQ;
  status.textContent = "Loading…";
  try {
    const r = await fetch(`/api/ashtakavarga?${params}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    if (seq !== AV_SEQ) return; // a newer request superseded this one
    status.textContent = "";
    avRender(data);
  } catch (err) {
    if (seq === AV_SEQ) status.textContent = `Could not load Ashtakavarga (${err.message}).`;
  }
}

(function avInit() {
  document.querySelector('[data-tab="tab-ashtakavarga"]')?.addEventListener("click", avLoad);
  // Follow the header session date until the tab's own date picker is used.
  document.getElementById("date")?.addEventListener("change", (e) => {
    if (AV_STATE.dateTouched || !e.target.value) return;
    AV_STATE.date = e.target.value;
    if (document.getElementById("tab-ashtakavarga")?.classList.contains("active")) avLoad();
  });
  if (window.location.hash === "#tab-ashtakavarga") avLoad();
})();
```

- [ ] **Step 5: Append styles** to `static/style.css`

```css
/* Ashtakavarga tab */
.av-root { overflow-x: auto; }
.av-controls { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; font-size: 13px; }
.av-grid th, .av-grid td { text-align: center; }
.av-grid td.av-transit { outline: 2px solid var(--accent); outline-offset: -2px; font-weight: 700; }
.av-sav td { font-weight: 700; background: color-mix(in srgb, var(--green) calc(var(--av-heat, 0) * 45%), transparent); }
```

`element.style.setProperty` is CSSOM, which the app's CSP allows (only `style=""` attributes are blocked).

- [ ] **Step 6: Run the tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_no_inline_js.py tests/test_route_pruning.py tests/test_ashtakavarga_api.py -v`
Expected: all PASS (requires `node` on PATH, as the existing parse tests already do).

- [ ] **Step 7: Commit**

```bash
git add templates/index.html static/js/ashtakavarga.js static/style.css tests/test_no_inline_js.py tests/test_route_pruning.py tests/test_ashtakavarga_api.py
git commit -m "feat(ui): Ashtakavarga tab under Research · unvalidated (SBC_Tool-ohb)"
```

---

### Task 7: Full verification

**Files:** none changed unless a check fails (then fix in the owning task's files and re-run).

**Interfaces:** Consumes everything above.

**Acceptance Criteria:**
- `venv/Scripts/python.exe -m pytest -q`: no failures beyond the baseline recorded before Task 1 (report any pre-existing failures as such).
- Dev server (`.claude/launch.json` config `sbc`, port 8010) in the browser pane:
  - the tab opens from the Research · unvalidated menu;
  - nifty shows the 7-planet grid, the "/7" header, the "birth time approximate" banner and the Moon ambiguity line;
  - switching to `india` + Classical shows "/8" and SAV sum 337;
  - changing the date updates the transit table;
  - no console errors;
  - screenshot taken.

- [ ] **Step 1:** `venv/Scripts/python.exe -m pytest -q` and compare with the baseline.
- [ ] **Step 2:** `preview_start {name: "sbc"}`, open the menu, click Ashtakavarga, `read_page` and check the banner and grid text.
- [ ] **Step 3:** switch anchor to `india` and Lagna to Classical. Check `/8` and that the SAV row sums to 337 (javascript_tool: sum the `.av-sav td` texts).
- [ ] **Step 4:** change the header session date and check that the tab follows it. Then change the tab's own transit date and check that the heading changes, and that later header changes no longer override it.
- [ ] **Step 5:** `read_console_messages {onlyErrors: true}` should be empty; take a screenshot as proof.

---

## Spec coverage map

| spec item | task |
|---|---|
| §0 prerequisite time parser | 1 |
| §1 constants, `BENEFIC_PLACES`, totals guard | 2 |
| §1 `bav`, `sav` | 2 |
| §1 `LAGNA_RELIABLE`, `resolve_mode` | 3 |
| §1 `ambiguous_contributors` (2 samples, own cache) | 3 |
| §1 `natal_ashtakavarga`, `chart_ashtakavarga`, `transit_scores` (09:15 IST) | 4 |
| §2 endpoint, params, response, errors, registration, route pruning | 5 (+6 removes the temporary API_ONLY entry) |
| §3 tab, controls, banner, grid, transit table, styles, no-inline-JS | 6 |
| §4 tests (invariants, synthetic, Raman, modes, ambiguity, cache, transit, API) | 2-6 |
| §4 verification (pytest + browser) | 7 |
| Follow-ups (study, Kakshya, Mumbai fallback SBC_Tool-9zw) | out of scope, beads |

## Stress Test Results: Ashtakavarga plan

Stress-test bead: SBC_Tool-69m.

### Resolved Decisions
- Baseline: Task 1 Step 0 records the failing tests before any change; Tasks 1 and 7 compare against it.
- Header date: the tab follows `#date` until its own date picker is used.
- Ordering: the linear chain cah → s3c → ow8 → sdc → 13w → ohb → bfl is correct (each task consumes the previous interface). Resolved by evidence.
- Rollback: additive apart from the engine parser and the blueprint registration; one commit per task. Resolved by evidence.
- Security: same controls as the sibling endpoints; no regression.
- Test pins: exact signs kept, with a re-measure-don't-loosen comment.
- Tab restore: saved-tab restore clicks the button on DOMContentLoaded, after all sync scripts register listeners. Verified in `static/app.js:131`.

### Changes Made
- Task 1 Step 0 added; `tests/test_ashtakavarga.py` docstring note; JS `dateTouched` and the header-date listener; Task 6 acceptance line; Task 7 Step 4.

### Deferred / Parking Lot
- None new (spec follow-ups stand: transit study, Kakshya, SBC_Tool-9zw).

### Confidence Assessment
- Overall: High
- Areas of concern: the pytest baseline may show pre-existing failures from the untracked in-progress work.
