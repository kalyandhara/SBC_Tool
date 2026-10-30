# AstroZ dated-calls ledger

Every falsifiable dated call made in the analysed AstroZ videos, recorded
here the day it was analysed, with its grading rule **frozen before the
outcome exists**. Graded from repo data at the first weekly review after
the window closes; a miss is recorded as a miss — no reinterpreting.
Calls without a date, a magnitude or an invalidation rule are recorded as
UNTESTABLE and count against the video's falsifiability, not in its
favour.

Grading data: repo CSV caches / market.db (IST). Reproduce any grade with
the scripts named in the source video's gap-analysis report.

## Open near-term calls

| # | video | call | window | frozen grading rule | outcome | grade |
|---|-------|------|--------|---------------------|---------|-------|
| 1 | 2026-10-25 Mercury | "positive opening for NIFTY, Gold and Silver tomorrow morning" (Moon in Ashwini) | 2026-10-26 session | each asset's open > its prior close (NIFTY prior close 22,600; GC=F, SI=F prior closes 2026-10-23) | pending | — |
| 2 | 2026-10-25 Mercury | "around 2:30 PM the market could flip" | 2026-10-26 ~14:30 IST | UNTESTABLE — repo holds no NIFTY intraday series; a daily proxy cannot isolate an afternoon flip | untestable | — |
| 3 | 2026-10-25 Mercury | "significant volatility in the afternoon" (Moon in Bharani) | 2026-10-27 session | NIFTY (high-low)/close > 1.5x the trailing 20-session median range = hit; 1.0-1.5x = partial; else miss. India VIX day change recorded alongside | pending | — |
| 4 | 2026-10-25 Mercury | "the market will likely be under pressure" (Fed outcome day) | 2026-10-28 session | NIFTY close-to-close negative = hit; positive = miss | pending | — |
| 5 | 2026-10-25 Mercury | "might open strong but could be pulled down again" | 2026-10-29 session | open > prior close AND close < open = hit; else miss | pending | — |
| 6 | 2026-10-25 Mercury | "Mars joins Ketu on the 12th... an attack is highly possible" | 2026-11-12 .. 2026-11-17 | the military event itself is outside repo scope. Price proxy: Brent 3-session move from 2026-11-12 > +3% or gold > +2% = "risk-off consistent"; else "no market footprint". Exact Mars-Ketu crossing: 2026-11-15 (repo ephemeris) | pending | — |
| 7 | 2026-10-25 Mercury | "I remain a bear through November, December, January, February" | 2026-11-01 .. 2027-02-28 | NIFTY total return over the window negative = hit; positive = miss | pending | — |

## Open long-dated calls

| # | video | call | window | frozen grading rule | outcome | grade |
|---|-------|------|--------|---------------------|---------|-------|
| 8 | 2026-10-24 gold | Saturn-in-Taurus bullish phase (dates confirmed exact by the repo ephemeris) | 2030-04-17 .. 2032-05-31 | gold (GC=F) total return over the window positive = hit; negative = miss | pending (2032-06) | — |
| 9 | 2026-10-24 gold | "caution" while Saturn transits debilitated Aries | 2027-06-03 .. 2027-10-20 and 2028-02-23 .. 2030-04-17 | gold drawdown >= 10% within each window = hit for that window | pending (2030-05) | — |
| 10 | 2026-10-24 gold | "gold goes to 6 lakhs per 10 g" | none given | NO FALSIFICATION RULE — no date, no path, no basis (retail vs MCX unreconciled; at repo FX/basis the target implies ~$13k-19.6k/oz). Recorded as unfalsifiable as stated | untestable | — |
| 11 | 2026-10-22 crash | Ju-Sat 6/8 (Shashtashtaka) bearish window | 2026-10-31 .. 2027-01-24 | NIFTY return over the window negative = hit; positive = miss (window confirmed by `sbc/transits.sign_distance_periods`) | pending (2027-02) | — |

## Graded (none yet — first grading due at the 2026-10-31 weekly review,
## which closes calls 1-5)

## Standing context (not graded)

- The 2026-10-25 video's "falling since September 2024" framing is false
  as history (NIFTY made a new ATH 26,373 on 2026-01-05; the -14% is a
  2026 correction) — recorded so a "hit" on call 7 cannot be read as
  vindicating the story that produced it.
- Historical base rates for the mechanisms invoked: Mercury retrograde
  trend-reversal — no edge (`reports/retrograde_reversal_study_2026-10-25.md`);
  Mercury retrograde windows — no edge (`reports/mercury_retrograde_study_2026-10-18.md`);
  Moon nakshatra day-calls — no edge (`reports/moon_mercury_nakshatra_nifty_2026-10-18.md`);
  Mars-node alignments and crude — not significant
  (`reports/mars_node_conjunction_study_2026-10-18.md`); Rahu ingress —
  the one nominal edge, opposite direction to the videos
  (`+7.0%` mean 21-session NIFTY move after Rahu sign changes, p=0.000).
