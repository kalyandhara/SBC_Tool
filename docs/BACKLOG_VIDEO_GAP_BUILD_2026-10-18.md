# BACKLOG: Video gap analysis build items (2026-10-18)

Source: `reports/video_gap_analysis_2026-10-18.md` (astrologer week-ahead
video vs SBC_Tool audit). Each item is built and validated one at a time.
Definition of done per item: ruff clean, runnable evidence in `reports/`,
status updated in this file.

| # | Item | Priority | Status |
|---|------|----------|--------|
| 1 | Crude oil series (`CL=F`) + Moon-in-Rahu-nakshatra (Ardra/Swati/Shatabhisha) magnitude study | High | **done 2026-10-18** - claim REFUTED (see notes) |
| 2 | Mars-Rahu/Ketu conjunction tracker + event study (crude/VIX/gold/NIFTY forward returns around exact conjunctions 2025-07-23, 2026-03-13, 2026-11-15) | High | **done 2026-10-18** - VIX-spike confirmed, crude/market-fall refuted |
| 3 | Nitya-yoga trading rules in `panchang_signals.py` (Vyatipat +/-24h rule; yogas already computed in `market_calendar.py`) | High | **done 2026-10-18** - claim INVERTED: Vyatipata is a bullish NIFTY window |
| 4 | Kendra-yoga scanner (Gaja-Kesari / Lakshmi / 6-in-kendra) on the 9:15 Mumbai open chart, extending `crash_windows.day_state` lagna machinery | Medium | **done 2026-10-18** - no edge; video's Oct 19 "6 planets in kendra" claim not supported |
| 5 | Mercury retrograde validation study (analog of `venus_station_validation.py`) | Medium | **done 2026-10-18** - no significant edge on any asset |
| 6 | Data expansion: USDINR (`USDINR=X` or `INR=X`), BankNIFTY (`^NSEBANK`), US VIX (`^VIX`) in `market_data._ASSETS`; FOMC calendar in `econ_calendar.py` | Medium | **done 2026-10-19** |
| 7 | Event studies: node sign-change (next 2026-12-06) and Jupiter-in-Magha (2026-10-31) forward returns | Medium | **done 2026-10-19** - node change -> NIFTY rally (p<0.001); Guru-Ketu-nakshatra decline claim refuted |
| 8 | Cross-asset crash-propagation module (equity crash -> all-asset drawdowns; grades "silver weak" and 2008-analog claims) | Low | **done 2026-10-19** - "all assets fall" refuted; rupee weakens in 16/16 episodes |

## Notes

- Item 1 result (2026-10-18, `reports/moon_rahu_nakshatra_crude_2026-10-18.md`):
  875 in-group vs 7,256 other Moon periods since 2000. Mean |move| in
  Rahu nakshatras **2.04% vs 2.24%** for all others - crude is marginally
  *quieter*, not wilder (permutation p = 0.958). >=2% moves: 38.6% vs
  40.3%. The video's flagship rule is **not supported** by the data.
  Companion rule (Moon in Mercury nakshatras -> NIFTY moves,
  `reports/moon_mercury_nakshatra_nifty_2026-10-18.md`): +0.07 pp
  uplift, p = 0.061 - a weak volatility hint, no direction edge (48% vs
  50% up); treat as noise pending a preregistered test. New tooling:
  `scripts/study_moon_lord_group.py` (any asset x any nakshatra lord).
- Item 2 result (2026-10-18, `reports/mars_node_conjunction_study_2026-10-18.md`):
  37 episodes 2000-2030 (next: **2026-11-15 Ketu, orb 0.01 deg**, then
  2028-01-08 Rahu). Event study (n=32): **India VIX rises sharply** after
  Mars-node conjunctions (+5d +8.8% mean, 78% up, p=0.004; +10d +16.6%,
  p<0.001; +21d +23.5%, p=0.006) - the strongest confirmed signal so
  far. NIFTY **rises** (+5d +1.85%, p=0.002; +21d +4.61%, p=0.001 -
  post-shock rebound, opposite of "market falls"). Crude does **not**
  systematically spike (+21d mean -2.5%, p=0.097); gold/silver flat-ish
  with mild dips. Video's crude-to-120 thesis and "market falls" get no
  support; his stress intuition maps to a volatility spike, not a
  directional crash. Tail caveat: 2020-02-24 episode = COVID onset.
  New tooling: `scripts/study_mars_node_conjunction.py`.
- Item 3 result (2026-10-18, `reports/vyatipat_formation_study_2026-10-18.md`):
  375 Vyatipata formations 2000-2026. NIFTY **rises** after formation
  (+1d +0.36%, 64% win; +3d +1.55%, 66% win; +5d +2.53%, 65% win;
  p<0.001 vs random windows) - the video's "markets fall after
  Vyatipat" is **inverted**. Gold/silver flat (p>0.6) - "bullions
  fall" refuted. Crude mild bearish drift at +5d (-0.82%, p=0.020).
  Tooling: nitya-yoga layer added to `sbc/nakshatra.py`
  (`nitya_yoga_of`, NITYA_YOGA_NAMES) + `panchang_signal()` now
  exposes nitya_index/nitya_yoga/vyatipata_active; study in
  `scripts/study_vyatipat_formation.py`. Candidate bullish window
  flagged for walk-forward validation, not yet a signal. Note: next
  Vyatipata 2026-10-27 11:29 IST - and it is a *bullish* base rate.
