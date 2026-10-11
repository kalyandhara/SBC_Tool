# Bullion KP sub-lord rules (B-57) — amendment 1

Registered **2026-10-11, before any intraday data has been downloaded or looked at.** It
amends `docs/research/bullion_sublord_preregistration_2026-10-11.md` (SHA-256
9d29f806…ff3), which stays as written. Where the two differ, this amendment applies. A
timestamped copy with its SHA-256 was posted to the claude.ai SBC project.

## Why

1. **Source.** MCX intraday history isn't freely available, and Yahoo keeps only 730 days of
   hourly COMEX bars, which barely meets the 2-year minimum. The user chose Dukascopy instead
   (2026-10-11), which has free hourly history going back many years.
2. **Two gaps in the original wording**, closed here before any data exists: "the first full
   year of the source" didn't name dates, and the rule for timing segment edges with hourly
   bars wasn't stated.

## Changes

| Item | Original | Amended |
|---|---|---|
| Prices | MCX, else COMEX GC/SI front month | **Dukascopy XAUUSD and XAGUSD spot, hourly BID candles**, timestamps UTC converted to IST. Spot and front-month futures move together intraday; the basis changes slowly and doesn't affect hour-scale returns. |
| Sample | from the first full year of the source, at least 2 years | **2010-01-01 to 2026-09-30** (IST dates). Fixed now; not extended or trimmed after a run. |
| Sessions | MCX trading days | Monday to Friday IST dates with at least 10 hourly bars inside the session window. |
| Session window | 09:00 to 23:30 IST (US daylight) or 23:55 IST (US standard) | Unchanged; bars are hourly, so the window is the hours 09:00-23:00 IST with daylight time, 09:00-24:00 IST without (the hour that contains 23:30 or 23:55 is included). |
| Segment edges | price at each edge time | Each segment edge is **floored to the hour**. A segment covers the hourly bars from its floored start up to its floored end. Segments that cover no full bar are dropped (this replaces the 30-minute minimum). |
| Segment return | log(end price / start price) | The sum of the hourly log returns (close/open of each bar) in the segment. |
| Hour-of-day control | subtract each clock hour's mean return | For `up`/`down`: subtract each IST clock hour's mean hourly return (over the whole sample) from each bar before summing. For `volatile`/`stable`: divide each bar's return by its clock hour's standard deviation before taking the absolute per-hour value. The control version must also pass. |

Everything else (groups, metrics, block permutation by session, 10,000 permutations, BH across
the 8 tests, the both-halves sign check, the pass rule) is unchanged.

## Data integrity

The fetch script records, per metal, the first and last bar, bar count, and any months with
no data. A month with no bars is reported, not filled. No price is synthesized.
