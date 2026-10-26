# Backlog — Monthly NIFTY projection (ingested 2026-10-05)

**Source:** Obsidian note `SBC-Tool/Financial Astrology-Oct26 monthly hypothetical NIFTY projection.md`.
The note is nine screenshots and two words of text ("aspect build up"). The screenshots
look like they come from a YouTube video; the source has no author or method notes.
Numbering continues from `BACKLOG_REVIEW_2026-10-01.md` (last item B-39).

## What the note contains

| # | Screenshot | Content |
|---|---|---|
| 1–2 | "Oct 2026 Month Market Forecast" (bar and line chart) | One unitless score per calendar day, −5 to 60, weekends included. Transcribed to `data/projections/2026-10_third_party_monthly.csv`. |
| 3 | "Forecast vs Actual for Sep 2026" | The Sep score line drawn over a TradingView price line. The price scale is 54,400–57,300, so the index is **not NIFTY** (NIFTY closed Sep near 22,600 in `data/nifty_ohlc.csv`); it looks like BANKNIFTY. By eye, the score and price don't track each other: price fell most of the month while the score swung around 20–60. |
| 4 | "Planets Shar" | Ecliptic latitude (Śara / vikshepa) of Mo, Ma, Me, Ju, Ve, Sa, Ur, Ne, Pl for each day. |
| 5 | "Grah Kranti" | Declination of Su…Pl plus Rahu/Ketu for each day. |
| 6 | "Planets Speed" | Daily motion in °/day, 1 Oct – 4 Nov. Shows Mercury slowing towards its station and Venus retrograde. |
| 7 | "Planets Motion for Oct 2026" | Stations to the minute (IST): Venus R 03-10 12:43 · Rahu (true node) D 03-10 19:06 · Rahu (true node) R 07-10 06:49 · Pluto D 16-10 11:02 · Mercury R 24-10 12:42. |
| 8 | "Aspect build up" table, 1–15 Oct | Columns: Date, Weekday, a muhurta note (Bhadra, Ghabad Muhurat, "3 to 6 Ra Direct"), Pl1, Aspect, Pl2, Time, Winner, Relations, Rashis, Combust, Retro. Aspects: 0/30/45/60/90/120/135/150/180 plus two codes, **KSc** and **KSp**. Moon conjunctions are highlighted. The rashis are sidereal (Sun in Virgo on 1 Oct). |
| 9 | AUGMONT daily chart (TradingView) | A trendline breakout after a post-earnings gap-down. Bought at 912.85, partial profit booked twice, exited at 1,224. No astrology in it; see B-48. |

**Trading days in Oct 2026:** 20 (holidays on 2 Oct, Gandhi Jayanti, and 20 Oct, Dussehra, from
`sbc/market_holidays.py`). Of the 31 scores, 11 fall on non-trading days, including the
5 on 3 Oct and the −5 on 20 Oct.

## What the tool already has

- Daily speed and retrograde flags per planet: `sbc/fingerprint.py` (`speed`, `stationary`, `retrograde`).
- Declination: `sbc/factors.py::declinations()`, used only for the `moon_out_of_bounds` factor.
- Stations and exact aspects in `sbc/forward_calendar.py`. These are dated to the first 09:15 IST snapshot after the event, not to the minute, and the Moon is left out.
- Bhadra: `sbc/bhadra.py`.
- A month view: `sbc/monthly_heatmap.py` is a sector × day heatmap, not one NIFTY score line.

**Missing:** ecliptic latitude, minute-level event times, a Moon aspect table, true-node
stations, "winner", "relations", Ghabad Muhurat, and any monthly NIFTY score line with a
forecast-vs-actual view.

## Priority order

Same rule as the main backlog: no claim of predictive value until it passes the validation
gate (`sbc/stats.py`, `sbc/incremental.py`, the forecast ledger). Phase 2 and B-39 found no
edge in 60 rule tests and 102 aspect-timing tests. So **B-40 comes first**: score the
third-party projection before building anything that copies it.

---

