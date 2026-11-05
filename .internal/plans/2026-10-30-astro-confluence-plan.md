# Astro-Technical Confluence Decision Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use beads-superpowers:subagent-driven-development (recommended) or beads-superpowers:executing-plans to implement this plan task-by-task. Each Task becomes a bead (`bd create -t task --parent <epic-id>`). Steps within tasks use checkbox (`- [ ]`) syntax for human readability.

**Goal:** Implement an astro-technical confluence decision module (`sbc/confluence_engine.py`) and pre-registered validation study (`scripts/study_astro_ma_confluence.py`) testing whether filtering EMA 9/21 crosses with astrological bias provides out-of-sample edge after transaction costs.

**Architecture:** Pure Python decision logic evaluating technical crossover conditions filtered by astrological alignment score thresholds, backed by vectorized permutation testing against same-day return decile controls.

**Tech Stack:** Python 3.11+, NumPy, Pandas, Pytest.

## Global Constraints

- Pre-registered, empirical validation with 0.20% transaction cost deduction.
- Closed-bar data only to prevent lookahead bias.
- Fully tested with unit test suite in `tests/test_confluence_engine.py`.

---

### Task 1: Create Confluence Decision Module & Unit Tests

**Files:**
- Create: `sbc/confluence_engine.py`
- Create: `tests/test_confluence_engine.py`

**Interfaces:**
- Consumes: Price series, EMA fast/slow series, astrological bias score (+1, 0, -1).
- Produces: Confluence trade signals ('BUY', 'SELL', 'HOLD') and filtered trade event records.

**Acceptance Criteria:**
- [ ] `sbc/confluence_engine.py` detects EMA crosses and enforces astrological directional confirmation.
- [ ] Unit tests pass verifying signal generation, neutral rejection, and net return calculation.

- [ ] **Step 1: Write `sbc/confluence_engine.py`**

```python
"""Astro-technical confluence decision engine: combines technical crossovers with astrological bias filters."""

from typing import Literal
import numpy as np
import pandas as pd


def detect_ma_cross(fast_ma: np.ndarray, slow_ma: np.ndarray) -> np.ndarray:
    """Detect bullish (+1) and bearish (-1) crossovers on closed bars."""
    diff = fast_ma - slow_ma
    prev_diff = np.roll(diff, 1)
    prev_diff[0] = 0.0

    cross = np.zeros(len(diff), dtype=int)
    cross[(prev_diff <= 0) & (diff > 0)] = 1
    cross[(prev_diff >= 0) & (diff < 0)] = -1
    return cross


def confluence_signal(
    technical_cross: int,
    astro_bias: Literal["bullish", "bearish", "neutral"] | float,
    astro_threshold: float = 0.0,
) -> Literal["BUY", "SELL", "HOLD"]:
    """Generate trade signal when technical cross aligns with astrological bias."""
    if technical_cross == 1:
        if astro_bias == "bullish" or (isinstance(astro_bias, (int, float)) and astro_bias > astro_threshold):
            return "BUY"
    elif technical_cross == -1:
        if astro_bias == "bearish" or (isinstance(astro_bias, (int, float)) and astro_bias < -astro_threshold):
            return "SELL"
    return "HOLD"


def net_trade_return(gross_return: float, round_trip_cost_pct: float = 0.20) -> float:
    """Calculate net return after subtracting transaction costs (in percent)."""
    return gross_return - (round_trip_cost_pct / 100.0)
```

- [ ] **Step 2: Write `tests/test_confluence_engine.py`**

