# SBC Tool — Review Backlog (2026-10-01)

Scope: design, code health, broken features and stale code/data across `app.py`,
`sbc/`, `research/`, `static/`, `templates/index.html`, data files, build and CI.
Baseline: branch `master` @ `6368c79` plus the uncommitted working tree.

**Test status:** `pytest` → 317 passed, 8 skipped (36 s). The suite is green, but it
misses most of the items below: UI wiring, data freshness, cache payload shape, and
fresh-clone builds.

Priority key: **P0** = broken or misleading output a trader would act on, or the repo
can't be rebuilt · **P1** = a feature doesn't work as advertised · **P2** = stale or dead
code and tech debt · **P3** = hygiene.

---

## Sprint 1 status (2026-10-01, branch `sprint1-review-fixes`)

| Item | Status |
|---|---|
| B-01 untracked work | ✅ committed in 3 slices (root clutter left for B-30) |
| B-02 cache poisoning | ✅ boot warm-up removed; trimmed rows rebuild on read; cold import 131 s → 0.6 s |
| B-03 demo Trading Signals | ✅ live tithi/Bhadra/reversal windows; panels moved into tabs |
| B-04 tests → real profiles DB | ✅ `SBC_PROFILES_DB`; 63 test rows removed (backup `data/profiles.db.pre-cleanup-2026-10-01`) |
| B-06 duplicate auth gate | ✅ header-only gate |
| **B-33 KP data is random** (new) | ✅ flagged in UI/API, then all files regenerated from Swiss Ephemeris (`sbc/kp_ephemeris.py`) |
| B-12 random KP sample button | ✅ button/endpoint now generate ephemeris data; won't overwrite real files without `force` |
| B-34 KP report crashed in render (new) | ✅ `timeScale().fit()` → `fitContent()` |
| Intraday forecast (SBC + KP), steps 1–3 | ✅ `/api/engine/intraday_forecast`, Plotly panel on the KP tab, forecast ledger (freeze before 09:15 IST, score after close). 40-day back-test: 50.8% hit vs 55.4% baseline |
| B-35 NSE holiday calendar (new) | ✅ `sbc/market_holidays.py` (2024–2026 + special closures + Muhurat); KP generation, forecast, ledger, KP report/path, Rahu–Ketu calendar and date picker use it |
| B-23 Lint debt / CI | ✅ ruff is the only linter (2,907 → 0 findings); CI runs on `master`; black/isort/flake8 dropped |
| B-08 Requirements drift | 🟡 runtime deps now match the tested stack and include openpyxl, python-docx, matplotlib; no lock file yet |
| **B-36 mypy debt** (new) | ✅ 0 errors (was 312 by 2026-10-03); the CI type check now blocks (2026-10-03, `fix-b36-mypy`) |
| B-20 Series cache engine version | ✅ rows carry `sbc.engine_version` (hash of the code behind `build_response` + the payload builder); other versions are ignored and purged on warm-up |
| B-15 Two app instances | ✅ engine moved to `sbc/engine.py`; nothing under `sbc/` imports `app`; `python app.py` serves one app on 127.0.0.1:8000; README run steps updated |
| B-25 Exception text in responses | ✅ 29 handlers use `sbc.api.errors.internal_error()` (logs traceback, generic 500); nested error fields and the crash-series cache no longer echo/cache exceptions; tz endpoints answer 400 for bad input; duplicate global handler removed |

| B-10 Placeholder research routes | ✅ removed (2026-10-03, `phase0-market-data`) |
| B-05 Stale market data | 🟡 NIFTY/SENSEX/VIX in `data/market.db` refresh after each close; sector CSVs and Kota still stale |

| **B-37** Phantom KP vedha school (new) | ✅ removed from fingerprint and README (2026-10-03, `phase2-stats`) |
| **B-38** `_nakshatra_bullish` misspells U.Phalguni (new) | ✅ fixed, plus the same misspelling in the intraday-path `NADI_MAP` (6 nakshatras fell back to "Madhya"); rule and incremental reports re-run: still no edge (2026-10-03, `backlog-sprint3`) |
| B-07 Cold start / health check | ✅ verified: `import app` 0.36 s, Python-based `HEALTHCHECK` with a 30 s start period |
| B-09 Dead UI controls | ✅ lunar Copy/Share wired up (with a "generate first" hint); the dead Gann Fan toggle and Gann Start input removed; the KP week calendar was already populated |
| B-11 `/api/vedha_daily` | ✅ real Moon nakshatra at 09:15 IST, `null` for missing days, only the months in range (cached per month), 2-year cap |
| B-13 Fetch timeouts | ✅ `fetchWithTimeout` honours a timeout argument (the 120 s/300 s calls were silently getting 8 s); heavy endpoints default to 120 s; timeouts say the server may still be computing |
| B-22 Duplicate definitions | ✅ verified: ruff F811/F601 clean, single `get_sign_type` / `get_jupiter_transit_table` / Krittika key |
| B-24 Fake-bar generator | ✅ removed; `data/ohlc` resolved from the package root and no longer created at import |
| B-26 Rate limiter growth | ✅ idle clients are swept once the table passes 1,000 entries (per-worker limits remain; nginx `limit_req` is the real limiter) |
| B-14 City search | ✅ `scripts/seed_cities.py` builds `data/cities.db` from GeoNames (34,152 cities ≥ 15,000 people, with state and time zone); `sbc/cities.py` ranks exact → prefix → substring then population, `LIMIT 20`; the UI shows a results list instead of `alert()`; Docker image seeds at build; boot warns if the DB is missing (2026-10-03, `fix-b14-cities`) |
| **B-39** Astro-quant swing windows: heliocentric aspect ENTRY + Gann/Fib/indicator EXIT (new) | ✅ built and validated 2026-10-03 (`b39-swing-windows`): no edge (see below) |

