# Specification: Ashtakavarga Module, API and Research Tab

Brainstorming bead: SBC_Tool-h1z. Source survey: `docs/VEDASTRO_INGEST_2026-10-31.md`.

## Overview

SBC_Tool has no Ashtakavarga support. Add the classical (BPHS) Bhinnashtakavarga
(BAV) and Sarvashtakavarga (SAV) on any anchor's natal chart, a transit lookup
(bindus of the sign each transiting planet occupies on a date), a read-only
API, and a tab under "Research · unvalidated". Output is descriptive only: no
good/bad labels, scores or thresholds. A later pre-registered study will pick
its own cut-offs.

## Decisions (from brainstorming)

| topic | decision |
|---|---|
| scope | calculation + transit lookup + API + UI |
| Lagna | two variants: `classical` (8 contributors incl. Lagna) and `seven` (7 planets only). `auto` picks `seven` when the anchor's birth time is approximate |
| data flow | live pure functions, computed per request; no precomputed report |
| UI home | new tab inside the `advanced-workspaces` ("Research · unvalidated") menu |

Why the Lagna variant: every Indian anchor (`nse`, `bse`, `nifty`, `sensex`)
and `nyse` is stored at 00:00 with "time approximate". The Lagna changes sign
about every 2 hours, so its contribution (one of 8 rows in every BAV) is close
to arbitrary for those anchors.

## 1. Core module `sbc/ashtakavarga.py`

Pure functions, no I/O beyond `sbc.natal` / `sbc.planets`.

**Constants**

- `PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")`
- `CONTRIBUTORS = PLANETS + ("Lagna",)`
- `BENEFIC_PLACES: dict[str, dict[str, tuple[int, ...]]]`, `[planet][contributor]`
  -> houses 1-12 counted from the contributor's sign (contributor's sign = 1).
  Values from BPHS, cross-checked against VedAstro `Ashtakavarga.cs`
  `PlanetBeneficAshtakaHouse`.
- `CLASSICAL_TOTALS = {"Sun": 48, "Moon": 49, "Mars": 39, "Mercury": 54,
  "Jupiter": 56, "Venus": 52, "Saturn": 39}`; SAV classical total 337.
  An import-time assertion checks that each planet's table sums to its total.

**Functions**

- `bav(signs: dict[str, int], lagna_sign: int | None) -> dict[str, list[int]]`
  `signs` maps each of the 7 planets to its sidereal sign index 0-11 (0 = Aries).
  For each planet P and each contributor C, add 1 to sign
  `(sign_of_C + house - 1) % 12` for every `house` in `BENEFIC_PLACES[P][C]`.
  `lagna_sign=None` skips the Lagna contributor. Returns 12 ints per planet.
  Raises `ValueError` if a planet is missing or a sign is outside 0-11.
- `sav(bav_result) -> list[int]` sums the 7 rows sign by sign.
- `LAGNA_RELIABLE: dict[str, tuple[str, str]] = {"india": ("exact official time, Indian place", "New Delhi")}`
  An explicit allow-list of (reason, birth city). A Lagna needs both an exact
  time and a real birth place (`natal.lagna_longitude` falls back to Mumbai for
  every anchor). The city matters: for 1947-08-15 00:00 IST, Mumbai gives Lagna
  28.54° (Aries) and New Delhi gives 37.74° (Taurus, the conventional
  Independence chart). User decision 2026-10-31, from the Task 4 review: New Delhi, pinned
  by a test. Every
  other anchor is unreliable by default, so a new anchor fails safe.
- `resolve_mode(anchor: str, lagna_mode: str) -> tuple[str, bool, str]`
  returns `(mode, lagna_reliable, lagna_reason)`. Reliable iff `anchor in
  LAGNA_RELIABLE`. Otherwise the reason is "birth time approximate" when the
  anchor's note contains "time approximate" (case-insensitive), else "no birth
  place" (e.g. `bitcoin`). `auto` -> `seven` if not reliable, else `classical`.
  `classical`/`seven` are honoured as asked (a user may force classical on an
  unreliable anchor; `lagna_reliable` still reports False). Unknown mode ->
  `ValueError`.
- `ambiguous_contributors(anchor: str) -> dict[str, list[str]]`
  for anchors whose time is approximate: each of the 7 planets whose sidereal
  sign differs between 00:00 and 23:59 local on the birth date, mapped
  to its two candidate sign names. Two samples are enough (no contributor
  moves 30° in a day; no retrograde can cross a sign boundary and come back in 24 h).
  Calls `sbc.planets.positions` directly, NOT `natal.chart`, so it doesn't push
  entries through natal's shared `lru_cache(64)`. Own `lru_cache` keyed by
  anchor. Exact-time anchors return `{}`. Contributors are flagged, never
  dropped automatically.
