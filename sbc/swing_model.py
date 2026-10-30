"""Astro-quant swing windows (B-39): heliocentric aspect ENTRY, technical-confluence EXIT.

Every rule below was fixed before the first test, so the back-test grades the
model as written rather than a version tuned to the data.

ENTRY
  The first NIFTY session on or after a window's entry (entries after the
  15:30 IST close count from the next session). The trade is entered at that
  session's close, in the direction that *reverses* the prior trend:
  direction = -sign(close[E] - close[E - TREND_BARS]). Windows whose entry
  session is still inside an open trade are skipped; one position at a time.

EXIT layers (each "fires" on a bar t > E; long shown, short mirrored)
  Gann       Square of Nine: high reaches the next untouched level
             (sqrt(entry) + k/8)^2, k = 1..16 (45-degree steps);
             1x1 angle: close falls below pivot_low + ATR14[E] * bars since the pivot;
             time: the first session at least 30/45/60/90/180 calendar days after entry.
  Fibonacci  the swing leading into E is [min low, max high] of the last SWING_BARS
             bars. A long fires when high first touches a level above the entry close:
             retracements 23.6/38.2/50/61.8/78.6%, extensions 127.2/161.8/261.8%.
  Indicator  RSI14 crosses into 70; bearish divergence (a new high since entry with
             RSI >= 5 below its high since entry); MACD(12,26,9) crosses below its
             signal; histogram flips negative; close crosses below EMA20; volume
             >= 2x its 20-day average (only from 2013, when NIFTY volume starts).

EXIT = the first bar on which every required layer has fired within the last
CONFLUENCE_BARS bars. Strict = all three (the request); "2of3" = any two.
Without confluence the trade closes at MAX_HOLD bars ("timeout").

This is a research model: the output is hypothetical, not a trading recommendation.
"""

from __future__ import annotations

import datetime as dt
import math

import numpy as np

from sbc import helio_aspects as ha
from sbc import market_store

TREND_BARS = 10
SWING_BARS = 20
CONFLUENCE_BARS = 3
MAX_HOLD = 60
GANN_DAYS = (30, 45, 60, 90, 180)
FIB_RETRACE = (0.236, 0.382, 0.5, 0.618, 0.786)
FIB_EXTEND = (1.272, 1.618, 2.618)
LAYERS = ("gann", "fib", "indicator")


# ── indicators ─────────────────────────────────────────────────────────────

def ema(x: np.ndarray, n: int) -> np.ndarray:
    out = np.empty(len(x))
    a = 2.0 / (n + 1)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def rsi(close: np.ndarray, n: int = 14) -> np.ndarray:
    """Wilder's RSI; NaN for the first n bars."""
    d = np.diff(close, prepend=close[0])
    up, dn = np.clip(d, 0, None), np.clip(-d, 0, None)
    out = np.full(len(close), np.nan)
    if len(close) <= n:
        return out
    au, ad = up[1:n + 1].mean(), dn[1:n + 1].mean()
    for i in range(n, len(close)):
        if i > n:
            au = (au * (n - 1) + up[i]) / n
            ad = (ad * (n - 1) + dn[i]) / n
        out[i] = 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)
    return out


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int = 14) -> np.ndarray:
    prev = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum(high - low, np.maximum(abs(high - prev), abs(low - prev)))
    out = np.full(len(tr), np.nan)
    if len(tr) > n:
        out[n] = tr[1:n + 1].mean()
        for i in range(n + 1, len(tr)):
            out[i] = (out[i - 1] * (n - 1) + tr[i]) / n
    return out


