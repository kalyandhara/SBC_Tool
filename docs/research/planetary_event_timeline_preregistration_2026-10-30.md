# Mars-in-Pushya with Moon-in-Rohini and NIFTY: event timeline (B-71) — pre-registration

**Status: DRAFT for review, not committed.** Once this file is committed, it is frozen. Any change
after the first run is a new registration, not an edit. Nothing in this draft has been run.

Source: the "Historical Event Impact" proposal in the 2026-10-30 session, which uses 2026-10-01
(Mars in Pushya, Moon in Rohini) as its example. The proposal's analog years and returns were not
reproduced here and are not evidence.

## Question

On sessions where Mars is in Pushya and the Moon is in Rohini, does NIFTY's forward return differ
from the return on ordinary sessions that had the same same-day move? If it does, in which
direction, and does the difference hold in both eras?

## Fixed inputs

| Item | Value | Note |
|---|---|---|
| Zodiac | Geocentric sidereal, Lahiri, Moshier | Same as `sbc.planets`. |
| Observation time | 09:15 IST on each session date | The project's standing sky time. Known before the session's close, so there is no lookahead. |
| Event condition | Mars nakshatra = Pushya (8th) **and** Moon nakshatra = Rohini (4th) at 09:15 IST | Both must hold on the same session. Use `sbc.nakshatra.nakshatra_of(longitude)`. Checked 2026-10-30: it returns 0-based index floor(lon / 13°20') with an Abhijit exception at 276°40'–280°53'20". Neither Pushya (106°40'–120°) nor Rohini (40°–53°20') overlaps that span, so the exception does not affect this test. |
| Episodes | A run of consecutive event sessions is one episode. The episode's first session is the event. | Stops one configuration from being counted once per day. The project has seen this collapse before (see `event-study-cluster-and-sample-lessons`). |
| Entry | Close of the event session | Matches the cost-adjusted entry rule in the astro-confluence study. |
| Horizons | +1, +5, +10, +20 sessions from the entry close | Sessions, not calendar days. The +5 horizon is primary (see below). |
| Cost | 0.20% round trip, subtracted from long-side returns | Same as `sbc.confluence_engine.net_trade_return`. |
| Sample | NIFTY daily closes in `data/market.db`, 2007-09-17 to the latest session | The store's first bar. |
| Eras | 2007-2020 and 2021-2026 | `sbc.rule_validation._era`. |
| Minimum episodes | 15 episodes in the sample | Below 15, the result is reported as "insufficient" and not graded. |

## Control (decile-matched)

Each session's same-day move is `r0 = close[t] / close[t-1] - 1`. Sessions are grouped into deciles of
`r0` over the full sample, computed once before the run.

- For each event episode, its **control** is every session in the same `r0` decile as the event session,
  excluding the episode-start sessions (the events). Later sessions of the same episode stay in the
  control pool. They share the configuration, so this dilutes any effect toward zero. Stated, not tuned.
- The **excess return** of an event is its forward return minus the mean forward return of its control
  set, at the same horizon.

This is the control the project's standing rule requires: the forward return has to beat what the same
day's price move would predict on its own. The unconditional all-days mean is reported as a second
reference, not used for grading.

## Hypotheses (one primary, three secondary; one BH family of 4)

| Name | Test | Role |
|---|---|---|
| `t5_excess` | Mean excess return at +5 sessions, two-sided | **Primary** |
| `t1_excess` | Mean excess return at +1 session, two-sided | Secondary |
| `t10_excess` | Mean excess return at +10 sessions, two-sided | Secondary |
| `t20_excess` | Mean excess return at +20 sessions, two-sided | Secondary |

The sign is not pre-committed. The proposal claimed a bullish tilt, but that claim has no evidence yet,
so the test is two-sided. Grading is on the excess return, not on the raw return.

## Permutation test

- Null: the event labels are exchangeable within each `r0` decile.
- For each permutation, the same number of event episodes is drawn at random from sessions in the same
  deciles, and the statistic is recomputed.
- 10,000 permutations, seed 42.
- p = (hits + 1) / (iters + 1), where a hit is a permutation whose absolute statistic is at least the
  observed absolute statistic. The +1 keeps p above zero.

## What counts as an edge

The project's standing rule (`docs/GAP_ANALYSIS_PREDICTION_ENGINE_2026-10-03.md`) applies:

1. The primary test needs p < 0.05, and the BH-adjusted q across the four horizons must also be < 0.05.
2. The excess return must have the same sign in both eras.
3. The net return after 0.20% is reported beside every gross number.

If the primary test passes but the other horizons do not, the result is reported as horizon-specific and
is not promoted to a forecast.

## Descriptive outputs (no grading)

- The timeline: mean and median NIFTY return from -5 to +20 sessions around each event, normalized to
  the event close = 100, with the decile-control band (5th to 95th percentile) shaded.
- Per-episode table: event date, episode length, `r0` decile, returns at +1, +5, +10, +20.
- Bhadra overlap flag for each episode. **Not in this version.** It would need a separate step and
  is not a condition of the test.

## Excluded (each would need its own registration)

- **Analog search** (`sbc.analogs`). The analog set is chosen by similarity to the target day, which
  would make the test depend on selection choices. Not used here.
- **Confidence score.** The proposal's 40/30/20/10 weighting has no validation behind it. Not used.
- **Sector matrix and radar charts.** Need a sector return source and a pre-defined sector list.
  Not used.
- **Other configurations** from the proposal (Cluster C, Ketu in Magha, Moon in Taurus, Bhadra as a
  condition). Not used.
- **Tropical zodiac.** Sidereal only.

## Known limits, stated up front

- **Few episodes.** Mars and Moon both in these nakshatras together happens a few times a year. Expect
  well under 60 episodes over the sample. Power is low, and a null result is the most likely outcome.
- **Overlap.** Episodes that fall close together share control sessions. The control sets are not
  de-duplicated across episodes.
- **Ephemeris.** The Moon moves about 13° a day, so a one-session shift in the Moon's nakshatra changes
  which episodes count. The 09:15 convention is fixed, not tuned.
- **Descriptive timeline is not evidence.** The -5 to +20 curve can look like a pattern when the sample
  is small. Only the graded tests above count.

## Outcome

Recorded in `docs/research/planetary_event_timeline_validation_<date>.md` by
`scripts/validate_planetary_event_timeline.py`. The script exists (logic in `sbc/planetary_event_timeline.py`,
13 tests in `tests/test_planetary_event_timeline.py`) but has **not been run on market data**. The run
waits for this registration to be committed. The outcome file must state N episodes per era, the
primary p and q, and the net return beside the gross.

## Decisions (2026-10-30)

The four open items were settled on the proposed defaults:

1. **Primary horizon:** +5 sessions.
2. **Two-sided** test.
3. **Minimum episodes:** 15.
4. **Bhadra** is not part of the test and is not built in this version.
