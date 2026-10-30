# Transit events and NIFTY (B-58)

Generated 2026-10-11T17:54:49 by `scripts/validate_transit_events.py`. Hypotheses, windows and pass rule were registered before this run: `docs/research/transit_events_preregistration_2026-10-11.md`.

Sample: 2007-09-17 to 2026-10-09, 4677 NIFTY sessions. Permutations per test: 1000. Horizons: 1, 5, 20 sessions.

Events in the sample (sidereal Lahiri): mercury stations 126, tense aspects 562, eclipses 89, jupiter saturn ingresses 48.

Share of sessions each signal is active: `h1_mercury_station_volatility` 18%, `h2_mercury_retrograde_down` 19%, `h3_tense_mars_saturn_pluto_volatility` 44%, `h4_eclipse_volatility` 19%, `h5_jupiter_saturn_ingress_reversal` 7%.

## Results

Pass = q < 0.05 (BH across all 15 tests) with the same direction in both eras, **and** the incremental test against the market controls q < 0.05.

| Hypothesis | h | n | effect | p | q | eras | beyond market (q) | verdict |
|---|---|---|---|---|---|---|---|---|
| `h1_mercury_station_volatility` | 1 | 840 | 0.00002 | 0.974 | 0.974 | 2007-2020: -0.0000, 2021-2026: 0.0001 | nothing beyond the market (0.889) | no edge |
| `h1_mercury_station_volatility` | 5 | 840 | 0.00273 | 0.024 | 0.097 | 2007-2020: 0.0031, 2021-2026: 0.0017 | adds information (0.015) | no edge |
| `h1_mercury_station_volatility` | 20 | 840 | 0.00564 | 0.015 | 0.097 | 2007-2020: 0.0084, 2021-2026: -0.0010 | adds information (0.030) | no edge |
| `h2_mercury_retrograde_down` | 1 | 899 | 0.00008 | 0.856 | 0.974 | 2007-2020: 0.0002, 2021-2026: -0.0003 | nothing beyond the market (0.889) | no edge |
| `h2_mercury_retrograde_down` | 5 | 899 | 0.00105 | 0.689 | 0.862 | 2007-2020: 0.0013, 2021-2026: 0.0006 | nothing beyond the market (0.889) | no edge |
| `h2_mercury_retrograde_down` | 20 | 899 | 0.01028 | 0.151 | 0.377 | 2007-2020: 0.0120, 2021-2026: 0.0064 | nothing beyond the market (0.889) | no edge |
| `h3_tense_mars_saturn_pluto_volatility` | 1 | 2046 | -0.00089 | 0.024 | 0.097 | 2007-2020: -0.0009, 2021-2026: -0.0011 | nothing beyond the market (0.889) | no edge |
| `h3_tense_mars_saturn_pluto_volatility` | 5 | 2044 | -0.00217 | 0.026 | 0.097 | 2007-2020: -0.0025, 2021-2026: -0.0018 | nothing beyond the market (0.889) | no edge |
| `h3_tense_mars_saturn_pluto_volatility` | 20 | 2034 | -0.00274 | 0.219 | 0.469 | 2007-2020: -0.0043, 2021-2026: 0.0000 | nothing beyond the market (0.889) | no edge |
| `h4_eclipse_volatility` | 1 | 881 | -0.00095 | 0.058 | 0.174 | 2007-2020: -0.0013, 2021-2026: -0.0003 | nothing beyond the market (0.889) | no edge |
| `h4_eclipse_volatility` | 5 | 881 | -0.00090 | 0.452 | 0.617 | 2007-2020: -0.0022, 2021-2026: 0.0015 | nothing beyond the market (0.889) | no edge |
| `h4_eclipse_volatility` | 20 | 881 | -0.00394 | 0.357 | 0.594 | 2007-2020: -0.0075, 2021-2026: 0.0035 | nothing beyond the market (0.889) | no edge |
| `h5_jupiter_saturn_ingress_reversal` | 1 | 309 | 0.00005 | 0.942 | 0.974 | 2007-2020: -0.0004, 2021-2026: 0.0009 | nothing beyond the market (0.889) | no edge |
| `h5_jupiter_saturn_ingress_reversal` | 5 | 309 | -0.00199 | 0.453 | 0.617 | 2007-2020: -0.0034, 2021-2026: 0.0009 | nothing beyond the market (0.889) | no edge |
| `h5_jupiter_saturn_ingress_reversal` | 20 | 309 | -0.00642 | 0.329 | 0.594 | 2007-2020: -0.0040, 2021-2026: -0.0116 | nothing beyond the market (0.889) | no edge |

## Control (no astro)

- `reversal_every_day` h=1: p 0.297, verdict no edge
- `reversal_every_day` h=5: p 0.793, verdict no edge
- `reversal_every_day` h=20: p 0.864, verdict no edge

Sessions inside at least one window: 70%.
