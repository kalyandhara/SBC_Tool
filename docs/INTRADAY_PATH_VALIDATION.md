# Predictive Intraday Path – Historical Validation

Period: 2026-08-04 to 2026-09-30  |  Days evaluated: 41

Model: `/api/engine/intraday_path` hourly series vs NIFTY 5m bars (^NSEI, yfinance).

## Aggregate Metrics

| Metric | Value |
|---|---|
| Mean per-day corr (score vs hourly return) | -0.026 |
| Pooled corr (score vs hourly return) | +0.004 |
| Pooled score direction hit rate | 50.8% (1024 windows) |
| Regime-shift direction hit rate | 49.7% (2183 shifts) |
| Day-direction hit (final cumulative vs day range) | 28/41 |
| ↳ chance baseline (model bearish 90% of days, market down 63%) | 60.8% |
| Strongest bullish window hit | 3/11 |
| Strongest bearish window hit | 15/19 |

## Per-Day Detail

| Date | r(score,ret) | score hit | day dir | day ret % | regime hit | bull win | bear win |
|---|---|---|---|---|---|---|---|
| 2026-08-04 | +0.242 | 68.0% | yes | -51.75 | 24/53 | n/a | n/a |
| 2026-08-05 | -0.239 | 44.0% | yes | -44.55 | 22/52 | no | n/a |
| 2026-08-06 | +0.024 | 44.0% | no | +3.30 | 20/51 | n/a | n/a |
| 2026-08-07 | -0.069 | 32.0% | yes | +35.60 | 24/52 | n/a | yes |
| 2026-08-10 | +0.141 | 52.0% | no | -0.25 | 29/52 | n/a | n/a |
| 2026-08-11 | +0.224 | 52.0% | yes | -103.80 | 26/50 | n/a | yes |
| 2026-08-12 | -0.242 | 48.0% | yes | -36.50 | 19/52 | yes | yes |
| 2026-08-13 | +0.043 | 56.0% | yes | -33.05 | 18/56 | yes | yes |
| 2026-08-14 | +0.125 | 48.0% | no | +2.25 | 23/54 | no | n/a |
| 2026-08-17 | -0.061 | 60.0% | yes | -55.80 | 29/52 | n/a | n/a |
| 2026-08-18 | +0.113 | 60.0% | yes | -68.15 | 33/52 | n/a | n/a |
| 2026-08-19 | -0.093 | 56.0% | yes | -84.75 | 21/52 | n/a | yes |
| 2026-08-20 | -0.399 | 32.0% | no | +6.65 | 23/51 | n/a | n/a |
| 2026-08-21 | -0.125 | 56.0% | yes | -30.00 | 22/51 | n/a | n/a |
| 2026-08-24 | +0.073 | 68.0% | yes | -66.00 | 24/52 | n/a | n/a |
| 2026-08-25 | +0.124 | 68.0% | no | +150.10 | 19/51 | n/a | n/a |
| 2026-08-26 | -0.195 | 48.0% | yes | -135.30 | 33/52 | n/a | yes |
| 2026-08-27 | -0.118 | 48.0% | yes | -186.75 | 33/53 | n/a | yes |
| 2026-08-28 | -0.668 | 28.0% | no | +46.70 | 19/49 | n/a | n/a |
| 2026-08-31 | -0.143 | 40.0% | yes | -36.70 | 22/54 | no | no |
| 2026-09-01 | +0.057 | 52.0% | yes | -21.25 | 29/53 | no | yes |
| 2026-09-02 | +0.088 | 48.0% | no | +35.05 | 21/54 | n/a | n/a |
| 2026-09-03 | +0.005 | 64.0% | yes | -124.50 | 32/54 | no | yes |
| 2026-09-04 | -0.251 | 36.0% | yes | -17.75 | 32/52 | n/a | n/a |
| 2026-09-07 | +0.023 | 36.0% | yes | -102.75 | 26/55 | n/a | n/a |
| 2026-09-08 | -0.020 | 52.0% | yes | -111.65 | 30/52 | no | n/a |
| 2026-09-09 | +0.073 | 52.0% | yes | -90.55 | 34/54 | n/a | no |
| 2026-09-10 | -0.137 | 36.0% | no | +31.20 | 21/53 | no | n/a |
| 2026-09-11 | +0.357 | 72.0% | no | +127.20 | 23/55 | n/a | yes |
| 2026-09-15 | -0.030 | 68.0% | yes | -457.55 | 34/56 | n/a | yes |
| 2026-09-16 | -0.178 | 60.0% | no | +16.55 | 35/56 | no | n/a |
| 2026-09-17 | +0.018 | 56.0% | yes | +75.35 | 33/54 | n/a | yes |
| 2026-09-18 | +0.047 | 40.0% | no | +11.70 | 24/54 | n/a | yes |
| 2026-09-21 | -0.066 | 41.7% | no | +98.80 | 24/52 | n/a | n/a |
| 2026-09-22 | -0.196 | 44.0% | yes | -125.05 | 33/55 | n/a | n/a |
| 2026-09-23 | +0.291 | 52.0% | no | +94.65 | 27/56 | n/a | no |
| 2026-09-24 | -0.406 | 44.0% | yes | -157.15 | 33/56 | n/a | yes |
| 2026-09-25 | -0.127 | 32.0% | yes | +105.50 | 21/57 | yes | no |
| 2026-09-28 | -0.040 | 60.0% | yes | -284.65 | 34/56 | n/a | yes |
| 2026-09-29 | +0.206 | 64.0% | yes | -16.25 | 23/54 | n/a | n/a |
| 2026-09-30 | +0.445 | 64.0% | yes | -44.50 | 33/54 | n/a | n/a |

Note: correlation and hit rates on hourly buckets are noisy (7 points/day); treat pooled metrics as the primary signal.
