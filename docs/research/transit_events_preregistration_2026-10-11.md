# Transit events and NIFTY (B-58) — pre-registration

Registered **2026-10-11, before the first validation run.** Written ahead of
`sbc/transit_event_validation.py` and `scripts/validate_transit_events.py`. A timestamped
copy with its SHA-256 was posted to the claude.ai SBC project before the run, because this
registration is not committed ahead of the code. Source: `docs/TRANSIT_BULLION_INGEST_2026-10-11.md`.

Nothing below may be changed after the first run. A different choice is a new hypothesis
with its own registration, not an edit to this one.

## Fixed inputs

| Item | Value | Note |
|---|---|---|
| Events | `sbc.transit_almanac.build(year, "sidereal")` | Sidereal Lahiri, Moshier, mean node, IST dates. The same events the Transit Almanac shows. |
| Event session | the first NIFTY session on or after the event's IST date | Weekend and holiday events move to the next session. |
| Window | ±k sessions around the event session, k fixed per hypothesis | Counted in sessions, not calendar days. |
| Sample | every NIFTY session in `market.db` (from 2007-09-17) to the latest session | Same as B-39 and B-53. |
| Horizons | 1, 5 and 20 sessions | Same as B-39 and B-53. |
| Eras | 2007-2020 and 2021-2026 | `sbc.rule_validation._era`. |
| Grading | `sbc.rule_validation.grade` plus the incremental test of `sbc.swing_validation.grade_a` | Unchanged harness. |

## Hypotheses (5 signals x 3 horizons = 15 tests, one BH family)

| Name | Kind | Signal | Traditional claim |
|---|---|---|---|
| `h1_mercury_station_volatility` | event | sessions within ±3 sessions of a Mercury station (retrograde or direct) | Stations bring disruption, so bigger moves. |
| `h2_mercury_retrograde_down` | directional | -1 on sessions when Mercury is retrograde at 09:15 IST, else 0 | Retrograde means delays and reversals, so weaker returns. Direction fixed: down. |
| `h3_tense_mars_saturn_pluto_volatility` | event | sessions within ±2 sessions of an exact square or opposition in which Mars, Saturn or Pluto is one of the two planets | Tense aspects of malefics bring pressure, so bigger moves. |
| `h4_eclipse_volatility` | event | sessions within ±5 sessions of a solar or lunar eclipse | Eclipses are turning points, so bigger moves. |
| `h5_jupiter_saturn_ingress_reversal` | directional | B-39's trend reversal, `-sign(close[t-1] - close[t-11])`, on sessions within ±3 sessions of a Jupiter or Saturn sign change, else 0 | Slow-planet ingresses mark trend changes. |

Event signals are graded on absolute forward returns ("bigger moves"). Directional signals
are graded on forward returns in the stated direction. The no-astro control is B-39's
reversal on every session, graded separately as in B-39.

## Headline

All five are primary. No hypothesis is preferred after the fact.

## What counts as an edge

The project's standing rule (`docs/GAP_ANALYSIS_PREDICTION_ENGINE_2026-10-03.md`): a test
counts only if it passes **both**

1. the circular-shift permutation test, q < 0.05 after BH across all 15 tests, with the same
   direction in both eras, and
2. the incremental test against the market controls (VIX, trend, volatility, calendar),
   q < 0.05.

A hypothesis that passes at one horizon and fails at the others is reported as such; it is
not promoted to the forecast on that basis alone.

## Known limits, stated up front

- **Few events.** Mercury stations about 6 a year, eclipses 4 to 5, Jupiter and Saturn sign
  changes about 1 a year each. H5 has the fewest windows and the least power.
- **Overlapping windows.** Windows can overlap each other and across hypotheses. The
  permutation test shifts the whole flag series, so overlap within a signal is preserved.
- **Tropical not tested.** Sidereal is the project's zodiac. Tropical would be a new registration.
- **Window widths** (±2, ±3, ±5) come from the ranges the sources describe ("days either
  side"); they are fixed here and will not be tuned.

## Outcome

Recorded in `docs/research/transit_event_validation_<date>.md` by
`scripts/validate_transit_events.py`.