### B-39 · Astro-quant swing-window model (P2, new feature request 2026-10-03) — ✅ done 2026-10-03
**Resolved.** Defaults chosen: heliocentric only, Earth against Mercury..Pluto, daily bars,
strict 3-of-3 confluence (2-of-3 reported too), max hold 60 sessions.
- **ENTRY:** `sbc/helio_aspects.py`, checked against known events: the Earth–Jupiter conjunction on 2026-01-10 is Jupiter's opposition.
- **EXIT:** `sbc/swing_model.py`.
- **API and chart:** `/api/engine/aspect_windows` (`format=tv`), `/api/engine/swing_windows`, the Swing Windows tab, and `tools/tradingview/astro_swing_windows.pine`. The Pine script is not yet compiled in TradingView.
- **Results** (`docs/research/swing_validation_2026-10-03.md`):
  - Entry timing: 0 of 102 tests show an edge, and none adds anything beyond the market. The plain 10-session reversal rule has no edge either.
  - Full model, 2008 onward (strict exit): 129 trades averaging 0.00%, versus +0.73% for simply holding the same entries for 30 sessions. Random entries with the same exit give p = 0.28.
  - The 2-of-3 exit gives p = 0.62.
- **Forecast:** `helio_all_reversal` is a forecast and ledger component, unvalidated.

**Request:** planetary aspects mark ENTRY (hypothetical reversal zones), technical
confluence marks EXIT (profit-booking zone), and both are plotted as vertical lines on a
TradingView NIFTY chart.

**What exists today:** geocentric sidereal aspects in `sbc/fingerprint.py`. There are no
heliocentric positions (no `FLG_HELCTR`) and no minor aspects (quincunx, sesquiquadrate).
Semi-square appears only in `lunar_forecast.py`. There are no Gann or Fibonacci levels and
no TradingView export.

**Scope:**
1. **ENTRY layer:** `sbc/helio_aspects.py`.
   - Heliocentric Earth vs Mercury…Pluto, scanned hourly over a date range.
   - Aspects: 0, 180, 120, 90, 60, 150, 45 and 135°, orb ±2°.
   - Each window yields `{pair, aspect, entry_ts, exact_ts, exit_ts}` in IST, refined by bisection from the 60-minute step.
   - Filters by planet and aspect code (CONJ/OPP/TRI/SQ/SXT/QCX/SS/SSQ).
   - Earth's heliocentric longitude is the geocentric Sun + 180°. Tropical vs sidereal is a parameter, and must not matter for aspects between two bodies.
2. **Chart payload:** `GET /api/engine/aspect_windows?start=&end=&planet=&aspect=&format=tv`.
   - Returns `{"dates": [...], "label": "<code>", "skip_holidays": false}`, with dates sorted ascending.
   - Add a Pine Script indicator under `tools/tradingview/` that draws vertical lines from pasted dates. Pine has no HTTP fetch, so the dates are embedded or pasted as input.
3. **EXIT layer:** `sbc/swing_exit.py`, run on `market.db` daily bars after each ENTRY.
   - Gann: Square-of-9 levels, 1x1/2x1/4x1 angles from the entry pivot, and 30/45/60/90/180-day time counts.
   - Fibonacci: retracements and extensions of the swing leading into ENTRY.
   - Indicators: RSI 70/30 and divergence, MACD opposite cross or histogram flip, EMA20 break, volume spike (≥2× the 20-day average; NIFTY index volume from yfinance is patchy).
   - EXIT is the first bar where a Gann hit, a Fib hit and an indicator signal coincide. Each rule needs a precise definition, including the tolerance band and the lookback for "swing", plus a max-hold fallback.
4. **Output:** an ENTRY→EXIT window list sorted by date, with direction, the move, max adverse excursion and the triggers that fired. Show it in the UI as a table plus chart markers, labelled hypothetical.

