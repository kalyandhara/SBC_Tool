# Venus Retrograde 2026 deck — ingest (2026-10-11)

**Source:** `Venus_Retrograde_2026.pptx` (15 slides, with speaker notes), by V.K. Ramesh, Astro Quant Research Lab. Window 4 Oct – 14 Nov 2026. Slide text, speaker notes and chart data were read; the deck has no embedded images.
**Status: ingested, not built, not tested.** It is a presenter's astrological view with a stated probability split. It is not a validated signal.

## What the deck claims

- **Direction:** Venus retrograde "re-prices" rather than sets direction. Expected: a volatile capitulation from 17 Oct to 4 Nov, a tradeable low near 24 Oct or 4 Nov, and a better market after 14 Nov.
- **Analogue:** 2026 rhymes with 2018 (a fall into the retrograde, then a low), not with 2010 (a rally into it, then a top). Venus repeats the Libra–Scorpio loop every 8 years (2002, 2010, 2018, 2026).
- **Vedic/KP reading:** Sun debilitated 17 Oct – 16 Nov, Venus combust 19–29 Oct, Mercury retrograde 24 Oct – 13 Nov, Mars debilitated, Jupiter leaves Cancer for Leo ~31 Oct.
- **Scenarios (presenter's weights):** base 55% (2018-type V, Nifty flat to +3% over the window), bull 25% (2025-type, low already in), bear 20% (2015-type, weekly close below 21,900 with VIX above 20, extends to 20,800–21,000).
- **Bank Nifty:** base 55% catch-down then lead; bear 20% weekly close below 52,000.

## What I checked against stored data (`data/market.db`, NIFTY daily)

| Claim | Deck | Stored data | Result |
|---|---|---|---|
| 1 Oct 2026 close | 22,422 | 22,421.9 | matches |
| 52-week high | 26,373 | 26,373.2 | matches |
| 52-week low | 22,183 | 22,179.9 (intraday low) | minor gap, 3 points |
| 10 retrograde windows, start and end closes (2010–2025) | as in table | all ten within 0.1 point | matches |
| Window returns (incl. average +0.8%, median +1.8%, 6 of 10 positive) | as stated | recomputed from the deck's own levels | consistent |
| 2018 low 26 Oct | 10,004 | 10,005 (close-based) | matches within rounding |

The deck's notes say its levels are "from memory" and should be replaced with exact closes. The stored closes say the table was right, so that caveat can be dropped for the Nifty window table.

Note: the store's last bar is **9 Oct 2026 at 22,520**, already above the deck's 1 Oct base. The deck's bear and base levels are therefore not current.

## Not checked

- **"8 of 10 windows printed a swing low"** and the **"7–12% high-to-low range"**: both need a definition of swing low and window range. Testable against the same ten windows.
- **Station and sidereal degrees, combustion and ingress dates** (Venus 14°15' Libra Rx, 28°38' Virgo direct, Mercury Rx 26°45' Libra, Jupiter ~31 Oct). The notes themselves say to verify ingresses against an ephemeris. The Swiss Ephemeris in the repo could check them.
- **Bank Nifty** levels and the 2018 figures (−6% to +10%). No Bank Nifty series was checked.
- **Sector monthly moves** (Auto −10.9%, FMCG −5.7%).
- **Scenario weights** (55/25/20): the deck calls them "the presenter's assessment, not a forecast". They have no derivation.
- **Event dates** (F&O expiry 27 Oct, FOMC 27–28 Oct, US midterms 3 Nov, Diwali Muhurat 8 Nov). Should be checked against the NSE and Fed calendars.

## How this fits the repo

The repo already has the test this deck invites. A pre-registered rule could be tested against the ten retrograde windows and the 2002–2025 stations, the same way B-53 was. Such a test would need the swing-low definition and the ±3-session window fixed before running it, and it would show whether the "low near a station" pattern holds at better than chance. Without that, the deck is an analogy.

The deck's own rules are reasonable risk habits: confirm astro dates with price, no naked shorts around the cazimi, cut size. They don't need the astrology to be right to be used.

## Recommendation

Log as an idea and a candidate for a pre-registered test, not as a signal. If you want the test, I'd first write the pre-registration (swing-low definition, window, ±3 sessions, pass/fail threshold) before scoring any window.

## Backlog

- **B-70 — Venus station test (not started).** Pre-register, then grade, the deck's rule that the
  swing low of a Venus retrograde falls within ±3 sessions of a station or the inferior conjunction.
  Scope: NIFTY daily bars, the ten windows from 2010 to 2025 (plus 2002 if the store holds it),
  and any other Venus station in the store for a control.
  - Before running: fix the swing-low definition, the window edges, the ±3-session rule, the
    pass threshold, and the control set. Record them in `docs/research/` with the date.
  - Then score: swing-low hit rate against the control, with a sign test or bootstrap.
  - Also check the deck's "8 of 10 windows" and "7–12% range" claims under the same definitions.
  - Acceptance: a report in `docs/research/` that says pass or fail on the pre-registered rule,
    and does not change the forecast unless it passes.
  - Depends on: nothing new. Station dates come from `sbc/stations.py`, already verified against
    the Swiss Ephemeris (Venus R 03-10 12:43 IST).
  - Not in scope: Bank Nifty, sector moves, the scenario weights.
