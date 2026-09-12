# SBC Tool Session Summary

## Objective
Enhance Sarvatobhadra Chakra web app with Birth Data Entry, Astro-Wellness, Monthly Sector Confluence Heatmap, Lunar Timing, Nakshatra Sector Bias backtest and Trading Signals Astro-Technical dashboard.

## Key Work Completed
- Flask venv `d:\SBC_Tool\venv\Scripts\python.exe` verified
- Birth Data Entry form with popover calendar/clock, DMS coords, timezone, altitude/pressure/temp
- City search cached to SQLite `data/cities.db`
- Astro personal endpoints + profile CRUD persistence
- Wellness tracker: habits, streaks, Weekly Summary, Export Habits CSV, server-side `habit_logs`
- Monthly Sector Confluence Heatmap fixes: Nifty Infra zero bug, sector gap analysis, new rows Defense/Shipping/Travel/Agri/Renewable/Other
- Lunar timing strip symbolized with icons, popover, detail panel, legend
- Nakshatra sector mapping backtest with yfinance, directional vedha backtest
- Daily Nakshatra + SBC Sector Confluence dashboard with 7-day forecast & CSV export
- Pine Script skeleton + strategy
- Webhook `POST /webhook/sbc`, `GET /api/sbc/latest`
- Trading Signals Astro-Technical panel with INTRADAY/SWING/POSITIONAL tabs, live Astro Score, signals, Reversal Zone, Sector Map
- Nakshatra Sector Astro Chart with lightweight-charts candlesticks, SBC vedha overlay line, Nakshatra markers, legend, toggle, hover tooltip, CSV download
- Price API with MultiIndex flatten and server/client fallback tickers CNX→NSE
- Vedha daily API with real monthly heatmap fallback to synthetic

## UI Bug Found & Fixed
**Bug:** Trading Signals panel HTML malformed after edits.
- `<div id="trading-signals-details">` opened, inner `<div id="astro-score">` never closed, sector selector and chart divs escaped hierarchy.
- Result: Hide Details toggle hid partial content, elements rendered outside container.

**Fix:** Re-indented hierarchy in `templates/index.html:822-853`:
```
<div id="trading-signals-details">
  <div id="astro-score">...</div>
  <div class="monthly-heatmap-controls">sector select...</div>
  <div id="nakshatra-astro-chart">...</div>
  <h1 id="astro-score-label">...</h1>
  <div id="astro-score-sub">...</div>
  <div id="astro-signals-list"></div>
  <div id="reversal-zone">...</div>
  <div id="sector-map">...</div>
</div>
```

## Remaining Gaps
- Vedha API falls back to synthetic if heatmap shape mismatches; validate output shape
- Chart reload leaks instances; need destroy previous chart & unique IDs for legend controls
- Sector name ↔ heatmap row mapping must be exact for real scores
- Client does not show fallback ticker name after retry
- Crosshair tooltip updates legend attribute only; add visible tooltip
- Chart does not resize on window resize
- Accessibility: Hide Details button missing aria-expanded

## Relevant Files
- `templates/index.html` – main UI, Trading Signals panel
- `static/style.css` – planet icons, form, wellness styling
- `static/app.js` – heatmap, lunar strip, habits, nakshatra dashboard
- `app.py` – Flask routes: cities, astro personal, tz, profiles, habits, monthly_heatmap, webhook, price, vedha_daily
- `sbc/monthly_heatmap.py` – `NIFTY_SECTOR_ROWS`, `_day_sector_net`
- `sbc/confluence.py` – `SECTOR_ALIASES`, `normalize_sectors`
- `data/profiles.db`, `data/cities.db`, `data/latest_sbc_signal.json`

## Next Moves Completed
1. Make chart load idempotent; destroy previous instance ✓
   - `nakshatraChartInstance` removed before new create, unique IDs for legend controls
2. Validate and align heatmap output shape; log mismatches ✓
   - `api_vedha_daily` logs shape warnings, returns `source:"real"` when available
3. Replace synthetic vedha with empty + warning ✓
   - Returns `score:null, nakshatra_idx:null, source:"missing"` and logs warning
4. Add resize observer for chart ✓
   - `ResizeObserver` updates chart width on container resize
5. Add proper hover tooltip and aria attributes ✓
   - Hide Details button has `aria-controls`/`aria-expanded`
   - Floating tooltip shows Date/Vedha/Nakshatra on crosshair move

*Generated Sat Sep 05 2026*