**Validation gate (mandatory before any "highly useful" claim):**
- Grade the ENTRY dates through `sbc/stats.py` like every other rule. Measure absolute 5/20-day move and reversal frequency against circular-shifted dates, then apply BH across pair×aspect combinations. Run `sbc/incremental.py` against the market controls.
- Back-test the EXIT layer against simple exits (fixed N-day hold, EMA20 break alone, ATR stop) on the same entries, and against random entries with the same EXIT rules. That separates the value of the timing from the value of the exit.
- Phase 2 found 0/60 rule tests with an edge, including aspect-based Bradley. Expect the same until shown otherwise.
- Add each pair×aspect as a component in `sbc/forecast.py` and the daily ledger, so it builds a live record.

**Open decisions:**
- Heliocentric (as requested) or also geocentric?
- Which pairs are the default set?
- Daily or intraday bars for EXIT?
- Strict 3-way confluence, or any 2 of 3?

### B-36 · mypy reports 231 errors (P3, new) — ✅ done 2026-10-03
**Resolved.** `mypy sbc/ app.py --ignore-missing-imports` reports 0 errors. There were 312 by
2026-10-03, after the prediction-engine phases. The CI job is now blocking.

**Fixes:**
- Mostly annotations: optional defaults, empty containers, numpy `ArrayLike` in `sbc/stats.py`, and `float()` around Swiss Ephemeris returns.
- Added `types-pytz` to the dev extra.

**Small behaviour changes** that the types exposed:
- `cgsp_framework.get_planet` and `rahu_ketu_trap._get_planet_longitude` raise a clear `ValueError` on a missing planet. Before, they returned `None` and the caller crashed later.
- `KPConfig` fills defaults for empty dicts as well as `None`.
- KP regime shifts skip rows whose timestamp can't be parsed.
- `applying_or_separating` returns `None` when the current separation is unknown.
- The rate limiter keys a missing client address as `"unknown"`.

**Removed:** the empty, unused `TITHI_GROUPS` in `lunar_forecast.py`. The real table is in `sbc/nakshatra.py`.

`mypy sbc/ app.py --ignore-missing-imports`: 68 assignment, 62 var-annotated, 31
no-untyped-def, 19 index, 18 no-any-return and others. Spot-checking found no runtime bug.
For example, `app.py`'s "MarketEvent is not indexable" comes from reusing a variable name
for plain dicts. CI runs mypy as an advisory job. **Fix:** annotate module by module,
starting with `sbc/api` and the engines, then make the job blocking.

### B-35 · No NSE trading-holiday calendar (P2, new) — ✅ done 2026-10-02
Resolved: `sbc/market_holidays.py`, refreshed yearly from NSE's December circular. `is_covered()` flags years beyond the list.

Weekends are the only closed days the code knows about. KP data files carry rows for
holidays, the forecast panel defaults to a holiday if it falls on the next weekday, and the
ledger auto-froze a live forecast for 2026-10-02 (Gandhi Jayanti). These are harmless:
holidays have no bars, so they never get scored. **Fix:** add `sbc/market_holidays.py` with NSE's
published list (refreshed yearly), and use it in `kp_ephemeris.trading_days`, the
forecast date picker, the ledger loop and the futurecast calendars.

### B-33 · Every KP data file is random sample output (P0, new)
- **Evidence:** all of `data/kp/KP_Data_{Jan2024,Aug2026,Sep2026,Oct2026,Nov2026}.csv`
  place a nakshatra in a sign it cannot occupy on **~89% of rows** (e.g. Uttara Bhadrapada
  in Leo, Mula in Cancer), and the Sun shows up in 10+ signs within one month. This is
  the output of `generate_sample_kp_csv`.
- **Impact:** the KP intraday report, the predictive intraday path, and its validation
  (`docs/INTRADAY_PATH_VALIDATION.md`: 49.8% regime hit rate) were all computed on
  noise. B-21's "no edge" result is explained by this.
- **Done so far:** `sbc.kp_intraday.assess_kp_data` checks star↔sign geometry. Both
  `/api/kp_intraday_report` and `/api/engine/intraday_path` return `data_quality`, and
  the UI shows a red "Not real KP data" banner when the file fails.
- **Resolved:** `sbc/kp_ephemeris.py` computes every row: KP ayanamsa, Moshier,
  Placidus cusps for NSE Mumbai, Vimshottari sub and sub-sub lords, KP house
  significations, sunrise-based Chaldean horas, and Vedic sign aspects. CLI:
  `python scripts/generate_kp_data.py 2026-10 [2026-12] [--step 1]`. Jan 2024 and
  Aug–Nov 2026 have been regenerated, with 0 impossible rows. Parser fixes made at
  the same time: hora slots are built on lord changes (with real end times), the day
  bias uses the Moon's star *lord* (it was passed the star name, so that term was
  always neutral), and Moon affliction reads the Moon row's aspects (it read the
  Sun's).
