# EMA 9/21 HA matrix - pre-registered validation

Frozen before the run (module docstring).  Universe NIFTY 50; crosses on closed HA candles; forward returns close-to-close; baseline = 10,000 stratified permutations, two-sided p.

## 1d - C1: fresh-cross follow-through (49 symbols)

| direction | h | events | mean % | random mean % | p |
|---|---|---|---|---|---|
| cross up | +1 | 1013 | +0.34 | +0.06 | 0.000 |
| cross up | +5 | 1013 | +0.62 | +0.30 | 0.003 |
| cross up | +21 | 1013 | +1.58 | +1.26 | 0.106 |
| cross down | +1 | 1048 | -0.18 | +0.06 | 0.000 |
| cross down | +5 | 1048 | +0.21 | +0.30 | 0.458 |
| cross down | +21 | 1048 | +0.78 | +1.26 | 0.058 |

- C2 survival (up): 845/1013 = 83.4% still bullish 5 bars after the cross
- C2 survival (down): 839/1048 = 80.1% still bearish 5 bars after the cross

## C3: daily+weekly alignment vs daily alone (+21 sessions)

| conditioning | days | mean % | p |
|---|---|---|---|
| daily bullish | 27460 | +1.36 | 0.950 |
| daily+weekly bullish | 3966 | +1.44 | 0.852 |
| daily bearish | 20822 | +1.16 | 0.917 |
| daily+weekly bearish | 17858 | +1.15 | 0.821 |

## 1wk - C1: fresh-cross follow-through (50 symbols)

| direction | h | events | mean % | random mean % | p |
|---|---|---|---|---|---|
| cross up | +1 | 110 | +0.55 | -0.01 | 0.035 |
| cross up | +2 | 110 | +0.83 | +0.03 | 0.074 |
| cross up | +4 | 110 | +0.75 | +0.12 | 0.369 |
| cross down | +1 | 134 | -0.96 | -0.01 | 0.001 |
| cross down | +2 | 134 | -1.00 | +0.03 | 0.012 |
| cross down | +4 | 134 | -0.78 | +0.12 | 0.135 |

- C2 survival (up): 90/110 = 81.8% still bullish 5 bars after the cross
- C2 survival (down): 108/130 = 83.1% still bearish 5 bars after the cross

## 1h: no data
Download errors: 50 symbols skipped (first few: [('ADANIENT.NS', 'no data returned'), ('ADANIPORTS.NS', 'no data returned'), ('APOLLOHOSP.NS', 'no data returned')])

Reading: a cell is interesting only if it survives the honest read across the printed cells; the matrix's value as a DISPLAY does not depend on any of these cells being significant, only its value as a SIGNAL does.

## Verdict (added 2026-10-28, after the run)

- **C1:** the only cells that survive the 18-cell read are the immediate
  post-cross sessions: daily cross-up +1d (+0.34% vs +0.06%, p=0.000),
  daily cross-down +1d (-0.18%, p=0.000) and weekly cross-down +1/+2w
  (-0.96%/-1.00%, p=0.001/0.012).  The edge DECAYS: daily +21 is +1.58%
  vs +1.26% random (p=0.106) - no tradeable 21-session edge.  This is
  short-horizon momentum continuation, not a matrix discovery.
- **C2:** 80-83% state survival 5 bars after a cross is mechanical
  (EMA states are smooth by construction), not evidence of signal.
- **C3 (the matrix's core premise): NULL.**  Conditioning on daily+weekly
  alignment adds +0.08% over the daily state alone (+1.44% vs +1.36%)
  and nothing on the bearish side (+1.15% vs +1.16%).  The Bull Count /
  Bias aggregation - the whole point of the 7-timeframe matrix - carries
  no measurable information beyond the daily state itself.
- The 1h leg is incomplete (yfinance rate-limited all 50 downloads);
  rerun for completeness, but the daily/weekly verdicts stand.
- Bottom line: build the matrix as a DISPLAY (it is a good one), not as
  a signal engine.  If any cell deserves a follow-up study with honest
  power, it is the next-session behaviour after daily fresh crosses.
