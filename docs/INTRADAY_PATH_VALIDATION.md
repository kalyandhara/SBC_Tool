# Predictive Intraday Path – Historical Validation

Period: 2026-08-03 to 2026-09-15  |  Days evaluated: 31

Model: `/api/engine/intraday_path` hourly series vs NIFTY 5m bars (^NSEI, yfinance).

## Aggregate Metrics

| Metric | Value |
|---|---|
| Mean per-day corr (score vs hourly return) | -0.119 |
| Pooled corr (score vs hourly return) | -0.150 |
| Pooled score direction hit rate | 54.8% (217 windows) |
| Regime-shift direction hit rate | 49.8% (3345 shifts) |
| Day-direction hit (final cumulative vs day range) | 20/31 |
| Strongest bullish window hit | 12/31 |
| Strongest bearish window hit | 16/31 |

## Per-Day Detail

| Date | r(score,ret) | score hit | day dir | day ret % | regime hit | bull win | bear win |
|---|---|---|---|---|---|---|---|
| 2026-08-03 | -0.326 | 28.6% | no | +206.30 | 53/105 | no | no |
| 2026-08-04 | -0.519 | 57.1% | yes | -51.75 | 51/105 | no | yes |
| 2026-08-05 | -0.769 | 28.6% | yes | -44.55 | 48/105 | yes | yes |
| 2026-08-06 | -0.540 | 28.6% | no | +3.30 | 55/105 | yes | no |
| 2026-08-07 | -0.069 | 42.9% | no | +35.60 | 46/105 | yes | yes |
| 2026-08-10 | -0.435 | 42.9% | yes | -0.25 | 57/105 | no | no |
| 2026-08-11 | -0.088 | 57.1% | yes | -103.80 | 47/104 | no | no |
| 2026-08-12 | -0.279 | 57.1% | yes | -36.50 | 50/105 | no | no |
| 2026-08-13 | +0.084 | 71.4% | yes | -33.05 | 56/105 | yes | yes |
| 2026-08-14 | +0.288 | 71.4% | no | +2.25 | 54/105 | yes | yes |
| 2026-08-17 | +0.687 | 85.7% | yes | -55.80 | 54/105 | no | yes |
| 2026-08-18 | +0.626 | 85.7% | yes | -68.15 | 52/105 | no | no |
| 2026-08-19 | -0.105 | 57.1% | yes | -84.75 | 54/105 | yes | yes |
| 2026-08-20 | +0.644 | 85.7% | no | +6.65 | 59/105 | no | yes |
| 2026-08-21 | -0.360 | 42.9% | yes | -30.00 | 48/105 | no | no |
| 2026-08-24 | -0.286 | 42.9% | yes | -66.00 | 48/105 | no | no |
| 2026-08-25 | -0.603 | 28.6% | no | +150.10 | 53/105 | yes | yes |
| 2026-08-26 | -0.124 | 42.9% | yes | -135.30 | 52/105 | yes | yes |
| 2026-08-27 | +0.411 | 71.4% | yes | -186.75 | 52/105 | no | yes |
| 2026-08-28 | -0.480 | 28.6% | no | +46.70 | 53/105 | no | no |
| 2026-08-31 | +0.267 | 71.4% | yes | -36.70 | 52/105 | no | no |
| 2026-09-01 | -0.220 | 42.9% | yes | -21.25 | 55/115 | no | no |
| 2026-09-02 | -0.613 | 42.9% | no | +35.05 | 48/115 | yes | no |
| 2026-09-03 | +0.202 | 85.7% | yes | -124.50 | 67/115 | yes | yes |
| 2026-09-04 | +0.559 | 71.4% | yes | -17.75 | 67/115 | no | yes |
| 2026-09-07 | -0.680 | 57.1% | yes | -102.75 | 52/115 | no | no |
| 2026-09-08 | -0.459 | 85.7% | yes | -111.65 | 67/115 | no | yes |
| 2026-09-09 | -0.183 | 57.1% | yes | -90.55 | 67/115 | no | yes |
| 2026-09-10 | -0.353 | 57.1% | no | +31.20 | 48/115 | no | no |
| 2026-09-11 | +0.167 | 28.6% | no | +127.20 | 52/115 | yes | yes |
| 2026-09-15 | -0.120 | 42.9% | no | -457.55 | 50/106 | yes | no |

Note: correlation and hit rates on hourly buckets are noisy (7 points/day); treat pooled metrics as the primary signal.