- **Convention to confirm:** house_set_strength scores houses 2/6/10/11 as rise and
  5/8/12 as fall (`RISE_HOUSES`/`FALL_HOUSES` in `kp_ephemeris.py`). Change these if
  your KP school uses a different set. NSE holidays aren't excluded yet (weekends are).
- **Re-validation on real data (2026-08-04 → 09-30, 41 days):** pooled hit rate 50.8%,
  regime-shift 49.7%, pooled correlation +0.004. Day direction was 28/41, against a
  60.8% chance baseline (the model is bearish on 90% of days in a market that was
  down on 63%). **Still no edge** — see B-21.

---

## P0 — Fix first

### B-01 · Working tree depends on 131 untracked files; HEAD can't be rebuilt
- **Evidence:** `app.py` (modified) imports untracked modules: `sbc/app_boot.py`, all 7 of
  `sbc/api/blueprints/*.py`, `sbc/astrogann.py`, `bradley.py`, `astro_cycles.py`,
  `expiry_range.py`, `gann_indicators.py`, `gann_zones.py`, `rahu_ketu_trap.py`, `kp_layers.py`,
  `kp_docx.py`, `transits.py`, and `static/js/api-token.js`. 10 test files are untracked too.
  27 tracked files are modified (+3438/−2345).
- **Impact:** Committing only the modified files breaks the app at import. A clone or Docker
  build of `main` doesn't match what runs locally. One disk failure loses about 3 weeks of work.
- **Fix:** Commit in logical slices (blueprint refactor → new engines + tests → UI) on a
  feature branch. Decide what to do with the root clutter (see B-30) before `git add -A`.
- **Done when:** `git status` is clean apart from intentionally ignored files, and a fresh
  clone passes `pytest`.

### B-02 · Boot warm-up writes a trimmed payload into the chart cache
- **Evidence:** `sbc/app_boot.py:17-31` writes `{date,score,net,verdict,strength,rec}` into
  the same `series` table that `/api/prediction_series`
  (`sbc/api/blueprints/chart_bp.py:157-173`) reads and expects to contain
  `risk_rank, risk_label, drivers, windows, confluence, lunar_phase, alert*`.
  The live `data/series_cache.db` has **591 trimmed rows** (2026-03-17 → 2026-10-01 for
  nifty/allthree, nse/allthree and nse/classical), next to 1407 full rows.
- **Impact:** On those dates the chart overlay loses its crash-risk bands, vedha drivers,
  reversal windows and confluence hover data. Nothing errors, so it fails silently.
- **Fix:** Delete `_warm_prediction_series` from `app_boot.py`. Keep a single warm path
  (`run_app.py` already warms through the real endpoint) or move the payload builder into
  one shared function. Run `series_cache.clear()` once after deploying.
- **Done when:** Every row in `series_cache.db` has a `drivers` key, and a test checks that
  the warm path and the endpoint produce the same keys.

### B-03 · "Trading Signals" panel shows hardcoded demo signals as live
- **Evidence:** `templates/index.html:1064-1119` and the inline script at `:1787-1793`:
  - "BADRA ACTIVE — avoid major positions" shows **every day**, whatever the real Bhadra state.
  - Tithi is always red ("inauspicious"), the weekday always reads "favorable market day",
    and the nakshatra always reads "caution, volatile".
  - The tithi falls back to the literal `'Krishna Ashtami'` and the nakshatra to `'Mula'`
    because `/api/astro/personal` (`chakra_bp.py:119-176`) returns **no `tithi` field**.
  - The Reversal Zone box is static HTML: "23:15 - 23:35 · Probability: High" (`:1111`).
  - The INTRADAY/SWING/POSITIONAL tabs only append `[SCOPE]` to the subtitle, and it grows
    on every click (`:1829`).
  - The panel sits **outside every tab pane**, so it shows under every tab.
- **Impact:** A trading UI is showing invented risk calls.
- **Fix:** Either drive each row from real data (Bhadra from `/api/bhadra_calendar`, tithi
  quality from `prediction.py`, reversal windows from `market_alert.windows`) or remove the
  panel. Move it into a tab.
- **Done when:** The panel contains no string literals that look like data, and a
  Bhadra-free day shows no Bhadra warning.

### B-04 · Tests write to the real `data/profiles.db`
- **Evidence:** `tests/test_integration.py:163` creates and renames profiles. The live DB has
  **63 profiles: 40 unnamed and 23 "Updated Profile"**. `conftest.py` redirects only the
  series cache. `app.py` opens `Path("data/profiles.db")` directly in 8 places
  (`:1278, 1295, 1351, 1372, 1590, 1608, 1634`…), ignoring `sbc/db.py:_DB_PATH`.
- **Impact:** Every test run pollutes your real birth-data profiles. The relative path also
  breaks if the app starts from another cwd.
- **Fix:** Route every DB access through `sbc.db` (one `get_conn()`). Add an
  `SBC_PROFILES_DB` env override and set it to a tmp file in `conftest.py`. Clean up the
  junk rows.
