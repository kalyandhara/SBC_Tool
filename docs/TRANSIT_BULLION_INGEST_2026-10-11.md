# Transit Almanac and Bullion Week — ingest note (2026-10-11)

Two third-party sources were ingested and rebuilt from Swiss Ephemeris:

1. A "2026 Astrological Aspects" yearly chart (tropical, UT+5:30) with a plain-language event list.
2. A daily "Bullion Trading Strategy" sheet for 18 Sep 2026: nakshatra "last 50" stats, Rahu Kaal,
   horas, Moon transit, Moon KP sub-lord timeline with an expected trend, US data releases.

## Shipped

- **B-55 — Transit Almanac.** `sbc/transit_almanac.py`, `GET /api/engine/transit-almanac?year=&zodiac=`,
  section at the foot of the Forward Calendar tab (`static/js/transit-almanac.js`). Stations, sign
  changes, exact aspects (listed under the faster planet), eclipses and mean-node sign changes for
  1990-2050, sidereal Lahiri or tropical, dates in IST. Every date on the source chart matches
  (`tests/test_transit_almanac.py`).
- **B-56 — Bullion Week.** `sbc/bullion_week.py`, `GET /api/engine/bullion-week?start=`, new
  "Bullion Week" tab (`static/js/bullion-week.js`). Per trading day: Rahu Kaal, 24 horas, tithi,
  Moon pada changes, Moon KP sub-lord segments over the MCX session (09:00-23:30 IST). Per week:
  ingresses, stations, Moon conjunctions, positions at Monday sunrise, US releases from
  `data/econ_events.json`, and each nakshatra's last-50-session gold and silver record against the
  base rate with a binomial p-value. Matches the 18 Sep sheet to within 2 minutes
  (`tests/test_bullion_week.py`).

## Findings

- **Ayanamsa trap.** `sbc.kp_ephemeris._flags()` sets Swiss Ephemeris' global sidereal mode to
  Krishnamurti. Code that assumes Lahiri without setting it gets timings that depend on call order
  (~10 minutes for Moon events). Both new modules set Lahiri on every call; tests pin this.
- **The sheet's nakshatra stats do not reproduce.** It shows Jyeshtha 31 up / 19 down for gold. Our
  COMEX history to 11 Sep 2026 (09:15 IST attribution) gives Jyeshtha 20 / 30 (p = 0.09) and Mula
  33 / 17 (p = 0.07) against a 53% base rate. Neither is significant, and with 27 nakshatras about
  one in twenty will show p < 0.05 by chance.

## Follow-ups

- **B-57 — Bullion sub-lord rules: registered, amended, code ready, waiting for data.**
  `docs/research/bullion_sublord_preregistration_2026-10-11.md` (SHA-256 9d29f806…ff3, posted
  2026-10-11T17:48:18Z) and `docs/research/bullion_sublord_amendment_1_2026-10-11.md` (SHA-256
  1bc8b4bd…9cb, posted 2026-10-11T18:08:05Z, before any intraday data was downloaded). The
  amendment moves the source to Dukascopy XAUUSD/XAGUSD hourly spot (user's choice), fixes the
  sample at 2010-01-01 to 2026-09-30 and defines hour-floored segment edges and the hour-of-day
  control. `scripts/fetch_dukascopy.py` downloads the bars (run on the user's PC; this sandbox
  can't reach Dukascopy). `scripts/validate_bullion_sublords.py` runs the registered test
  (~4 minutes). Plumbing tested on synthetic data only (`tests/test_bullion_sublord_validation.py`).
- **B-58 — Transit events and NIFTY: registered and run, no edge.**
  `docs/research/transit_events_preregistration_2026-10-11.md` (SHA-256 074b68cc…c35, posted
  2026-10-11T17:48:18Z, before any code), results in
  `docs/research/transit_event_validation_2026-10-11.md`. None of the 15 tests passes BH
  (lowest q = 0.097). Two notes, neither a pass: Mercury-station windows show bigger 5- and
  20-session moves at p ≈ 0.02 and survive the market controls, but fail BH, and the 20-session
  effect flips sign in 2021-2026. Tense Mars/Saturn/Pluto windows show *smaller* moves than other
  sessions in both eras, the opposite of the traditional claim. Forecast stays at the base rate
  for all five; a follow-up on either note would be a new registration.
- **B-59 — Econ calendar and MCX hours: done (feed refresh runs on the user's PC).**
  `sbc/econ_calendar.py` parses the BLS and BEA iCalendar feeds, keeps the bullion-relevant
  releases (CPI, PPI, payrolls, JOLTS, GDP, PCE, trade), and converts US Eastern to IST with
  daylight time (8:30 ET = 18:00 IST in summer, 19:00 IST in winter).
  `scripts/refresh_econ_calendar.py` rewrites `data/econ_events.json`, keeps rows marked
  `"source": "manual"` (Census retail sales has no feed), drops manual rows a feed row
  supersedes, and keeps a feed's old rows if that feed fails. The Bullion Week session now
  ends at 23:30 IST on US daylight time and 23:55 IST otherwise, per day
  (`bullion_week.session_for`). Tests: `tests/test_econ_calendar.py`.