```python
import numpy as np
import pytest
from sbc.confluence_engine import detect_ma_cross, confluence_signal, net_trade_return


def test_detect_ma_cross():
    fast = np.array([10.0, 10.0, 12.0, 11.0, 9.0])
    slow = np.array([11.0, 11.0, 11.0, 11.0, 11.0])
    # Bar 0: 10 vs 11 -> neg
    # Bar 1: 10 vs 11 -> neg
    # Bar 2: 12 vs 11 -> pos (Bullish cross = +1)
    # Bar 3: 11 vs 11 -> zero
    # Bar 4: 9 vs 11 -> neg (Bearish cross = -1)
    cross = detect_ma_cross(fast, slow)
    assert cross[2] == 1
    assert cross[4] == -1


def test_confluence_signal_aligned():
    assert confluence_signal(1, "bullish") == "BUY"
    assert confluence_signal(-1, "bearish") == "SELL"
    assert confluence_signal(1, 1.5, astro_threshold=0.5) == "BUY"


def test_confluence_signal_filtered():
    # Technical bull cross but astro is bearish -> HOLD
    assert confluence_signal(1, "bearish") == "HOLD"
    # Technical bear cross but astro is bullish -> HOLD
    assert confluence_signal(-1, "bullish") == "HOLD"
    # No technical cross -> HOLD
    assert confluence_signal(0, "bullish") == "HOLD"


def test_net_trade_return():
    gross = 0.01  # +1.0%
    net = net_trade_return(gross, round_trip_cost_pct=0.20)
    assert pytest.approx(net, 0.0001) == 0.008  # +0.8%
```

- [ ] **Step 3: Run pytest**

Run: `& "venv/Scripts/python.exe" -m pytest tests/test_confluence_engine.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add sbc/confluence_engine.py tests/test_confluence_engine.py
git commit -m "feat: add astro-technical confluence decision engine and tests"
```

---

### Task 2: Create Backtest Study Script (`scripts/study_astro_ma_confluence.py`)

**Files:**
- Create: `scripts/study_astro_ma_confluence.py`
- Test: Script execution test

**Interfaces:**
- Consumes: Historical NIFTY daily OHLC.
- Produces: Statistical backtest report comparing raw MA crosses vs astro-confluence filtered crosses.

**Acceptance Criteria:**
- [ ] Runs backtest over NIFTY series.
- [ ] Computes win rate, mean return, and net return after 0.20% costs.

- [ ] **Step 1: Write `scripts/study_astro_ma_confluence.py`**

```python
"""Empirical validation study: Does astro-technical confluence improve EMA cross forward returns?"""

import os
import sys
import numpy as np
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from sbc.screener.indicators import ema, heikin_ashi
from sbc.confluence_engine import detect_ma_cross, net_trade_return


def run_confluence_study(csv_path: str = "data/nifty_ohlc.csv"):
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return
    df = pd.read_csv(csv_path)
    ha = heikin_ashi(df)
    fast = ema(ha["close"], 9).values
    slow = ema(ha["close"], 21).values

    crosses = detect_ma_cross(fast, slow)
    bull_idx = np.where(crosses == 1)[0]
    bear_idx = np.where(crosses == -1)[0]

    closes = df["close"].values
    n = len(closes)

    # Next-day returns
    fwd_returns = []
    for idx in bull_idx:
        if idx < n - 1:
            ret = (closes[idx + 1] / closes[idx]) - 1.0
            fwd_returns.append(ret)

    if fwd_returns:
        fwd_arr = np.array(fwd_returns)
        mean_gross = np.mean(fwd_arr)
        mean_net = net_trade_return(mean_gross)
        win_rate = np.mean(fwd_arr > 0)
        print(f"Bullish EMA 9/21 Crosses: N={len(fwd_returns)}, Mean Gross: {mean_gross*100:.2f}%, Net: {mean_net*100:.2f}%, Win Rate: {win_rate*100:.1f}%")


if __name__ == "__main__":
    run_confluence_study()
```

- [ ] **Step 2: Run script to verify execution**

Run: `& "venv/Scripts/python.exe" scripts/study_astro_ma_confluence.py`
Expected: Outputs performance summary without crashing.

- [ ] **Step 3: Commit**

```bash
git add scripts/study_astro_ma_confluence.py
git commit -m "feat: add astro-technical confluence empirical study script"
```
