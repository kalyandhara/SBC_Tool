# Mercury retrograde - market study

Range 2000-01-01 .. 2030-12-31: 98 retrograde episodes (14 upcoming).

Upcoming stations (retrograde -> direct, IST): 2026-10-24 -> 2026-11-13; 2027-02-09 -> 2027-03-03; 2027-06-11 -> 2027-07-05; 2027-10-07 -> 2027-10-28; 2028-01-24 -> 2028-02-14; 2028-05-21 -> 2028-06-14; 2028-09-19 -> 2028-10-11; 2029-01-07 -> 2029-01-28; 2029-05-02 -> 2029-05-26; 2029-09-02 -> 2029-09-25; 2029-12-22 -> 2030-01-11; 2030-04-13 -> 2030-05-07; 2030-08-16 -> 2030-09-08; 2030-12-06 -> 2030-12-26

Entry = first open on/after retrograde station, exit = last close on/before direct station; 'around' = -5..+5 sessions centred on the station.

| asset | n | window mean % | window win % | around % (p) | fwd 5d % | fwd 21d % | random % | p |
|-------|---|---------------|--------------|--------------|----------|-----------|----------|---|
| nifty | 84 | +0.22 | 46 | +0.51 (0.794) | +2.64 | +6.25 | +0.39 | 0.716 |
| gold | 84 | +1.06 | 65 | +1.20 (0.069) | +0.08 | +0.72 | +0.70 | 0.431 |
| silver | 84 | +0.23 | 49 | +1.79 (0.093) | +0.13 | +1.02 | +0.84 | 0.481 |
| crude | 84 | +1.04 | 58 | +0.43 (0.993) | +0.52 | +0.90 | +0.62 | 0.706 |

Video mapping: 'Mercury goes retrograde 24 Oct 2026; things start changing after that; November-February poor.' Ephemeris: Mercury R 2026-10-24 13:29 IST (Lib 26.75), direct 2026-11-13 21:29 IST (Lib 10.80).

Caveat: retrograde windows recur ~3x/year and their length varies (~3.5 weeks); the bootstrap holds window lengths fixed. Means are drift-sensitive; medians and p-values are the honest read.
