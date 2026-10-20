# Cross-asset crash-propagation study

NIFTY episodes 2000-2026: 21-session return <= -10.0% alarms a crash; window = ~21 sessions before the alarm to the NIFTY trough within 40 sessions. 16 episodes found.

## Episodes

| start | trough | NIFTY drawdown % |
|-------|--------|------------------|
| 2007-12-20 | 2008-03-17 | -21.9 |
| 2008-02-19 | 2008-03-17 | -14.7 |
| 2008-05-05 | 2008-07-16 | -26.5 |
| 2008-08-13 | 2008-10-27 | -44.3 |
| 2008-10-15 | 2008-10-27 | -24.4 |
| 2008-12-18 | 2009-03-09 | -15.9 |
| 2009-06-09 | 2009-07-13 | -12.7 |
| 2010-01-06 | 2010-02-05 | -10.7 |
| 2010-12-31 | 2011-02-10 | -14.8 |
| 2011-07-07 | 2011-08-26 | -17.1 |
| 2013-07-18 | 2013-08-28 | -12.5 |
| 2015-08-06 | 2015-09-07 | -12.0 |
| 2018-09-03 | 2018-10-26 | -13.4 |
| 2020-02-06 | 2020-03-23 | -37.3 |
| 2022-04-08 | 2022-06-17 | -14.0 |
| 2026-02-11 | 2026-03-30 | -14.0 |

## Propagation: asset return over each crash window

| asset | n | mean % | median % | fell in % of episodes | random % | p |
|-------|---|--------|----------|------------------------|----------|---|
| gold | 16 | +1.93 | +1.40 | 44% | +1.65 | 0.845 |
| silver | 16 | -0.85 | -1.77 | 56% | +2.02 | 0.327 |
| crude | 16 | -1.63 | -0.63 | 50% | +1.59 | 0.379 |
| usdinr | 16 | +5.42 | +4.10 | 0% | +0.48 | 0.000 |
| INDIAVIX | 14 | +78.67 | +48.20 | 14% | +2.73 | 0.000 |

## Stress days (NIFTY <= -2%)

| asset | stress days | mean ret on stress days % | all-days mean % | down on stress % | corr stress | corr all |
|-------|-------------|---------------------------|----------------|------------------|-------------|----------|
| gold | 197 | -0.27 | +0.046 | 58% | -0.04 | +0.06 |
| silver | 197 | -1.07 | +0.058 | 61% | +0.08 | +0.15 |
| crude | 197 | -2.03 | -0.037 | 64% | +0.09 | +0.08 |
| usdinr | 198 | +0.34 | +0.020 | 29% | -0.03 | -0.22 |
| INDIAVIX | 183 | +9.31 | +0.153 | 16% | -0.00 | -0.43 |

Current state: NIFTY last close 22889.0 (2026-10-19), -13.1% vs its 52-session high.

Video mapping: 'when equities crash all asset classes fall - 2008; silver weak; protect capital.' USDINR up = rupee weaker = INR gold tailwind (his rupee point at 4:50 relies on the opposite move). Bootstrap p-values are two-sided; episodes overlap major regimes, so treat as a propagation profile, not a signal.
