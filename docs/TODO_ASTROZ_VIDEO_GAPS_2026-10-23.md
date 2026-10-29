# TODO — filling the AstroZ crash-video gaps (2026-10-23)

Companion to `reports/video_gap_analysis_astroz_crash_video_2026-10-22.md`.
Ordered by validation value; check off as each lands with a study report.

## A. Tool gaps (from report section 4)

- [x] **A1. Mutual 6/8 (Shashtashtaka) scanner in `sbc/transits.py`.** ✅ DONE
      2026-10-23 — `sign_distance_periods(planet_a, planet_b, start, end,
      distances=(5, 7), ...)`, CLI `--shashtashtaka`; confirms the video's
      Ju-Sat 6/8 as 2026-10-31..2027-01-24 (85.6d) + a second window
      2027-10-20..11-26 it never mentions. Tests:
      `tests/test_transits_distance.py` (4 passed; incl. `distances=(0,)`
      cross-check vs `same_sign_periods` and the 1929 window).
- [x] **A2. Combustion-of-Jupiter factor in `sbc/factors.py`** ✅ ALREADY
      EXISTS AND GRADED. `jupiter_combust` is a registered G8 factor
      (bearish, direction pre-fixed) and the 2026-10-03 harness verdict is
      **no edge at all horizons** (n=355; 1d p=0.711, 5d p=0.580, 20d
      p=0.947; `jupiter_dignity` also no edge, q=0.252 after BH).
      `docs/research/factor_validation_2026-10-03.md`. The 2015/1992
      combust-crash cases are 2 of 355 non-predictive days.
- [x] **A3. Mars-node conjunction tracker.** ✅ DONE 2026-10-23. The event
      study already existed (`scripts/study_mars_node_conjunction.py` ->
      `reports/mars_node_conjunction_study_2026-10-18.md`: 37 episodes,
      crude 21d mean -2.35% p=0.121, n=32 — not significant; medians
      honest read). Added the missing library-grade exact-crossing
      scanner: `sbc/transits.conjunction_events(planet_a, planet_b, ...)`
      (conjunctions AND oppositions, ~1 s precision, Ketu-aware) + CLI
      `--conjunctions`. Pins the video's "Mars joins Ketu Nov 12-13" to
      **2026-11-15, orb 0.0000 deg**. Tests:
      `tests/test_transits_conjunctions.py` (5 passed; fixtures: the
      three recent Mars-node events, the Dec 2020 great conjunction,
      Sun-Moon alternation).
