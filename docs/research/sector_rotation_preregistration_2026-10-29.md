# Sector rotation around planetary events: pre-registration (2026-10-29)

Registered 2026-10-29, before any sector-rotation report run. Written against the approved spec `.internal/specs/2026-10-29-sector-rotation-design.md` and the stress-tested plan `.internal/plans/2026-10-29-sector-rotation.md`. Once committed, nothing below may change. A different choice is a new registration, not an edit to this one.

## Confirmatory list

**Confirmatory list: empty.** Every sector output in phase 1 is descriptive.

Basis, from the prior findings only:

| Prior finding | Result | Source |
|---|---|---|
| B-58 transit events vs NIFTY (15 tests, horizons 1, 5, 20) | 0 of 15 pass. Several tests have a nominal p < 0.05 (h1 at h=5 and h=20; h3 at h=1 and h=5), but every one has q = 0.097 or higher after BH, and none reaches q < 0.05 | `docs/research/transit_event_validation_2026-10-11.md` |
| Sector vedha scenarios, out of sample (67 findings; graded on history before 2021-08-01) | 0 edge, 0 wrong way, 67 no edge | `docs/research/sector_validation_2026-10-03.md` |

No prior finding supports a directional sector hypothesis for the core four events, so none is pre-registered here. The requirement's example numbers (for example "Mercury retrograde → Pharma 75%") are illustrations and are not used as hypotheses. New directional hypotheses belong in a later registration.

## Fixed inputs

| Item | Value |
|---|---|
| Events | Mercury retrograde windows (one occurrence per window, anchored at the retrograde start station; the direct station is metadata), solar eclipses, lunar eclipses, Jupiter sign ingress, Saturn sign ingress |
| Event source | `sbc.stations.by_date` (Mercury), `sbc.transit_almanac.build(year, "sidereal")` (eclipses, ingresses). Sidereal Lahiri, IST dates |
| Event session | first NIFTY session on or after the event's IST date |
| Sectors (15) | NIFTY BANK, FIN SERVICE, IT, PHARMA, AUTO, FMCG, METAL, ENERGY, REALTY, MEDIA, PSU BANK, INFRASTRUCTURE, CONSUMER DURABLES, HEALTHCARE, OIL & GAS |
| Benchmark | NIFTY (`market.db`, from 2007-09-17) |
| Horizons | T+5, T+10, T+20 sessions from the anchor session |
| Sample cut | latest settled NIFTY session at run time, recorded in the report |
| Cluster rule | events whose anchors are fewer than 20 sessions apart merge into one cluster; the permutation shifts whole clusters |
| Effect window | ±10 sessions around each anchor, for the event-effect measure |
| Null | circular shift via `sbc.stats` (`np.roll`), `MIN_SHIFT` = 60 sessions, `N_PERMUTATIONS` = 1000, seed 0 |
| Minimum signal days | `sbc.stats.MIN_SIGNAL_DAYS` = 30 |
| Minimum independent clusters | 8 out of sample, in addition to the 30 signal days. Clusters are the binding count |
| Era boundary | out-of-sample = 2021-10-01 onward. Earlier history is descriptive. This differs from B-58's 2021-2026 era; the difference is deliberate and is stated here so it is not a silent change |
| Multiple testing | Benjamini-Hochberg across the confirmatory family only (currently zero tests) |

## Grader inputs

- Signal on day t = hypothesis direction (+1 or -1) on pre-registered anchor-window days, else 0.
- Forward return on day t = sector h-session return minus NIFTY h-session return.
- Graded with `sbc.stats.evaluate_directional`, unchanged.

## Pass rule (confirmatory only)

A hypothesis passes only if all three hold:

1. q < 0.05 after BH across the confirmatory family, in the pre-registered direction.
2. The same direction holds in both eras.
3. The incremental test against market controls (the control helper used by `sbc/transit_event_validation.py`) gives q < 0.05.

It also needs the minimum signal days and the minimum independent clusters. Anything below either floor is reported as `insufficient`, not as a finding.

## Descriptive outputs

Rank tables, top-5 appearance rates, beat-NIFTY shares, the event effect, the heatmap, the rotation matrix, the radar, and the rotation wheel and Sankey are descriptive. They are labelled "descriptive, not graded" and carry raw and cluster counts. None carries a p-value, q-value, or pass flag.

## Forecast rule

- **High**: the sector's hypothesis passes the confirmatory rule out of sample. With the empty list, no forecast can reach High in phase 1.
- **No call**: every other case.
- There is no "Medium" level. Any threshold for it would be chosen after seeing the data.
- The forecast section is a historical pattern, not a trading recommendation.

## Rotation pattern labels

Fixed here, from the spec's section 5:

- Defensive: FMCG, PHARMA, HEALTHCARE, CONSUMER DURABLES
- Growth: IT, MEDIA, AUTO
- Risk-On: BANK, FIN SERVICE, REALTY, METAL, INFRASTRUCTURE, PSU BANK
- Neutral: ENERGY, OIL & GAS

A pattern is the majority group among the top-5 sectors. Ties are "Mixed". The top-5 list is shown beside every label. The matrix is descriptive.

## Data pulls and look-ahead restriction

- Data pulls made before this registration: none.
- The ticker check (Task 2) reads row counts and first and last dates only. It does not print, summarise, or inspect returns, prices, or statistics.
- Each pull is logged with its date in an addendum to this file, before any analysis uses that data.

## Reproducibility

- Determinism tests run on a frozen synthetic fixture, never the live `market.db`.
- Each report records the last session per series and a hash of the price rows it used.

## Security scope

The new endpoint is read-only over the newest precomputed JSON. Its query parameters are allow-listed. It uses the same auth as its sibling blueprints. No new credentials are needed.

## Commit

This file's commit hash is the registration record. The first report run must come after it.