class Bars:
    """Daily OHLCV with the indicators the exit rules use."""

    def __init__(self, rows: list[dict]):
        self.dates = [r["date"] for r in rows]
        self.open = np.array([r["open"] for r in rows], dtype=float)
        self.high = np.array([r["high"] for r in rows], dtype=float)
        self.low = np.array([r["low"] for r in rows], dtype=float)
        self.close = np.array([r["close"] for r in rows], dtype=float)
        self.volume = np.array([r["volume"] or 0 for r in rows], dtype=float)
        self.rsi = rsi(self.close)
        self.atr = atr(self.high, self.low, self.close)
        self.ema20 = ema(self.close, 20)
        macd = ema(self.close, 12) - ema(self.close, 26)
        self.macd, self.signal = macd, ema(macd, 9)
        self.hist = macd - self.signal
        vol = self.volume
        avg = np.convolve(vol, np.ones(20) / 20, mode="full")[:len(vol)]
        self.vol_avg20 = np.concatenate([[np.nan], avg[:-1]])  # average of the 20 bars before t
        self.vol_avg20[:20] = np.nan

    @classmethod
    def for_symbol(cls, symbol: str, start: str | None = None, end: str | None = None) -> Bars:
        """Daily bars for any series market_store holds (NIFTY, sector stocks, commodities)."""
        rows = market_store.get_daily(symbol, start, end)
        if not rows:
            raise market_store.MarketDataMissing(
                f"no {symbol} bars; run scripts/refresh_market_data.py --full (or --research)")
        return cls(rows)

    @classmethod
    def nifty(cls, start: str | None = None, end: str | None = None) -> Bars:
        return cls.for_symbol("NIFTY", start, end)

    def session_on_or_after(self, day: str) -> int | None:
        i = int(np.searchsorted(self.dates, day))
        return i if i < len(self.dates) else None


# ── exit layers ────────────────────────────────────────────────────────────

def _sq9_levels(price: float, direction: int) -> list[float]:
    root = math.sqrt(price)
    return [(root + direction * k / 8) ** 2 for k in range(1, 17) if root + direction * k / 8 > 0]


def _fib_levels(lo: float, hi: float, entry: float, direction: int) -> list[float]:
    r = hi - lo
    if direction > 0:
        levels = [lo + f * r for f in FIB_RETRACE + FIB_EXTEND]
        return sorted(v for v in levels if v > entry)
    levels = [hi - f * r for f in FIB_RETRACE + FIB_EXTEND]
    return sorted((v for v in levels if v < entry), reverse=True)


