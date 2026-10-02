"""Gann indicator toolkit - swing/positional price-level generators.

Implements the AstroGann Pro should/could-have indicators from the backlog
as deterministic, unit-testable functions over daily OHLC bars:

- Gann Momentum Analyzer: long/short trigger + target levels from momentum
- Gann Apex Reversal Suite: dynamic reversal signals with auto target/SL
- Gann Harmonic Opens: weekly/monthly/quarterly/yearly opens with buy
  above / sell below levels
- Gann Harmonic Vibrations: 1/8th vibration S/R levels from swing inputs
- Gann Wave Levels: dynamic S/R from the previous day's OHLC
- Gann Lightning Scalper: tight instant buy/sell scalping levels
- Gann Mega Trend X / Annual Pulse: monthly/annual trend change levels

Research output, not investment advice.
"""

from datetime import date, timedelta
from typing import Any


def _window(bars: list[dict[str, Any]], lookback: int) -> list[dict[str, Any]]:
    return bars[-max(1, lookback):]


def _swing(bars: list[dict[str, Any]], lookback: int) -> tuple[float, float]:
    window = _window(bars, lookback)
    high = max(b["high"] for b in window)
    low = min(b["low"] for b in window)
    if high <= low:
        ref = max(abs(low), 0.05)
        low, high = low - ref, low + ref
    return high, low


def momentum_levels(
    bars: list[dict[str, Any]], lookback: int = 20
) -> dict[str, Any]:
    """Gann Momentum Analyzer: long/short trigger and target levels.

    Trigger at the swing high/low of the lookback window; targets at the
    0.618/0.786 Gann ratios of the window range; SL at the opposite swing.
    """
    if len(bars) < 2:
        raise ValueError("at least 2 bars required")
    high, low = _swing(bars, lookback)
    close = float(bars[-1]["close"])
    momentum = close - float(bars[-2]["close"])
    range_ = high - low
    return {
        "trend": "bullish" if momentum >= 0 else "bearish",
        "momentum": round(momentum, 2),
        "long": {
            "trigger": round(high, 2),
            "target": round(low + range_ * 0.618, 2),
            "stop_loss": round(low, 2),
        },
        "short": {
            "trigger": round(low, 2),
            "target": round(high - range_ * 0.618, 2),
            "stop_loss": round(high, 2),
        },
    }


def apex_reversal(
    bars: list[dict[str, Any]], lookback: int = 20, proximity_pct: float = 0.03
) -> dict[str, Any]:
    """Gann Apex Reversal Suite: reversal candidates at range extremes.

    A close within `proximity_pct` of the swing high flags a bearish reversal
    candidate (target at range mid, SL beyond the high); near the swing low
    flags a bullish reversal candidate.
    """
    high, low = _swing(bars, lookback)
    close = float(bars[-1]["close"])
    range_ = high - low
    mid = low + range_ * 0.5

    signals = []
    if close >= high - range_ * proximity_pct:
        signals.append({
            "direction": "bearish",
            "trigger": round(close, 2),
            "target": round(mid, 2),
            "stop_loss": round(high + range_ * 0.05, 2),
        })
    if close <= low + range_ * proximity_pct:
        signals.append({
            "direction": "bullish",
            "trigger": round(close, 2),
            "target": round(mid, 2),
            "stop_loss": round(low - range_ * 0.05, 2),
        })
    return {"close": round(close, 2), "range_mid": round(mid, 2), "signals": signals}