- **Done when:** The `profiles` row count is the same before and after `pytest`.

### B-05 · Market data is stale: NIFTY daily ends 2026-09-21; Kota covers only 1–15 Sep
- **Evidence:** `data/nifty_ohlc.csv` last row is `2026-09-21` (10 days old; some rows have
  volume 0). `data/kota/` holds only `Prediction_Kota_Chakra_01.09.2026 till 15.09.2026.xlsx`.
  `data/ohlc/` (3-min bars) is now empty because the sample files were deleted, so
  `/api/engine/market/ohlc` returns nothing. Probed on 2026-10-01: `/api/engine/kota/daily`,
  `/weekly` and `/monthly` all answer **200 with empty `records`/`summary`**, and
  `market/ohlc` answers `bars: []`. None of them says the data is missing or stale, so
  the UI just renders blank.
- **Impact:** Chart candles, the intraday validation, and the Kota daily/weekly/monthly views
  for October have no data or serve September's.
- **Fix:** Add a refresh job (`scripts/fetch_history.py` already exists; schedule it and
  make `get_nifty_ohlc` refresh when the last bar is more than 1 trading day old). Add a real
  3-min bar source or hide the panel. Show a "data as of" stamp plus a staleness banner on
  every panel that uses price or Kota data.
- **Done when:** Each data-backed panel shows an as-of date, and it turns amber after 1
  trading day.

---

## P1 — Features broken or not as advertised

### B-06 · Duplicate, conflicting write-auth gates
- **Evidence:** `app.py:75-81` `require_token_for_writes` (accepts `?token=` in the query
  string, reads an unstripped env var) **and** `app.py:112-129` `_require_write_token`
  (header only, localhost fallback). A query-string token passes gate 1 and then fails
  gate 2.
- **Fix:** Delete gate 1. Never accept tokens in URLs, since they end up in logs and history.
- **Done when:** Only one `before_request` auth hook exists, with tests covering
  header/no-header/remote cases.

### B-07 · Cold start blocks import for minutes; Docker health check can't pass — ✅ done 2026-10-03
- **Evidence:** `boot()` runs at import (`app.py:395`) and computes up to 4×181
  `build_response` calls in the foreground. Importing with a cold cache took **131 s**
  in this review. Under gunicorn (`-w 4`, no `--preload`) every worker repeats it. The
  Dockerfile `HEALTHCHECK` uses `curl`, which `python:3.12-slim` doesn't have, and uses
  `start-period=5s`.
- **Fix:** No work at import time. Warm in a background thread or a CLI step (`flask warm`),
  and use `--preload` or a single warmer. Use a Python-based health check
  (`python -c "urllib.request.urlopen(...)"`) with a realistic start period.
- **Done when:** `import app` takes under 3 s with an empty cache, and the container reports
  healthy.

### B-08 · Requirements don't match the stack that actually runs; 3 runtime deps missing
- **Evidence:** The venv has numpy 2.4, pandas 3.0, pytest 9.1, timezonefinder 8.3 and
  yfinance 1.6. `requirements.txt` pins `numpy<2`, `pandas<3`, `pytest<8`,
  `timezonefinder<7` and `yfinance<1`. `openpyxl` (Kota), `python-docx` (`kp_docx`) and
  `matplotlib` (`/api/nakshatra_chart`, `astro_plot`) are imported but **not listed**.
- **Impact:** A fresh install or Docker image gets a different stack, and Kota, KP DOCX and
  the nakshatra chart fail with ImportError.
- **Fix:** `pip freeze` to a lock file (or update the pins to the tested versions). Add the 3
  missing packages. Split dev deps out (sphinx, black, mypy… don't belong in the runtime
  image).
- **Done when:** A clean venv from `requirements.txt` passes `pytest` and the route smoke test.

### B-09 · Advertised UI controls have no handlers — ✅ done 2026-10-03
| Control | Location | State |
|---|---|---|
| Lunar forecast **Copy to Clipboard** / **Share** (README: "clipboard/share ready") | `index.html:859-860` | No JS listener |
| **Gann Fan** toggle + **Gann Start** date | `index.html:1092-1094` | No JS listener |
| KP intraday week calendar dropdown | `index.html:880` | Never populated |
- **Fix:** Wire them up (the lunar card already returns `card` data from `lunar_forecast.py`)
  or remove them.
- **Done when:** A UI test clicks each control and sees an effect.

### B-10 · 10 research endpoints return placeholders
- **Evidence:** `research/astro_research.py` says in its own docstring that the
  implementations "are placeholders". It backs `research_bp` (`/api/research/astro_lab`,
  `walk_forward_validation`, `canonical_market_event_model`, `new_moon_efficiency_study`,
  `planetary_aspect_grid`) and `app.py` (`bradley_barometer_overlay`,
  `regime_aware_reports`, `research_export`, `solar_lunar_cycle_explorer`,
  `unified_daily_forecast_contract`). The real implementations are the dash-named routes the
  UI calls (`/api/research/event-study`, `walk-forward`, `aspects`, `cycles`), so the API has
  two parallel naming schemes.
