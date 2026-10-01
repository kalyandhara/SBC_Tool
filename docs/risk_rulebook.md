# Risk-Management Rulebook

Derived from the transit-wise historical studies in this workspace
(`data/output/study_*.csv`, 2002-2026, yfinance GC=F / SI=F / ^NSEI,
Lahiri sidereal ephemeris).  Numbers below are historical averages from
those studies — treat them as regime bias, not guarantees.

## 1. Regime sizing by Mars-Jupiter same-sign status

| Regime | Gold | Silver | Nifty | Action |
|---|---|---|---|---|
| Same sign (co-present) | 74% positive, avg +1.84% | 63% positive, avg +1.40% | 31% positive, avg −1.65% | Full size long bias in metals; halve or avoid index longs; prefer hedging Nifty |
| Not same sign | n/a | n/a | n/a | Normal rules apply |

- The same transit that lifts metals is historically **bearish for
  Nifty** (2013 Gemini: gold +9.50% vs Nifty −4.95%) — do not assume
  one reading transfers across assets.
- Live period Sep 2026 (Cancer): gold +0.40%, silver −0.18%, Nifty flat
  so far — consistent with the chop regime early in the window.

## 2. Nakshatra filters (fresh-entry longs)

**Positive windows (Jupiter transits):**
- Jyeshtha — gold +11.55% avg, 100% positive over 4 visits; Nifty +10.62%
- Dhanishta — Nifty +23.68% avg, 4/4 positive
- Punarvasu — silver +20.30% avg
- Vishakha, Ardra, Rohini — solidly positive for metals

**Caution windows (avoid fresh longs):**
- Jupiter in Pushya / P.Ashadha / Krittika — worst Jupiter transits
  (P.Ashadha: Nifty −16.25% avg; Krittika: gold 0% positive)
- Mars in Ashwini / P.Phalguni / U.Phalguni — worst Mars transits for
  metals (Ashwini: silver −4.88% avg, 33% positive; U.Phalguni: gold
  21% positive)
- Mercury transits are weak signals overall (52-53% positive) — use
  only as confluence, never standalone.

## 3. Moon daily nakshatra — volatility and day bias

- Highest-volatility Moon nakshatras for Nifty: **Abhijit (1.63%),
  U.Bhadrapada, P.Ashadha, Revati, Ardra** (≈1.5% daily range) —
  widen intraday stops accordingly.
- **Jyeshtha Moon days are bearish for both metals** (gold 40.5% up,
  silver 38.9% up) — avoid longs, favour intraday shorts.
- **P.Bhadrapada is the weakest Nifty Moon day** (43.3% up, −0.25% avg).
- **U.Phalguni is the strongest Nifty Moon day** (59.3% up, +0.15%).
- Silver gaps run 0.9-1.0% daily (2-3x Nifty's ~0.35%) — reduce
  overnight size in silver.

## 4. Stop and event rules

- Never hold full size into a **Negative-cycle entry**: the 2020
  Sagittarius window produced gold −5.2%, silver −30.1%, Nifty −28.0%.
- A **Flat result** (|move| < 0.1% for the transit period) marks a chop
  regime — reduce targets, avoid breakout entries until the next
  ingress.
- Transit-period opens/closes use the first/last available trading day
  (weekend adjustment) — do not place orders on the calendar date
  itself when it falls on a weekend/holiday.

## 5. General

- Risk 0.5-1% of capital per trade; scale by regime multipliers above
  (halve in caution windows, stand aside in negative ones).
- Confluence requirement: act when at least two of {same-sign regime,
  Jupiter nakshatra, Moon nakshatra} agree; skip single-signal trades.
- Re-check `scripts/fetch_history.py` weekly so studies include the
  latest data before generating the weekly report.