def layer_events(b: Bars, e: int, direction: int, until: int) -> dict[str, dict[int, list[str]]]:
    """{layer: {bar: [trigger names]}} for bars e+1..until."""
    events: dict[str, dict[int, list[str]]] = {k: {} for k in LAYERS}

    def fire(layer: str, t: int, name: str) -> None:
        events[layer].setdefault(t, []).append(name)

    entry = b.close[e]
    lo_i = max(0, e - SWING_BARS)
    window_lo, window_hi = b.low[lo_i:e + 1], b.high[lo_i:e + 1]
    lo, hi = window_lo.min(), window_hi.max()
    pivot_i = lo_i + int(np.argmin(window_lo) if direction > 0 else np.argmax(window_hi))
    pivot = b.low[pivot_i] if direction > 0 else b.high[pivot_i]
    unit = b.atr[e] if np.isfinite(b.atr[e]) else entry * 0.01

    sq9 = _sq9_levels(entry, direction)
    fib = _fib_levels(lo, hi, entry, direction)
    entry_day = dt.date.fromisoformat(b.dates[e])
    gann_days = list(GANN_DAYS)
    best_px = entry
    best_rsi = b.rsi[e] if np.isfinite(b.rsi[e]) else 50.0

    for t in range(e + 1, until + 1):
        reach = b.high[t] if direction > 0 else b.low[t]
        # Gann: Square of Nine
        while sq9 and (reach >= sq9[0] if direction > 0 else reach <= sq9[0]):
            fire("gann", t, f"sq9 {sq9.pop(0):.0f}")
        # Gann: 1x1 angle from the pivot
        line = pivot + direction * unit * (t - pivot_i)
        if (b.close[t] < line) if direction > 0 else (b.close[t] > line):
            fire("gann", t, "1x1 break")
        # Gann: time
        days = (dt.date.fromisoformat(b.dates[t]) - entry_day).days
        while gann_days and days >= gann_days[0]:
            fire("gann", t, f"{gann_days.pop(0)}d cycle")
        # Fibonacci
        while fib and (reach >= fib[0] if direction > 0 else reach <= fib[0]):
            fire("fib", t, f"fib {fib.pop(0):.0f}")
        # Indicators
        r, rp = b.rsi[t], b.rsi[t - 1]
        if direction > 0 and rp < 70 <= r:
            fire("indicator", t, "RSI 70")
        if direction < 0 and rp > 30 >= r:
            fire("indicator", t, "RSI 30")
        new_extreme = (b.high[t] >= best_px) if direction > 0 else (b.low[t] <= best_px)
        if np.isfinite(r):
            if new_extreme and (r <= best_rsi - 5 if direction > 0 else r >= best_rsi + 5):
                fire("indicator", t, "RSI divergence")
            best_rsi = max(best_rsi, r) if direction > 0 else min(best_rsi, r)
        if new_extreme:
            best_px = b.high[t] if direction > 0 else b.low[t]
        d_now, d_prev = b.macd[t] - b.signal[t], b.macd[t - 1] - b.signal[t - 1]
        if (d_prev >= 0 > d_now) if direction > 0 else (d_prev <= 0 < d_now):
            fire("indicator", t, "MACD cross")
        if (b.hist[t - 1] > 0 >= b.hist[t]) if direction > 0 else (b.hist[t - 1] < 0 <= b.hist[t]):
            fire("indicator", t, "histogram flip")
        crossed = ((b.close[t - 1] >= b.ema20[t - 1] and b.close[t] < b.ema20[t]) if direction > 0
                   else (b.close[t - 1] <= b.ema20[t - 1] and b.close[t] > b.ema20[t]))
        if crossed:
            fire("indicator", t, "EMA20 break")
        if b.volume[t] > 0 and np.isfinite(b.vol_avg20[t]) and b.volume[t] >= 2 * b.vol_avg20[t]:
            fire("indicator", t, "volume spike")
    return events


def confluence_exit(events: dict, e: int, until: int, need: int = 3) -> int | None:
    """First bar where `need` layers have each fired within the last CONFLUENCE_BARS bars."""
    for t in range(e + 1, until + 1):
        recent = sum(1 for layer in LAYERS
                     if any(t - CONFLUENCE_BARS < s <= t for s in events[layer]))
        if recent >= need:
            return t
    return None


# ── trades ─────────────────────────────────────────────────────────────────

def direction_at(b: Bars, e: int) -> int:
    if e < TREND_BARS:
        return 0
    trend = b.close[e] - b.close[e - TREND_BARS]
    return -int(np.sign(trend))


def trade(b: Bars, e: int, direction: int, exit_rule: str = "confluence", need: int = 3,
          hold: int = 10) -> dict | None:
    """Simulate one trade from the close of bar e. exit_rule: confluence | hold | ema20 | atr_stop."""
    last = min(e + MAX_HOLD, len(b.close) - 1)
    if last <= e or direction == 0:
        return None
    reason, triggers = "timeout", {}
    x = last
    if exit_rule == "confluence":
        events = layer_events(b, e, direction, last)
        hit = confluence_exit(events, e, last, need)
        if hit is not None:
            x, reason = hit, "confluence"
            triggers = {layer: [n for s, names in events[layer].items()
                                if hit - CONFLUENCE_BARS < s <= hit for n in names] for layer in LAYERS}
    elif exit_rule == "hold":
        x, reason = min(e + hold, last), "hold"
    elif exit_rule == "ema20":
        for t in range(e + 1, last + 1):
            if (b.close[t] < b.ema20[t]) if direction > 0 else (b.close[t] > b.ema20[t]):
                x, reason = t, "ema20"
                break
    elif exit_rule == "atr_stop":
        unit = b.atr[e] if np.isfinite(b.atr[e]) else b.close[e] * 0.01
        best = b.close[e]
        for t in range(e + 1, last + 1):
            best = max(best, b.high[t]) if direction > 0 else min(best, b.low[t])
            stop = best - direction * 2 * unit
            if (b.low[t] <= stop) if direction > 0 else (b.high[t] >= stop):
                x, reason = t, "atr_stop"
                break
    else:
        raise ValueError(f"unknown exit rule {exit_rule}")
    if reason == "timeout" and e + MAX_HOLD > len(b.close) - 1:
        reason = "open"  # the data ends before the trade could finish
    path_hi, path_lo = b.high[e + 1:x + 1].max(), b.low[e + 1:x + 1].min()
    entry_px = b.close[e]
    mfe = (path_hi / entry_px - 1) if direction > 0 else (1 - path_lo / entry_px)
    mae = (path_lo / entry_px - 1) if direction > 0 else (1 - path_hi / entry_px)
    return {
        "entry_session": b.dates[e], "exit_session": b.dates[x], "direction": direction,
        "entry_close": round(float(entry_px), 2), "exit_close": round(float(b.close[x]), 2),
        "return": float(direction * (b.close[x] / entry_px - 1)), "bars": x - e,
        "mfe": float(mfe), "mae": float(mae), "exit_reason": reason, "triggers": triggers,
    }


