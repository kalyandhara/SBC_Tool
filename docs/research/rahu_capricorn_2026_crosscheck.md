# Cross-checks: astrology forecasts for late 2026 vs. ephemeris, history and the SBC tool

- **Part 1:** "December 2026 Rahu–Ketu shift" video (2026-10-02)
- **Part 2:** Q4 2026 transit predictions, Mars–Ketu in Leo (2026-10-03)

# Part 1 · "December 2026 Rahu–Ketu shift" video

Date: 2026-10-02. Conventions match the tool: sidereal Lahiri, mean node, Swiss Ephemeris (Moshier).
Markets: S&P 500 (^GSPC, from 1950), NIFTY (^NSEI, from 2007-09), Sensex (^BSESN, from 1997), via yfinance.

## Verdict

| Claim in the video | Check | Result |
|---|---|---|
| Rahu moves Aquarius → Capricorn and Ketu Leo → Cancer on **5 Dec 2026**, until **23 Jun 2028** | Ephemeris | ✅ Exact (mean node, Lahiri). KP ayanamsa: 7 Dec 2026 – 25 Jun 2028. True node: 25 Nov 2026 – 24 May 2028. |
| Rahu "meets Pluto" in Capricorn | Ephemeris | ⚠️ Not at ingress: Pluto is at Capricorn 9°, about 20° away. The conjunction is exact on **30 Nov 2027**, within 5° from 25 Aug 2027 to 30 Jan 2028. Pluto isn't part of the tool's 9-graha system. |
| Every ~18 years the axis returns | Ephemeris | ✅ 18.6-year nodal cycle. Rahu was in Capricorn in 1952–54, 1971–72, 1989–91 and 2008–09. |
| 2008: Lehman, subprime, global crisis | Dates | ✅ Lehman (15 Sep 2008) falls in the window (30 Apr 2008 – 17 Nov 2009). ⚠️ The subprime crisis began earlier, while Rahu was in **Aquarius**: US housing peaked in 2006, Bear Stearns funds failed in Jun 2007, Bear Stearns itself in Mar 2008. The market top (Jan 2008) was also in Aquarius. |
| 1989–90: Berlin Wall, Kuwait/Gulf War, Soviet collapse, Mandal | Dates | ✅ Berlin Wall (9 Nov 1989), Kuwait invasion (2 Aug 1990) and Desert Storm (Jan–Feb 1991) fall in the window (24 Sep 1989 – 13 Apr 1991). ❌ The Soviet Union dissolved in Dec 1991, after the window. ⚠️ The Mandal Commission was *formed* in 1979; its *implementation* (7 Aug 1990) is in the window. |
| 1971: Nixon shock, Indo-Pak war, Bangladesh | Dates | ✅ All in the window (17 Feb 1971 – 5 Sep 1972). |
| "The shift **always** brings a crisis" | Markets | ❌ **1 of 4** windows had a market crash (see below). The video skips the 1952–54 window. |
| Markets and economies collapse; banks collapse (2026–28) | Tool | ⚠️ Partial. The tool shows more bearish risk while Rahu is in Capricorn, concentrated in **Jun–Aug 2027**. It is driven by Saturn entering Aries, eclipses and Jupiter in a Ketu nakshatra, not by the Rahu ingress. The tool is **quietest** during the Rahu–Pluto conjunction. Banks read only mildly negative. |
| AI rises for ~1.5 years, then the bubble collapses | Tool | ❌ Not supported. The tool's Technology sector (Aquarius rashi) turns *more* bearish in the window (mean vedha −0.21 → −0.87). |
| World war 2029–32, food crisis, conscription | — | Not testable: future, non-market, and outside anything the tool models. |

## 1. Markets during past Rahu-in-Capricorn windows

| Window | S&P 500 return | S&P worst drawdown | NIFTY / Sensex |
|---|---|---|---|
| 13 Jul 1952 – 30 Jan 1954 | +4.2% | −14.8% | — |
| 17 Feb 1971 – 5 Sep 1972 | +13.3% | −13.9% | — |
| 24 Sep 1989 – 13 Apr 1991 | +10.5% | −19.9% | — |
| 30 Apr 2008 – 17 Nov 2009 | −19.9% | **−52.6%** | −2.0% / −1.4% return, about −52% drawdown |
| *Base rate: every 19-month window 1950–2024 (n=900)* | *median +14.2%; 21% negative* | *median −14.2%; 25% worse than −20%* | *Sensex 1998–2024: median drawdown −20.1%* |

Three of the four windows look like ordinary 19-month stretches. Only 2008–09 was a crash, and its trigger events and market top came during the preceding Aquarius window. The preceding Aquarius windows returned between +1.7% and +29.8% on the S&P 500.

## 2. What the SBC tool says about Dec 2026 – Jun 2028

**Crash analyzer** (`sbc/crash_analyzer.py`, every weekday):