- [x] **A4. Price-trigger rule tester ("note the low of date D; trend flips
      when broken within N sessions").** ✅ DONE 2026-10-23 —
      `scripts/study_low_break_trigger.py` ->
      `reports/low_break_trigger_study_2026-10-23.md` (NIFTY 2007-2026).
      The literal device (1-day low, 10-session window) breaks in 65% of
      anchors and forward returns after the break are indistinguishable
      from random (21d p=0.754) — **no bearish edge**. Notably the
      K=5 close-break variant showed a *positive* +5d bounce vs random
      (p=0.005; does not survive the 15-test multiple-testing eye) —
      the opposite sign to the video's use.
- [x] **A5. Dow Jones series (^DJI).** ✅ DONE 2026-10-25. Repo asset
      added (`sbc/market_data._ASSETS["djia"] = ("^DJI",
      "djia_ohlc.csv")`; 8,765 daily rows, 1992-01-02 → 2026-10-23,
      cached). Pre-1992 Dow daily is unreachable free (FRED = 10-year
      window, WSJ 401, Stooq JS-challenge + IP-denied), so episodes
      1965-1992 are graded on the DataHub/Shiller S&P monthly proxy
      (`data/sp500_monthly_long.csv`, documented). The video's four Dow
      depths are broadly right as history (proxy: 1966 -17.3% monthly
      closes vs Dow -26.5% intraday; 73-74 -43.4% vs -45%; 79-80
      -10.7% close-basis vs -16.1%; 87 -26.8% quarterly vs -22.6% day).
      Under its own strict rule (Ketu-nakshatra stay at the peak AND
      afflicted) it covers **1/3 pre-1992 and 1/4 post-1992** Dow
      episodes (loose: 3/3, 3/4) - vs NIFTY 4/7. Cherry-picked hits.
      `scripts/study_dow_crash_claims.py` ->
      `reports/dow_crash_claims_study_2026-10-25.md`.
- [x] **A6. Pre-2000 gold series.** ✅ DONE 2026-10-25. DataHub/LBMA
      monthly gold (1833-2026) cached to `data/gold_monthly_long.csv`;
      `scripts/study_saturn_sign_gold.py --source long` (Stooq was
      blocked by a JS proof-of-work + IP denial - probe kept in git
      history). Verdict on the full 1971-2026 span: Taurus +206% and
      Leo +301% totals are the two best signs and Taurus+Leo is
      nominally p=0.000 - **but** it is two episodes (1971-73,
      1977-79), autocorrelated monthly returns overstate the shuffle
      significance, and it does **not replicate** modern-only
      (1998-2026 p=0.284; GC=F 2000-2026 p=0.398). The video's dates
      are exact; the sign rule is one 1970s episode plus noise.
      `reports/saturn_sign_gold_study_long_2026-10-25.md`.
- [x] **A7. USDINR series.** ✅ DONE 2026-10-24 — already wired in the
      working tree (`sbc/market_data._ASSETS["usdinr"] = ("USDINR=X",
      "usdinr_ohlc.csv")`, user's WIP); verified live and current:
      **2003-12-01 → 2026-10-24, 5,939 rows** (94.71 on 2026-10-23).
      Immediately used to reconcile the gold video's INR claims with
      real FX (implied premium table: +4.6% / +14.9% / +15.3% / +27.0%)
      — and it **corrected the gap-analysis draft**, which had claimed a
      constant USDINR ≈ 95-96 from bad arithmetic: the Jan/Jun claims
      fit a ~15% retail basis, but the "currently 1.5-1.6L" claim breaks
      even that basis (his own basis implies ~Rs 1.40-1.42L).
      `reports/video_gap_analysis_astroz_gold_video_2026-10-24.md`
      section 2; repro in
      `scripts/adhoc/validate_transcript_astroz_gold_video.py`.
- [x] **A8. Brent crude series (BZ=F).** ✅ DONE 2026-10-26.
      `sbc/market_data._ASSETS["brent"] = ("BZ=F", "brent_ohlc.csv")`;
      4,790 daily rows 2007-07-30 -> 2026-10-25 (ICE trades Sunday
      evenings; weekend bars harmless to the studies). Immediately
      grades the 2026-10-25 video: "Brent hit around $116" = the
      2026-10-23 high $117.41 / close $116.72 — exact. 2026 YTD avg
      $90.67 (video's "averaging over $80" also holds on Brent).
      `reports/video_gap_analysis_astroz_mercury_video_2026-10-25.md`
      section 2 updated.
- [x] **A9. Asian equity indices (KOSPI ^KS11, N225, HSI).** ✅ DONE
      2026-10-26. Added to `sbc/market_data._ASSETS` (kospi 1996-12+,
      nikkei/hsi 1990+; 7-9k rows each) and ran the pre-registered
      study: `scripts/study_asia_contagion.py` ->
      `reports/asia_contagion_study_2026-10-25.md` (India = SENSEX
      1997-07+, the only Indian series deep enough for 2000). Crash
      clusters: bear = >=20% under the trailing 252-session high,
      episodes <=63 sessions apart merged. Verdict: co-movement real
      (worst India dd within ~6 months after a neighbour trough
      -26.5..-29.3% vs -21.4% random; KOSPI p=0.012, others 0.064-0.068;
      India <= -15% within 126 sessions after ~70% of troughs vs ~51%
      random) but the TIMING claim fails — neighbour weekly returns
      carry zero next-week information (r=+0.02..+0.05, same as
      India's own autocorrelation; contemporaneous r=+0.41..+0.46).
      "India falls less" (2026): true vs KOSPI -39.1% and HSI -17.4%,
      false vs Nikkei -13.4%. 2008: neighbours led the bear entry,
      troughs were near-simultaneous (+24..27 d).
- [x] **A10. FII flow history.** ✅ DONE 2026-10-26 (as a documented
      limitation, not a series). NSE's API exposes the latest session
      only; the store accumulates from its first refresh
      (data/market.db flows: 2026-10-01 → 2026-10-26, 14 sessions), so
      cumulative claims ("FIIs withdrew ~4 lakh crore") can never be
      audited from the repo. No UI or weekly-commentary surface shows
      flow totals; the one place coverage is surfaced -
      `market_store.freshness()` / `/api/engine/market/freshness` -
      now carries the limitation note on its FII_DII entry (the module
      docstring and `sbc/market_features.py` already documented it).

## B. Commentary gaps -> validation studies

- [x] **B1. Base-rate study: "Jupiter afflicted in a Ketu nakshatra".** ✅ DONE
      2026-10-23 — `scripts/study_jupiter_ketu_afflictions.py` ->
      `reports/jupiter_ketu_affliction_study_2026-10-23.md`. 18 stays
      1990-2035, day-grain affliction flags (6/8 or same-sign Saturn,
      node <=10 deg, Mars <=10 deg, combust <=11 deg). Whole stays: NIFTY
      mean +1.89% vs random +1.89%, p=0.994. Afflicted sub-windows: mean
      +0.74% vs random +1.13%, p=0.857, win 57% — below random. The
      video's rule shows no edge at its most favourable reading.
      → *gaps #1, #2, #4.*
- [x] **B2. False-negative ledger.** ✅ DONE (folded into B1 report).
      7 NIFTY drawdowns >= 15% since 2007; only 4/7 had a stay/affliction
      at/near the peak. Clean misses: 2015-03->2016-02 (-22.5%),
      2024-09->2025-03 (-15.8%), and the ongoing 2026-01->2026-10
      (-15.6%) — a real 2026 correction with zero Ketu-nakshatra
      involvement that the video never mentions. 2020 is a partial hit
      under the fair sign-based reading (Sat+Node+Comb near peak).
      → *gap #2.*
- [x] **B3. Guru-Chandal (Jupiter-Rahu) check.** ✅ DONE 2026-10-25 —
      `scripts/study_guru_chandal.py` ->
      `reports/guru_chandal_study_2026-10-25.md`. Grades the crash
      tool's own definition (sign co-presence, combo weight 0.14):
      Jupiter-Rahu co-presence windows with NIFTY data — 2008-09
      **+24.7%**, 2009 +12.2%, 2016 +15.9%, 2023 +8.5% — **all four
      positive**, forward +21d mixed; exact crossings pinned
      (1994-10-07, 2001-08-02, 2009-02-12, 2016-06-25, 2023-05-27).
      Jupiter-Ketu windows: 3 positive, one -27.4% (the COVID window,
      2019-11→2020-03). n stays tiny (Jupiter reaches a node every
      ~7.3 y) — no significance claim possible; the 2023 counter-
      example stands; the w=0.14 bearish Trigger has no study support.
      The B1 node_10 flag stays combined; the rahu/ketu split lives in
      this dedicated study instead. → *gap #8.*
- [x] **B4. Counter-evidence into the forward calendar.** ✅ DONE 2026-10-25.
      Verified the calendar already renders every video-relevant event with
      exact dates: Ju conj Ketu exact 0.04° **2026-11-12**, Mars conj Ketu
      exact 0.07° **2026-11-15**, **Rahu enters Capricorn 2026-12-06**,
      Jupiter -> Ashlesha (Magha exit) **2027-01-25**. Added
      `sbc/forward_calendar.NODE_INGRESS_NOTE` + `node_changes()`: when a
      window contains a node sign change, the calendar (JSON, markdown
      blockquote, HTML) now surfaces the event-study context - after the
      last 17 Rahu sign changes NIFTY's mean +21-session move was +7.0%
      (71% up, p=0.000), historically a bottoming marker, not a crash
      trigger; research prompt, small n. First weekly report to carry it:
      2026-11-14 (4-week window reaching Dec 12). Tests:
      `tests/test_forward_calendar.py` 10 passed.

## C. Already covered (no action)

- [x] Rahu ingress event study (2026-10-19) — B4 evidence source.
- [x] Jupiter-in-Ketu-nakshatra stays (unafflicted) event study (2026-10-19).
- [x] Ephemeris scoreboard for the video's own dates (2026-10-22 report).
- [x] Mars-Ketu exact date refinement (2026-11-15, ad-hoc script).

## D. Mercury-retrograde video (2026-10-25) — done same day

- [x] **D1. Transcript validation.** ✅ 2026-10-25 —
      `scripts/adhoc/validate_transcript_astroz_mercury_video.py` ->
      `reports/video_gap_analysis_astroz_mercury_video_2026-10-25.md`
      (section 1 scoreboard). Video day pinned to 2026-10-25 by the
      station time (Mercury R 2026-10-24 12:42 IST). Timing claims
      near-perfect: Venus/Saturn retro + Venus combust (1.6 deg)
      correct; Moon-in-Ashwini/Bharani day calls exact; Oct-28
      "Moon between nodes + Saturn's 3rd aspect" correct; Mercury
      count 63 exact; gold/silver/crude-avg/copper claims correct.
      Errors: Purnima a day early; "falling since Sept 2024" false
      (new ATH 26,373 on 2026-01-05); Mars-node attack dates drift
      (Jul 23 2025, Mar 13 2026, Nov 15); Oct-29 Fed presser does not
      exist.
- [x] **D2. Trend-reversal backtest, all planets.** ✅ 2026-10-25 —
      `scripts/study_retrograde_reversal.py` (pre-registered) ->
      `reports/retrograde_reversal_study_2026-10-25.md` (NIFTY) and
      `reports/retrograde_reversal_gold_2026-10-25.md`. Conditioned on
      the pre-station trend with matched permutation baselines (the
      claim the 2026-10-18 study did not test): Mercury x NIFTY
      rebound-after-downtrend 14/26 = 53.8% vs 58.6% base (p=0.758);
      gold 16/33 = 48.5% vs 59.1% base (p=0.286); K/M grid 44-65%,
      all p >= 0.248; the video's 65.5%/71% claims never appear. The
      window stats (+0.51%, 65% win) reproduce the video's +0.55%/65.1%
      but match random windows (10-18 study, p=0.716) — drift, not
      Mercury. One nominal outlier (Saturn: trends *continue*, 4/18,
      p=0.041) points opposite to the thesis and dies among 25 cells.
      → Mercury retrograde is now covered twice: unconditional
      windows (2026-10-18) and conditional reversal (2026-10-25).
      Both null.
- [x] **D3. (minor) Near-term calls on the record.** ✅ Ledger built
      2026-10-26 — `reports/astroz_calls_ledger.md`: every falsifiable
      dated call from the three analysed videos, grading rules frozen
      at record time (open-day rules for the Ashwini/Bharani/Fed/Oct-29
      calls, window-return rules for the bear-through-February,
      Ju-Sat-6/8 and Saturn-Taurus calls, price-proxy rule for the
      Mars-Ketu risk window). First grading due at the 2026-10-31
      weekly review (closes calls 1-5); calls 8-11 carry dates to
      2032. Untestable calls (2:30 PM flip, the unfalsifiable
      "6 lakhs") are recorded against the video's falsifiability.
