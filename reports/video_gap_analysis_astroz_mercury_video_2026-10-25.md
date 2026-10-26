# Video gap analysis — AstroZ Mercury-retrograde video (2026-10-25)

Transcript validated 2026-10-25. The video day is pinned to **Saturday
2026-10-25** by its own opening line ("Mercury has gone retrograde as of
yesterday") against the repo station time: Mercury R **2026-10-24
12:42 IST**. Ephemeris: repo pipeline (Swiss Ephemeris Moshier, sidereal
Lahiri, mean node, IST). Prices: repo CSV caches (GC=F, SI=F, CL=F, HG=F,
^NSEI) auto-refreshed to 2026-10-23. Reproduce with
`python scripts/adhoc/validate_transcript_astroz_mercury_video.py`,
`python scripts/study_retrograde_reversal.py --asset nifty` and
`--asset gold`.

## 1. Ephemeris and panchang scoreboard (the timing work is excellent)

| # | Claim | Repo ephemeris | Verdict |
|---|-------|----------------|---------|
| 1 | "Mercury retrograde as of yesterday" | Mercury R 2026-10-24 12:42 IST (Libra 26.7) | correct (pins the video day) |
| 2 | Venus already retrograde | Venus R since 2026-10-03 12:43 | correct |
| 3 | Saturn already retrograde | Saturn R since 2026-07-13 (direct 2026-11-27) | correct |
| 4 | "Venus is combust" | Venus-Sun 1.6 deg on the video day (orb 10) | correct — deep combust |
| 5 | "Today is Purnima" | tithi 14 (Chaturdashi) 2026-10-25 09:15; **Purnima = 2026-10-26** | one day early |
| 6 | "Tomorrow Moon in Aries (Ashwini) - recovery" | 2026-10-26: Moon Aries, Ashwini pada 3 | exact |
| 7 | "Day after: Moon in Bharani - volatility" | 2026-10-27: Moon Bharani | exact |
| 8 | NIFTY "high of 26,277 on Sept 27" (2024) | 2024-09-27 high **26,277.35** | exact |
| 9 | "falling since September 2024" | NIFTY made a **new ATH 26,373.20 on 2026-01-05**; the current -14.3% runs from Jan 2026, and 2025 rallied 19.4% off the Mar-2025 low (22,083) | **false as history** |
| 10 | "Mercury and Venus both went retrograde in March [2025] and a recovery began" | Venus R 2025-03-02, Mercury R 2025-03-15; NIFTY trough 2025-03-04, +5% by 2025-03-20 | half-right: the low printed 11 days *before* the Mercury station, at the Venus station |
| 11 | "63 completed periods, Oct 2006 - Jul 2026" | **63** Mercury retro stations 2006-10-01..2026-08-01 | exact count |
| 12 | Mars-Ketu "attack last June" (2025) | exact crossing **2025-07-23** (June: approaching, ~10+ deg out) | loose — same secondary-date drift as prior videos |
| 13 | "February attack with Mars-Rahu" (2026) | exact crossing **2026-03-13** | ~2 weeks off |
| 14 | "Mars and Ketu align November 12" | **2026-11-15**, orb 0.000 (TODO A3) | 3 days early |
| 15 | Fed "outcome Oct 28"; "Oct 29 press conference" | FOMC 2026-10-28 (statement + presser same day, repo econ calendar) | date right; Oct-29 presser does not exist |
| 16 | Oct 28: "Moon between Rahu and Ketu, under Saturn's aspect" | Moon Taurus Krittika, 95/85 deg from Rahu/Ketu (mid-arc), Saturn (Pisces) Vedic 3rd aspect on Taurus | correct |

## 2. Price levels vs transcript

| Claim | Repo data | Verdict |
|---|---|---|
| Gold "around $4,000" (COMEX) | 2026-10-23 close $4,007.90 | correct |
| Silver "around $53" | 2026-10-23 close $53.95 | correct |
| "Brent hit around $116" | repo has no Brent; WTI 90-session high $110.48 (2026-10-20); typical spread $3-4 implies Brent ~$113-114 | unverifiable, plausible-ish — tool gap |
| "Crude averaging over $80" | WTI 2026 YTD close avg $84.80 | correct |
| Copper "hasn't fallen much, recovered first" | HG -1.3% off its 2026-08-06 high ($6.73), vs silver -24%, NIFTY -14% | correct (data to Aug 25) |
| NIFTY "fallen about 14%" | -14.3% from the 2026-01-05 high | correct level, wrong starting story (claim 9) |

## 3. Backtest — the trend-reversal claim, graded with matched baselines

The video's core numbers (its own card): 63 periods, trend reversed
31/63 (49.2%); **after a downtrend 19/29 rebounded (65.5%)**; 41/63
positive (65.1%), average +0.55%. Speech drifts from the card (33/63 =
52.4%).

The honest test is not against 50%: after ANY 10-session downtrend,
NIFTY's next 21 sessions are positive **58.6%** of the time (base rate,
n=1,994; gold 59.1%). Station days must beat *that* to matter.
`scripts/study_retrograde_reversal.py` (pre-registered definitions:
K=10-session pre-trend, M=21-session forward return, matched
permutation baseline of same-sign pre-trend random days):

