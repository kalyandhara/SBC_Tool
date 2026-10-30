# Transit-to-natal reversal windows (B-49 / B-51 / B-53) — pre-registration

Registered **2026-10-10, before the first validation run.** Committed ahead of
`sbc/natal_validation.py` and `scripts/validate_natal.py`; the commit order is the
evidence. Source method: `docs/KUNDALI_METHOD_INGEST_2026-10-10.md`.

Nothing below may be changed after the first run. A different choice is a new
hypothesis with its own registration, not an edit to this one.

## Hypothesis

NIFTY reverses its prior 10-session trend, or moves more, on sessions when a
transiting planet is within 2 deg of an aspect to a planet in NIFTY's own natal chart.

## Fixed inputs

| Item | Value | Note |
|---|---|---|
| Natal chart | `sbc.natal.chart("nifty")`: 1995-11-03 00:00 IST | The engine's existing NIFTY anchor. The birth **time is an assumption**; the Moon's natal longitude moves ~13 deg/day, so Moon-based rows depend on it. Other planets barely change. |
| Zodiac | Geocentric sidereal, Lahiri | Same as `sbc.planets`. |
| Transiting planets | Sun, Mercury, Venus, Mars, Jupiter, Saturn, Rahu | Moon excluded (inside a 2 deg orb most days), Ketu excluded (Rahu + 180). |
| Natal points | all nine grahas | |
| Aspects | all eight of B-39 (CONJ, OPP, TRI, SQ, SXT, QCX, SS, SSQ) | Plus one extra group, `lecture5` = CONJ, SQ, SXT, SS, TRI, the five the lecture names. |
| Orb | 2.0 deg | Same as B-39. |
| Sample | NIFTY 2007-09-17 to the latest session, horizons 1, 5, 20 sessions | |
| Signal | `-sign(close[t-1] - close[t-11])` on sessions inside a window | Identical to B-39's `reversal`, so the two reports compare directly. |
| Control | the same reversal rule on every session (no astro) | An astro edge has to beat it, not just the drift. |

## Groups tested (26)

`all`; one per aspect (8); `lecture5`; one per transiting planet (7); one per natal
point (9). Each is graded as a directional reversal call and as a volatility call, at
three horizons: **156 tests**, Benjamini-Hochberg corrected together as one family.
The per-planet rows are the planet comparison the lecture asks for ("which planet does
this script vibrate to"). Picking the best planet after the fact would be snooping;
the corrected per-planet rows are the honest version of that question.

## Headline test

`natal_all_reversal` at 1, 5 and 20 sessions. Everything else is secondary.

## What counts as an edge

The project's standing rule (`docs/GAP_ANALYSIS_PREDICTION_ENGINE_2026-10-03.md`): a
component counts only if it passes **both**

1. the circular-shift permutation test, q < 0.05 after BH, with the same direction in
   both eras (2007-2020 / 2021-2026), and
2. the incremental test against the market controls (VIX, trend, volatility, calendar),
   q < 0.05.

**Part B** (the full swing model on these windows, 2008 onward): the model counts only
if its mean excess return beats 500 random-entry sets drawn with the same size, direction
rule and exit (p < 0.05).

## Known limits, stated up front

- **Window density.** About two windows open per session across 7 x 9 x 8 pairs. The
  share of sessions inside at least one window is reported; a share near 100% means the
  `all` group is close to the control by construction. The per-planet and per-point
  groups are where a real difference would show.
- **Birth time.** Unknown; midnight IST assumed (above).
- **One instrument, one chart.** NIFTY only. Stocks and commodities (B-50, B-52) are not
  built and are not worth building unless this passes.
- **Daily bars only.** The lecture's 30/60-minute stop and 50% retracement need intraday
  data and are not tested (B-54).

## Outcome

Recorded in `docs/research/natal_validation_<date>.md` by `scripts/validate_natal.py`.
