# Venus stations and the Sun-Venus conjunction against NIFTY swing lows (B-70)

Generated 2026-10-12T02:12:48 by `scripts/validate_venus_stations.py`. Hypotheses, pivot definition, window and pass rule were registered before this run: `docs/research/venus_station_preregistration_2026-10-12.md`.

Sample: 2007-09-17 to 2026-10-09, 4677 NIFTY sessions. Permutations per test: 1000, seed 20261012.

Events in the sample: 23 Venus stations, 12 Sun-Venus conjunctions.

## Results

Pass = BH q < 0.05 across the two tests, and in each era the hit rate beats its shift null (lift > 0, one-sided p < 0.05). Under 20 events is reported as underpowered.

| Hypothesis | n | hits | hit rate | null mean | lift | p | q | 2007-2020 lift (p) | 2021-2026 lift (p) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| `h1_venus_station` | 23 | 12 | 0.522 | 0.401 | 0.121 | 0.231 | 0.462 | 0.085 (0.362) | 0.157 (0.318) | **no edge** |
| `h2_venus_inferior_conjunction` | 12 | 5 | 0.417 | 0.423 | -0.006 | 0.581 | 0.581 | -0.063 (0.733) | 0.093 (0.538) | **underpowered** |

## Deck claims (reported, not graded)

- Retrograde windows (R to D, store-derived): 11. Windows with a swing low inside: 11 of 11 (deck: 8 of 10).
- Median high-to-low close range inside a window: 7.0% over a median 29 sessions. Median range over rolling windows of that length: 7.2% (deck: 7–12% against about 5%).

## Forward returns from each event (mean %, descriptive)

- `h1_venus_station`: 1 session 0.09, 5 sessions 1.21, 20 sessions 5.08
- `h2_venus_inferior_conjunction`: 1 session 0.45, 5 sessions 0.47, 20 sessions 0.58
