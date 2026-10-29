# BACKLOG: Transit Report Generator + NSE Momentum Screener (2026-10-19)

Gap analysis of two product specs vs SBC_Tool, with build plan. Statuses:
**Exists** / **Partial** (engine exists, assembly missing) / **Missing**.

## Product 1: Planet Transit Report Generator (Excel)

Coverage: engine ~65%, product ~30%.

| # | Feature | SBC_Tool today | Status |
|---|---------|----------------|--------|
| 1 | Zodiac / Nakshatra / Pada transit types | `sbc/transits.py` sign_ingresses + nakshatra_ingresses (3h scan, 1-min bisect, UTC+IST, retro re-entries detected). Pada-level: only carried on nakshatra events, no pada scanner | Partial |
| 2 | All 12 bodies | `planets.py` SWE_BODIES has all 12 (outers + Ketu derived) but `transits.py._BODIES` scans only 7 classical + Rahu | Partial |
| 3 | Exact to-the-second + duration | Bisect stops at 1 minute; no paired entry/exit durations for sign transits (`nakshatra_periods` has days) | Partial |
| 4 | Any city's local time | `sbc/cities.py` + `data/cities.db` store **timezone** per city; transits output UTC+IST only | Partial |
| 5 | Any date range | All functions take ranges | Exists |
| 6 | Ayanamsa KP / Lahiri / Raman + date-varying value | transits fixed Lahiri; KP exists in `kp_ephemeris.py` (SIDM_KRISHNAMURTI); Raman (SIDM_RAMAN) unused; `swe.get_ayanamsa_ut` not surfaced | Partial |
| 7 | True vs Mean node | transits = MEAN_NODE (repo convention), `stations.py` uses TRUE_NODE - inconsistent, no selector | Partial |
| 8 | Retrograde intelligence | Re-entries detected in scans; motion-at-event flag missing; `stations.py` gives exact R/D stations (Mercury..Pluto+Rahu, to-the-minute) | Partial |
| 9 | Gandanta alerts | `nakshatra.py gandanta_of()` exists; not wired into transit events | Partial |
| 10 | 6-sheet Excel workbook | openpyxl in deps; export endpoint pattern exists (`kp_bp.py` send_file). No transit workbook builder | Missing |
| 11 | All-Transits Timeline (merged, Nifty-ready) | Missing | Missing |
| 12 | Prompt-driven page + auto-download | Flask multi-tab app exists; no transit-report tab | Missing |

### Build plan P1  —  STATUS: **BUILT 2026-10-19** (T1+T2+T3 complete)

- **T1 - Engine upgrade (`sbc/transits.py`, backward-compatible) — DONE**
  - T1.1 Outer bodies (Uranus/Neptune/Pluto) + derived Ketu; `node_mode`
    ("mean"/"true"); `ayanamsa` ("lahiri"/"kp"/"raman"); motion (D/R/S)
    + re-entry (60-day window) flags on every event; `_BISECT_DAYS`
    now 1/86400 (1-second precision; `_from_jd` no longer truncates).
  - T1.2 `pada_ingresses()` — 108-sector scanner with pada_index.
  - T1.3 `sign_periods()` — paired entry/exit + duration + motion.
  - T1.4 Gandanta flags on all three event kinds (`nakshatra.gandanta_of`).
  - T1.5 `cities.resolve()` + `cities.local_time()` (IANA tz from
    cities.db, UTC fallback).
  - Acceptance: `tests/test_transit_report_engine.py` (10 tests) +
    updated `tests/test_transits.py` — 18 passing.
- **T2 - Excel builder (`sbc/transit_report.py`) — DONE**
  - 6 sheets: Report Info (settings, ayanamsa value at range start,
    start positions, legend), Zodiac (sign lord), Nakshatra (star lord
    via `market_calendar.NAKSHATRA_LORDS`, sign), Pada (star lord, sign,
    ayanamsa index), All-Transits Timeline (merged, local-time sorted),
    Stations (R-D) via `stations.between` enriched with position +
    nakshatra + star lord. All times in the city's local timezone.
  - Perf: 6 bodies x 3 types x 1 year = 2.1 s; full 12-body year well
    under the 60 s budget.
  - Endpoint: `sbc/api/blueprints/transit_bp.py` —
    `GET /api/transits/cities` (autocomplete) and `GET /api/transits/report`
    (xlsx download; bad dates -> 400; defaults normalized). Registered
    in `app_factory`.
  - Acceptance: `tests/test_transit_report_api.py` (4 tests passing).
- **T3 - UI — DONE**
  - New "🪐 Transit Report" main tab (`templates/index.html`): city
    autocomplete (debounced `/api/transits/cities` datalist), date
    range, ayanamsa + node selects, transit-type and planet checkbox
    groups (all/none toggle), Generate -> blob download with status
    line. Wiring in `static/app.js`, styles in `static/style.css`.
    `node --check` passes.