### B-40 · Freeze and score the third-party October projection (P1)
**Status (2026-10-05): step 1 done.** 31 rows frozen in `data/forecast_ledger.db` table `external_forecasts` at 01:41 IST on 6 Oct, before the open: 26 `live`, 5 `post_hoc` (1–5 Oct). `forecast_ledger.score_external()` implements step 2 (persistence baseline measured on the same days as the score's calls; one-sided binomial p against a coin). After the 30 Oct close, run `python scripts/forecast_ledger.py external-score --source third_party_monthly --month 2026-10 [--symbol BANKNIFTY]` and write the report. Steps 2–4 still open.

**Why:** this is the cheapest test of whether the method is worth copying, and the scores
were published before the month played out.
**Scope:**
1. Load `data/projections/2026-10_third_party_monthly.csv` into the forecast ledger as an external component (`source="third_party_monthly"`, frozen 2026-10-05). Scores for 1–5 Oct were published after those sessions opened, so mark them `post_hoc` and leave them out of the score.
2. After the 30 Oct close, score the 20 trading days (or the 16 from 6 Oct on):
   - The sign of the day-over-day change in score against the sign of NIFTY's daily return. Report the hit rate against a 50% baseline and against "same as yesterday's return".
   - Spearman correlation of score against the next-session return, and against the close.
   - The two lowest-score trading days (19 and 22 Oct, both −5): did NIFTY fall?
3. Run the same check against BANKNIFTY. Screenshot 3 suggests that is the index the source overlays.
4. Repeat for Sep 2026 if the Sep scores can be read reliably from screenshot 3 (y-axis labels are illegible; mark the transcription approximate).

**Acceptance:** a short report in `docs/research/third_party_monthly_2026-10.md`. It must
say that 20 sessions is far too few for significance, and keep the series in the ledger
so later months can extend it.
**Open:** which index the score is meant for, and what the score scale means (is 30 neutral? 0?).

### B-41 · Monthly NIFTY score line with forecast-vs-actual overlay (P2) — ✅ done
**Status (2026-10-11): done.** Score source decided with the owner: the fingerprint classical net that `/api/engine/monthly_projection` already returned, not `sbc/forecast.py` probability. That composite adds only validated components, so it is the base rate every day (a flat line). Panel: Monthly Score on the Forward Calendar tab (`static/js/monthly-score.js`): score on the left axis, NIFTY close on the right, hollow markers for non-trading days, freshness badge, "hypothetical, unvalidated" label and live 5-session hit rate. Tests: `tests/test_monthly_projection.py`. Browser-checked on a local server.
**Scope:**
- `GET /api/engine/monthly_projection?month=YYYY-MM` returns one value per calendar day from our own composite in `sbc/forecast.py`, flagged for trading or non-trading days, plus NIFTY closes so far.
- A chart on the Forward Calendar tab: score line (left axis), NIFTY close (right axis), and an option to overlay an external series such as B-40's.
- Label it "hypothetical, unvalidated" with the ledger's live hit rate, as the forecast card already does.

**Acceptance:** past days show the actual close; future days show only the score; a freshness badge (B-05) shows when the price data is behind.

### B-42 · Exact-time station table, including true-node Rahu/Ketu (P2)
**Status (2026-10-05): done.** `sbc/stations.py`, `GET /api/engine/stations`, forward-calendar events and trap-calendar `node_stations` (for reference; the trap score is unchanged). Sidereal speed matches 4 of 5: Venus 12:43, Rahu R 06:48, Pluto 11:02, Mercury 12:42. **Rahu D 03-10 is 22:01, not 19:06.** The cause is not UTC (that would be 5:30 off). The true node's speed is almost flat there, so a lunar-theory difference (Moshier, no ephemeris files) moves the time by hours. Tropical speed puts Pluto at 08:10, so the source is sidereal.

**Why:** `forward_calendar` dates a station to the next 09:15 snapshot, which can be a day late.
Rahu's true node stations several times a month; the code tracks only the mean node.
**Scope:** `sbc/stations.py`. Scan Swiss Ephemeris speed in hourly steps, find each sign
change, refine by bisection to the minute, and return IST times. Planets: Mercury…Pluto,
plus the true node (`swe.TRUE_NODE`). Feed the results into `forward_calendar` and the
Rahu–Ketu trap calendar.
**Acceptance test:** reproduce the five stations in screenshot 7 to within ±5 minutes
(Venus R 03-10 12:43, Rahu D 03-10 19:06, Rahu R 07-10 06:49, Pluto D 16-10 11:02,
Mercury R 24-10 12:42). If a time is off by about 5:30 hours, the source used UTC.

### B-43 · Exact-time aspect table ("aspect build up") (P2) — ✅ done 2026-10-13
**Status (2026-10-13): done.** Backend, API, UI integration, and tests complete.
- `sbc/aspect_table.py`: Exact-time geocentric sidereal aspects with Moon included, IST to the minute
- `GET /api/engine/aspect_table?start=&end=`: API endpoint in `engine_bp.py`
- UI: New "Aspect Table" panel on Forward Calendar tab with planet and aspect filters
- Tests: `tests/test_aspect_table.py` with acceptance test matching screenshot 8 to ±2 minutes
- **KSc/KSp resolved**: Orb-entry events - KSp for conjunctions (0°), KSc for all other aspects
- **Winner resolved**: Speed-based (higher absolute speed wins), with rank tie-breaker
- **Relations resolved**: 1/7 for conjunctions, 7/1 for oppositions, otherwise sign-count X/Y
**Acceptance test passed**: Mo 0 Ur 01-10 08:17, Su 120 Mo 01-10 12:36, Su 180 Sa 04-10 17:53,
Su 0 Mo 10-10 21:22 (new moon), Mo 0 Ve 12-10 09:58 all reproduced within ±2 minutes.
**Scope:** `sbc/aspect_table.py` and `GET /api/engine/aspect_table?start=&end=`. One row
per exact geocentric sidereal (Lahiri) aspect, **Moon included**, with:
Date, Weekday, Time (IST, to the minute), Pl1, Aspect, Pl2, Rashis (`Vi-Ta`), Relations
(sign count each way, e.g. `5/9`), Combust (planets within the combustion orb of the Sun),
Retro (retrograde planets of the pair), and the day's muhurta notes (Bhadra from
`sbc/bhadra.py`; Ghabad from B-46). Highlight conjunctions. Show it as a table on the
Forward Calendar tab with a planet and aspect filter.