| Period | Mean score | Days ≥ 40 | Notable |
|---|---|---|---|
| Rahu in Aquarius (19 May 2025 – 5 Dec 2026) | 13.5 | 6% | — |
| Rahu in Capricorn (6 Dec 2026 – 23 Jun 2028) | 16.7 | **12%** | one CRASH_RISK day, **23 Jul 2027** (score 68); CORRECTION_RISK cluster 28 Jun – Jul 2027 |
| Rahu–Pluto within 5° (25 Aug 2027 – 30 Jan 2028) | **3.8** | 4% | quietest stretch |

The main driver is `jupiter_ketu_nakshatra`: 81 days in the Capricorn window against 25 before.

**Crash calendar** (`market_alert` windows behind the NIFTY chart). Bearish windows per day: **0.40** (Aquarius) → **0.77** (Capricorn) → **0.97** (Rahu–Pluto stretch). The bearish windows in the Capricorn period:

- 11 Jan – 12 Apr 2027 · HIGH · Cluster E: Mars retrograde, eclipses, Mercury retrograde
- 3 Jun – 17 Aug 2027 · **EXTREME** · Cluster F: Saturn enters Aries + eclipse pressure
- 21 Jul – 3 Aug 2027 · HIGH · Malefics in Pushya (Sun)
- 30 Jul – 6 Aug 2027 · **CRITICAL** · Total solar eclipse conjunct Ketu (2 Aug 2027)
- 16 Aug 2027 – 21 Apr 2028 · HIGH · Malefics in Pushya (Ketu). This is the tool's closest equivalent to the video's "Ketu in Cancer".

The overall SBC vedha net moves *up*: −2.19 → −0.68 → +0.70 (more benefic).

> Caveat: the calendar's "severity" field takes the highest level of *any* window, including bullish ones (e.g. "Jupiter trine Saturn, multi-year bull run foundation" is VERY HIGH). Only the bearish-window counts above measure risk.

**Sector reads** (SBC vedha net; sampled 4×/month; mean and bearish share):

