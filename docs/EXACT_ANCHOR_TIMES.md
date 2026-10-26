# Exact Anchor Times Research

This document tracks research into exact birth times for existing market anchors.

## Priority: Medium (Phase 3.3)

Current status: All anchors use approximate times (00:00 for most). This is a known limitation.

---

## NSE (National Stock Exchange)
- **Date:** 1992-11-27
- **Current Time:** 00:00 (approximate)
- **Required Research:** Exact incorporation time from NSE incorporation documents or government gazette
- **Sources to Check:**
  - NSE official incorporation documents
  - Ministry of Finance, Government of India gazette
  - SEBI historical records
- **Notes:** Time may not be precisely recorded in incorporation documents. May need to use "first trading day" opening time (09:15 IST) as proxy.

---

## BSE (Bombay Stock Exchange)
- **Date:** 1875-07-09
- **Current Time:** 00:00 (approximate)
- **Required Research:** Exact founding time from BSE historical records
- **Sources to Check:**
  - BSE historical archives
  - Bombay Stock Exchange official history documents
  - Indian business history archives
- **Notes:** Historical records from 1875 may not have precise time. May need to use reasonable approximation (e.g., 09:00 opening time of that era).

---

## NIFTY 50
- **Date:** 1995-11-03
- **Current Time:** 00:00 (approximate)
- **Required Research:** Exact base time from NSE historical data
- **Sources to Check:**
  - NSE historical index data documentation
  - NIFTY 50 index methodology documents
  - Business newspapers from November 1995
- **Notes:** Base date may be calculated from historical data. First trading day opening time (09:15 IST) may be appropriate proxy.

---

## SENSEX
- **Date:** 1979-04-01
- **Current Time:** 00:00 (approximate)
- **Required Research:** Exact base time from BSE historical data
- **Sources to Check:**
  - BSE historical index data documentation
  - SENSEX index methodology documents
  - Business newspapers from April 1979
- **Notes:** Base date may be calculated from historical data. First trading day opening time (09:15 IST) may be appropriate proxy.

---

## India (National Market)
- **Date:** 1947-08-15
- **Current Time:** 00:00 (midnight, official)
- **Status:** Correct
- **Notes:** Independence was officially at midnight. This is the accurate time.

---

## Bitcoin (BTC)
- **Date:** 2009-01-03
- **Current Time:** 18:15:05 UTC
- **Status:** Accurate
- **Source:** Bitcoin blockchain Genesis Block timestamp
- **Notes:** This is the exact time the Genesis Block was mined by Satoshi Nakamoto.

---

## NYSE (New York Stock Exchange)
- **Date:** 1792-05-17
- **Current Time:** 09:00 (approximate)
- **Required Research:** Exact signing time of Buttonwood Agreement
- **Sources to Check:**
  - NYSE historical archives
  - Buttonwood Agreement documentation
  - Financial history books/research papers
- **Notes:** Historical records from 1792 may not have precise time. 09:00 is a reasonable approximation for morning business hours of that era.

---

## Research Recommendations

1. **Priority 1:** Research NSE and NIFTY exact times (most relevant to current user base)
2. **Priority 2:** Research BSE and SENSEX exact times (secondary importance)
3. **Priority 3:** Research NYSE exact time (for global expansion)
4. **Accept Approximations:** If exact times cannot be found, document the limitation and use reasonable proxies (e.g., first trading day opening time)

---

## Alternative Approach: Sensitivity Analysis

If exact times cannot be determined, consider:
- Running sensitivity analysis with different times (00:00, 09:15, 12:00)
- Comparing prediction accuracy across different anchor times
- Selecting the time that produces the best backtest results
- Documenting this methodology clearly

---

## Last Updated
2026-10-13 (during Phase 3.3 implementation)