- **Fix:** Delete the placeholder routes and module, or point them at the real ones.
- **Done when:** No route returns a body containing "placeholder".

### B-11 · `/api/vedha_daily` returns a fabricated `nakshatra_idx`, hides gaps, and is slow — ✅ done 2026-10-03
- **Evidence:** `app.py:~1487` sets `nakshatra_idx = days_since_start % 27`, which counts
  days rather than computing the Moon's nakshatra. Missing days default to `score 0` (reads
  as "neutral") instead of `null`. Every call builds 6 full `monthly_heatmap` months no
  matter what range was requested, and ranges longer than 6 months come back zero-filled.
  There's also dead code after `break` at `:1434` (ruff F821, undefined `k`).
- **Fix:** Compute the real Moon nakshatra. Return `null` for missing days. Compute only the
  months the range covers, and cache them.
- **Done when:** `nakshatra_idx` matches `sbc.nakshatra` for sampled dates.

### B-12 · "KP sample" button writes random data under the real KP filename
- **Evidence:** UI `generateKPSampleData` (`static/app.js:3728`) → `POST /api/kp_intraday_sample`
  → `generate_sample_kp_csv` (`sbc/kp_intraday.py:1201-1225`, all `random.*`) writes
  `data/kp/KP_Data_<Mon><YYYY>.csv`, the same name real data uses. An existing file is
  protected, but for an uncovered month (e.g. Dec 2026) random data becomes "the" KP data,
  and reports built from it look real.
- **Fix:** Write samples to `data/kp/samples/` with a `SAMPLE_` prefix, flag reports built
  from them (`is_sample: true`), and add a banner in the UI. Or drop the button.

### B-13 · Front-end 8 s fetch timeout is shorter than heavy endpoints — ✅ done 2026-10-03
- **Evidence:** `static/app.js:3` `FETCH_TIMEOUT = 8000`, used by 29 calls, including the
  KP report, prediction_series (about 100 s cold), heatmap and futurecasts.
- **Fix:** Per-call timeouts (heavy ones 60–120 s), or async job plus polling for heavy
  computations. Show "computing…" rather than a generic failure.

### B-14 · City search has 5 rows — ✅ done 2026-10-03
- **Evidence:** `data/cities.db` → `cities: 5` rows, and it's gitignored, so a fresh clone has
  no DB. Birth-data city lookup is effectively broken. The inline UI also uses `alert()`
  for results (`index.html:1197-1205`).
- **Fix:** Ship a seed script (e.g. GeoNames cities15000 → SQLite), run it on bootstrap,
  and add `LIMIT 20`. Replace `alert()` with a dropdown.

### B-15 · `python app.py` creates two app instances (circular import) — ✅ done 2026-10-03
Resolved: `sbc/engine.py` holds `build_response`, `ANCHORS` and the time helpers; blueprints and `sbc.intraday_forecast` import it, `app.py` re-exports it. `tests/test_single_app_instance.py` runs `app.py` as `__main__`, makes requests through the blueprints and asserts one Flask app.

- **Evidence:** Blueprints do `from app import build_response, ANCHORS, …`
  (`overview_bp.py:10,22,42`, `chart_bp.py:58`, `balance_bp.py:19`, `chakra_bp.py:121`). Run
  as a script, `app.py` is `__main__`, so `from app import` re-executes the file: a second
  Flask app, a second `boot()`, and a second warm-up. The README tells users to run
  `python app.py`.
- **Fix:** Move `build_response`, `ANCHORS`, `_utc_from_local` and `_julday` into
  `sbc/engine.py` (or similar) and import from there. Use an app factory
  (`create_app()`). Update the README to `python run_app.py`.

---

## P2 — Design debt and stale code

### B-16 · `app.py` is still a 2,631-line monolith; the blueprint migration stalled halfway
About 75 routes are still in `app.py`, while 7 blueprints + `engine_bp` + `sector_bp` hold the
rest. `app.py` also still carries leftover imports from the moved routes (ruff F401:
`NAKSHATRAS_27`, `generate_weekly_commentary`, `format_commentary_text`, `moon_rashi`,
`RASHI_TREND`, `list_setups`, unused `pandas`/`math`).
**Fix:** Finish the move (habits/profile → `profile_bp`, sector signals → `sectors_bp`,
backtests → `research_bp`, gann/astrogann/expiry → `chart_bp` or `gann_bp`), then switch to
an app factory.

### B-17 · About 1,400 lines of inline JS in `index.html`
`templates/index.html:1158-2584` holds profiles, habits, the trading-signals demo,
backtests, price/vedha charts and nakshatra. It duplicates helpers (`localTodayISO`, fetch
logic), bypasses `fetchWithTimeout` and error handling, and can't be linted or cached.
**Fix:** Move it into `static/js/*.js` modules; keep the template markup-only.