def entry_session(b: Bars, window: dict) -> int | None:
    day = window["entry_date"]
    if window["entry_time"] >= "15:30":
        day = (dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()
    return b.session_on_or_after(day)


def swing_windows(windows: list[dict], b: Bars, need: int = 3, exit_rule: str = "confluence") -> list[dict]:
    """One trade per aspect window (no overlapping positions), sorted by entry."""
    out, busy_until = [], -1
    for w in sorted(windows, key=lambda w: (w["entry_date"], w["entry_time"])):
        if w["starts_before_range"]:
            continue
        e = entry_session(b, w)
        if e is None or e <= busy_until:
            continue
        t = trade(b, e, direction_at(b, e), exit_rule, need)
        if t is None:
            continue
        out.append({**t, "pair": w["pair"], "aspect": w["aspect"], "aspect_name": w["aspect_name"],
                    "window_entry": f"{w['entry_date']} {w['entry_time']}",
                    "window_exact": f"{w['exact_date']} {w['exact_time']}",
                    "window_exit": f"{w['exit_date']} {w['exit_time']}"})
        busy_until = b.dates.index(t["exit_session"])
    return out


def build(start: str, end: str, planets: list[str] | None = None, aspects: list[str] | None = None,
          need: int = 3, bars: Bars | None = None) -> dict:
    """ENTRY windows, EXIT confluence and the resulting swing windows for [start, end]."""
    windows = ha.scan(start, end, planets, aspects)
    b = bars or Bars.nifty()
    swings = swing_windows(windows, b, need)
    closed = [s for s in swings if s["exit_reason"] != "open"]
    rets = np.array([s["return"] for s in closed]) if closed else np.array([])
    summary = {
        "trades": len(closed),
        "mean_return": float(rets.mean()) if len(rets) else None,
        "win_rate": float((rets > 0).mean()) if len(rets) else None,
        "confluence_exits": sum(1 for s in closed if s["exit_reason"] == "confluence"),
        "median_bars": float(np.median([s["bars"] for s in closed])) if closed else None,
    }
    return {
        "start": start, "end": end, "need": need, "data_as_of": b.dates[-1],
        "entries": ha.tv_payload(windows, None),
        "exits": {"dates": sorted({s["exit_session"] for s in swings if s["exit_reason"] == "confluence"}),
                  "label": "EXIT", "skip_holidays": False},
        "windows": windows, "swings": swings, "summary": summary,
        "bars": [{"date": d, "open": round(float(b.open[i]), 2), "high": round(float(b.high[i]), 2),
                  "low": round(float(b.low[i]), 2), "close": round(float(b.close[i]), 2)}
                 for i, d in enumerate(b.dates) if start <= d <= end],
        "status": "research",
        "caveat": ("Hypothetical swing windows for research, not trading advice. See the swing "
                   "validation report for how these entries and exits compare with random dates "
                   "and simple exits."),
    }
