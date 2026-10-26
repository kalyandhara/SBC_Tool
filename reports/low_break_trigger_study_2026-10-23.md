# 'Note the low of date D; trend flips when broken'

NIFTY 2007-01-01 .. 2026-10-23, close-basis outcomes; anchor = every session; break within N sessions; entry at the break-day close; p = two-sided bootstrap vs random same-length close windows.

## How often does the anchor low break at all?

| anchor | basis | P(break in 5) | P(break in 10) | P(break in 21) |
|--------|-------|---------------|----------------|----------------|
| 1-day low (literal device) | close | 54% | 65% | 74% |
| 1-day low (literal device) | intraday | 69% | 77% | 83% |
| lowest low of 5 sessions | close | 34% | 46% | 58% |
| lowest low of 5 sessions | intraday | 44% | 56% | 66% |

### Break of 1-day low (literal device), close basis, within 10 sessions (n=3025 breaks)

| horizon | mean % | median % | win % | random % | p |
|---------|--------|----------|-------|----------|---|
| +5d | +0.23 | +0.29 | 54 | +0.21 | 0.692 |
| +10d | +0.46 | +0.56 | 57 | +0.42 | 0.578 |
| +21d | +0.83 | +1.11 | 61 | +0.86 | 0.754 |

### Break of 1-day low (literal device), intraday basis, within 10 sessions (n=3579 breaks)

| horizon | mean % | median % | win % | random % | p |
|---------|--------|----------|-------|----------|---|
| +5d | +0.21 | +0.29 | 54 | +0.21 | 0.928 |
| +10d | +0.43 | +0.52 | 57 | +0.42 | 0.846 |
| +21d | +0.80 | +1.00 | 60 | +0.86 | 0.566 |

### Break of lowest low of 5 sessions, close basis, within 10 sessions (n=2152 breaks)

| horizon | mean % | median % | win % | random % | p |
|---------|--------|----------|-------|----------|---|
| +5d | +0.38 | +0.39 | 55 | +0.21 | 0.005 |
| +10d | +0.62 | +0.97 | 58 | +0.42 | 0.016 |
| +21d | +0.89 | +1.24 | 59 | +0.86 | 0.815 |

### Break of lowest low of 5 sessions, intraday basis, within 10 sessions (n=2584 breaks)

| horizon | mean % | median % | win % | random % | p |
|---------|--------|----------|-------|----------|---|
| +5d | +0.34 | +0.40 | 56 | +0.21 | 0.021 |
| +10d | +0.55 | +0.68 | 58 | +0.42 | 0.088 |
| +21d | +0.96 | +1.32 | 61 | +0.86 | 0.429 |

Video mapping: 'note the low of the market on November 1, 2026; when that day's low is broken, a negative trend begins.' Nov 1, 2026 is a Sunday - no session anywhere; the nearest anchors are Oct 30 and Nov 2. The device only becomes falsifiable with a validity window (this study uses 10 sessions) and a break definition (close or intraday).

Caveat: five variant grids were checked, so treat any single small p with a multiple-testing eye. Event means are also tail-sensitive (2008, 2020); medians and p-values are the honest read.
