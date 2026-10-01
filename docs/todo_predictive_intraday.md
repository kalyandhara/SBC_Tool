# Predictive Intraday Path – Todo List

## Readiness Assessment
- [x] Intraday projection endpoint exists `/api/intraday_projection`
- [x] KP intraday report endpoint exists `/api/kp_intraday_report`
- [x] UI panels for intraday projection and KP intraday present
- [x] Cumulative KP composite score series endpoint
- [x] Hora/DL-hora/Dahan/Chand-Vat overlay flags in API response
- [x] Frontend chart rendering for predictive path with colour bands
- [x] Validation against historical NIFTY intraday (`docs/INTRADAY_PATH_VALIDATION.md`,
      script `scripts/validate_intraday_path.py`, 31 days 2026-08-03..2026-09-15)

## Implementation Tasks — STATUS: COMPLETE (2026-09-19)
1. **API – Cumulative Path** ✅
   - `GET /api/engine/intraday_path` implemented in `sbc/api/engine_bp.py`
   - Canonical builder `build_cumulative_path(report)` in `sbc/kp_intraday.py`
   - Returns series: `{time, cumulative, score, hora_lord, dl_hora, dahan, chand_vat, markers}`

2. **Backend – KP Composite Scoring** ✅
   - `sbc/kp_intraday.py:build_cumulative_path(report, step_minutes)` helper
   - Scoring weights: hora quality map, regime shift delta (±1.5), window vote (±1.0)
   - DL-hora / Dahan / Chand-Vat flag logic included

3. **Frontend – Chart** ✅ (pre-existing)
   - Predictive Intraday Path panel with cumulative line + markers

4. **Data** ✅
   - KP data CSV covers market hours; 24h in-memory cache in `engine_bp.py`
   - Fixed: endpoint now reads `report.day_signature.hora_slots` (was always empty before)

5. **Testing** ✅
   - Unit tests for cumulative path builder (`tests/test_kp_intraday.py::TestBuildCumulativePath`)
   - Smoke test endpoint in `tests/test_integration.py`

## Definition of Done
- Endpoint returns series ready for chart.js / lightweight-charts
- UI renders path matching the example image layout
- Hora lords labelled on X-axis, vertical lines for regime shifts
- Can toggle hora / DL-hora / Dahan / Chand-Vat overlays