### B-18 · 23 backend routes have no UI caller
`/api/backtest`, `bearish_futurecast`, `cgsp_backtest`, `cgsp_framework`, `contra_signals`,
`crash_analysis`, `crash_backtest`, `saturn_macro`, `trade_setups`, `gann/indicators`,
`gann/turbo_zones`, `astrogann/signal`, `habits/summary`, `kp_intraday_config`,
`sbc/latest`, `engine/confluence/daily`, `engine/summary`, `engine/trace`,
`engine/version`, `sector/planet_read`, `sector/vedha_read`, and the 10 placeholders in
B-10. The README advertises **Crash Analyzer** and **CGSP Framework** as features, but
neither has a panel.
**Decision needed:** For each route, either expose it in the UI, keep it as a documented
API-only route, or delete it.

### B-19 · `/api/contra_signals` uses market-structure labels for astro signals
`app.py:664-760`: "POC trap", "distribution/accumulation", "selling exhaustion" and "Layer 3
Price Confirmation" are all derived from **vedha weights only**, with no price or volume
input. The docstring itself says "synthetic".
**Fix:** Rename the fields to what they measure (e.g. `vedha_extreme`, `benefic_dominance`)
or feed in real price data.

### B-20 · Series cache has no engine version, so stale predictions persist forever — ✅ done 2026-10-03
Resolved: `sbc/engine_version.py` hashes `build_response`, the app.py helpers it reaches, `chart_bp.prediction_series`, and the transitive closure of the sbc modules they import (12 files today). `sbc/series_cache.py` stores the version per row, serves only matching rows, migrates old databases (rows without a version count as stale), and `run_app.py` purges stale rows before warming.

`sbc/series_cache.py` assumes prediction is "a pure function of (date, anchor, school)".
It is pure, but only for a fixed engine. `prediction.py`, `confluence.py` and
`market_calendar.py` all changed in the working tree, and cached rows still reflect the old
engine until someone remembers to call `clear()`.
**Fix:** Add an `engine_version` column (hash of the relevant module sources, or a constant
bumped manually), and miss on mismatch.

### B-21 · Intraday path is marked "COMPLETE" but shows no edge (confirmed on real KP data 2026-10-01)
`docs/INTRADAY_PATH_VALIDATION.md`: regime-shift direction hit rate **49.8%** (3345
shifts), and pooled score hit rate **54.8%** on 217 windows (not significant). Per-day
correlation swings between −0.77 and +0.69. `docs/todo_predictive_intraday.md` still says
"STATUS: COMPLETE".
**Fix:** Label the panel "Experimental — no validated edge" and add a rolling hit-rate badge.
Track re-weighting work as research rather than calling it done.

### B-22 · Duplicate and shadowed definitions (ruff F811/F601) — ✅ done 2026-10-03
- `sbc/cgsp_framework.py:49` — `"Krittika"` key repeated, so the earlier pada mapping is
  silently overwritten. `get_sign_type` (`:98` vs `:107`) and `get_jupiter_transit_table`
  (`:134` vs `:191`) are each defined twice; the second wins.
- `sbc/lunar_forecast.py:549, :570` — `overall_bias`, `key_dates` repeated in the card dict.
  Lines `:300, :322, :536-537` re-import and redefine `get_planet`/`angular_distance` locally.
- `sbc/alcohol_signals.py:47` (`paksha_of`), `sbc/backtest.py:742` (`gandanta_of`) shadow imports.
**Fix:** Delete the dead copies and check which Krittika mapping is intended.

### B-23 · Lint debt: 178 pyflakes-class errors; CI can't pass and doesn't run on this branch
`ruff --select F`: 96 unused imports, 56 unused variables, 12 empty f-strings, 10
redefinitions, 3 duplicate keys, 1 undefined name. CI (`.github/workflows/ci.yml`) runs
ruff + black + isort + flake8 + mypy on **push to `main`/`develop` only**, while work
happens on `master`. `pyproject.toml` uses deprecated top-level ruff keys.
**Fix:** `ruff check --fix`, then fix the rest by hand. Point CI at `master` (or rename the
branch). Drop the overlapping flake8/isort in favor of ruff. Move the config to `[tool.ruff.lint]`.

### B-24 · `sbc/market_ohlc.py` still contains the fake-bar generator — ✅ done 2026-10-03
`ensure_week_cache` / `generate_sample_ohlc` (`:14-48`) fabricate random 3-min NIFTY bars
around 25000. The read path no longer uses them, but they're one call away from coming back.
`DATA_DIR = Path("data/ohlc")` is cwd-relative and is created as an import-time side effect.
**Fix:** Delete the generator (move it to `tests/fixtures` if a test needs it) and resolve
paths from the package root.

