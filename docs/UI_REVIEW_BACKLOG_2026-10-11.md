# End-to-end UI review — suggestion backlog (2026-10-11)

Reviewed on the running app (`http://127.0.0.1:8000`, the process started before today's
B-55..B-59 changes) in a 1509 px browser window: every tab opened in turn, with network
requests, console errors, rendered text and layout recorded. Bullion Week and the Transit
Almanac were reviewed separately on a render of the current code. Item numbers continue the
project's B- series.

Priority: **P1** wrong or broken for the user · **P2** slow · **P3** confusing or misleading ·
**P4** code health.

## P1 — broken or wrong

- **B-60 Overview shows "Prediction unavailable" next to a working forecast.** The forecast card
  (52.9% up, 68% range) loads, but the SBC Vedha panel below shows the error card. A direct call
  to the same `/api/prediction` returns 200 in ~170 ms, so a transient failure during the page-load
  burst (see B-66) leaves the error state stuck. Fix: retry once automatically, and clear the error
  on any later success.
- **B-61 Weekend dates sent to weekday-only endpoints.** The header date defaults to today. On a
  Sunday, `/api/kp_intraday_report?date=2026-10-11` returns 400 (seen on every load), and the
  Vedha prediction is computed for Sunday while the forecast card uses the next session
  (2026-10-12). Fix: default the header to the next trading day (`market_holidays.next_trading_day`)
  and say so ("next session: Mon 12 Oct").
