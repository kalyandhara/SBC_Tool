# Gold: Sun+Mercury+Venus in sidereal Libra - backtest

Generated 2026-10-18. Data: COMEX GC=F (2000-08-30 .. 2026-10-16).
Convention: entry = first session open on/after window start, exit = last session close on/before window end.

## 1. Ephemeris windows (Lahiri sidereal)

| # | start | end | days | status |
|---|-------|-----|------|--------|
| 1 | 2001-11-03 | 2001-11-16 | 12.5 | completed |
| 2 | 2002-10-28 | 2002-11-15 | 18.3 | completed |
| 3 | 2003-10-21 | 2003-10-29 | 8.1 | completed |
| 4 | 2006-10-19 | 2006-10-24 | 4.9 | completed |
| 5 | 2006-11-01 | 2006-11-12 | 10.8 | completed |
| 6 | 2009-11-03 | 2009-11-12 | 9.0 | completed |
| 7 | 2010-10-17 | 2010-11-05 | 18.5 | completed |
| 8 | 2011-10-17 | 2011-10-28 | 10.8 | completed |
| 9 | 2014-11-04 | 2014-11-12 | 7.4 | completed |
| 10 | 2018-10-17 | 2018-10-26 | 9.1 | completed |
| 11 | 2019-10-18 | 2019-10-23 | 5.9 | completed |
| 12 | 2022-10-26 | 2022-11-11 | 16.3 | completed |
| 13 | 2026-10-17 | 2026-11-06 | 19.2 | ongoing |
| 14 | 2027-10-18 | 2027-10-21 | 3.3 | upcoming |
| 15 | 2030-10-18 | 2030-11-03 | 16.0 | upcoming |
| 16 | 2033-11-02 | 2033-11-16 | 14.5 | upcoming |

## 2. Image table verification

| year | image window | computed open | image open | computed ret % | image ret % | diff pp |
|------|--------------|---------------|------------|----------------|-------------|---------|
| 2001 | 11-04..11-16 | 278.50/274.70 | 280.00/274.90 | -1.36 | -1.82 | +0.46 **MISMATCH** |
| 2002 | 10-29..11-15 | 317.70/320.70 | 315.70/320.90 | +0.94 | +1.65 | -0.71 **MISMATCH** |
| 2003 | 10-21..10-29 | 378.70/386.80 | 374.30/387.00 | +2.14 | +3.39 | -1.25 **MISMATCH** |
| 2006 | 10-20..10-24 | 597.50/584.40 | 601.80/587.60 | -2.19 | -2.36 | +0.17 |
| 2006 | 11-02..11-12 | 625.40/628.40 | 620.40/630.10 | +0.48 | +1.56 | -1.08 **MISMATCH** |
| 2009 | 11-04..11-12 | 1086.70/1106.00 | 1085.60/1106.60 | +1.78 | +1.93 | -0.15 |
| 2010 | 10-18..11-05 | 1358.00/1397.30 | 1371.00/1397.70 | +2.89 | +1.95 | +0.94 **MISMATCH** |
| 2011 | 10-18..10-28 | 1666.00/1746.20 | 1672.50/1747.20 | +4.81 | +4.47 | +0.34 **MISMATCH** |
| 2014 | 11-05..11-12 | 1168.10/1158.90 | 1168.40/1159.10 | -0.79 | -0.80 | +0.01 |
| 2018 | 10-18..10-26 | 1226.50/1232.50 | 1225.50/1235.80 | +0.49 | +0.84 | -0.35 **MISMATCH** |
| 2019 | 10-18..10-23 | 1487.30/1489.90 | 1495.60/1495.70 | +0.17 | +0.01 | +0.16 |
| 2022 | 10-27..11-11 | 1668.80/1769.40 | 1668.80/1769.40 | +6.03 | +6.03 | -0.00 |

5/12 rows reproduce within 0.20pp using GC=F.

## 3. Curated image sample vs complete ephemeris sample

```
IMAGE rows (curated)   : n=12, mean=+1.28%, median=+0.72%, std=2.42, win=75%, worst=-2.19%, best=+6.03%, t=+1.83, deepest intra-window adverse=-3.51%
ALL windows (complete) : n=12, mean=+1.68%, median=+2.07%, std=2.28, win=75%, worst=-1.36%, best=+6.74%, t=+2.55, deepest intra-window adverse=-4.45%
```

## 4. Random-window bootstrap (10,000 draws, same window lengths, 2000-2026 span)

- observed mean (all windows): +1.68%
- random-window mean: +0.37% (90% range -1.15% .. +1.92%)
- one-sided p(random mean >= observed): 0.083; two-sided 0.166

## 5. Crash-regime coverage

| regime | regime window | overlapping conjunction windows | covered? |
|--------|---------------|--------------------------------|----------|
| Dot-com bust | 2000-09-01..2002-10-09 | 2001-11-03..2001-11-16 | yes |
| 2008 GFC | 2007-10-09..2009-03-09 | none | **NO** |
| 2011 gold blow-off top | 2011-09-01..2011-12-31 | 2011-10-17..2011-10-28 | yes |
| 2013 gold crash (taper) | 2013-04-01..2013-12-31 | none | **NO** |
| 2020 COVID crash | 2020-02-19..2020-03-23 | none | **NO** |
| 2022 rate shock | 2022-01-01..2022-11-10 | 2022-10-26..2022-11-11 | yes |
| 2025 Oct gold correction | 2025-10-01..2025-11-30 | none | **NO** |
| 2026 Oct pullback | 2026-09-15..2026-11-10 | 2026-10-17..2026-11-06 | yes |

