# Video gap analysis — AstroZ gold video (Saturn-in-Taurus thesis)

Transcript validated 2026-10-24. Ephemeris: repo pipeline (Swiss Ephemeris
Moshier, sidereal Lahiri, mean node, IST). Gold prices: repo `GC=F`
(market.db, closes to 2026-10-23). Reproduce with
`python scripts/adhoc/validate_transcript_astroz_gold_video.py` and
`python scripts/study_saturn_sign_gold.py`.

## 1. Ephemeris scoreboard (the dates are excellent)

| # | Claim | Repo ephemeris | Verdict |
|---|-------|----------------|---------|
| 1 | Saturn entered Taurus 2000-06-06 | **2000-06-07** | correct (1 day) |
| 2 | Saturn in Aries 1968-71 and 1998-2000 | 1968-06-17 → 1971-04-28; 1998-04-17 → 2000-06-07 | correct |
| 3 | Caution Jun 2027 - Oct 2027 (Saturn debilitated) | Aries 2027-06-03 → 2027-10-20 | correct |
| 4 | Caution Feb 2028 - Apr 2030 | Aries 2028-02-23 → 2030-04-17 (unmentioned Taurus dip 2029-08-08..10-05) | correct (minor omission) |
| 5 | Taurus **2030-04-17 → 2032-05-31** | 2030-04-17 → 2032-05-31 | **exact to the day, both ends** |
| 6 | J-S opposition inside that window | opposition passes 2029-12-22 → 2031-10-07 | correct |
| 7 | 2036-08-27: Saturn in Magha | Saturn enters Leo that day (09:15 IST still Cancer 29.94 Ashlesha p4) | correct at the boundary |
| 8 | 2036-08-27: "30 deg axis with Jupiter" | separation **61.6 deg** | **wrong** (2x off; 60 deg sextile is the nearest real aspect) |
| 9 | Bullish window ends 2041-01-29 | Saturn enters Libra 2041-01-28, stations retrograde 2041-02-01; J-S conj was 2040-10-31 | correct (real cluster) |
| 10 | J-S conjoin ~20 y, oppose ~10 y | conj 1981/2000-05-28/2020-12-21/2040-10-31; opp 1969-71, 1989-91, 2010-11, 2029-31 | correct (19.86 y synodic) |

## 2. Gold price claims vs repo data (GC=F + repo USDINR series)

Repo gold: 2025-04-21..30 avg $3,348 · peak **2026-01-29 high $5,586**
(−29.2% to the 2026-06-30 low $3,955) · latest 2026-10-23 close **$4,008**.
Repo USDINR (verified live, 2003-12 → 2026-10-24): 85.26 / 92.04 / 94.79 /
94.71 on those dates.  What basis does each INR claim imply?

| Claim (INR/10 g) | Gold level | Actual FX | Implied FX | Premium over actual |
|---|---|---|---|---|
| Apr 2025 video: "around 96,000" | $3,348 | 85.26 | 89.2 | **+4.6%** |
| "hit 1,90,000 in January" | $5,586 (peak high) | 92.04 | 105.8 | **+14.9%** |
| "dropped back to ~1,39,000" | $3,955 (trough low) | 94.79 | 109.3 | **+15.3%** |
| "currently 1,50,000-1,60,000" | $4,008 | 94.71 | 120.3 | **+27.0%** (+22.8 to +31.3) |

Reading (corrects the 2026-10-24 draft's constant-FX note, which used a
bad conversion):

- The Apr 2025 figure carries a ~+5% premium — consistent with an
  MCX/import-duty basis.
- The Jan peak and Jun trough figures both carry ~+15% — consistent
  with each other and with a **retail-jewellery basis** (making charges
  + GST), so those two claims are internally coherent.
- The **"currently" claim breaks even that basis**: at the ~15%
  premium his own Jan/Jun figures imply, today's $4,008 at 94.71
  would be **~Rs 1.40-1.42L/10g, not 1.5-1.6L** — the current-price
  claim is ~10% above the video's own implied basis.
- "6 lakhs" = **~$19,300/oz at actual FX** (94.71), i.e. ~4.8x from
  the current bullion level — the floating multiple rides on an
  unstated basis throughout.

## 3. Backtest (reports/saturn_sign_gold_study_2026-10-24.md)

Segment returns per Saturn sidereal sign, repo data (one full lap,
2000-08 → 2026-10), reproduce his cycle-2 table almost line by line:
Taurus +14.2% (claimed +12), Gemini +24.8% (+25), Cancer +47.2% (+52),
Leo +49.2% (+63), **Virgo +77.8% (claimed +77 — exact)**.

But per-day permutation test (10,000 shuffles):