### B-25 · Error responses leak exception text — ✅ done 2026-10-03
Resolved: see `sbc/api/errors.py`; `tests/test_error_leaks.py` forces failures in app and blueprint routes and statically guards against `str(e)` in 500 responses. Intentional 400 validation messages are kept.

Many handlers end with `return jsonify({"error": str(e)}), 500` (e.g. `chakra_bp.py:176`,
`app.py:1398, 1503`). These bypass the global JSON handler and expose internals.
**Fix:** Let exceptions propagate to `handle_exception`, and log with `exc_info`.

### B-26 · Rate limiter grows without bound — ✅ done 2026-10-03
`app.py:88-101` keeps `_request_times` keyed by IP forever, per worker, and each worker
counts separately (4×240/min effective).
**Fix:** Evict empty keys, or rely on nginx `limit_req` only.

### B-27 · Leftover template/jinja reload settings repeated 3×
`TEMPLATES_AUTO_RELOAD`, `jinja_env.auto_reload` and `jinja_env.cache = {}` are set in
`app.py:84-86` and `app_boot.py:41-45`. Turning off the jinja cache in production costs a
template re-parse on every request.
**Fix:** Enable it only when `app.debug`.

---

## P3 — Repo hygiene

### B-28 · Dockerfile copies everything
There's no `.dockerignore`, so `venv/`, `venv-py314/`, `node_modules/`, `data/*.db`,
`Financial_Astrology/`, `SBC-Tool/` and PDFs all go into the image. Add a `.dockerignore`.

### B-29 · Stray Node project
`package.json` / `package-lock.json` / `node_modules/` contain only
`opencode-models-discovery`, which is unrelated to the app. Remove them, or move them out
of the repo.

### B-30 · Root and scripts clutter (again)
- Root: `check_kota.py`, `create_summary.py`, `export_excel.py`, `extract_book.py`,
  `extract_pdf*.py`, `test_api.py`, `test_yf*.py` (4), `kota_*.txt`,
  `kn_rao_planets_children.txt`, `actionable_verdict_2026-09-14.md`.
- Obsidian vaults committed beside code: `Financial_Astrology/`, `SBC-Tool/` (`Untitled*.canvas`).
- `scripts/`: `_chk*.py`, `_dbg.py`, `_find.py`, `fix_all*.py`, `fix_end.py`, `fix_final.py`,
  `debug_*.py`, `check_*.py` are one-off repair scripts from earlier sessions.
- `data/output/study_*` CSVs (18 files) are generated artefacts.
- Two overlapping smoke tests: `tests/test_route_smoke.py` and `tests/test_routes_smoke.py`.
**Fix:** Move scripts to `scripts/adhoc/` or delete them. Move vaults outside the repo or
gitignore them. Gitignore `data/output/`. Merge the smoke tests.

### B-31 · Stale docs
- `README.md`: says `python app.py` (see B-15), lists Crash Analyzer/CGSP/clipboard-share as
  features (B-09, B-18), and doesn't mention Gann/AstroGann/Bradley/Expiry/Rahu-Ketu trap.
- `docs/ASTRO_GANN_BACKLOG.md` is a generic proposal template (asks you to "confirm
  ayanamsha", "skyfield vs swisseph") that predates the implemented `astrogann.py`.
- `docs/todo_predictive_intraday.md` says COMPLETE (B-21).
- `docs/session_summary.md`, `backtest_summary.md` are point-in-time notes.
**Fix:** Rewrite the README feature table from the actual tabs. Archive dated notes under
`docs/archive/`.

### B-32 · Mixed line endings
Git warns "LF will be replaced by CRLF" on 14 files. Add a `.gitattributes`
(`* text=auto eol=lf`) and renormalize once.

---

## Suggested order of work

| Sprint | Items | Outcome |
|---|---|---|
| 1 (1–2 days) | B-01, B-04, B-02, B-06, B-03 | Work is safe in git; no polluted data; chart overlay correct; no invented signals |
| 2 | B-05, B-08, B-07, B-15 | Fresh data and staleness banners; reproducible install; fast boot; one app instance |
| 3 | B-09, B-10, B-11, B-12, B-13, B-14 | Every visible control works or is gone |
| 4 | B-16, B-17, B-20, B-23, B-22 | Monolith split, cache versioned, lint and CI green |
| 5 | B-18, B-19, B-21, B-24…B-32 | Dead routes pruned, honest labels, clean repo and docs |

## Tests to add along the way
- Payload-shape contract test for `/api/prediction_series` across both warm and cold paths (B-02).
- `profiles` row count unchanged across the test session (B-04).
- Clean-venv install + route smoke in CI (B-08).
- Headless UI test (Playwright) that clicks every button in every tab and asserts no console
  errors and no unhandled controls (B-03, B-09).
- No route body contains "placeholder", and no panel contains hardcoded date/time strings
  (B-03, B-10).
