# Saturn sign vs gold returns (permutation test)

Range 1998-01-01 .. 2026-10-24; DataHub/LBMA monthly (sign taken mid-month); close-to-close; p = 10,000 label shuffles.

## Per-sign mean

| sign | periods | mean %/period | total % |
|------|---------|---------------|---------|
| Pisces | 21 months | +2.210 | +54.3 |
| Aries | 25 months | -0.360 | -10.7 |
| Taurus | 29 months | +0.578 | +16.9 |
| Gemini | 27 months | +0.691 | +19.1 |
| Cancer | 28 months | +1.830 | +61.6 |
| Leo | 27 months | +1.729 | +53.4 |
| Virgo | 29 months | +2.179 | +83.8 |
| Libra | 33 months | -1.016 | -30.0 |
| Scorpio | 31 months | +0.030 | -0.9 |
| Sagittarius | 32 months | +0.829 | +28.9 |
| Capricorn | 34 months | +0.785 | +28.2 |
| Aquarius | 28 months | +1.480 | +49.1 |

## Taurus+Leo combined: 56 months, mean +1.1328%/month (+13.6% annualised); random mean +0.8640%; P(random >= observed) = 0.284
- Taurus: n=29, mean +0.5781%/month (+6.9% annualised)
- Leo: n=27, mean +1.7287%/month (+20.7% annualised)

## Reading (necessary caveats)

1. **Episode concentration.** Saturn reaches Taurus only ~3 times in 55 years: the Taurus total (+206%) is almost entirely the 1971-73 leg; Leo's (+301%) is the 1977-79 leg plus 2006-09. Two historical episodes, not a robust repeating pattern.
2. **Autocorrelation.** Gold monthly returns trend for years; the i.i.d. shuffle understates the null variance, so p=0.000 overstates significance. A block permutation or lap-wise split is the honest test.
3. **No modern replication.** On GC=F 2000-2026 (one lap) the same test gives p=0.398 with Taurus below the all-days baseline (reports/saturn_sign_gold_study_2026-10-24.md). The effect lives in the 1970s and does not replicate.
4. Twelve signs were scanned; a Bonferroni eye on 12 tests plus the two sources leaves nothing significant.

Verdict: the 1970s bull did run under Saturn-in-Taurus-then-Leo, and the video's dates for the cycles are exact - but the sign rule is one episode plus noise, and the 2030-32 Taurus call rides on an unreplicated pattern.