## 6. Per-window detail (all completed windows)

| start | end | entry | exit | move % | dd from 52w high at entry % | adverse (low vs entry) % | max close dd % | fwd 5d % | fwd 21d % |
|-------|-----|-------|------|--------|-------------------------|-----------------------|----------------|----------|-----------|
| 2001-11-03 | 2001-11-16 | 278.50 | 274.70 | -1.36 | -5.0 | -1.36 | -2.24 | -0.55 | +0.29 |
| 2002-10-28 | 2002-11-15 | 314.00 | 320.70 | +2.13 | -4.2 | +0.00 | -2.03 | +0.00 | +6.67 |
| 2003-10-21 | 2003-10-29 | 378.70 | 386.80 | +2.14 | -2.3 | -0.29 | -1.47 | -1.09 | +4.11 |
| 2006-10-19 | 2006-10-24 | 588.90 | 584.40 | -0.76 | -18.2 | -2.11 | -3.22 | +3.37 | +7.58 |
| 2006-11-01 | 2006-11-12 | 612.50 | 628.40 | +2.60 | -14.9 | +0.00 | -1.67 | -1.10 | -0.08 |
| 2009-11-03 | 2009-11-12 | 1084.30 | 1106.00 | +2.00 | +0.0 | -2.54 | -0.72 | +3.20 | +1.56 |
| 2010-10-17 | 2010-11-05 | 1358.00 | 1397.30 | +2.89 | -1.4 | -2.98 | -3.57 | -2.28 | +0.79 |
| 2011-10-17 | 2011-10-28 | 1683.60 | 1746.20 | +3.72 | -10.9 | -4.45 | -3.80 | +0.52 | -1.88 |
| 2014-11-04 | 2014-11-12 | 1166.90 | 1158.90 | -0.69 | -15.4 | -2.91 | -2.15 | +2.99 | +5.44 |
| 2018-10-17 | 2018-10-26 | 1225.90 | 1232.50 | +0.54 | -10.0 | -0.51 | -0.45 | -0.13 | -1.73 |
| 2019-10-18 | 2019-10-23 | 1487.30 | 1489.90 | +0.17 | -4.1 | -0.39 | -0.44 | +0.22 | -1.80 |
| 2022-10-26 | 2022-11-11 | 1657.70 | 1769.40 | +6.74 | -18.9 | -2.38 | -2.29 | -0.85 | +3.17 |

Mean forward returns after window exit: 5d +0.36%, 21d +2.01% (n=12).

### Windows entered with gold >=10% below its 52-session high (crash/bear entries)

| start | dd at entry % | move % | fwd 21d % |
|-------|---------------|--------|-----------|
| 2006-10-19 | -18.2 | -0.76 | +7.58 |
| 2006-11-01 | -14.9 | +2.60 | -0.08 |
| 2011-10-17 | -10.9 | +3.72 | -1.88 |
| 2014-11-04 | -15.4 | -0.69 | +5.44 |
| 2018-10-17 | -10.0 | +0.54 | -1.73 |
| 2022-10-26 | -18.9 | +6.74 | +3.17 |

Deep-drawdown entries: n=6, mean window move=+2.02%, win=67%, mean fwd 21d=+2.08%

## 7. Ongoing 2026 window and current market context

- window 2026-10-17..2026-11-06: first tradable session has not occurred yet
- window 2027-10-18..2027-10-21: first tradable session has not occurred yet
- window 2030-10-18..2030-11-03: first tradable session has not occurred yet
- window 2033-11-02..2033-11-16: first tradable session has not occurred yet
- last close 4181.10 (2026-10-16); 52-session-high 5318.40 on 2026-01-29; drawdown from that high -21.38%
- the 2026 window's entry drawdown is the deepest of any window in the sample (see section 6)

## 8. Current and upcoming windows - what sbc.crash_windows says

Day scores come from the repo's fixed 26-crash-day study (in-sample, not a validated signal). Thresholds: elevated 1.85 (top ~10% of days), high 2.36 (top ~3%).

| window | peak score | level | flagged days | slow backdrop active |
|--------|-----------|-------|--------------|-----------------|
| 2026-10-17..2026-11-06 | 2.37 (2026-11-06) | HIGH | 2026-11-06 | - |
| 2027-10-18..2027-10-21 | 1.48 (2027-10-20) | normal | - | - |
| 2030-10-18..2030-11-03 | 1.68 (2030-10-23) | normal | - | Jupiter–Saturn hard aspect |
| 2033-11-02..2033-11-16 | 0.91 (2033-11-14) | normal | - | - |

- **HIGH day 2026-11-06 (score 2.37) in window 2026-10-17..2026-11-06:** Jupiter in a fire sign (Jupiter Leo 0°); Venus in 11th house (Mumbai open) (Lagna Scorpio at 09:15 IST, Venus Vir 29° in 11th); Sun debilitated in Libra (Sun Lib 19°); Sun–Saturn in 6/8 (shadashtak) (Sun Lib 19° / Saturn Pis 14°)

Note: the tool's own header warns these combos are in-sample and none passed a multiple-testing correction - a research prompt, not a signal.

- last sessions: 2026-10-05 4156.8, 2026-10-06 4187.1, 2026-10-07 4140.7, 2026-10-08 4157.0, 2026-10-09 4216.3, 2026-10-12 4190.6, 2026-10-13 4177.3, 2026-10-14 4107.9, 2026-10-15 4170.1, 2026-10-16 4181.1
