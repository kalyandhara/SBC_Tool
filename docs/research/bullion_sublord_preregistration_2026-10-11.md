# Bullion KP sub-lord rules (B-57) — pre-registration

Registered **2026-10-11, before any intraday data has been loaded or looked at.** A
timestamped copy with its SHA-256 was posted to the claude.ai SBC project. The test cannot
run yet: it needs intraday gold and silver bars (blocked with B-54). When a source arrives,
the test runs exactly as written here.

Nothing below may be changed after the first run, or after anyone has looked at intraday
returns by sub-lord. A different choice is a new hypothesis with its own registration.

## Source rules (as the 18 Sep 2026 bullion sheet states them)

| Moon KP sub-lord | Sheet's reading | Group |
|---|---|---|
| Venus, Jupiter | Positive direction, buying may emerge | UP |
| Sun, Ketu, Rahu | Pressure possible / pressure and volatility | DOWN |
| Moon | Sharp volatility | VOLATILE |
| Mars, Saturn | Relative stability / range-bound | STABLE |
| Mercury | no rule | not tested |

## Fixed inputs

| Item | Value |
|---|---|
| Segments | `sbc.bullion_week.moon_day` sub-lord segments (sidereal Lahiri, Moshier), clipped to the trading session |
| Session | MCX 09:00 IST to 23:30 IST (US daylight time) or 23:55 IST (US standard time) |
| Prices | hourly or finer bars for gold and silver from one free source, named in the run report. MCX futures if available, otherwise COMEX GC/SI front month with times converted to IST. |
| Segment return | log(price at segment end / price at segment start), using the last bar at or before each time |
| Minimum segment | 30 minutes inside the session; shorter segments are dropped |
| Sample | every segment from the first full year of the source to the run date; at least 2 years required, otherwise no verdict |

## Hypotheses (4 groups x 2 metals = 8 tests, one BH family)

| Name | Metric per segment | Claim |
|---|---|---|
| `up` | segment return minus the all-segment mean, per hour | Venus and Jupiter segments are above the mean |
| `down` | same | Sun, Ketu and Rahu segments are below the mean |
| `volatile` | absolute segment return per hour, minus the all-segment mean | Moon segments are above the mean |
| `stable` | same | Mars and Saturn segments are below the mean |

## Test

- Statistic: the mean of the metric over the group's segments, signed so the claim is positive.
- Null: 10,000 permutations shuffling sub-lord labels across sessions in whole-session blocks
  (each session's sequence of labels moves together), which keeps the intraday time-of-day
  pattern intact.
- Correction: Benjamini-Hochberg across the 8 tests.

## What counts as an edge

A group passes for a metal only if q < 0.05 **and** the effect has the claimed sign in both
halves of the sample (split at its midpoint date). The time-of-day effect is controlled by
also requiring the result to hold after subtracting each clock hour's mean return
(hour-of-day demeaning). A pass on gold alone or silver alone is reported per metal.

## Known limits, stated up front

- Segments average 1 to 4 hours, so there are only a few per session; two years gives about
  2,500 to 3,500 segments per metal.
- Liquidity differs across the MCX day; the hour-of-day control is there for that.
- The sheet's location and ayanamsa match ours to within two minutes on 18 Sep 2026, but the
  sheet may change its rules; this registration tests the rules as captured on that date.

## Outcome

Recorded in `docs/research/bullion_sublord_validation_<date>.md` when intraday data exists.