- `natal_ashtakavarga(anchor: str, lagna_mode: str = "auto") -> dict`
  signs from `natal.chart(anchor)` (`int(lon // 30)`), Lagna from
  `natal.lagna_longitude(anchor)`. Returns
  `{"mode", "lagna_reliable", "lagna_reason", "ambiguous_contributors",
  "max_per_sign": 8|7, "bav", "sav"}`.
  Only anchor keys are accepted (unknown anchor -> `ValueError`).
- `chart_ashtakavarga(date, time, tz, city, lagna_mode)`: same, for a
  hand-given birth moment (needed for book fixtures). `auto` is not allowed
  here (no anchor note); default `classical`.
- `transit_scores(anchor: str, date: datetime.date, lagna_mode="auto") -> dict`
  transit positions at **09:15 IST** on `date` (the NSE open, the same session
  convention as `transit_natal.active_on`) via `sbc.planets.positions`
  (Lahiri). For each of the 7
  planets: `{"sign": name, "sign_index", "bav_points": natal_bav[P][sign],
  "sav_points": natal_sav[sign]}`. Rahu and Ketu are omitted (no classical
  BAV).

Conventions: sidereal Lahiri, whole signs, sign names from
`sbc.nakshatra.RASHIS`.

**Out of scope:** Kakshya (3°45' sub-divisions), Trikona/Ekadhipatya
shodhana (reductions), Shodhya pinda, transit studies.

## 2. API `GET /api/ashtakavarga`

New blueprint `sbc/api/blueprints/ashtakavarga_bp.py`, registered in
`sbc/app_factory.py`.

**Parameters (allow-listed; any other key -> 400)**

| param | rule | default |
|---|---|---|
| `anchor` | key of `engine.ANCHORS` | `nifty` |
| `date` | ISO `YYYY-MM-DD`, 1900-01-01..2100-12-31 | today (IST) |
| `lagna_mode` | `auto` / `classical` / `seven` | `auto` |

**Response 200**

```json
{
  "anchor": "nifty", "anchor_name": "...", "anchor_note": "...",
  "anchors": ["nse", "nifty", "..."],
  "date": "2026-10-31", "transit_time": "09:15 IST",
  "mode": "seven", "lagna_reliable": false,
  "lagna_reason": "birth time approximate",
  "ambiguous_contributors": {"Moon": ["Aquarius", "Pisces"]},
  "status": "experimental",
  "signs": ["Aries", "..."],
  "natal": {"max_per_sign": 7, "bav": {"Sun": [12 ints], "...": []}, "sav": [12 ints]},
  "transit": {"Sun": {"sign": "Libra", "sign_index": 6, "bav_points": 4, "sav_points": 28}}
}
```

**Errors:** validation failures `abort(400)` (the sibling convention, as in
`sector_rotation_bp.py`; `errors.py` has no 400 helper). Calculation failures
are caught and answered with `sbc.api.errors.internal_error()` from inside the
`except`: a generic JSON 500, traceback logged server-side only. Nothing from
the request reaches a path, SQL or a shell. GET only; inherits the
app-wide write-token guard for non-GET. `tests/test_route_pruning.py`
updated for the new route.

## 3. UI tab

- `templates/index.html`: a `nav-tab` button (`data-tab="tab-ashtakavarga"`,
  icon 🔢, label "Ashtakavarga") inside `.advanced-workspace-tabs`, and a
  `tab-ashtakavarga` section. Markup only.
- `static/js/ashtakavarga.js`, loaded with `<script src>`; added to the
  `node --check` list in `tests/test_no_inline_js.py`. All API data rendered
  with `textContent`/DOM nodes, never `innerHTML`.
- Controls: anchor select (from `anchors`), Lagna-mode select, transit date
  (defaults to the dashboard as-of date when set, else today).
- Content:
  1. Banner: "Experimental · descriptive. No validated market edge." plus, when
     `mode == "seven"`, "Lagna excluded: <lagna_reason>" (or "Lagna excluded
     by choice" if forced). For each entry in `ambiguous_contributors`: "Moon
     changes sign during the birth day (Aquarius/Pisces); its points may
     be misplaced". The transit header shows "as of 09:15 IST".
  2. Grid: 7 planet rows + SAV row × 12 sign columns; cells show the count,
     header shows `/8` or `/7`; SAV row heat-shaded with existing tokens.
  3. Transit: each transiting planet's current sign column outlined in its
     row, plus a small table `planet · sign · BAV · SAV`.
- Styles in `static/style.css` using existing CSS variables.

## 4. Testing

`tests/test_ashtakavarga.py`

- Table invariants: per-planet sums equal `CLASSICAL_TOTALS`; classical SAV
  sums to 337 for every anchor; classical cells in 0..8, `seven` cells in
  0..7; for every planet and sign, classical minus seven equals the Lagna's
  contribution (0 or 1).
- Synthetic chart, every planet and the Lagna in Aries: planet P's bindus in
  sign s equal the number of contributors whose list contains house s+1
  (computed independently in the test from a hand-written count, not by
  reusing `bav`).
- Book fixture (B.V. Raman, *Ashtakavarga System of Prediction* p. 39, as
  cited in VedAstro's `CalculateAshtakvargaTests.SunAshtakavargaYoga10Test`):
  1912-08-08 19:35 IST, Bengaluru -> Sun in Cancer, Cancer is 6th from Lagna,
  Sun has 6 bindus in its own BAV (classical). Plain asserts. Verified
  2026-10-31 under Lahiri: Lagna Aquarius 8.26°, Sun Cancer 22.98°; the hand
  count gives 6 (Sun, Moon, Mercury, Jupiter, Venus, Lagna).
- Mode resolution pinned per anchor: `india` -> `classical`/reliable;
  `nifty`, `nse`, `bse`, `sensex`, `nyse` -> `seven`/"birth time approximate";
  `bitcoin` -> `seven`/"no birth place". Every `ANCHORS` key resolves (a new
  anchor defaults to unreliable).
- Ambiguous contributors pinned: `nifty` -> Moon, `nyse` -> Moon, `nse` ->
  Mercury, all others -> none. A test also asserts `natal._planets.cache_info()`
  is unchanged by `ambiguous_contributors` (the shared cache isn't touched).
- Transit: Rahu/Ketu absent; each planet's `bav_points`/`sav_points` equals a
  direct lookup into `natal_ashtakavarga` at the reported `sign_index`.

`tests/test_ashtakavarga_api.py`: 200 + shape; 400 for unknown anchor, bad
date, out-of-range date, bad mode, unknown param; POST rejected.

Updated: `tests/test_route_pruning.py`, `tests/test_no_inline_js.py`.

Verification: full `pytest`; dev server in the browser pane: switch anchors
and modes, no console errors, screenshot.

## Follow-ups (separate beads, not this spec)

- Pre-registered Ashtakavarga-transit event study (decile-matched controls,
  event counts, frozen fixture, costs).
- Kakshya transit timing.

## 0. Prerequisite (plan task 1)

`engine._utc_from_local` accepts only `HH:MM`, so `natal.chart("bitcoin")`
(anchor time `18:15:05`) raises today. Extend it to `HH:MM[:SS]`, test-first,
with a regression test that `natal.chart("bitcoin")` works. Tracked as its own
bug bead.

## Stress Test Results: Ashtakavarga spec

Stress-test bead: SBC_Tool-a8y.

### Resolved Decisions
- Transit time: 09:15 IST (NSE open), matching `transit_natal.active_on`, not 00:00 IST.
- Birth-day sign changes: contributors whose sign changes on an approximate
  anchor's birth date are flagged (`ambiguous_contributors`) and warned about
  in the UI, never dropped. Measured: nifty Moon (Aquarius/Pisces), nyse Moon
  (Pisces/Aries), nse Mercury (Scorpio/Libra).
- Lagna reliability needs an exact time AND a real place; `natal` falls back to
  Mumbai. Only `india` qualifies; `bitcoin` -> seven ("no birth place").
- Detection: an explicit `LAGNA_RELIABLE` allow-list replaces note-substring
  detection; new anchors default to unreliable.
- Security: `abort(400)` for validation, `internal_error()` in `except` for
  failures; allow-listed params, textContent rendering, GET-only. No
  regression.
- Performance: ambiguity check uses 2 samples via `planets.positions` in the
  module's own cache; natal's shared `lru_cache(64)` stays untouched.
- Book fixture: verified under Lahiri (6 bindus); plain asserts, no xfail.
- Existing bug: HH:MM-only time parser breaks the bitcoin anchor; fixed first.

### Changes Made
- Sections 1, 2, 3 and 4 updated as above; section 0 added.

### Deferred / Parking Lot
- `natal.lagna_longitude` Mumbai fallback for non-Indian anchors (nyse,
  bitcoin): file a bead; out of scope here.
- `bav_alt` (second grid for an ambiguous contributor's other sign): only if needed.

### Confidence Assessment
- Overall: High
- Areas of concern: the "seven" mode isn't a classical figure; the labels must stay honest.
