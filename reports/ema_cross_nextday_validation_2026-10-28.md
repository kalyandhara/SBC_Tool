# EMA 9/21 HA daily fresh cross - next-session study

Pre-registered before the run (docstring).  Question: does the +1-session edge after a daily fresh EMA9/21 HA cross survive matching on the SAME-DAY return (i.e. is it the cross, or just big-move-day continuation)?  Universe NIFTY 500 as of today (survivorship acknowledged); baseline 10,000 same-decile permutations, two-sided p.

| direction | events | cross-day move % | +1d % | +1d matched-random % | p | hit rate | +5d % | +5d p |
|---|---|---|---|---|---|---|---|---|
| cross up | 38569 | +2.41 | +0.522 | +0.599 | 0.000 | 58.2% | +0.98 | 0.062 |
| cross down | 38657 | -1.57 | -0.137 | -0.272 | 0.062 | 43.4% | +0.26 | 0.167 |
| all other days (unmatched) | 1919149 | - | +0.124 | - | - | - | - | - |

Half-sample stability (split at year 2017; +1d, same-decile matched):
- cross up, first half: 20322 events, +1d +0.455% vs matched +0.623% (p=0.000)
- cross up, second half: 18247 events, +1d +0.597% vs matched +0.572% (p=0.314)
- cross down, first half: 20160 events, +1d -0.007% vs matched -0.277% (p=0.028)
- cross down, second half: 18497 events, +1d -0.278% vs matched -0.267% (p=0.775)

Direction-pooled +1d: +0.192% gross; net of a 0.20% round trip: -0.008% per trade; the edge breaks even at a 0.192% round-trip cost.

- ^NSEI cross up: 92 events, next-day +0.274% (descriptive, n too small to test)
- ^NSEI cross down: 93 events, next-day -0.075% (descriptive, n too small to test)

Reading: if the matched-random column sits at the observed value (p well above 0.05), the cross carries nothing beyond the day's own move - the matrix stays a display.  A surviving p means the cross timing itself adds information; check the net-of-cost line before caring.

## Verdict (added 2026-10-28, after the run)

**The next-session "edge" is the big-move-day effect, not the cross.**

- Matched on the SAME-DAY return, fresh cross-up days do WORSE than
  equally-big non-cross days: +0.522% vs +0.599% (p=0.000 - significant
  in the UNFAVORABLE direction, concentrated pre-2017; since 2017 it is
  a wash, p=0.314).
- Cross-down days fall LESS than equally-big down days: -0.137% vs
  -0.272% (p=0.062) - again the opposite of a directional signal.
- The first study's "+0.34% next-day after cross-up vs +0.06% all-days"
  was pure selection: crosses co-occur with big moves (+2.41% average
  cross-day move), and big moves continue.  The cross itself marks
  nothing except that the move began from below the EMAs.
- Economics: direction-pooled +1d +0.192% gross - net of a 0.20% round
  trip it is -0.008% per trade.  Dead on arrival as a 1-day trade even
  before slippage.

Bottom line: the EMA 9/21 HA matrix is a DISPLAY, not a signal engine -
its own aggregation was already null (C3) and its fresh-cross flag
carries no information beyond the day's move (this study).  No further
study of this rule is warranted; the closed-candle snapshot remains
useful as a market-structure view.
