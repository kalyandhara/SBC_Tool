# Ghabad Muhurat (घबाड मुहूर्त): definition for B-46

**Source:** Marathi Wikipedia, [घबाड मुहूर्त](https://mr.wikipedia.org/wiki/%E0%A4%98%E0%A4%AC%E0%A4%BE%E0%A4%A1_%E0%A4%AE%E0%A5%81%E0%A4%B9%E0%A5%82%E0%A4%B0%E0%A5%8D%E0%A4%A4),
read 2026-10-05 (CC BY-SA 4.0). Below is an English summary of the rule, not a full translation.
The article cites no classical text for the rule itself. It lists muhurta texts in general
(Muhurta Chintamani, Dharmasindhu, Nirnayasindhu and others) and says panchangs print Ghabad times.

## The rule

1. **Count** the nakshatras from the Sun's nakshatra to the Moon's, inclusive (the Sun's own star counts as 1). Range 1–27.
2. **Multiply** the count by 3.
3. **Add** the tithi, numbered from Shukla Pratipada: Shukla 1–15, then Krishna 1–15 as 16–30.
4. **Divide by 7.** Remainder **3** is **Ghabad**; remainder **0** is **Ardha-ghabad** (half Ghabad).

The article says work started in a Ghabad muhurat succeeds with a large gain. That's where the
Marathi idiom comes from: a sudden windfall is "getting a ghabad".

### Worked example (from the article)

| Step | Value |
|---|---|
| Sun nakshatra | Purva Ashadha (#20) |
| Moon nakshatra | Swati (#15) |
| Count, Sun → Moon, inclusive | 23 |
| × 3 | 69 |
| Tithi: Krishna Dashami = 15 + 10 | 25 |
| Sum | 94 |
| 94 ÷ 7 | 13 remainder **3**: Ghabad |

A computed check reproduces this (count 23, remainder 3).

## Check against the monthly-projection note

Screenshot 8 of the note marks **05-10-2026** as "Ghabad Muhurat". With sidereal Lahiri
positions (Moshier), the rule gives:

- Sun in Hasta (#13), Moon in Pushya (#8): count = 23
- Tithi Krishna 10 = 25 (from 03:55 IST)
- 23 × 3 + 25 = 94, remainder 3, so **Ghabad from 03:55 to 23:10 IST on 5 Oct**, covering the whole NSE session.

These are the same numbers as the article's example, by coincidence. Of 1–15 Oct (the table's
range), 5 Oct is the only day with a Ghabad window inside market hours (09:15–15:30); the others
fall at night. That's consistent with the source marking only 5 Oct, but it is one date, not a validation.

### October 2026 windows (IST, minute resolution)

| Kind | From | To |
|---|---|---|
| Ardha-ghabad | 01-10 Thu 06:03 | 01-10 12:36 |
| **Ghabad** | **05-10 Mon 03:55** | **05-10 23:10** |
| Ardha-ghabad | 06-10 Tue 02:09 | 06-10 22:18 |
| Ghabad | 06-10 Tue 22:18 | 07-10 00:36 |
| Ardha-ghabad | 07-10 Wed 21:41 | 07-10 23:18 |
| Ardha-ghabad | 10-10 Sat 21:43 | 11-10 02:21 |
| Ghabad | 15-10 Thu 01:14 | 15-10 04:04 |
| Ardha-ghabad | 16-10 Fri 03:26 | 16-10 06:48 |
| Ghabad | 16-10 Fri 06:48 | 17-10 05:55 |
| Ardha-ghabad | 17-10 Sat 09:48 | 18-10 08:29 |
| Ghabad | 22-10 Thu 14:49 | 22-10 20:50 |
| Ardha-ghabad | 23-10 Fri 14:37 | 23-10 21:04 |
| Ghabad | 23-10 Fri 21:04 | 24-10 12:51 |
| Ardha-ghabad | 24-10 Sat 12:51 | 24-10 13:38 |
| Ghabad | 28-10 Wed 04:08 | 28-10 13:27 |
| Ardha-ghabad | 29-10 Thu 01:08 | 29-10 11:12 |
| Ghabad | 29-10 Thu 11:12 | 29-10 22:11 |
| Ardha-ghabad | 30-10 Fri 09:05 | 30-10 19:26 |

## Conventions chosen (the article doesn't state them)

- **Continuous windows, not a whole-day verdict.** The remainder changes whenever the Moon's
  nakshatra, the tithi or the Sun's nakshatra changes, so the result is a set of time windows.
  A panchang that judges the day by its sunrise values would differ on days with a change after sunrise.
- **Sidereal Lahiri nakshatras** for both Sun and Moon, as elsewhere in the tool.
- **Inclusive count**, confirmed by the article's example (20 → 15 gives 23, not 22).

## Status

This unblocks B-46 (`sbc/muhurta.py` plus the B-43 table's muhurta column). As with every other
factor, it's a candidate: whether Ghabad sessions differ from other sessions is untested.
