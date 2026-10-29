# Ingest: NSEBANK Gann Square-of-Nine daily forecast (2026-10-11)

Source: `docs/reference/NSEBANK_gann_forecast_2026-09-14.docx` (from Telegram, dated 14 Sep 2026).
Target: the **Chart & Timing** tab. Item numbers continue the B- series.

## What the report does

- Takes the last daily close of `^NSEBANK` (11 Sep 2026: 56,606.55), with 500 Yahoo daily bars of history.
- Projects Square-of-Nine levels: `level = (sqrt(close × m) ± degrees/180)² / m`. Here m (the price multiplier) is chosen automatically, and was 1 for Bank Nifty.
  I checked this against the report: (√56,606.55 + 45/180)² = 56,725.57, which matches its primary high.
- Lists levels at ±45, 60, 90, 120, 135, 144, 180, 216, 225, 240, 270, 300, 315 and 360°. Each level is tagged by family:
  - core 45°
  - secondary 60°
  - special 144/216
- The primary band is ±45° (56,487.65 – 56,725.57). A close above the band reads as strength, below as weakness, and inside as neutral.
- Each level carries a **next-day touch probability**: the share of historical next-day Highs (for upside levels) or Lows (for downside levels) that reached it. These fall with distance: ±45° is about 70%, ±360° about 7%.
- Its own diagnostic: the whole next bar fell inside the ±45° band only **0.2%** of the time. The report itself says it has no established edge.
- It also shows a 60-close chart with the ±45° levels, and the 14-bar average range (478.78).

## What the app already has

- `sbc/swing_model._sq9_levels`: the same formula in 1/8-root steps (= 22.5° increments), used only as a swing exit layer.
- `/api/gann/precision` and `sbc/gann_zones.py`: range-fraction Gann zones on the Chart & Timing price chart. These are a different method from Square-of-Nine.
- `market_store` has NIFTY, SENSEX and VIX locally. **There is no Bank Nifty**, so it would need Yahoo, which has been failing lately.

## Enhancement backlog (Chart & Timing)

- **B-81 Square-of-Nine daily levels panel.**
  - Instrument picker (NIFTY, BANKNIFTY, SENSEX) and an "as of" close date.
  - Levels table from the report: side, degrees, level, family and touch %, centred on the close.
  - Primary-band verdict: strength, weakness or neutral.
  - Move the formula into `sbc/gann.py` as `sq9_levels(price, degrees, multiplier="auto")` and reuse it in `swing_model`.
  - New endpoint `/api/gann/sq9?symbol&date`.
- **B-82 Touch probabilities with a control.** Compute next-day touch % per level from local bars, as the report does.
  - Also show the touch % for an **equal-distance level that is not on the Square of Nine**: the same number of points away, or the same multiple of ATR14.
  - The report's percentages mostly measure distance from the close. Only the gap between the Square-of-Nine column and the control column says anything about the method.
- **B-83 Overlay on the price chart.**
  - A "Sq9 levels" toggle beside "Gann Zones" draws the ±45° band and the next 90/180/360° levels as price lines from the latest close.
  - Each line is labelled with its degrees.
- **B-84 Bank Nifty in the local market store.**
  - Add `"BANKNIFTY": ("^NSEBANK", "2007-09-17")` to `market_store.SYMBOLS` so B-81 to B-83 don't depend on live Yahoo calls.
  - Nightly refresh, as for NIFTY.
- **B-85 Pre-registered test: are Square-of-Nine levels reaction points?**
  - Before looking at results, register this in `claude/preregistrations.md`. On days when the next bar touches a level, is the reversal rate higher at Square-of-Nine levels than at equal-distance control levels?
  - Measure reversal as a close back on the near side of the level, for NIFTY and BANKNIFTY from 2008 onwards.
  - Use a permutation test against shifted levels, with BH correction across the 14 angle steps.
  - The panel stays labelled "unvalidated" until this test passes.
- **B-86 Report export.** An Infographic/DOCX button for the B-81 panel that reproduces this report's layout:
  - summary table
  - recent OHLC
  - 360° level guide
  - diagnostic
  - 60-close chart
  - method and limitations

Suggested order: B-84 → B-81 → B-83 → B-82 → B-85 → B-86.
