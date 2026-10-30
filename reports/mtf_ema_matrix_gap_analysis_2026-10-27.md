# Gap analysis — EMA 9/21 multi-timeframe Heikin-Ashi trend matrix (2026-10-27)

Source: a spreadsheet screenshot ("EMA 9/21 Multi-Timeframe Trend Matrix
(Heikin Ashi candles)", as of 27-10-2026 15:30 IST, universe Nifty 50).
This is a screener-method artifact, not a video; the analysis grades the
method against what the repo already computes, states what is missing,
and flags what the house rules require before any of it becomes a signal.

## 1. The method as stated (frozen from the legend)

- EMA 9/21 per timeframe on **Heikin-Ashi** candles, seven timeframes:
  5m, 10m, 15m, 30m, 1h, Daily, Weekly; universe Nifty 50; the running
  candle is included.
- Bullish = EMA9 > EMA21; Bearish = EMA9 < EMA21.
- `(n)` = candles since the crossover (state age); "n/a" = not enough
  data; no number = no crossover in the loaded window.
- **Weak** (paler, italic) = HA close not beyond both EMAs — a strength
  filter on the state.
- ▲/▼ = crossed on the latest candle (fresh-cross flag).
- Aggregation: Bull Count (x/7) and a Bias label ("Strong Bullish" etc.),
  and a Price column at the actual last traded price.

## 2. What the repo already has (evidence)

| piece | where | status |
|---|---|---|
| Heikin-Ashi transform | `sbc/screener/indicators.heikin_ashi()` | exact |
| EMA | `sbc/screener/indicators.ema()` | exact |
| Multi-timeframe batch downloads | `sbc/screener/data.py`: TIMEFRAMES 5m/10m/15m/1h/1d/1wk with Yahoo history clamps (intraday 60d, 1h 730d) and **`batch(as_ha=True)`** — HA is built into the batch | exact for 6 of the 7 timeframes |
| EMA cross state + age | `sbc/screener/engine.py` ema mode: EMA(fast)/EMA(slow) cross signals and `candles_held` = bars since the cross | the matrix's `(n)` exists as `candles_held` |
| Nifty 50 universe | `sbc/screener/universes.load("nifty50")` | exact |
| Trade tracking off an EMA cross (entry, trailing slow-EMA stop, P&L) | engine ema mode | more than the matrix does |
| 30-minute bars | — | **missing** (no "30m" anywhere in sbc/ or scripts/) |
| Multi-timeframe state snapshot (per-symbol x per-timeframe state table) | — | **missing** |
| Bull-count / bias aggregation | — | **missing** |
| "Weak" strength filter (HA close not beyond both EMAs) | — | **missing** |
| Fresh-cross flag on the latest bar | derivable from the cross conditions | not surfaced |

Reading: the matrix is ~70% buildable from existing parts. The primitives
(EMA, HA, batch MTF downloads, cross+age) are already library-grade; what
is missing is a state-snapshot layer on top of them, one interval, two
flags, and the aggregation.

## 3. The gaps, each with its build

1. **30m timeframe.** Add `"30m": ("30m", 60)` to
   `sbc/screener/data.TIMEFRAMES` (+ a default lookback). Yahoo serves
   30m within the same 60-day window as 5-15m. Trivial.
2. **State-snapshot module** (`sbc/screener/mtf_matrix.py`): for each
   symbol, for each timeframe: current EMA9/21 state on HA candles, age
   (candles since the cross, from the same shift logic the engine uses),
   weak flag, fresh-cross flag. Output: one row per symbol with the
   7-tuple of states + bull count + bias. This is new code but sits
   entirely on existing primitives.
3. **Bias rule is undefined in the source.** The legend does not state
   the mapping from Bull Count to Bias (the image shows 7/7 → "Strong
   Bullish" but also 6/7 → "Strong Bullish" and 5/7, 4/7 → "Bullish").
   Before building, freeze a rule — e.g. 7/7 Strong Bullish, 6/7
   Bullish (Strong-candidate), ≤3/7 mirrors for bearish — otherwise the
   headline label is unfalsifiable. Same discipline as the debt-threshold
   gap in `docs/SCREENING_METHOD_INGEST_2026-10-11.md`.
4. **"Weak" filter needs a frozen reading.** "HA close not beyond both
   EMAs" is ambiguous in the edge cases (beyond one but not the other;
   equal). Freeze: weak = NOT (HA close > both EMAs) for a bullish
   state, mirrored for bearish.
5. **Running candle conflicts with the repo's closed-candle convention.**
   The engine evaluates "on closed candles; a signal fires on the bar
   the conditions first turn true". The matrix includes the running
   candle, so its 15:30 snapshot cannot be reproduced from stored bars
   and any cell can flip until the bar closes (HA open/close both depend
   on the running bar). Recommendation: build the snapshot on closed
   candles and render the running bar as a separate provisional cell
   marker, not as part of the state. This keeps every stored report
   reproducible.
6. **No validation.** The matrix is a display, but it implies testable
   claims: (a) 7/7 alignment persists (continuation), (b) fresh crosses
   (▲/▼) have follow-through, (c) MTF alignment beats a single
   timeframe. None has been tested. Under the house rules (B-70
   pattern), the study is pre-registered before the run: for each
   Nifty 50 name, conditional forward returns +1/+5/+21 sessions after
   a fresh EMA9/21-HA cross on a timeframe, vs a matched baseline of
   random non-cross days (same permutation design as
   `scripts/study_retrograde_reversal.py`), and alignment-conditioned
   returns (daily+weekly bullish vs daily alone) on 1d/1wk/1h history.
   The 5-15m legs can only be described, not validated — Yahoo serves
   ~60 days, ~2,300 bars per name, too thin for anything but a
   description.

## 4. Relation to the eVector adoption list

The matrix is a simpler cousin of adoption item 4 (the 7-state momentum
machine): its state = {Bullish, Bearish} x {Strong, Weak} x age. If the
screener is upgraded to the eVector-style state machine
(Ignition/Acceleration/Expansion/HealthyPullback/Weakening/Breakdown
with transition reasons), the MTF matrix becomes one presentation of it
— a state grid with ages — rather than a separate subsystem. Build the
snapshot layer so its per-timeframe output is a state object, not a
boolean, and both views stay available.

## 5. Verdict

- **Already covered:** HA transform, EMA, 6 of 7 timeframes with
  history-aware batch downloads (including `as_ha`), cross detection
  with bar-age counting, the Nifty 50 universe, and trade tracking off
  the cross.
- **Missing (small build):** 30m interval; the per-symbol x per-
  timeframe state snapshot with weak/fresh flags; bull-count/bias
  aggregation; an Excel/report panel for it.
- **Missing (before it means anything):** a frozen Bias rule and weak
  definition, the closed-candle convention decision, and the
  pre-registered validation of the fresh-cross and alignment claims.
- The build itself is roughly a day: ~40 lines in `data.py`, a new
  ~150-line `mtf_matrix.py` + tests, a report sheet. The validation
  study is the part the repo's own standards will not let skip.
