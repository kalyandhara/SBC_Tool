# Mars-Rahu/Ketu conjunction tracker + event study

Range 2000-01-01 .. 2030-12-31; episodes = Mars-node separation < 2.5 deg (mean node, Lahiri); event date = minimum-separation day.

## Tracker: 37 episodes (5 upcoming)

| date | node | orb | status |
|------|------|-----|--------|
| 2000-07-23 | Rahu | 0.15 | past |
| 2001-09-13 | Ketu | 0.04 | past |
| 2002-05-12 | Rahu | 0.35 | past |
| 2003-01-26 | Ketu | 0.02 | past |
| 2004-02-26 | Rahu | 0.32 | past |
| 2004-11-13 | Ketu | 0.27 | past |
| 2005-07-09 | Rahu | 0.18 | past |
| 2006-09-02 | Ketu | 0.05 | past |
| 2007-04-24 | Rahu | 0.16 | past |
| 2008-06-17 | Ketu | 0.08 | past |
| 2009-02-16 | Rahu | 0.27 | past |
| 2009-10-09 | Ketu | 0.03 | past |
| 2010-12-12 | Rahu | 0.33 | past |
| 2011-07-22 | Ketu | 0.00 | past |
| 2012-10-05 | Rahu | 0.23 | past |
| 2013-05-13 | Ketu | 0.06 | past |
| 2014-07-14 | Rahu | 0.00 | past |
| 2015-03-07 | Ketu | 0.03 | past |
| 2015-11-10 | Rahu | 0.11 | past |
| 2016-12-28 | Ketu | 0.06 | past |
| 2017-08-26 | Rahu | 0.29 | past |
| 2018-06-14 | Ketu | 0.00 | past |
| 2018-09-22 | Ketu | 0.15 | past |
| 2019-06-14 | Rahu | 0.34 | past |
| 2020-02-24 | Ketu | 0.20 | past |
| 2021-03-28 | Rahu | 0.25 | past |
| 2021-12-14 | Ketu | 0.07 | past |
| 2022-08-01 | Rahu | 0.24 | past |
| 2023-10-05 | Ketu | 0.36 | past |
| 2024-05-18 | Rahu | 0.27 | past |
| 2025-07-23 | Ketu | 0.05 | past |
| 2026-03-13 | Rahu | 0.21 | past |
| 2026-11-15 | Ketu | 0.01 | upcoming |
| 2028-01-08 | Rahu | 0.25 | upcoming |
| 2028-08-22 | Ketu | 0.16 | upcoming |
| 2029-11-01 | Rahu | 0.29 | upcoming |
| 2030-06-12 | Ketu | 0.33 | upcoming |

## Event study (entry = first open on/after event date; returns in %)


### crude (n=32 events)

| window | mean | median | win % | random mean | p |
|--------|------|--------|-------|-------------|---|
| +5d | -0.32 | +0.19 | 50 | +0.22 | 0.578 |
| +10d | -1.17 | -0.73 | 47 | +0.43 | 0.261 |
| +21d | -2.35 | -1.19 | 50 | +0.95 | 0.121 |

Worst/best 21d excursion: MAE -63.00% / MFE +31.90%

### gold (n=32 events)

| window | mean | median | win % | random mean | p |
|--------|------|--------|-------|-------------|---|
| +5d | -0.56 | -0.01 | 50 | +0.24 | 0.089 |
| +10d | +0.15 | +0.68 | 56 | +0.48 | 0.599 |
| +21d | +0.68 | -0.07 | 47 | +0.99 | 0.722 |

Worst/best 21d excursion: MAE -19.35% / MFE +19.29%

### silver (n=32 events)

| window | mean | median | win % | random mean | p |
|--------|------|--------|-------|-------------|---|
| +5d | -1.04 | +0.10 | 50 | +0.27 | 0.121 |
| +10d | -0.64 | -0.04 | 50 | +0.57 | 0.292 |
| +21d | -1.43 | -1.07 | 41 | +1.20 | 0.107 |

Worst/best 21d excursion: MAE -37.24% / MFE +18.68%

### nifty (n=32 events)

| window | mean | median | win % | random mean | p |
|--------|------|--------|-------|-------------|---|
| +5d | +1.85 | +1.35 | 59 | +0.16 | 0.002 |
| +10d | +1.57 | +0.14 | 50 | +0.36 | 0.098 |
| +21d | +4.61 | +0.88 | 53 | +0.80 | 0.001 |

Worst/best 21d excursion: MAE -37.47% / MFE +26.33%

### INDIAVIX (n=32 events)

| window | mean | median | win % | random mean | p |
|--------|------|--------|-------|-------------|---|
| +5d | +8.76 | +5.92 | 78 | +0.86 | 0.004 |
| +10d | +16.55 | +9.90 | 69 | +1.35 | 0.000 |
| +21d | +23.51 | +7.64 | 66 | +2.61 | 0.006 |

Worst/best 21d excursion: MAE -55.15% / MFE +532.41%

## Recent events detail (gold)

| event | node | orb | entry | +5d | +10d | +21d |
|-------|------|-----|-------|-----|------|------|
| 2020-02-24 | Ketu | 0.20 | 2020-02-24 | -3.90 | +1.06 | +0.19 |
| 2021-03-28 | Rahu | 0.25 | 2021-03-29 | +0.66 | +0.93 | +2.45 |
| 2021-12-14 | Ketu | 0.07 | 2021-12-14 | +0.06 | +1.02 | +1.89 |
| 2022-08-01 | Rahu | 0.24 | 2022-08-01 | +1.27 | +0.88 | -2.59 |
| 2023-10-05 | Ketu | 0.36 | 2023-10-05 | +2.47 | +7.78 | +8.79 |
| 2024-05-18 | Rahu | 0.27 | 2024-05-20 | -2.71 | -3.09 | -2.20 |
| 2025-07-23 | Ketu | 0.05 | 2025-07-23 | -4.31 | -0.32 | -1.82 |
| 2026-03-13 | Rahu | 0.21 | 2026-03-13 | -10.01 | -11.63 | -4.60 |

Video mapping: claimed Mars-Ketu Jun 12-13 2025 (attack Jun 22), Mars-Rahu Feb 23-28 2026 (attack), Mars-Ketu Nov 12 2026 (attack after). Ephemeris: exact conjunctions 2025-07-23 (Ketu), 2026-03-13 (Rahu), 2026-11-15 (Ketu) - see tracker above.

Caveat: means are tail-sensitive - the 2020-02-24 episode is the COVID crash onset (crude MAE -63%, VIX MFE +532%) and 2026-03-13 saw gold -10%. Medians and p-values are the honest read; treat this as an event-study prompt, not a validated signal.