### B-44 · Ecliptic latitude (Śara) per planet (P3)
**Status (2026-10-05): done.** `latitude` on every fingerprint planet record (0 for the mean nodes); the fingerprint store rebuilds stale rows on its own. Not added to `feature_vector`, so the analog search is unchanged. The node-crossing factor is still a follow-up.

**Scope:** add `latitude` to the planet records in `sbc/fingerprint.py` (`swe.calc_ut` already
returns it) and expose a daily series. Fingerprint rows carry `sbc.engine_version`, so B-20's
cache logic rebuilds stale ones.
**Acceptance:** Moon latitude for October 2026 runs about +5° → −5° → +5°, Venus about −7.5° → −5°, as in screenshot 4.
**Follow-up:** Moon crossing latitude 0 (node crossing) as a candidate factor in `sbc/factors.py`, graded like the rest.

### B-45 · Declination (Kranti) and speed charts (P3)
**Status (2026-10-05): done.** `sbc/planet_series.py`, `GET /api/engine/planet_series`, and the Planet Motion panel on the Forward Calendar tab (station table plus the Plotly chart, which starts with the Moon hidden on the speed chart). Candidate factors not started.

**Scope:** `declinations()` and fingerprint `speed` already exist; this item is display only.
`GET /api/engine/planet_series?metric=declination|latitude|speed&start=&end=` and one
Plotly panel with a metric toggle and per-planet legend, matching screenshots 4–6.
Mark the out-of-bounds band (±23.44°) on the declination chart and the 0 line on the speed chart.
**Candidate factors** (graded before use): declination parallels and contra-parallels (no
such factor exists today), and Mercury speed below 0.2°/day before a station.

### B-46 · Ghabad Muhurat (P3) — ✅ done
**Status (2026-10-05): definition found. Built and tested.** `ghabad_windows()` and `ghabad_kind_at()` in `sbc/muhurta.py` reproduce all 18 October windows in the research note to within a minute (`tests/test_muhurta.py`). The B-43 aspect table's `muhurta` column shows Ghabad / Ardha-ghabad. Bhadra is still empty there (B-43). Rule from Marathi Wikipedia, summarised in `docs/research/ghabad_muhurat.md`: count nakshatras Sun → Moon inclusive, × 3, + tithi (1–30), mod 7; remainder 3 = Ghabad, 0 = Ardha-ghabad. It reproduces the note's 05-10 mark (Ghabad 03:55–23:10 IST, the whole session).
The note marks 05-10 as "Ghabad Muhurat, Bhadra". The codebase has no Ghabad calculation.

### B-47 · Rebuild the source's monthly score (P3, gated on B-40)
Only start if B-40 (and at least two further months in the ledger) show the third-party
score beating the baselines. The method isn't published. A rebuild would mean fitting
weights for B-42…B-46 inputs to the published scores, which risks overfitting 31 numbers.
If B-40 shows no edge, close this item as "won't do" with the B-40 report as the reason.

### B-48 · AUGMONT breakout chart — confirm intent (P3, triage)
Screenshot 9 is a trendline-breakout trade with no astrology in it. Possible readings:
(a) it was pasted into the wrong note; (b) it's a request for a trade journal (entry,
partial exits, exit, R-multiple); (c) it's a request for a breakout scanner (descending
trendline after a post-earnings gap-down). **Ask before scoping.**

---

## Suggested order

| Step | Items | Outcome |
|---|---|---|
| Now (before 6 Oct open) | B-40 step 1 | Projection frozen in the ledger before more sessions trade |
| This week | B-42, B-43 | Minute-level events, the table from the note (both done) |
| Any time | B-44, B-45 | Latitude, declination and speed charts (both done) |
| After 30 Oct close | B-40 steps 2–4, B-41 | Verdict on the projection, our own month line |
| Gated | B-46, B-47, B-48 | Wait on definitions, the B-40 verdict, or the user |
