# Kundali Method (Financial Astrology) — Ingest for next build (2026-10-10)

Source: `SBC-Tool/Kundali Method -Financial Astrology.md` — a transcribed lecture
on timing market reversals from a chart's horoscope, with 14 reference screenshots
(`SBC-Tool/Pasted image 20261007*.png`, `20261010*.png`).

**Status: ingested, not built.** This note extracts the method into backlog items.
Nothing here is implemented yet, and nothing here is investment advice. The house
rule still applies: a forecast stays at the base rate until it passes both the
permutation test and the incremental test (`docs/GAP_ANALYSIS_PREDICTION_ENGINE_2026-10-03.md`).

---

## 1. What the method is

1. **Cast the D1 horoscope** of the instrument from its first trading date (NIFTY,
   a stock's listing date from the NSE, MCX for a commodity, or a significant date
   when the first trade date is unknown).
2. **Time the reversals from aspects**, two ways:
   - **Heliocentric:** aspects between Earth and each planet (the transcript's
     worked example). Jupiter gives multi-year moves; Mars gives 6–10 day swings.
   - **Transit-to-natal:** a transiting planet forming an aspect with a planet in
     the instrument's own D1 chart.
3. **Aspects used:** conjunction (0°), square (90°), sextile (60°), semi-square (45°),
   trine (120°), at **orb ≤ 2°**. The window's duration is how long the trend is
   expected to last.
4. **Trade the window, don't assume a reversal.** On the date, one of three things
   happens: pause, reversal, or continuation. A reversal needs a prior trend
   (higher-highs/higher-lows vs lower-lows/lower-highs).
5. **Entry and stop.** Mark the window day's high and low. A close beyond the high
   (even on a 30- or 60-minute candle) stops the trade out; re-enter on a small
   pullback. Risk is always limited.
6. **50% retracement trick.** A large candle on the window day tends to retrace 50%;
   use that level to tighten the stop.
7. **Targets.** Gann levels (Square of Nine from the day's high) and Fibonacci.
   RSI is an optional fifth confirmation, derivable from the tithi or the aspect.
8. **Per-instrument fit.** Backtest which planet an instrument "vibrates" to, and
   trade that pair (Earth–Mars and Sun–Venus are named as prominent).

## 2. What already exists (do not rebuild)

| Method step | Existing code | Verdict |
|---|---|---|
| Heliocentric Earth–planet aspects, 8 aspects, orb ±2°, window entry/exact/exit to the minute | `sbc/helio_aspects.py` | Done |
| Entry that reverses the prior trend; Gann + Fibonacci + indicator exit | `sbc/swing_model.py` | Done |
| TradingView payload for the entry dates | `/api/engine/aspect_windows?format=tv`, `tools/tradingview/astro_swing_windows.pine` | Done |
| Out-of-sample test, 2007–2026, 1/5/20 day | `docs/research/swing_validation_2026-10-03.md` | **102 of 102 tests: no edge** |

The transcript's heliocentric timing layer is therefore already built and already
graded, and it did not beat drift. New work should extend it, not duplicate it.

## 3. The gap (what the next build would add)

| # | Gap | Why it matters |
|---|---|---|
| G1 | **Transit-to-natal aspects.** A transiting planet aspecting a planet in the instrument's own birth chart. No module computes a natal chart or transit-to-natal contacts. | The transcript treats this as the primary timing method; heliocentric is the worked example of it. |
| G2 | **Per-instrument birth data.** `ANCHORS` in `sbc/engine.py` holds exchange dates only. A stock needs its NSE listing date; a commodity its MCX first-trade date. | The method is per script, not per index. |
| G3 | **Non-NIFTY bars.** `sbc/swing_model.py` reads NIFTY only (`Bars.nifty`). | Can't test a stock or commodity without its own series. |
| G4 | **Intraday stop rule.** The stop is a 30/60-minute close beyond the window day's high/low, plus the 50% retracement of a large candle. The model exits on daily bars. | This is the actual risk rule, and it needs intraday data the store doesn't have. |
| G5 | **Planet ranking per instrument.** "Which planet does this script vibrate to" — a pre-registered comparison, not a fit after the fact. | The transcript's claim that Earth–Mars and Sun–Venus stand out is testable. |

## 4. Proposed backlog (continues from B-48)

- **B-49 — Natal chart.** `sbc/natal.py`: given a birth date/time/place, return each
  planet's longitude (Swiss Ephemeris, Lahiri, matching the rest of the engine).
  Reuse `sbc/planets.py`. No new ephemeris code.
- **B-50 — Instrument registry.** Extend `ANCHORS` (or a sibling table) with a source
  for listing dates: NSE equity listing date, MCX first-trade date, and a manual
  override. Start with a hand-entered set; don't scrape.
- **B-51 — Transit-to-natal windows.** Generalise `sbc/helio_aspects.py` so the
  reference body can be a natal planet instead of Earth, same orb, same aspects,
  same entry/exact/exit output. This is the one new calculation.
- **B-52 — Per-instrument bars.** ✅ Done 2026-10-11: `Bars.for_symbol(symbol)` in `sbc/swing_model.py`; `Bars.nifty()` delegates to it. The research series were already in `data/market.db`, so no refresh was needed.
  Original scope: Let `swing_model.Bars` take any series
  `market_store` holds, not just NIFTY. Depends on `scripts/refresh_market_data.py --research`.
- **B-53 — Grade it.** Register the transit-to-natal reversal hypothesis *before*
  running it, then `scripts/validate_swing.py`-style report into `docs/research/`.
  Planet ranking (G5) is a separate pre-registered comparison in the same report.
- **B-54 — Intraday stop (blocked).** The 30/60-minute stop and 50% retracement need
  intraday bars. `/api/engine/market/ohlc` already reports that no 3-minute source is
  configured, so this waits on a data source. Do not fake it from daily bars.

## 5. Recommended first slice

**B-49 + B-51 + B-53, NIFTY only.** NIFTY's birth data and daily bars already exist,
so transit-to-natal can be graded without B-50 or B-52. If it shows no edge there,
the per-stock work (B-50, B-52) is not worth doing. B-54 stays blocked.

## 6. Open questions for the user

1. **Birth time.** The transcript says "morning" for one example and doesn't fix a
   time. The engine's anchors use `00:00`. Confirm the time to cast D1 charts at.
2. **Which aspects count.** The transcript names five (conjunction, square, sextile,
   semi-square, trine). The existing model tests eight. Use the five, or keep all eight?
3. **Orb.** Confirm 2° is the maximum, applied the same way to natal contacts.