- **B-62 "Advanced analysis" breaks the nav bar.** Opening it expands the list inline, making the
  bar 371 px tall, and the active tab button stretches to the full height as a tall yellow block
  (visible in the user's screenshot). Fix: render the advanced list as an overlay menu, or as a
  second row of tabs, so the bar keeps one line height.
- **B-63 Price chart wastes most of its width.** Chart & Timing loads 245 candles plus 543
  prediction days (178 future), and the candles end up squeezed into the right ~15% of the plot.
  Fix: set the initial visible range to the loaded candles plus ~30 future days, and let the user
  zoom out.
- **B-64 Page load triggers a 409.** `POST /api/kp_intraday_sample` returns 409 CONFLICT on
  every load (console error). Either don't call it when the sample exists, or treat 409 as "already
  there" without logging an error.
- **B-65 Monthly Projection: chart library CSS appears as page text.** The tab's text content
  includes `a#tv-attr-logo{--fill:#131722;...}`. Check whether it is visible; if so, move the
  lightweight-charts attribution style out of the content area.

## P2 — speed

- **B-66 One page load makes ~30 API calls, including duplicates.** On load: 12 separate
  `/api/prediction_series` calls (one per month, Jan–Dec), `/api/prediction` twice (10-11 and 10-12),
  `/api/astro/profile` twice; opening Monthly Projection calls `/api/daily_indication_balance` three
  times. Fix: one series call for the range; fetch each tab's data on first open; share in-flight
  requests.
- **B-67 Every tab is rendered at once.** About 9,000 DOM nodes, 30 canvases and 33 SVGs live in
  the page together. Switching tabs blocks the main thread: nine 2.5 s timed waits took over 45 s.
  Fix: build each tab on first open, and pause or destroy charts in hidden tabs.
- **B-68 The server handles one request at a time.** `run_app.py` uses Flask's built-in server
  (`app.run`), which serializes the load-time burst; that is the likely cause of B-60's transient
  failure. Fix: serve with `waitress` (pure Python, works on Windows) with 4-8 threads.

## P3 — confusing or misleading

- **B-69 KP Intraday Report shows a stale sample.** It opens on "Trading Day: sample report, not a
  live session" built from August 2026 data. Generate it for the selected session, or label it
  clearly as an example and show the date it represents.
- **B-70 KP Chart (NIFTY) opens empty.** Only the form shows (~330 characters) until Generate is
  pressed. Auto-run for the next session or show an empty state that says what will appear.
- **B-71 Seven tabs carry "no validated edge" warnings.** KP Intraday, KP Chart, KP Report, Crash
  Windows, Monthly Projection, Analog Lab and Swing Windows all say they are unvalidated or tested at
  chance. That fits the project's honest-forecast goal, but it puts research next to the forecast with
  equal weight. Suggest grouping them under "Research (unvalidated)" and keeping the main nav to:
  Overview/forecast, Forward Calendar, Bullion Week, Chart & Timing.
- **B-72 Header inputs apply to some tabs and not others.** The forecast card ignores the header
  date (always next session); the Vedha prediction, KP pages and sector heatmap follow it. Show an
  "as of" line on every tab, and make the header date the single source for all of them.
- **B-73 Data freshness isn't shown everywhere.** NIFTY shows "data as of 2026-10-09"; gold and
  silver (last bar 2026-10-02) and the bullion nakshatra record don't show their age. Reuse the
  existing freshness badge (`static/js/freshness.js`).
- **B-74 Transit Almanac: Mars row is crowded.** With fast-planet aspects off, Mars still stacks
  labels three deep. Show only the marker and date on the timeline, with details on hover and in the
  ledger.

## P3 — accessibility

- **B-75 Ten form controls have no label:** longitude and latitude degree/minute/second boxes
  (6), saved-profile select and import, `kota-date`, `kota-instrument`. Add `<label>`s or
  `aria-label`.
- **B-76 Emoji tab icons are read aloud** by screen readers. Mark the icon spans `aria-hidden="true"`.
- **B-77 Console noise:** 7 requests blocked by a browser extension (`ERR_BLOCKED_BY_CLIENT`)
  per load. Identify which URLs trip ad blockers and rename them if they're the app's own (paths
  with words like `track`, `analytics`, `ads`, `beacon` are common triggers).

## P4 — code health

- **B-78 `static/app.js` is 5,733 lines.** Newer tabs already live in `static/js/<tab>.js`. Move the
  remaining tabs out one at a time, starting with the Overview, which B-60, B-61 and B-66 all touch.
- **B-79 Remove Research Lab leftovers.** The page is removed (2026-10-11), but `initResearchLab()`
  in `app.js` and the `/api/research/*` routes remain. Check nothing else uses those routes, then
  delete them. The walk-forward route also returned 400 with the page's own defaults
  (train 730 / test 180 / step 180), so it was already broken.
- **B-80 42 inline `style=` attributes** in `index.html` (mostly legend swatches). Move them to
  classes so the light theme can restyle them.

## Suggested order

1. B-68 (waitress) and B-66 (fewer calls): they likely clear B-60 too.
2. B-61, B-62, B-63: visible bugs on the first screen.
3. B-67: tab-switch freezes.
4. B-71 and B-72: navigation and "as of" clarity.
5. The rest as cleanup.

## P1 outcome (2026-10-11)

- **B-60 fixed.** Root cause: `run()` reported "Prediction unavailable" for any exception in the
  block, including failures in the supporting loads (futurecast, lunar forecast, KP report) after the
  prediction itself had succeeded. Those now fail on their own (logged, not shown as a prediction
  failure), and the core `/api/prediction` request retries once on a network error or timeout.
- **B-61 fixed.** New `GET /api/market/next_session?date=` (uses `sbc.market_holidays`). The header
  date now starts from today **in IST** (it used the browser's clock, which is a day behind India on
  US evenings) and moves to the next NSE session on weekends and holidays, with the reason in the
  date field's tooltip. The first prediction runs after the date is settled.
- **B-62 fixed.** Root cause: the `.nav-tab` rule in `static/style.css` was never closed, so the
  Advanced analysis dropdown rules were parsed as nested inside it and never applied. Rule closed;
  the menu is now an overlay (bar stays 55 px with it open, was 371 px), uses theme colours, closes on
  a pick, an outside click or Escape, and is highlighted when the active page is inside it. A test
  now fails if any CSS rule is nested inside another.
- **B-63 fixed.** The price chart called `fitContent()`, which also fitted six months of future
  forecast bands and crash bands. It now opens on the loaded candles plus ~30 forecast sessions;
  zoom out for the rest.
- **B-64 not a bug.** Only the "Generate KP Data" buttons send `POST /api/kp_intraday_sample`; the
  409 means the month already has ephemeris data, which the page handles. The browser console keeps
  messages across reloads, which made it look like a page-load error. The 409 is a deliberate,
  tested contract (`test_generate_endpoint_refuses_to_overwrite_real_data`) and is kept.
- **B-65 not a bug.** The `tv-attr-logo` text is a hidden `<style>` element (display: none) from
  the chart library; it was picked up by a text extraction, not shown on screen.

Tests: `tests/test_ui_review_p1.py` (5).

Side finding: `tests/test_integration.py::test_kp_report_generation` writes
`data/kp/KP_Data_Jun2026.csv` and doesn't remove it, which is why that file keeps appearing
untracked.

## P2 outcome (2026-10-11)

- **B-68 premise corrected.** Flask's `app.run` has been multi-threaded by default since Flask 1.0,
  so the server already handles requests in parallel; waitress would add little. Threading does
  expose a shared-state risk instead: Swiss Ephemeris' sidereal mode (Lahiri vs Krishnamurti) is one
  process-wide setting, used from request threads and the background warm-up and ledger threads.
  New `sbc/ephem_guard.py`, installed first thing in `sbc/__init__.py`, makes the mode per-thread
  without touching the 66 modules that set it. A forced-switching stress test (16,000 calls, 8
  threads) produced no wrong results with or without the guard, so this is insurance against a
  theoretical race, not a fix for an observed one. Cost: one lock per ephemeris call.
- **B-66 done.**
  - Identical GET requests already in flight now share one network call (`fetchWithTimeout`).
  - Monthly Projection's 30-day computation can't be started twice for the same date (it was
    started up to three times by its four triggers).
  - The year-long Calendar Confluence grid (12 heavy requests, below the fold on Overview) starts
    when it scrolls into view instead of on page load.
- **B-67 partly done.** The price chart (a year of candles plus a six-month overlay, the heaviest
  hidden render) builds the first time Chart & Timing opens. Other tabs still build at start-up;
  converting each one is part of the `app.js` split (B-78).
- Cache-busting versions bumped: `style.css?v=24`, `app.js?v=39`, `nifty-chart.js?v=18`.

Tests: `tests/test_ephem_guard.py`. Full suite: 630 passed, 6 skipped; the 4 failures are the
Yahoo-dependent tests that can't reach the network from the sandbox.

Side finding resolved: `data/kp/KP_Data_Jun2026.csv` was left by an earlier test run in the
sandbox while file deletion was off; the test's own cleanup works and the file is removed.

## P3 outcome (2026-10-11)

- **B-69 done.** KP Intraday Report no longer shows the September sample pasted into
  `index.html`; it loads the live report (`/api/kp_intraday_report`, HTML) for the header date's
  session on open, moving to the next session on weekends and holidays, with a status line naming
  the date.
- **B-70 done.** KP Chart (NIFTY) loads the header date's report the first time it opens.
  Note: B-69 and B-70 now show the same report. Merging the two tabs is left to the user.
- **B-71 done.** Main bar: Executive Overview, Chart & Timing, Sector Heatmap, Forward Calendar,
  Bullion Week. The dropdown is renamed "Research · unvalidated" and holds the seven pages that
  carry no-edge warnings (KP Intraday, KP Chart, KP Report, Crash Windows, Monthly Projection,
  Analog Lab, Swing Windows).
- **B-72 done.** A "Session Mon, 12 Oct 2026" chip in the nav bar shows the date the pages are
  computed for; it follows the header date and the next-session default.
- **B-73 done.** Bullion Week warns when the gold or silver price file ends more than 7 days before
  the week shown.
- **B-74 done.** Transit Almanac: Mars, Venus and Mercury aspects show a marker only (details in the
  tooltip and ledger), so those rows are readable.
- **B-75 done.** The ten unlabelled controls have `aria-label`s.
- **B-76 done.** Tab icons are `aria-hidden`.
- **B-77 not an app issue.** The `ERR_BLOCKED_BY_CLIENT` errors came from the review browser (the
  Claude desktop app's built-in browser); every resource the page references loads.

Cache-busting versions: `style.css?v=25`, `app.js?v=40`, `transit-almanac.js?v=3`,
`bullion-week.js?v=4`.

## P4 outcome (2026-10-11)

- **B-78 first slice done.** `static/app.js` 5,865 → 4,049 lines. Moved unchanged into classic
  scripts loaded right after it: `static/js/kp-intraday.js` (KP Intraday, KP Chart, KP Report,
  728 lines), `static/js/overview-calendars.js` (Monthly Projection, Bhadra, confluence grid,
  monthly heatmap, 674), `static/js/sector-dashboard.js` (232). Still in `app.js`: Overview
  rendering, run(), settings, tab switching, and the six panels marked "commented out in UI"
  (sector vedha, large-cap, FMCG, tourism, chemical, alcohol), which look dead and are a separate
  decision.
- **B-79 done.** Research Lab JS (181 lines) and the four `/api/research/*` routes plus their only
  helper (388 lines of `research_bp.py`) removed; the other routes in that blueprint are untouched.
- **B-80 done.** 39 of 42 inline `style=` attributes moved to classes; hard-coded dark colours now
  use theme tokens. The three `display:none` ones stay inline because scripts show those elements
  by clearing the inline style.
- **Verification.** The app was run twice side by side (before/after) and every tab probed in a
  headless browser: same text, charts, API calls (23 on load) and errors on all 12 tabs, and
  screenshots pixel-identical apart from the Overview's "generated at" time.
- **Correction to B-60.** The original finding was an artefact: the error card is hidden with a
  class, and the review read hidden text; the user's screenshot showed it because the stylesheet
  hadn't loaded. The P1 change stays as hardening.
- **New findings from the probe:** `GET /api/backtest/moon?...&vedha=false` returns 400 on every
  page load; the Bhadra calendar can time out at 8 s on a cold server (`/api/bhadra_calendar` is
  not in `HEAVY_ENDPOINTS`).