def harmonic_opens(
    bars: list[dict[str, Any]], buffer_pct: float = 0.0025
) -> dict[str, Any]:
    """Gann Harmonic Opens: period opens with buy above / sell below levels."""
    if not bars:
        raise ValueError("at least 1 bar required")

    last = date.fromisoformat(bars[-1]["date"])
    periods = {
        "weekly": last - timedelta(days=last.weekday()),
        "monthly": last.replace(day=1),
        "quarterly": last.replace(day=1, month=((last.month - 1) // 3) * 3 + 1),
        "yearly": last.replace(month=1, day=1),
    }

    opens = []
    for name, start in periods.items():
        ref = next((b for b in bars if date.fromisoformat(b["date"]) >= start), None)
        if not ref:
            continue
        open_price = float(ref["open"])
        opens.append({
            "period": name,
            "date": ref["date"],
            "open": round(open_price, 2),
            "buy_above": round(open_price * (1 + buffer_pct), 2),
            "sell_below": round(open_price * (1 - buffer_pct), 2),
        })
    return {"opens": opens, "buffer_pct": buffer_pct}


def harmonic_vibrations(
    bars: list[dict[str, Any]],
    lookback: int = 60,
    swing_high: float | None = None,
    swing_low: float | None = None,
) -> dict[str, Any]:
    """Gann Harmonic Vibrations: 1/8th division S/R levels.

    Uses the supplied swing high/low, or the lookback-window extremes when
    omitted. Levels at low + range * n/8 for n = 1..7.
    """
    if swing_high is None or swing_low is None:
        sh, sl = _swing(bars, lookback)
        swing_high = swing_high if swing_high is not None else sh
        swing_low = swing_low if swing_low is not None else sl
    if swing_high <= swing_low:
        raise ValueError("swing_high must exceed swing_low")

    range_ = swing_high - swing_low
    labels = ["1/8", "2/8", "3/8", "4/8", "5/8", "6/8", "7/8"]
    levels = [{
        "label": labels[n - 1],
        "price": round(swing_low + range_ * n / 8, 2),
        "support_resistance": "resistance" if n >= 5 else "pivot" if n == 4 else "support",
    } for n in range(1, 8)]
    return {
        "swing_high": round(swing_high, 2),
        "swing_low": round(swing_low, 2),
        "levels": levels,
    }


def wave_levels(bars: list[dict[str, Any]]) -> dict[str, Any]:
    """Gann Wave Levels: dynamic S/R from the previous day's OHLC.

    Bullish wave above the previous close's projection; bearish wave below.
    """
    if len(bars) < 2:
        raise ValueError("at least 2 bars required")
    prev = bars[-2]
    p_open, p_high, p_low, p_close = (float(prev[k]) for k in ("open", "high", "low", "close"))
    body = p_close - p_open
    bullish = body >= 0
    return {
        "reference_date": prev["date"],
        "bullish": {
            "wave_level": round(p_close + abs(body), 2),
            "support": round(p_low, 2),
            "valid_above": round(p_high, 2),
        },
        "bearish": {
            "wave_level": round(p_close - abs(body), 2),
            "resistance": round(p_high, 2),
            "valid_below": round(p_low, 2),
        },
        "prev_day_bias": "bullish" if bullish else "bearish",
    }


def lightning_scalper(
    bars: list[dict[str, Any]], sl_fraction: float = 0.1
) -> dict[str, Any]:
    """Gann Lightning Scalper: tight instant buy/sell scalping levels.

    Buy above the previous day's high, sell below its low; tight SL as a
    fraction of the previous day's range; target at 2x the SL distance.
    """
    if len(bars) < 2:
        raise ValueError("at least 2 bars required")
    prev = bars[-2]
    p_high = float(prev["high"])
    p_low = float(prev["low"])
    p_close = float(prev["close"])
    range_ = p_high - p_low
    if range_ <= 0:
        raise ValueError("previous bar has no range")
    sl = round(range_ * sl_fraction, 2)
    return {
        "reference_date": prev["date"],
        "buy_above": round(p_high, 2),
        "sell_below": round(p_low, 2),
        "stop_loss": round(p_close, 2),
        "target_above": round(p_high + 2 * sl, 2),
        "target_below": round(p_low - 2 * sl, 2),
        "sl_distance": sl,
    }


def mega_trend(
    bars: list[dict[str, Any]], buffer_pct: float = 0.0025
) -> dict[str, Any]:
    """Gann Mega Trend X / Annual Pulse: monthly/annual trend change levels.

    Buy above the period open's trend level, sell below; trend direction from
    the close's position within the period range.
    """
    if not bars:
        raise ValueError("at least 1 bar required")
    last = date.fromisoformat(bars[-1]["date"])
    close = float(bars[-1]["close"])

    def period_level(start: date) -> dict[str, Any] | None:
        ref = next((b for b in bars if date.fromisoformat(b["date"]) >= start), None)
        if not ref:
            return None
        o = float(ref["open"])
        return {
            "date": ref["date"],
            "level": round(o, 2),
            "buy_above": round(o * (1 + buffer_pct), 2),
            "sell_below": round(o * (1 - buffer_pct), 2),
        }

    monthly = period_level(last.replace(day=1))
    annual = period_level(last.replace(month=1, day=1))
    annual_ref = next((b for b in bars if date.fromisoformat(b["date"]) >= last.replace(month=1, day=1)), None)
    if annual_ref:
        year_high = max(b["high"] for b in bars if b["date"] >= annual_ref["date"])
        year_low = min(b["low"] for b in bars if b["date"] >= annual_ref["date"])
        trend = "bullish" if close >= (year_high + year_low) / 2 else "bearish"
    else:
        trend = "neutral"
    return {"monthly": monthly, "annual": annual, "trend": trend, "close": round(close, 2)}


GANN_INDICATOR_KINDS = {
    "momentum": momentum_levels,
    "apex_reversal": apex_reversal,
    "harmonic_opens": harmonic_opens,
    "harmonic_vibrations": harmonic_vibrations,
    "wave_levels": wave_levels,
    "lightning_scalper": lightning_scalper,
    "mega_trend": mega_trend,
}


def run_indicator(kind: str, bars: list[dict[str, Any]]) -> dict[str, Any]:
    """Run one Gann indicator by kind over daily OHLC bars."""
    fn = GANN_INDICATOR_KINDS.get(kind)
    if not fn:
        raise ValueError(
            "unknown kind (momentum/apex_reversal/harmonic_opens/"
            "harmonic_vibrations/wave_levels/lightning_scalper/mega_trend)"
        )
    return fn(bars)


__all__ = [
    "momentum_levels",
    "apex_reversal",
    "harmonic_opens",
    "harmonic_vibrations",
    "wave_levels",
    "lightning_scalper",
    "mega_trend",
    "run_indicator",
    "GANN_INDICATOR_KINDS",
]
