# Video gap analysis — astrologer's week-ahead video vs SBC_Tool

Video (English summary provided), synced to the original transcript
timestamps. Ephemeris checks below use the repo pipeline: Swiss Ephemeris
Moshier, sidereal Lahiri, mean nodes, IST.

## 1. Claims synced to video time

| # | Video time | Claim | Verified with repo ephemeris? | Tool coverage | Status |
|---|------------|-------|-------------------------------|---------------|--------|
| 1 | 2:27 | Mercury retro 24 Oct → market can reverse; Nov-Feb bad | **Yes** — Mercury R 2026-10-24 13:29 IST (Lib 26.75°) | `sbc/stations.py` computes stations; `crash_windows` has mercury_retro combo (w=0.24) | Partial — no Mercury-retro market validation study |
| 2 | 2:46 | Nov 3 US midterms; Iran attack "evident"; attack after Nov 12 | Mars-Ketu exact **Nov 15** (orb 0.01°), not Nov 12 | No geopolitical/event module; Mars-node conjunctions not tracked | **Missing** |
| 3 | 3:11 | Mars-Ketu Jun 12-13 2025 → Jun 22 attack; Mars-Rahu Feb 23-28 2026 → attack | **No** — exact: Mars-Ketu **Jul 23 2025**, Mars-Rahu **Mar 13 2026** (mean node) | Same as #2 | **Missing + video dates wrong** |
| 4 | 3:42 | All 6 crash instances in same solar years (Oct-Nov clustering) | n/a (historical) | `crash_windows` 26-crash-day study + sun_lib seasonal combo (w=0.39, "October effect") | Covered |
| 5 | 4:01 | Goal-based advice (2027 targets at risk, 2040 fine) | n/a | Advisory, out of tool scope | N/A |
| 6 | 4:50 | COMEX gold ~4,220 Fri; India gold fell on rupee appreciation | n/a (market fact) | GC=F ✓; **no USDINR series** → MCX/rupee-adjusted gold not computable | **Missing (USDINR)** |
| 7 | 5:22 | Silver weak astrologically; $50 possible Nov 6-22; bullions fall with equities | n/a | silver_ohlc + bullion modules; no silver-specific astro study; no cross-asset crash-propagation module | Partial |
| 8 | 6:04-11:24 | Sun+Venus+Mercury in Libra: 12 instances, 9 positive, max +6%, min -2.36% | **Yes** — 13 windows 2000-2035 found; 12 completed: 9/12 positive, mean +1.68%, max +6.74% (2022), min -1.36% | `scripts/study_gold_libra_triple.py` + `reports/gold_libra_triple_backtest.md` (this study) | **Covered (built today)** |
| 9 | 9:30 | Yog lasts until Nov 6 when "Venus goes retrograde" | Break date **Yes** (Venus retro exits Libra Nov 6); mechanism **No** — Venus R since **Oct 3** (Lib 14.26°), turns **direct Nov 14** | Same study + `stations.py` | Covered (date); video mechanism wrong |
| 10 | 10:23 | Gold range from ~4,200: max +6% → 4,300-4,400; min -2.5% → ~4,100 | n/a | Our backtest: max window gain +6.74% (similar), but deepest **intra-window adverse -4.45%** (2011) — his -2.36% is close-based only | Covered (tool shows deeper risk) |
| 11 | 11:35 | Fed chair speech; FOMC Oct 27-28; market 83% no-hike | n/a | `econ_calendar.py` has US releases but **no FOMC/Fed calendar** | **Missing (FOMC)** |
| 12 | 12:00 | Friday Hormuz attack news → crude up, gold dipped, closed green | n/a | **No crude price series anywhere**; sentiment_data is news-only | **Missing (crude)** |
| 13 | 12:38 | Jio IPO Oct 21-23, listing 28; anchor lock-in outflows; FII selling | n/a | FII/DII flows ✓ (`market_store`); IPO calendar absent | Partial |
| 14 | 14:23 | NIFTY up-swing possible before Oct 24; exit on strength; after 24 negative | n/a | `forecast.py`/daily ledger exist; no "Mercury-R regime" rule validated | Partial |
| 15 | 14:56 | Brent ~$105; tariff pause; Iran FM deadline; Russia oil-infra attack | n/a | No crude series; no geopolitical feed | **Missing (crude)** |
| 16 | 16:33 | Moon in Capricorn → gold up; Monday Cap, then Aqu | Moon→Aqu **Oct 21 11:30 IST** (video said ~7:00 — ~4.5 h off, looks like UT/IST error in video software) | `scripts/adhoc/backtest_moon_rasi_multi.py` (Moon-rashi trend rulebook, adhoc only) | Partial — not productized/validated |
| 17 | 17:11 | Six October crashes: 1907, 1929, 1987, 1989, 1997, 2000 | n/a | `crash_windows` fixed 26-crash-day study 1929-2025 | Covered |
| 18 | 19:46 | Cycle: NIFTY -40 to -60% from top this cycle-year; DJ 1929/73/79/87; bad till March | n/a | `bradley.py`, crash study; no bear-cycle depth table (depth by year-from-top) | Partial |
| 19 | 20:56 | Oct 19 9:00 AM Mumbai chart: 6 planets in kendra, Gaja-Kesari + Lakshmi yog; open positive then throw down | n/a | `crash_windows` has Mumbai-open lagna machinery (venus11) but **no Gaja-Kesari/Lakshmi/kendra yoga scanner** | **Missing (yogas)** |
| 20 | 22:14 | **Vyatipat yog Oct 21 ~6:00 PM**; next 24 h critical; bullions fall | **No** — Vyatipat actual: **begins 2026-10-27 11:29 IST, ends 2026-10-28 07:29 IST** (6 days later) | `market_calendar.py` computes nitya yogas (incl. Vyatipat, Indra, Ravi); `panchang_signals.py` has **no yoga trading rules** | **Missing (rule) + video date wrong** |
| 21 | 23:16 | Oct 20 Diwali holiday; evening chart; Moon 22° Shravana; gold sign active | n/a | `market_holidays` ✓; Moon-nakshatra studies exist for NIFTY | Partial |
| 22 | 25:15 | Oct 21: Moon over Rahu in Mars nakshatra; rashi change ~7:00 AM stirs COMEX; defence positive | Moon→Aqu Oct 21 **11:30 IST** (see #16) | No Moon-over-Rahu asset study; `sector_keywords` has defence | **Missing (Moon-Rahu rule)** |
| 23 | 29:03 | **Moon in Rahu nakshatra (Ardra/Swati/Shatabhisha) → big CRUDE moves; Moon in Mercury nakshatra → NIFTY + BankNIFTY** (his own backtest) | n/a | Moon-nakshatra studies exist for NIFTY only; **no crude series; no BankNIFTY series** | **Missing (biggest gap)** |
| 24 | 29:57 | Indra yog Oct 9 gold low broke | n/a | `market_calendar` flags Indra yoga; no market-impact rule | Partial |
| 25 | 31:06 | Oct 23: Moon→Pisces 3:03 PM; 3:00 PM reversal window; 30/50 positive base rate | Moon→Pisces **Oct 23 17:30 IST** (video 3:03 PM — same ~4.5 h offset) | `astro_cycles.py` makes intraday reversal bars from Moon nakshatra ingresses + horas | Partial — close to his method, not rashi-ingress based |
| 26 | 33:01 | US data times: Oct 20 permits 6PM/home sales 7:30PM; Oct 22 jobless 6PM; Oct 23 consumer sentiment | n/a | `econ_calendar.py` (US releases) | Covered |
| 27 | 34:15 | **Oct 31 Jupiter enters Ketu's nakshatra (Magha) with Ketu → decline begins after** | **Yes — exact: 2026-10-31 17:30 IST, Jupiter Leo 0.03° (Magha)** | `transits.nakshatra_ingresses` computes it; no Guru-in-Ketu-nakshatra market study; guru_chandal combo only in crash tool (w=0.14) | Partial |
| 28 | 35:43 | NIFTY 22,000 retest; opportunity coming | n/a | Technical level — out of astro scope | N/A |
| 29 | 38:26 | Rahu-Ketu change Dec 5 (axis 4-10); falls historically in Guru-Ketu nakshatra; node transits form bottoms (Apr 4) | **Near-yes** — node sign ingress **2026-12-06 05:30 IST** (Rahu→Capricorn / Ketu→Cancer; video said Dec 5) | Node ingresses computable; no node-change event study | Partial |
| 30 | 40:05 | Nov 4 or Nov 14 falls; crude 120-130 on Iran strike; inflation 11%; Fed must hike; 40T debt | n/a | `crash_windows` shows no elevated days Nov 2026; no scenario/crude module | Partial/missing |

## 2. Date scoreboard (video vs repo ephemeris)

| Event | Video | Repo ephemeris | Verdict |
|-------|-------|----------------|---------|
| Mercury retrograde | 24 Oct | 2026-10-24 13:29 IST | correct |
| Triple yog breaks | 6 Nov | 2026-11-06 | correct (Venus retro exits Libra) |
| "Venus goes retrograde" | 6 Nov | R since **Oct 3**, direct **Nov 14** | wrong mechanism |
| Jupiter → Ketu nakshatra (Magha) | 31 Oct | 2026-10-31 17:30 IST | correct |
| Rahu-Ketu sign change | 5 Dec | 2026-12-06 05:30 IST | off ~1 day |
| Vyatipat yog | 21 Oct 6 PM | **27 Oct 11:29 IST** – 28 Oct 07:29 IST | **wrong by 6 days** |
| Moon → Aquarius | 21 Oct ~7 AM | 2026-10-21 11:30 IST | off ~4.5 h (UT/IST slip) |
| Moon → Pisces | 23 Oct 3:03 PM | 2026-10-23 17:30 IST | off ~4.5 h (UT/IST slip) |
| Mars-Ketu (2025) | 12-13 Jun | **23 Jul 2025** | wrong |
| Mars-Rahu (2026) | 23-28 Feb | **13 Mar 2026** | wrong |
| Mars-Ketu (upcoming) | 12 Nov (attack 13-15) | exact **15 Nov 2026** | ~3 days off |

Pattern: his *in-signal* facts (Libra triple, Magha ingress, Mercury R) are
right, but *secondary* timing claims (Vyatipat, Mars-node dates, Moon
ingress times) drift by hours to weeks — exactly the class of dates our
tool computes exactly.

## 3. Gaps in our tool realization (ranked)

1. **Crude oil price series is absent entirely** (no CL=F/BZ=F in
   `market_data._ASSETS`, no CSV in `data/`). His most testable unique
   rule — Moon in Rahu nakshatra (Ardra/Swati/Shatabhisha) → big crude
   moves — cannot be validated. Add CL=F to `_ASSETS` + a
   `study_moon_nakshatra.py`-style rule test for crude.
2. **Mars–Rahu/Ketu conjunction tracker + event study** — nothing in `sbc/`
   detects Mars-node conjunctions. Add a `stations.py`-style scan plus a
   forward-returns study on crude/VIX/gold/NIFTY around exact conjunction
   dates (2025-07-23, 2026-03-13, 2026-11-15 are the recent three).
3. **Nitya-yoga trading rules**: `market_calendar.py` computes Vyatipat/
   Indra/Ravi yogas but `panchang_signals.py` (the rule-book) never uses
   them. Add a "Vyatipat ±24h" rule test — and note the video's own date
   was 6 days off; our tool would not have been.
4. **Kendra-yoga scanner for the 9:15 Mumbai open chart** (Gaja-Kesari,
   Lakshmi, 6-planets-in-kendra): `crash_windows.day_state` already
   computes the Mumbai lagna; extend it rather than build new.
5. **Mercury retrograde validation study**: analog of
   `venus_station_validation.py` — stations are computed, the edge is not
   measured (his Oct 24 thesis).
6. **USDINR series**: India gold vs COMEX divergence (his rupee point at
   4:50) is not computable.
7. **BankNIFTY + US VIX series** (`^NSEBANK`, `^VIX`): needed for the
   Moon-in-Mercury-nakshatra rule (NIFTY *and* BankNIFTY) and for a real
   stress gauge.
8. **FOMC/Fed-meeting calendar** in `econ_calendar.py` (his Oct 27-28
   meeting; only data releases are covered today).
9. **Jupiter-in-Ketu-nakshatra / Guru-Chandal bullion study**: combo exists
   in the crash tool at weight 0.14; his Oct 31 "decline begins after"
   thesis is untested for gold/NIFTY forward returns.
10. **Node sign-change event study**: ingress dates are computable (next:
    Dec 6); no historical bottom-formation/return study around them.
11. **Cross-asset crash propagation** ("when equities crash, everything
    falls"): no multi-asset drawdown/correlation module; would also grade
    his silver thesis (gap #7 in table).
12. **Productize Moon-rashi rules**: `backtest_moon_rasi_multi.py` is an
    adhoc script; Moon-in-Capricorn→gold should either graduate into
    `sbc/` with a validation verdict or be retired.

## 4. What the tool already says about the coming days

- 2026-11-06 (triple-yog break): crash tool flags **HIGH 2.37** (top ~3%).
- 2026-10-24 (Mercury R): crash score 0.89, normal.
- Vyatipat 2026-10-27 11:29 → 10-28 07:29: crash score 1.13, normal level.
- Mars-Ketu exact 2026-11-15; Mercury direct 2026-11-13.
- 2027-10-18..21 is the next full conjunction window (tool: peak 1.48,
  clean).
