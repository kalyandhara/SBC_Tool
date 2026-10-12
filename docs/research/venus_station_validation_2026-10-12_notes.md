# B-70 run notes: where the code departs from the registration

The registration (`venus_station_preregistration_2026-10-12.md`, commit 4f82b7d) is frozen and was
not edited. These are the differences between it and the code that produced
`venus_station_validation_2026-10-12.md`. Each was found after the run, by reading the code against the text.

1. **Pass rule is stricter in the code.** The registration requires the hit rate to beat the null in both
   eras in the same direction. `sbc/venus_station_validation.py` also requires a one-sided p < 0.05
   within each era. The verdicts do not depend on this: h1 has q = 0.46 under either rule, and h2 is
   underpowered (12 events) under either.
2. **Conjunction dates are day-level.** The registration says the crossing is "refined to the minute".
   The code takes whichever of the two bracketing days has the smaller |difference|. The event session
   is the first NIFTY session on or after that date, so the effect is at most one session, inside the
   ±3-session window. Dates from the run: 2008-06-09 to 2026-01-07 (12 events).
3. **Era nulls are era-restricted.** The registration's step 2 describes a whole-sample null. The code
   also runs a null inside each era, drawing offsets so every shifted event stays in that era. The
   registration's step 5 is ambiguous on this point, so this is an interpretation, not a clear departure.

Other items in the report, outside the registered tests:
- The deck's "8 of 10 windows" is 11 of 11 in the store (windows from each R to the next D, 2007 onward).
- The deck's 7–12% range compares with 7.2% over rolling windows of the same length. The deck's "about 5%"
  for a normal window is not reproduced.

Verdict: no edge for h1; h2 underpowered. A registration that tests the pivot rule at 20 or more events
would need a different sample, which means a new registration.
