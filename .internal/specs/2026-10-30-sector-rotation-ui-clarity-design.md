# Specification: Sector Rotation UI Clarity Enhancement

## Overview
Enhance the Sector Rotation tab (`tab-rotation`, `static/js/sector-rotation.js`) to provide transparent explanations of descriptive vs. validated signals, data coverage limits (12 of 15 sectors covered; Media, Healthcare, Oil & Gas missing in yfinance), and explicit guidance that past event outcomes show no statistically validated out-of-sample edge.

## Objectives
1. **Prominent Explanatory Banner:** Replace the simple one-line banner with a structured guidance box answering what the charts show, confirming there is no validated edge (0/511 passes), and clarifying historical base rates vs. predictive signals.
2. **Panel-Specific Tooltips & Subtitles:** Add contextual explanations for Heatmap, Rotation Matrix, Rotation Wheel, and Sankey Flow panels.
3. **Data Coverage Disclosure:** Explicitly note missing sector coverage (Media, Healthcare, Oil & Gas) so users understand why 12 sectors appear instead of 15.

## Technical Changes
- **`static/js/sector-rotation.js`:**
  - Update `srBanner` to render an informative multi-bullet disclaimer and context card.
  - Add explanatory subtitles to `srHeatmap`, `srRotationMatrix`, `srWheel`, and `srSankey`.
- **`static/style.css`:**
  - Add styling rules for enhanced info boxes and guidance callouts.

## Verification Plan
1. Open http://127.0.0.1:8000/#tab-rotation in Playwright/browser.
2. Verify banner content, explanatory notes on each sub-panel, and clear distinction of descriptive stats.

## Stress Test Results: Sector Rotation UI Clarity Enhancement

### Resolved Decisions
- [Disclaimer Expansion]: Approved structured info box clarifying descriptive status and 0/511 validated edge.
- [Coverage Disclosure]: Approved explicit disclosure of missing yfinance sector coverage (Media, Healthcare, Oil & Gas).
- [Panel Subtitles]: Approved instructional subtitles across Heatmap, Rotation Matrix, Wheel, and Sankey.
- [Security & Risk]: Verified secure DOM rendering via `textContent` and SVG attributes.

### Changes Made
- None to core backend logic; front-end UI enhancements specified.

### Confidence Assessment
- Overall: High
- Areas of concern: None.