| test | days | mean %/day | annualised | p |
|------|------|------------|------------|---|
| Taurus+Leo combined | 1,118 | +0.0553 | +13.9% | **0.398** |
| Taurus alone | 529 | +0.0233 | **+5.9%** | below the +12.7%/yr all-day baseline |
| Leo alone | 589 | +0.0841 | +21.2% | (driven by 2007-09) |

- **Taurus was the weakest of the bull signs** in the only lap we can
  test, and below the unconditional gold baseline — the video's core
  sign story is contradicted where it is testable.
- The biggest modern gold leg ran in **Aquarius** (+60.4%, 2023-01 →
  2025-03) — a sign the video never mentions; Virgo (+26.9%/yr) and
  Cancer (+24.1%/yr) also beat Taurus.
- His cycle-1 segment numbers are roughly right against known gold
  history ($35-40 → ~$120 by Jun 1973 ✓; Cancer -10% ✓; Leo +155-165%
  ✓; peak Jan 1980 ✓; -70% to $256 by 2000 ✓; 1979 ≈ +126-135% ✓) —
  with one slip: the claimed Taurus endpoint "$195 (April 1971-June
  1973)" belongs to **December 1974, inside the Gemini window**.
- Cycle phase is inconsistent between his own examples: cycle 1 ran
  **opposition → conjunction** (1971 opp passes bracket the Nixon
  shock; gold peaked Jan 1980 just before the 1981 conj passes), but
  cycle 2 ran **conjunction → opposition** (2000-05-28 conj; gold
  peaked Sep 2011 between the 2010-11 opp passes). The 2030-41
  prediction adopts cycle-1's phase without saying why.

## 4. Gaps in the commentary (ranked)

1. **The sign story is one 1970s episode, now tested.** With the
   pre-2000 series in hand (DataHub/LBMA monthly,
   `reports/saturn_sign_gold_study_long_2026-10-25.md`): over
   1971-2026 Taurus (+206% total) and Leo (+301%) are indeed the two
   best signs and Taurus+Leo is nominally p=0.000 — but that is the
   1971-73 and 1977-79 legs, the shuffle ignores gold's return
   autocorrelation, and the pattern does **not replicate** modern-only
   (1998-2026 p=0.284; GC=F 2000-2026 p=0.398, Taurus below baseline,
   biggest modern leg in Aquarius). Exact dates, unreplicated rule:
   the 2030-32 Taurus call rides on a pattern that has fired once.
2. **Phase inconsistency between his own two cycles** (opp→conj vs
   conj→opp, section 3). The 2030-41 window's *J-S skeleton* is real;
   the rule for *why the rally starts at the opposition* is fitted
   per cycle.
3. **Unstated price basis.** Against the repo's real USDINR series the
   claims imply premiums of +4.6% (Apr 2025, MCX-like), ~+15% (Jan/Jun
   2026, retail-like) — then +27% for the "currently" claim, breaking
   even his own basis (it implies ~Rs 1.40-1.42L/10g, not 1.5-1.6L).
   The "4-6x" target depends entirely on which basis you anchor to
   (6 lakhs = ~$19.3k/oz at actual FX, ~4.8x from $4,008 bullion).
4. **Floating multiple rhetoric:** the target is always "6 lakhs", so
   the multiple was 6x at 96k, 3.2x at 1.9L and "4-6x from here" now —
   the anchoring number never updates on new information.
5. **No falsification or path risk.** An 11-year window needs an
   invalidation rule ("thesis dead below X by 2030-04-17") and must
   carry cycle-2's path (gold fell -45% from the 2011 peak inside a
   decade-long bull narrative). "Not for speculators" is stated — good —
   but no rebalancing or drawdown discipline is given.
6. **"Inflation above 9%"** — ambiguous (US CPI is nowhere near 9%; India
   CPI has not run 9% since 2013-14; M2 growth is not 9%). The
   fundamental leg of the thesis rests on an unlabelled number.
7. Minor: the "30 deg axis" on 2036-08-27 is actually 61.6 deg (2x off —
   the same secondary-date drift pattern the 2026-10-18 analysis found);
   the 2029 Saturn Taurus dip (Aug-Oct 2029) sits inside his "Aries
   caution" window unmentioned.

## 5. Tool gaps this video exposes (added to the TODO)

1. **Pre-2000 gold series** — ✅ resolved 2026-10-25 (DataHub/LBMA
   monthly, 1833-2026, cached to `data/gold_monthly_long.csv`; Stooq
   itself is JS-challenge + IP-denied). See TODO A6 for the verdict.
2. **USDINR series** — ✅ resolved 2026-10-24 (live to 2026-10-24, depth
   2003-12 → today; see TODO A7). Remaining: surface FX alongside gold
   wherever the tool prints INR gold levels.
3. A stated bullion-vs-retail basis note wherever the tool prints INR
   gold levels.