Estimates: T1 ~1 day, T2 ~1 day, T3 ~0.5 day.

## Product 2: NSE Momentum Screener

Coverage: ~10% (plumbing only). No technical-indicator code exists in
the repo (no RSI/Supertrend/Bollinger/EMA/pivot/Heikin-Ashi anywhere).

| # | Feature | Status |
|---|---------|--------|
| 1 | Supertrend(10,3) / RSI(14) / pivot R1,S1 / Bollinger(20,2) / EMA 10-30 | Missing |
| 2 | 6 timeframes incl. intraday + Heikin Ashi | Missing (NIFTY 5-min fetch exists; no batch stock downloader) |
| 3 | 13 NSE universes (50/Next50/100/200/500, Midcap150, Smallcap250, Bank, F&O, all, indices, sectors, watchlist) | Missing (no NSE list files; `market_store.RESEARCH_SYMBOLS` pattern reusable) |
| 4 | Back-scan past dates | Missing (yfinance history limits apply) |
| 5 | Long/short/both | Missing |
| 6 | Signal list + risk plan + trade tracking (SL, trailing, P&L, candles held) | Missing (`trade_setups.py`/`trade_journal.py` are astro-based; concepts reusable) |
| 7 | Excel workbook download | Pattern exists (openpyxl + send_file) - reuse |
| 8 | Guided UI | App tab pattern exists - reuse |

### Build plan P2  —  STATUS: **BUILT 2026-10-20** (S1+S2 complete)

- **S1 - Engine (`sbc/screener/`) — DONE**
  - S1.1 `indicators.py`: EMA (adjust=False), Wilder RSI, Bollinger
    (population sd), previous-candle floor-trader pivots P/R1/S1,
    classic Wilder ATR, canonical Pine-reference Supertrend (ratchet
    bands, current-close flip vs previous final band), Heikin-Ashi.
    Golden tests: `tests/test_screener_indicators.py` (12).
  - S1.2 `universes.py`: NSE archive loaders (Nifty 50/Next 50/100/
    200/500, Midcap 150, Smallcap 250, Bank, F&O market lots, 11
    sector lists, merged indices with ^NSEI/^NSEBANK/^CNX* map,
    all_nse), daily-cached under `data/universes/` with stale-cache
    fallback, free-text watchlists. Tests (11).
  - S1.3 `data.py`: yfinance batch download, 5m/10m/15m->60d and
    1h->730d clamps, back-scan `end` clipping, Heikin-Ashi transform,
    per-symbol error collection. Tests (9).
  - S1.4 `engine.py`: three modes (full 4-rule / RSI-50-cross /
    EMA 10-30), fresh-signal detection (condition transition), entry
    at candle close, Supertrend trailing stop (slow EMA in ema mode),
    exit on stop/opposite cross, P&L %, candles held, per-symbol
    failure isolation. Tests (7).
  - S1.5 `report.py`: Excel workbook - Long Signals / Short Signals /
    Scorecard / Params.
  - S1.6 `sbc/api/blueprints/screener_bp.py`: `GET /api/screener/
    universes` and `GET /api/screener/scan` (json preview capped at
    200 signals, xlsx download, symbol caps 100 intraday / 600 daily,
    watchlist:TEXT universes). Registered in app_factory. Tests (6).
- **S2 - UI — DONE**
  - New "🚀 Momentum Screener" main tab: universe dropdown from
    /universes, watchlist override, mode/timeframe/scan-date/lookback/
    Heikin-Ashi controls, Run Scan (JSON preview table: entry, %chg,
    RSI, initial + trailing SL, status, exit, P&L) and Excel download.
    Wiring in `static/app.js`, styles in `static/style.css`.
    `node --check` passes.

Full-suite state after both products: 678+ passing; the only failures
are the pre-existing branch-WIP ones (route-pruning orphans from the
economic/sentiment feature and the /api/sentiment/daily sqlite error),
verified independent of this work by stash-testing.
- **S2 - UI**: "Momentum Screener" tab - mode/timeframe/universe/date
  pickers, run, download; server-side cap on universe x timeframe.

Estimates: S1 ~2 days, S2 ~0.5-1 day.

## Suggested order

T1 -> T2 -> T3 (fast wins on an existing engine), then S1 -> S2.
**All shipped: T1/T2/T3 on 2026-10-19, S1/S2 on 2026-10-20.** Both
products run inside the SBC web app with download endpoints - no
Colab dependency (the spec's Colab wrapper is a delivery detail we
replaced with our own UI + download endpoints).
