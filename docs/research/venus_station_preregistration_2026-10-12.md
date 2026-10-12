# Venus station and conjunction timing (B-70) — pre-registration

**Status: DRAFT, not yet committed. Do not run until this file is committed.** Once committed,
the file is frozen: a change after the first run is a new registration, not an edit.
Source: `docs/VENUS_RETROGRADE_INGEST_2026-10-11.md`, claims in slides 10, 11 and 14 of
`Venus_Retrograde_2026.pptx`.

## Question

Does NIFTY's swing low fall near Venus's stations or its inferior conjunction more often than
it would at random? The deck says it does: "historically the sharpest swings cluster within
±3 trading days" of the stations and the 24 Oct inferior conjunction, and "8 of 10 windows
printed a swing low inside the retrograde".

## Fixed inputs

| Item | Value | Note |
|---|---|---|
| Events, stations | `sbc.stations.between(start, end, ("Venus",))` | Sidereal Lahiri, Moshier. Rows with `direction` `retrograde` (R) and `direct` (D). |
| Events, conjunction | Sidereal Venus and Sun longitudes equal (geocentric conjunction, which is always inferior) | Found as the sign change of `(lon_Venus - lon_Sun) mod 360` through 0, refined to the minute. Use the same ephemeris path as `sbc/stations.py`. |
| Event session | First NIFTY session on or after the event's IST date | Weekend and holiday events move forward. |
| Sample | NIFTY daily closes in `data/market.db`, 2007-09-17 to the latest session | The store's first bar. Events before 2007-09 are excluded, which drops the deck's 2002 window. |
| Event windows | Every retrograde period from the store's first Venus R after 2007-09-17 up to the last full one | Taken from the stations, not from the deck's hand-picked windows. |
| Eras | 2007-2020 and 2021-2026 | `sbc.rule_validation._era`. |

## Definitions

- **Pivot low.** A session `t` is a pivot low if its close is the lowest close in `t-5 … t+5`.
  This uses future closes, so it describes where lows formed. It is not a tradable signal, and
  it is said so in the report.
- **Hit.** An event hits if a pivot low falls within ±3 sessions of its event session.
- **Hit rate.** Hits divided by events, per hypothesis and per era.

## Hypotheses (2 primary, one BH family)

| Name | Events | Claim |
|---|---|---|
| `h1_venus_station` | every Venus R and D station in the sample | Swing lows cluster near stations. |
| `h2_venus_inferior_conjunction` | every Sun–Venus conjunction in the sample | Swing lows cluster near the conjunction. |

No other event type is tested under B-70. Mercury, the 8-year echo, the sector and Bank Nifty
claims are out of scope and need their own registration.

## Test

1. Count hits for each hypothesis on the real event dates.
2. Build the null by shifting every event of a hypothesis by the same offset `k` sessions. Draw
   1,000 offsets, `k` uniform over whole sessions in `[-250, 250]` with `|k| >= 30`, using a
   fixed seed written into the report. Each shifted set keeps the real event count and spacing.
   Shifts that land past the last session are dropped and redrawn.
3. One-sided p-value: the fraction of offsets with hit rate at least the observed rate.
4. Benjamini–Hochberg across `h1` and `h2`, q < 0.05.
5. Repeat steps 1–3 within each era. The sign of the hit-rate lift over the null mean must match
   in both eras.

## What counts as an edge

A hypothesis passes only if all three hold:

1. BH q < 0.05 across the two primary tests;
2. the hit rate beats the null in both eras, in the same direction;
3. the observed count is at least 20 events. Below that the test is reported as underpowered
   and is not a pass.

A pass means the timing pattern beats the shift control in this sample. It does not by itself
change the forecast. The forecast changes only after a separate registration.

## Reported but not graded

- The deck's "8 of 10 windows printed a swing low inside the retrograde" claim, using the
  store-derived windows and the same pivot definition. Reported as a count with its null.
- The deck's "7–12% high-to-low range in the window versus about 5% normally". Reported as
  computed, with a normal-window comparison. No pass or fail.
- Event-level returns, 1 / 5 / 20 sessions after each event, as descriptive output.

## Known limits, stated up front

- **Few events.** Venus stations are about 2 a year each, so roughly 40 events for `h1` and about
  30 for `h2` in this sample. The 20-event floor may be met only just.
- **Overlapping windows.** Retrograde periods are about 40 days apart at most, so the ±3-session
  windows around nearby events can overlap. The shift null keeps that structure because it moves
  all events together.
- **Volatility clustering.** A pivot low is more likely in a volatile stretch. The shift null does
  not control for volatility, so a pass should be checked against the market-control harness
  (`sbc.swing_validation.grade_a`) before anyone relies on it. This registration does not run that
  check; it is a separate step.
- **Pivot window choice.** A ±5-session pivot is fixed here. Changing it after the run would
  change the hypothesis.
- **Sidereal only.** The deck's degrees are sidereal. A tropical version is a new registration.

## Run

- Script: `scripts/validate_venus_stations.py` (to be written). Output:
  `docs/research/venus_station_validation_<date>.md` and `.json`.
- Commit this file before writing or running the script. Record its SHA in the report.