| NIFTY | n | rebound after downtrend (p) | flip after uptrend (p) | overall reversal (p) | window mean / win |
|---|---|---|---|---|---|
| Mercury | 60 | **14/26 = 53.8% (0.758)** vs 58.6% base | 13/34 = 38.2% (0.959) | 45.0% (0.721) | +0.51% / 65% |
| Venus | 11 | 6/6 (0.075) | 2/5 (1.000) | 72.7% (0.185) | +3.41% / 64% |
| Mars | 9 | 3/3 (0.398) | 2/6 (1.000) | 55.6% (0.887) | +2.78% / 78% |
| Jupiter | 17 | 2/6 (0.390) | 4/11 (1.000) | 35.3% (0.407) | +4.77% / 71% |
| Saturn | 18 | 1/7 (0.051) | 3/11 (0.580) | 22.2% (**0.041**, nominal — direction *opposite* to the claim; dies among 25 cells) | +4.98% / 56% |

- Sensitivity grid (Mercury x NIFTY, K in {5,10,20} x M in {5,10,21}):
  rebound rates 44-65%, **all p >= 0.248**. The video's 65.5% is
  reachable only as the best cell of nine — the multiple-testing trap.
- Gold (n=82 Mercury stations, 2000-2026): rebound after downtrend
  **16/33 = 48.5% (p=0.286)** vs 59.1% base — the claimed "22/31 = 71%"
  is nowhere in the data; "11/32 turned negative in uptrends" is
  matched by 18/49 = 36.7%, but the *base rate* is 45.1%, so it is
  randomness wearing a number.
- The video's headline "+0.55% average, 65.1% positive" **reproduces**
  (+0.51%, 65%, n=60) — and is meaningless: the 2026-10-18 window
  study already showed random same-length windows match it (p=0.716,
  `reports/mercury_retrograde_study_2026-10-18.md`). It is NIFTY's
  upward drift, not Mercury.
- The Mar-2025 hero episode (claim 10) does not support the mechanism:
  the trough printed at the *Venus* station, 11 days before Mercury's.

Reading: Mercury retrograde station days are statistically
indistinguishable from any other day, before *and* after conditioning
on the trend. The one nominal outlier (Saturn stations: trends
*continue*, 4/18 reversals, p=0.041) points the opposite way to the
video's thesis and does not survive the 25-cell multiple-testing eye.
Existing coverage stands: `scripts/study_mercury_retrograde.py`
(2026-10-18, unconditional windows, no edge on any asset) and the
crash tool's `mercury_retrograde` bearish trigger (w=1) now has two
independent null studies against it.

## 4. Gaps in the commentary (ranked)

1. **The 65.5%/71% "reversal" numbers are the base rate of mean
   reversion, plus selection.** After any 10-session downtrend the
   market bounces more often than not (NIFTY 58.6%, gold 59.1% in 21
   sessions). The video never compares against this, and its own card
   (49.2% overall = coin flip) contradicts its speech (52.4%).
2. **No definitions.** Trend length, reversal window and the "+0.55%
   average return" window are never stated; every reasonable choice
   (K 5-20, M 5-21) lands at p >= 0.25 on NIFTY and below base rate on
   gold.
3. **"Falling since September 2024" erases a 19.4% rally and a new
   ATH (2026-01-05).** The current -14% is a 2026 correction from a
   high the video does not mention — the same anchoring pattern as the
   gold video's floating "6 lakhs".
4. **Attack-timing dates drift** (Jun->Jul 23 2025; Feb->Mar 13 2026;
   Nov 12->Nov 15): precise-sounding dates that are weeks off — the
   recurring secondary-date drift pattern (10-18, 10-24 analyses).
5. **Small unforced errors:** Purnima a day early; an Oct-29 Fed
   presser that does not exist; Mars-Rahu/Ketu crossed weeks off the
   named months.
6. **Untestable as stated:** "2:30 PM flip tomorrow", "1.13% crude
   drop on the news", "FIIs withdrew ~4 lakh crore" (repo flows start
   2025-10), "Korea/Japan/China fell first" (no Asian index series).
7. **Not falsifiable.** "Volatile next week", "pullback then
   pressure", "no full-scale rally" fit almost any path; the one
   testable near call (Moon-in-Ashwini recovery day, 2026-10-26) is a
   single day — the tool's own moon studies found no nakshatra edge
   (`reports/moon_mercury_nakshatra_nifty_2026-10-18.md`).

## 5. Tool gaps this video exposes (added to the TODO)

1. **Brent (BZ=F) series** — crude claims are graded on a WTI proxy
   with an unquantified spread.
2. **Asian equity indices (KOSPI/N225/HSI)** — the "neighbours fell
   first, we crash later" contagion story (this video and the
   2026-10-22 crash video) is ungradeable without them.
3. **FII flow history** — NSE's API only exposes the latest session;
   cumulative-year claims ("4 lakh crore") cannot be audited.