- Item 4 result (2026-10-18, `reports/kendra_yoga_study_2026-10-18.md`):
  4,682 NIFTY sessions 2007-2026 scored on the 9:15 IST Mumbai chart.
  Gaja-Kesari (n=1,537): day mean -0.01% vs baseline -0.07%, 48% win,
  p=0.145 - no edge. Benefics-in-kendra Lakshmi proxy (n=758): day mean
  -0.12%, 42% win, red candles 58% vs 52% baseline, p=0.071 - the
  "positive open then fade" half of the video claim shows up as a mild
  bearish fade, not a bullish yog. High-kendra days (>=5 of 7, n=77):
  p=0.923, nothing. The video's specific Oct 19 reading ("6 planets in
  kendra") fails ephemeris check: tool finds 0 of 7 (2 of 9 incl.
  nodes) in kendra that morning. Tooling:
  `scripts/study_kendra_yogas.py` (scanner reusable for any date).
- Item 5 result (2026-10-18, `reports/mercury_retrograde_study_2026-10-18.md`):
  98 retrograde episodes 2000-2030 (84 with data; 14 upcoming, next
  2026-10-24 -> 2026-11-13). No significant edge anywhere: NIFTY window
  mean +0.22% (46% win, p=0.716), gold +1.06% (65% win, p=0.431),
  crude +1.04% (p=0.706). Around-station (-5..+5 sessions) mild
  positive drift for gold +1.20% (p=0.069) and silver +1.79%
  (p=0.093) - directionally the opposite of "market turns down after
  the station". Post-window NIFTY forward returns are strong (+2.6%
  5d, +6.3% 21d average) - the "after Mercury R things get bad" claim
  has no base-rate support. Tooling:
  `scripts/study_mercury_retrograde.py`.
- Item 6 result (2026-10-19): three new cached series in
  `sbc/market_data._ASSETS` - usdinr (5,934 rows, 2003-12-01..),
  banknifty (4,698 rows, 2007-09-17..), vix (9,269 rows, 1990-01-02..).
  `sbc/econ_calendar.py` gains `static_rows()` (FOMC rate decisions
  2026 + provisional 2027, statement 14:00 ET -> IST with DST handling,
  plus 2026-11-03 US midterms), wired into
  `scripts/refresh_econ_calendar.py`; data/econ_events.json now 134
  rows (BLS ICS returned 403 this run - no prior BLS rows existed, no
  regression; retry another day). Payoff test
  (`reports/moon_mercury_nakshatra_banknifty_2026-10-19.md`): Moon in
  Mercury nakshatras -> BankNIFTY |move| +0.11 pp (1.43% vs 1.32%,
  p=0.038; >=2% days 23.9% vs 20.4%; direction 51/50) - the first
  video claim with nominal support, but a tiny magnitude-only effect
  within multiple-testing noise; preregister before trusting. NIFTY
  same rule: +0.07 pp, p=0.061.
- Item 7 result (2026-10-19, `reports/node_jupiter_event_study_2026-10-19.md`):
  20 Rahu sign ingresses 2000-2030 (next **2026-12-05**, matching the
  video's Dec 5-6 within a day). Post-ingress NIFTY **rallies**: +5d
  +2.9%, +10d +3.8%, +21d **+7.0% (71% win, p<0.001)** - the video's
  "big planets bring the flood" is inverted for equities; consistent
  with build #2's pattern (node events -> VIX spike then rebound).
  Bottom-hold check: NIFTY 67% of events hold the pre-ingress low for
  21 sessions vs 47% random baseline (p=0.152 - directionally supports
  his "bottom holds" claim, not significant at n=17). Jupiter in Ketu
  nakshatras (12 stays, 8-9 with data): NIFTY stay mean +1.89% (62%
  win, p=0.998 vs the bearish claim), gold +2.33% (67% win) - the
  "declines happen while Guru is in Ketu nakshatras" claim is
  refuted. Current Magha stay 2026-10-31..2027-01-24 has a positive
  base rate. Tooling: `scripts/study_node_jupiter_events.py`.
- Item 8 result (2026-10-19, `reports/crash_propagation_study_2026-10-19.md`):
  16 NIFTY crash episodes (21-session return <= -10%) 2000-2026, incl.
  the 2008 GFC cluster, COVID (-37.3%) and 2026 Feb-Mar (-14.0%).
  Propagation profile over crash windows: gold **+1.93%** mean (44%
  fell) - gold does not systematically fall with equities; silver
  -0.85% (56% fell, mildest bearish tilt - his "silver weak" has a
  grain of truth); crude -1.63% (ns). The two systematic propagators
  are **USDINR (+5.4%, rupee weaker in 16/16 episodes, p<0.001)** and
  India VIX (+79%, p<0.001). The rupee result directly contradicts
  the video's current premise (rupee appreciation hurting Indian
  gold): in NIFTY crash regimes the rupee has never strengthened -
  INR-priced gold gets a tailwind. Stress days (NIFTY <= -2%, n~197):
  gold -0.27%, silver -1.07%, crude -2.03% - single-day dips, not
  episode-level crashes. Tooling: `scripts/study_crash_propagation.py`.

## Sprint close (2026-10-19)

All 8 items built and validated. Confirmed patterns: Mars-node events
-> VIX spike + NIFTY rebound (builds #2/#7); Vyatipata -> mild NIFTY
bullish window (#3, walk-forward pending); BankNIFTY Mercury-nakshatra
volatility hint (#6, preregister first); rupee weakness as the only
reliable crash propagation (#8). Refuted: Moon-Rahu-nakshatra crude,
Mars-node crude spike / market fall, Vyatipat bearish, kendra yogas
bullish, Mercury-retro bearish, Jupiter-Ketu-nakshatra decline,
all-assets-fall propagation. The video's recurring failure mode is
directional storytelling on patterns whose real signature is
volatility, not direction; and roughly half its dates do not survive
ephemeris verification.
- The Libra triple-conjunction study (claim #8 of the video) is already
  done: `scripts/study_gold_libra_triple.py`,
  `reports/gold_libra_triple_backtest.md`.
