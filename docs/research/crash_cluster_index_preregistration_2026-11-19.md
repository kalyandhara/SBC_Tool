# Crash Cluster Index (CCI) and NIFTY/DJIA: pre-registration

> **Research document. Not financial advice.**

**Status: frozen before any outcome was computed (2026-11-19).** The definitions, windows,
outcomes, tests and pass rule below were written before `sbc/crash_cluster.py` was run on any
price data. A change after the first run is a new version and must be disclosed as in-sample.
The **Results** section at the end is filled in once, from a single run.

Source: T1.4 and T1.5 in `docs/research/crash_engine_audit_2026-11-19.md`. The CCI is not
wired into any UI or production score.

## Question

When three independent families of astrological crash conditions are active at the same time,
do NIFTY and DJIA show:
- lower forward returns,
- deeper forward drawdowns, or
- higher forward realized volatility,

than ordinary sessions with the same same-day move? Does the difference hold in both eras and
in both markets?

## Fixed inputs

| Item | Value |
|---|---|
| Ephemeris | Swiss Ephemeris, Moshier, geocentric, sidereal Lahiri (`sbc.planets` conventions). Aspect angles don't depend on the zodiac. |
| Sky time | 09:15 IST on each session date (the project's standing sky time). |
| Hard aspect | Unsigned separation (0–180°) within the orb of 0°, 90° or 180°. |
| Applying | \|separation − target\| is decreasing at the sky time. This is computed from the longitudes and longitudinal speeds at that instant: first-order step dt = 0.01 day. |
| Stations | `sbc.stations.between` (exact sign change of sidereal speed). A station is placed on the first session on or after its IST date. |
| Eclipses | `sbc.backtest._eclipses_in_year` (the B2 lookup). Every type Swiss Ephemeris returns, solar and lunar, penumbral included, in any sign. |

The flags depend only on the date. The ephemeris is a deterministic function of time and can
be computed in advance, so windows that look a few sessions ahead (stations, eclipses) use no
market information. No flag ever reads a price.

## Families (one vote each)

| Family | Condition on a session (any member makes the family true) |
|---|---|
| **B: backdrop** | A hard aspect between any two of Saturn, Uranus, Neptune and Pluto, ≤ 3° and applying. |
| **T: trigger** | (a) a hard Mars–Saturn aspect ≤ 3° and applying; or (b) a hard Mars–Uranus aspect ≤ 3°; or (c) a hard Mars–Pluto aspect ≤ 3°; or (d) a Mars station within ±3 sessions. (b) and (c) carry no applying condition, as T1.4 states them. |
| **W: timing** | (a) an eclipse maximum within ±10 calendar days of the session date; or (b) a Saturn, Uranus, Neptune or Pluto station within ±5 sessions. |

- `CCI = B + T + W` (0–3), where each family is 0 or 1. This is never a weighted sum.
- **The CCI fires at CCI = 3.**
- **Episodes:** a run of consecutive sessions with CCI = 3 is one episode. The episode's first
  session is the event.

## Samples

| Market | File | Eras |
|---|---|---|
| NIFTY (primary) | `data/nifty_ohlc.csv` as committed on `master` (2007-09-17 onward) | 2007-09-17 to 2014-12-31; 2015-01-01 onward |
| DJIA (replication) | `data/djia_ohlc.csv` as committed (1992-01-02 onward) | 1992-01-02 to 2014-12-31; 2015-01-01 onward |

Close prices only.

## Outcomes (all measured from the event session's close)

| Outcome | Definition | Expected direction if the hypothesis holds |
|---|---|---|
| Forward return | close[t+h] / close[t] − 1 | Negative excess |
| Max drawdown (T1.5) | min(close[t+1..t+h]) / close[t] − 1 | Negative excess (deeper) |
| Realized volatility | Standard deviation of daily log returns over t+1..t+h | Positive excess |

- Horizons: h = 5 and h = 20 sessions. This gives **6 tests per market**: 3 outcomes × 2 horizons.
- **Cost:** a short or hedge position on the forward-return outcome pays 0.20% round trip (the
  `sbc.confluence_engine.net_trade_return` convention). The forward-return test can pass only if
  the mean excess is ≤ −0.20%.
- Drawdown and volatility are risk-forecast outcomes, not trades, so no cost applies to them.

## Test

- **Control:** decile-matched. Each session's same-day move `r0 = close[t]/close[t−1] − 1` is
  binned into full-sample deciles. Each event is compared with the mean outcome of the non-event
  sessions in its decile, using `sbc.planetary_event_timeline.excess_statistic`.
- **p-value:** two-sided, from the decile-preserving permutation of event labels
  (`permutation_p`), 10,000 iterations, seed 42.
- **Benjamini-Hochberg:** applied within each market across its 6 tests.
- **Minimum:** 15 episodes per market. Below that, the market is reported as "insufficient" and
  not graded.

## Pass rule (per outcome × horizon)

**edge** only if every one of these holds:
1. NIFTY q < 0.05 **and** DJIA q < 0.05;
2. the excess has the expected direction in all four market × era cells;
3. for forward return, the NIFTY mean excess is ≤ −0.20% (it beats costs).

Otherwise the result is **no edge**, or **insufficient** if either market has fewer than 15
episodes. The CCI as a whole is graded **edge** only if at least one outcome × horizon passes.

## Placebos

1. **Shifted sky.**
   - 20 lags are drawn uniformly from 180–720 days, using `numpy.random.default_rng(42)`.
   - For each lag, the CCI is recomputed with every session's sky date = session date + lag.
     Stations and eclipses are placed by the same shifted mapping.
   - The 6 NIFTY tests are run with 2,000 permutation iterations each.
   - Reported: how many of the 20 × 6 placebo tests reach p < 0.05.
   - Expectation under the null: about 5%. If the real CCI's p-values aren't clearly better than
     the placebo distribution, the result is treated as noise, whatever its q.
2. **Hash placebo.**
   - Events are sessions whose `sha256(date)` first byte is < k. k is set so the expected count
     equals the number of NIFTY CCI episodes. Those events are then collapsed into episodes and
     run through the same 6 NIFTY tests.
   - A monthly version uses `sha256(YYYY-MM)` instead. It mirrors `rule_signals.placebo_daily`
     and `placebo_monthly`.

## Not part of this registration

- Regime controls (trailing drawdown and volatility deciles, audit section 6.2 item 4).
- Weights.
- Any other family member.
- Any change after the first run. Each of these is a new version.

## Prior expectation

**No edge.** Every earlier crash-related test in this repo (rule, factor, transit, natal and
station families) returned no edge.

## Results


Single run on 2026-11-19 with `scripts/validate_crash_cluster.py`, working tree on branch
`fix/crash-b1-b2` (uncommitted). Nothing was tuned before or after the run.

**Verdict: insufficient.**
- NIFTY produced 11 CCI = 3 episodes, below the registered minimum of 15. So no forward-return,
  drawdown or volatility statistic was computed or graded for either market.
- DJIA, with 25 episodes, was not tested on its own. The pass rule needs both markets.
- No shifted-sky lag reached 15 NIFTY episodes, so the placebo has 0 graded tests.
- The hash placebos ran and are shown for completeness only.

The CCI as defined is too rare on NIFTY's 19-year sample to test. Loosening any orb or window
to get more episodes would be a new, in-sample version and must be registered and disclosed as
such.

### Run output (verbatim)

- NIFTY: 4694 sessions 2007-09-17..2026-11-04; CCI=3 on 49 sessions, 11 episodes; family rates B 0.182, T 0.178, W 0.473
- DJIA: 8765 sessions 1992-01-02..2026-10-23; CCI=3 on 118 sessions, 25 episodes; family rates B 0.183, T 0.183, W 0.462

**Verdict: insufficient** (fewer than 15 episodes in at least one market).
- Shifted-sky placebo (NIFTY, lags [228, 598, 534, 417, 414, 644, 226, 557, 288, 230, 464, 707, 578, 591, 568, 605, 457, 249, 634, 423]): 0/0 placebo tests with p < 0.05 (nan%); real CCI p-values: 
- Hash placebo (daily, 12 episodes): p = fwd_return/5 0.2729, fwd_return/20 0.9980, max_drawdown/5 0.1504, max_drawdown/20 0.2019, realized_vol/5 0.2684, realized_vol/20 0.1229
- Hash placebo (monthly, 10 episodes): p = fwd_return/5 0.7496, fwd_return/20 0.7071, max_drawdown/5 0.4838, max_drawdown/20 0.6087, realized_vol/5 0.9085, realized_vol/20 0.7536

