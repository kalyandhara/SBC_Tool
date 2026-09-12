# Predictive Intraday Path – Todo List

## Readiness Assessment
- [x] Intraday projection endpoint exists `/api/intraday_projection`
- [x] KP intraday report endpoint exists `/api/kp_intraday_report`
- [x] UI panels for intraday projection and KP intraday present
- [ ] Cumulative KP composite score series endpoint
- [ ] Hora/DL-hora/Dahan/Chand-Vat overlay flags in API response
- [ ] Frontend chart rendering for predictive path with colour bands
- [ ] Validation against historical NIFTY intraday

## Implementation Tasks
1. **API – Cumulative Path**
   - Create `GET /api/engine/intraday_path?date=YYYY-MM-DD&instrument=NIFTY`
   - Aggregate KP hora_slots, regime shifts, window scores into cumulative composite score per 5-min/15-min interval
   - Map DL-hora, Dahan, Chand/Vat flags from KP data
   - Return series: `{time, cumulative_score, hora_lord, dl_hora, dahan, chand_vat, sbc_bias}`

2. **Backend – KP Composite Scoring**
   - Extend `sbc/kp_intraday.py` with `build_cumulative_path(report)` helper
   - Define scoring weights: hora quality, regime shift strength, window score
   - Add DL-hora detection logic
   - Add Dahan/whipsaw and Chand/Vat high-conviction flags

3. **Frontend – Chart**
   - Add panel tab “Predictive Intraday Path”
   - Render top line chart: cumulative score with markers for signals
   - Colour bands: dotted hora, gold DL-hora, grey Dahan, green Chand/Vat
   - Bottom pane: TradingView embed for NIFTY 3-min candlesticks

4. **Data**
   - Ensure KP data CSV generation covers market hours with minute resolution
   - Cache KP composite paths for 24h

5. **Testing**
   - Unit test cumulative path builder
   - Smoke test endpoint for 2026-08-15
   - Visual check of overlay bands

## Definition of Done
- Endpoint returns series ready for chart.js / lightweight-charts
- UI renders path matching the example image layout
- Hora lords labelled on X-axis, vertical lines for regime shifts
- Can toggle hora / DL-hora / Dahan / Chand-Vat overlays
