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

## Addendum 1: ticker check (2026-10-29)

Logged before any analysis uses the data. The check read row counts and first and last dates only (yfinance, `end` = 2026-10-29). No prices, returns or statistics were printed or summarised.

| Sector | Ticker | Rows | First | Last |
|---|---|---|---|---|
| BANK | ^NSEBANK | 4704 | 2007-09-17 | 2026-10-28 |
| FIN SERVICE | NIFTY_FIN_SERVICE.NS | 3711 | 2011-09-07 | 2026-10-28 |
| IT | ^CNXIT | 4704 | 2007-09-17 | 2026-10-28 |
| PHARMA | ^CNXPHARMA | 3876 | 2011-01-31 | 2026-10-28 |
| AUTO | ^CNXAUTO | 3750 | 2011-07-12 | 2026-10-28 |
| FMCG | ^CNXFMCG | 3861 | 2011-01-31 | 2026-10-28 |
| METAL | ^CNXMETAL | 3750 | 2011-07-12 | 2026-10-28 |
| ENERGY | ^CNXENERGY | 3862 | 2011-01-31 | 2026-10-28 |
| REALTY | ^CNXREALTY | 3997 | 2010-07-19 | 2026-10-28 |
| PSU BANK | ^CNXPSUBANK | 3862 | 2011-01-31 | 2026-10-28 |
| INFRASTRUCTURE | ^CNXINFRA | 3997 | 2010-07-19 | 2026-10-28 |
| CONSUMER DURABLES | ^CNXCONSUM | 3748 | 2011-07-12 | 2026-10-28 |
| MEDIA | ^CNXMEDIA | 0 | - | - |
| HEALTHCARE | ^CNXHEALTH | 0 | - | - |
| OIL & GAS | ^CNXOILGAS | 0 | - | - |

Alternates tried for the three zero-row sectors (counts and dates only), all returning 0 rows: `NIFTY_MEDIA.NS`, `^CNXMEDIA.NS`, `^NIFTYHEALTH`, `NIFTY_HEALTHCARE.NS`, `^CNXHEALTHCARE`, `NIFTY_OIL_AND_GAS.NS`, `^CNXOILGAS.NS`, `^NIFTYOILGAS`.

Finding: `^CNXFIN` returned no rows. `NIFTY_FIN_SERVICE.NS` is used instead. (`^NIFTYFIN` and `^CNXFINANCE` also returned no rows.)

Consequence for the registration: **the sector set is 12 available indices, not 15.** MEDIA, HEALTHCARE and OIL & GAS have no usable history from yfinance. The Fixed inputs above list 15 sectors and are not changed by this addendum. The approved sector-set decision is recorded in Addendum 2 below; no report run is made before that decision is recorded.

Also recorded: sector series start between 2007 and 2011. Several sectors have roughly 3,700 to 3,900 sessions, so the out-of-sample era holds fewer sessions per sector than the full history.

## Addendum 2: registered sector set (2026-10-29)

**Sector set decision: 12 available indices.** Per the approved decision, MEDIA (`CNXMEDIA`), HEALTHCARE (`CNXHEALTH`) and OIL & GAS (`CNXOILGAS`) are excluded because the ticker check and alternates in Addendum 1 returned zero rows. No replacement data source is used.

Sector set decision: 12 available indices — CNXBANK, CNXFIN, CNXIT, CNXPHARMA, CNXAUTO, CNXFMCG, CNXMETAL, CNXENERGY, CNXREALTY, CNXPSUBANK, CNXINFRA, CNXCONSUM.

The fixed-input sector set is therefore amended from 15 to these 12 indices: NIFTY BANK (`CNXBANK`), FIN SERVICE (`CNXFIN`), IT (`CNXIT`), PHARMA (`CNXPHARMA`), AUTO (`CNXAUTO`), FMCG (`CNXFMCG`), METAL (`CNXMETAL`), ENERGY (`CNXENERGY`), REALTY (`CNXREALTY`), PSU BANK (`CNXPSUBANK`), INFRASTRUCTURE (`CNXINFRA`) and CONSUMER DURABLES (`CNXCONSUM`). The confirmatory list remains empty; this data-availability decision does not introduce hypotheses or change the analysis methods.

Rotation-pattern groups apply only to the registered sectors: Defensive = FMCG, PHARMA, CONSUMER DURABLES; Growth = IT, AUTO; Risk-On = BANK, FIN SERVICE, REALTY, METAL, INFRASTRUCTURE, PSU BANK; Neutral = ENERGY. Wheel groups likewise omit the three unavailable sectors. The original ticker-check results and 15-sector proposal above are retained as the historical registration record; this addendum is the controlling sector-set decision.

## Addendum 3: sector history pull (2026-10-29)

Logged before any analysis uses the data. The first full history pull for the 12 registered sector indices, via `scripts/refresh_market_data.py --research --full` (yfinance, `end` = 2026-10-29 settled session). This stores daily bars for `CNXBANK`, `CNXFIN`, `CNXIT`, `CNXPHARMA`, `CNXAUTO`, `CNXFMCG`, `CNXMETAL`, `CNXENERGY`, `CNXREALTY`, `CNXPSUBANK`, `CNXINFRA`, `CNXCONSUM` into `data/market.db` under the symbol key. Per stress-test branch 8, this pull stores prices required for the report; prior pulls (Addendum 1) read counts and dates only. The pull date and the per-series last session are recorded in the generated report's `input.last_session` block and its `price_sha256` hash.

## Addendum 4: event-combination slices (2026-10-29)

Logged before the report is regenerated with this slice. The approved scope for the what-if scenario filter is event combinations only. No VIX or market-regime condition is added, and no new data is pulled.

**Definition.** A combination is two or more distinct core event kinds that fall in the same cluster under the registered rule (anchors fewer than `CLUSTER_GAP` = 20 sessions apart). Same-kind repeats are not combinations. For each combination the unit is the cluster, and its anchor is the earliest member session. Window returns are taken from that anchor at the registered horizons (T+5, T+10, T+20), relative to NIFTY over the same window.

**Reused parameters, none new.** `CLUSTER_GAP` = 20 sessions; `MIN_CLUSTERS` = 8 independent clusters as the thin-sample floor; the same heat buckets, rank rule and pattern labels as the single-event tables.

**Status.** Descriptive, not graded. Each combination carries its cluster count and the thin-sample flag. No p-value, q-value or pass flag is produced. The confirmatory list stays empty, so combinations cannot produce a High forecast.

**Multiplicity.** Combinations are a descriptive slice of the same history, so they are not tested. Any combination reported as having an edge must be re-registered as a confirmatory hypothesis in a later registration, not promoted from this table.