| Sector (tool's rashi) | Rahu in Aquarius | Rahu in Capricorn |
|---|---|---|
| Banks & Finance (Taurus) | +0.03 (20/50 bearish) | −0.22 (19/59) |
| Technology (Aquarius) | −0.21 (21/50) | **−0.87** (28/59) |
| IT & Media (Gemini) | −0.42 | −0.35 |
| Insurance (Scorpio) | −0.32 | −0.15 |

The tool maps banks to Taurus, not Capricorn. In the tool, Capricorn is Manufacturing, Cement & Infra, Coal & Railways.

## 3. How much weight the tool's view deserves

- Its crash analyzer scored **Lehman day (15 Sep 2008) NORMAL (15)**, and every month of the Sep–Nov 2008 crash scored a flat 15. Its strong 2008 signal (44–58) was **January**, the top, with Rahu still in Aquarius. Its own historical backtest catches 5 of 8 crash dates.
- The KP and intraday signals have no validated edge (`docs/INTRADAY_PATH_VALIDATION.md`).
- So the tool's 2027 risk cluster is a hypothesis to watch, not a forecast with a track record.

## Bottom line

The video's dates and its 18-year cycle are correct, and most of the historical events it cites do fall in Rahu-in-Capricorn windows. Its stronger claims don't hold up:

- **"Always a crisis":** the market record shows 1 crash in 4 windows. The 2008 crisis started and topped before the window.
- **Rahu meets Pluto:** this happens in late 2027, not at the December 2026 ingress.
- **The tool's risk peak** (Jun–Aug 2027) comes from other transits: Saturn into Aries, the 2 Aug 2027 eclipse on Ketu, Jupiter in a Ketu nakshatra. The tool reads the Rahu–Pluto conjunction itself as calm.

None of this is a basis for investment decisions.

---

# Part 2 · Q4 2026 transit predictions (Mars–Ketu in Leo)

Date: 2026-10-03. Same conventions as Part 1. The source said "October to December
(extending into early 2025)"; the dates only fit 2026, so "2025" is a typo.

## Verdict

| Claim | Check | Result |
|---|---|---|
| **Oct 17:** Sun enters debilitation (Libra); Sun–Venus–Mercury conjunction | Ephemeris | ✅ Sun enters Libra 17 Oct 19:52 IST. Mercury (Libra 24°) and Venus (Libra 10°, retrograde) are already there. |
| **Oct 31:** Jupiter leaves exaltation (Cancer) for Leo, joins Ketu | Ephemeris | ✅ Jupiter enters Leo 31 Oct 12:05. Jupiter–Ketu exact 12 Nov; same sign until 5 Dec. |
| **Nov 6:** Venus debilitated (Virgo) in Parivartan with Mercury | Ephemeris | ✅ Venus (retrograde) enters Virgo 6 Nov 01:07 with Mercury in Libra. The exchange holds until Venus returns to Libra on 22 Nov. |
| **Nov 12 – Dec 5:** Mars–Ketu conjunction in a fire sign | Ephemeris | ✅ Mars enters Leo 12 Nov 20:20; exact 15 Nov; same sign until 5 Dec. With Jupiter it's a **triple conjunction** in Leo. |
| **Dec 5:** nodes change sign | Ephemeris | ✅ 5 Dec 22:35 IST (see Part 1). |
| Nov 12 – Dec 5 is "high risk" for markets | Tool + history | ⚠️ Partial. The tool flags CORRECTION_RISK every trading day but never CRASH_RISK. History shows a mild bearish tilt for Indian indices only. |
| "Global economic havoc" | History | ❌ No effect on the S&P 500 across 47 episodes since 1950. |
| NIFTY: sell on rise at 23,500–24,000; targets 22,000, then 20,000 | Arithmetic + history | ⚠️ NIFTY is ~22,600 (30 Sep), so the "rise" first needs +4–6%. 22,000 (−2.7%) is a normal 3–4 week move; 20,000 (−11.6%) is about three times the median worst drop in a Mars–Ketu episode. |
| Positive momentum after Dec 5 | Tool | ❌ The tool keeps CORRECTION_RISK on 34 of 39 trading days to 31 Jan 2027, with a negative SBC net. The next bearish cluster is Jan–Apr 2027. |
| Gold: buy on dip; don't short Nov 12 – Dec 5; record highs | Tool + history | ✅ Aligned. The tool reads gold BULLISH on all 17 trading days (EXTREME "Retrograde Ketu in Leo"). Gold historically rose in these episodes (+2.9% median vs +0.7% base). |
| Silver range-bound, less volatile than gold | Tool + history | ⚠️ Mixed. The tool reads silver mostly NEUTRAL (11 of 17 days), but historically silver moved with gold (+3.0% median) and was *more* volatile (median worst drop −4.9% vs gold −2.6%). |

## 1. What the tool says, Oct 2026 – Jan 2027

| Period | Crash score (mean / max) | Conditions | SBC net | Bearish vs bullish windows per day |
|---|---|---|---|---|
| 1 Oct – 11 Nov | 31.7 / 50 | 12 elevated, 7 correction, 8 normal | −2.76 | 1.33 vs 2.74 |
| **12 Nov – 5 Dec** (Mars–Ketu) | **50.0 / 50** | **correction risk all 16 days** | −3.25 | 0.69 vs 2.69 |
| 6 Dec – 31 Jan | 32.8 / 50 | correction 34, normal 5 | −3.28 | 0.38 vs 2.46 |

Crash-analyzer signatures during Mars–Ketu: `mars_ketu_conjunction` and
`jupiter_ketu_nakshatra` on all 16 days. The only bearish calendar window in that span is
"Cluster C: Venus and Mercury retrograde overlap" (12–27 Nov, HIGH).

**Bullion vedha** (`sbc/bullion_vedha.py`):
- Gold BULLISH on 24 of 30 weekdays before 12 Nov, **17 of 17** during Mars–Ketu, and
  15 of 40 after (mostly NEUTRAL).
- Silver: BEARISH 19 of 30 before, NEUTRAL 11 of 17 during, NEUTRAL 32 of 40 after.

## 2. Mars–Ketu conjunctions in market history

Episodes: Mars and Ketu in the same sidereal sign within 10°, 1950 – Sep 2026. That gives
47 episodes with a median length of 22 days. The base rate is every 22-day window of the
same series.

| Market | Episodes | Median return | Base | Share negative | Base | Median worst drop | Base |
|---|---|---|---|---|---|---|---|
| S&P 500 (1950–) | 47 | +1.4% | +0.8% | 38% | 39% | −2.1% | −2.4% |
| Sensex (1997–) | 18 | +0.7% | +0.8% | 44% | 42% | −3.6% | −3.3% |
| NIFTY (2007–) | 11 | −1.4% | +0.7% | 55% | 43% | −4.0% | −3.0% |
| Gold GC=F (2000–) | 16 | +2.9% | +0.7% | 31% | 44% | −2.6% | −3.0% |
| Silver SI=F (2000–) | 16 | +3.0% | +0.6% | 38% | 46% | −4.9% | −5.1% |

Fire-sign episodes only (Aries/Leo/Sagittarius): S&P 500 +2.1% (12), Sensex −3.4% (5),
NIFTY −3.3% (3), gold +6.7% (5), silver +4.3% (5). These samples are too small to rely on.

## Bottom line

The astronomy is right on every date. Two of the forecast's calls line up with the tool and
lean the same way in history:
- a weaker stretch for Indian equities during Mars–Ketu, which looks like a correction,
  not a crash;
- strength in gold.

Three don't hold up:
- the global-havoc framing (the S&P 500 shows nothing);
- the 20,000 NIFTY target, far outside typical episode moves;
- recovery from 5 Dec (the tool sees risk persisting into early 2027).

The tool's signals themselves have no validated edge (Part 1, §3), so agreement with it is
agreement between two astrological readings, not independent confirmation. None of this is
a basis for investment decisions.
