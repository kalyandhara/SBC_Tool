# Video gap analysis — AstroZ (Neesh Kumar) crash-cycle video vs SBC_Tool

Transcript validated 2026-10-22. Ephemeris checks use the repo pipeline:
Swiss Ephemeris (Moshier), sidereal Lahiri, mean node, IST. Reproduce with
`python scripts/adhoc/validate_transcript_astroz_crash_video.py` (per-claim
snapshots, station/ingress scans, NIFTY drawdown checks).  Statistical
context: `reports/node_jupiter_event_study_2026-10-19.md` and
`reports/video_gap_analysis_2026-10-18.md` (same channel, earlier video).

## 1. Ephemeris scoreboard (forward claims)

| # | Transcript claim | Repo ephemeris | Verdict |
|---|------------------|----------------|---------|
| 1 | Oct 31, 2026: Jupiter enters Leo / Magha (Ketu's nakshatra) | **2026-10-31 17:30 IST** (Ashlesha -> Magha) | **correct** |
| 2 | Jupiter aligns with the Rahu-Ketu axis | Jupiter conjunct Ketu: exact **2026-11-12** (0.0 deg); 1.9 deg on Oct 31; stays within 3.4 deg through Jan 24 (Ketu trails into Cancer after the 2026-12-05/06 node ingress) | **correct** |
| 3 | Shatashtak (6/8) with Saturn | Ju-Sat mutual 6/8 **2026-11-01 .. 2027-01-24** (Saturn Pisces, Jupiter Leo) | **correct, but wording reversed**: Jupiter is *6th* from Saturn; Saturn is 8th from Jupiter |
| 4 | Window lasts until Jan 25, 2027 | Magha -> Ashlesha (retrograde re-entry) **2027-01-25** | **correct** |
| 5 | "Jupiter goes retrograde on January 27th" | Jupiter stations retrograde **2026-12-13 06:00 IST**; direct **2027-04-13**. On Jan 27 it is mid-retrograde, 2 days after leaving Magha. Nearest real stations: Mars R **2027-01-10**, Mercury R **2027-02-09** | **wrong planet and date** (probably a garble of the Jan 25 retrograde re-entry) |
| 6 | Mars joins Ketu Nov 12-13 | Mars-Ketu exact **2026-11-15** (0.13 deg); Jupiter-Ketu exact Nov 12; on Nov 15 Jupiter 1.56 / Mars 1.16 / Ketu 1.09 all in Magha p1 with Rahu opposite in Aquarius | **~2-3 days early; configuration is real and tighter than claimed** |
| 7 | Cycle "starts again around November 3rd" | No discrete event on Nov 3; regime begins Oct 31 (Sat) / Nov 1-2 (first 6/8 days). Nov 3 = US midterms (geopolitical, not planetary) | **unexplained** |
| 8 | "Note the low of the market on November 1, 2026" | **Nov 1, 2026 is a Sunday** — no session anywhere | **unexecutable as stated** (Oct 30 or Nov 2 intended) |
| 9 | June 2027: Saturn debilitated | Saturn Pisces -> Aries **2027-06-03** (Rx back 2027-10-20, re-enter 2028-02-23) | **correct** |
| 10 | June 2027: Jupiter "surrounded by malefics" | Jupiter re-enters Magha **2027-06-26**; Ketu conjunct (10.5 deg, closing) Jun-Jul; Sun conjunct/combust in Magha ~**2027-08-25** (4.6 deg) | **partially supported** (Ketu + Sun; Saturn is 4/5th away, not an affliction) |
| 11 | 2033: Ju-Sat Shatashtak, no malefics -> bull market | 6/8 windows: **2032-06-01..08-12** and **2032-10-24..2033-03-17** (not "2033" broadly); inside the window no node/Mars hits, but Sun transits Capricorn mid-Jan 2033 (combustion) | **imprecise; internally inconsistent** (see gap #11) |
| 12 | "Cycle similar to 1929" | Oct 1929: Jupiter **Rohini** (Moon-ruled), **Saturn in Mula** (Ketu's nakshatra — the pattern's subject is Saturn, not Jupiter); only shared feature is the Ju-Sat 6/8 | **not similar on his own stated pattern** |

## 2. Historical crash table — claim vs ephemeris (crash-relevant date)

| Event | Claimed | Ephemeris | Verdict |
|-------|---------|-----------|---------|
| 1966 Dow -26% | Ju "with Rahu, centered between Mars and Saturn" | Peak 1966-02-09: Ju Taurus 27.9 Mrigashira (Mars-nak), Rahu same sign but 20.7 deg; low 1966-10-07: Ju **Cancer/Pushya**, no node hit, no 6/8 | **fails** |
| 1973-74 Dow -45% | Ju "between Rahu and Ketu", Shatashtak with Saturn | Peak 1973-01-11: Ju conj **Rahu 3.5 deg**, on the node axis (Ketu 176 deg), **6/8 with Saturn**, combust (Ju-Su 0.6) | **holds at the peak** |
| 1979-80 Dow -20% | Ju entered Magha, aligned Rahu-Ketu, Saturn, Sun | 1980-02-13 and 04-21: Ju **Magha** + conj **Rahu** (7.2/4.3) + conj **Mars** (3.6/3.2); Saturn same sign at the low; Sun not involved | **holds** (but the fall was **-16%**, not -20%) |
| 1987 Black Monday -23% | Ju in Ashwini | 1987-10-19: Ju **Aries 0.91 Ashwini p1 Rx** + 6/8 with Saturn | **exact** |
| 1992 Sensex -57% | Ju in Magha afflicted by Saturn, Rahu, Mars, Sun | 1992-04-23: Ju **Magha p4 Rx** + 6/8 with Saturn ok; **Rahu 119 deg, Mars 165 deg, Sun 122 deg** — no conjunctions (Sun only combusts late Aug 1992; Rahu itself sits in Mula) | **half right** |
| 2000 Nifty -53% | Ju with Saturn, in Ashwini | 2000-02-11: Ju **Ashwini 5.55**, Saturn Aries same sign, 11.7 deg apart | **holds** (wide conjunction) |
| 2008 Nifty -64% | Ju in Moola afflicted by Mars and Ketu ("very similar to 2008") | Peak 2008-01-08: Ju **Mula p4** but Ketu 124.7 deg, Mars 172.9 deg; low 2008-10-27: Ju **P.Ashadha** (not Mula) | **fails** (nakshatra true only at the peak; claimed afflictions absent at both dates) |
| 2020 Nifty -39% | Ju with Saturn and Sun, in Moola | Peak 2020-01-20: Ju **P.Ashadha** (Mula stay ended Jan 4), conj **Ketu 3.8**, Saturn same sign 12.6; low 2020-03-23: Ju **U.Ashadha**, conj **Mars 1.5** | **fails as stated** |
| 1995 (benign) | Ju in Ketu's constellation, unafflicted | Ju in Jyeshtha/Anuradha all year; enters **Mula 1995-12-07** — and the Sensex kept falling into Feb 1996 | **wrong** (decline happened while Ju was *outside* Ketu naks) |
| 2003 (benign) | Ju in Magha, unafflicted | Magha 2003-07-30..09-30, no 6/8, no node hit; Nifty rallies | **valid** |
| 2023 (benign) | Ju in Ashwini, unafflicted | Ashwini stays 2023-04-21..06-21 and 2023-11-26..2024-02-03; Nifty +20% — but note Ju was conjunct **Rahu 3.5 deg** in Ashwini in May 2023 | **valid, and weakens the "node affliction" rule** |
| Omitted in-thesis cases | — | 2011-12-20 low: Ju **Ashwini Rx**; 2015-08-24 China crash: Ju **Magha** + **Sun combust 2.1 deg** (2015 is in his intro list, dropped from the table) | **omitted** |

Market numbers (repo data where available): 1966 -26.5% ok; 1973-74 -45.1% ok;
1979-80 **-16.1%** (claimed -20%); 1987 -22.6% ok; 1992 Sensex ~-57% ok;
2000 Nifty ~-50% close-basis (claimed -53%; Sensex ~-58%); 2008 Nifty
**-64.6%** intraday (market.db) ok; 2020 Nifty **-38.2%** (market.db) ok.
"Sensex 500" does not exist (Nifty 500 / BSE 500 do). ~200M demat accounts is
plausible for late 2026.

## 3. Gaps in the commentary (ranked)

1. **No base rate / unfalsifiable selection.** The repo event study on the
   exact same pattern (12 Jupiter-in-Ketu-nakshatra stays 2000-2030) finds
   NIFTY *during* the stays mean **+1.89%** (62% up) and forward-21d **-1.14%**
   vs a random baseline of +1.89%, **p = 0.998** — no detectable effect, n=8-9.
   The video counts hits (8 crashes) and never counts misses.
2. **Large false negatives.** Dow 2000-02 (-38%), 2007-09 (-54%), 2011, 2018,
   2020 (-37%), 2022 (-25%) and NIFTY 2010-11, 2015-16, 2022 declines do not
   fit "Jupiter in Ketu nakshatra + afflicted" at the crash dates. The
   "common thread" survives only because those bigger declines are excluded.
3. **Wrong retrograde story.** Jupiter's Rx station is **2026-12-13**, not
   Jan 27; the Jan 25/27 "shift" is actually Jupiter retrograding *back into
   Cancer/Ashlesha*, which ends the Magha window he spent the video building.
4. **Flagship 2008 comparison fails its own test** (see table): at the 2008
   low Jupiter was in P.Ashadha with no Mars/Ketu affliction. The 2026 setup
   actually matches **1980** (Magha + Rahu + Mars: Dow -16%) and **1987**
   (Ashwini + 6/8) — outcomes between -16% and -23%, not -64%.
5. **Nov 1, 2026 is a Sunday** — the "note the low of Nov 1" trigger cannot be
   set, and it carries no validity window, so it can never be wrong.
6. **Date slippage on the marquee events**: Mars-Ketu exact is Nov 15 (claimed
   12-13); nothing planetary happens on Nov 3; the node ingress that actually
   ends the Leo axis (Rahu -> Capricorn, **2026-12-05/06**) is never mentioned —
   and repo data shows post-ingress NIFTY forward 21d mean **+7.0%, p=0.000,
   71% up** — evidence *against* his December-January bearishness.
7. **Internal contradiction on Shatashtak**: in 1973/1987/1992 he treats the
   Ju-Sat 6/8 as a crash engine (1987 had *nothing else* and still fell 23% in
   a day), yet the 2033 bull call uses the same 6/8 as bullish "because other
   malefics are absent". Same yoga, opposite outcome, decided post hoc.
8. **The 1995 counter-example is factually confused** (Ju not in Ketu naks
   during the 1995 fall; Mula entry in Dec 1995 did not stop it), while the
   genuinely strong 2023 counter-example (Ju **with Rahu** in Ashwini, +20%
   year) quietly undermines his own affliction rule and is left unexamined.
9. **Direction errors and naming**: "Jupiter in the 8th house from Saturn" is
   reversed (it is 6th-from / mutual 6-8); "Sensex 500" is not an index.
10. **No falsification or risk framing**: no stop, position-size, or explicit
    "the call is wrong if X"; historical outcomes under the *same* claimed
    configuration range from -16% to -57% to +0% (2003/2023), so the setup
    carries no usable magnitude. The "consult your advisor" line is present —
    good — but the video's own rule would have kept you out of 2003, 2023
    (both booms) and still missed 2022's -25% Dow bear.

## 4. Tool coverage for this video

Already covered: Magha ingress datetime, nakshatra_periods scanner, node
ingresses, stations, NIFTY/gold/silver/crude event studies (all stored under
`reports/`). Prototyped today: Shashtashtaka-window scanner, 1929/2033
snapshots, Mars-node exact conjunction refinement
(`scripts/adhoc/validate_transcript_astroz_crash_video.py`).
Remaining gaps if we want to grade future videos of this type:
1. A reusable `jupiter_saturn_shashtashtaka` scanner in `sbc/transits.py`
   (mutual 6/8 sign windows for any planet pair).
2. A "note the low of date D, signal when broken within N sessions" rule
   tester in `sbc/factors.py` (his recurring price-trigger device).
3. Combustion-of-Jupiter (Sun conj within 11 deg) as a factor — 2015 and
   1992 (Aug) fit his thesis better than the events he cites.
