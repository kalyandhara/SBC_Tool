"""Momentum scan engine: three modes with signal detection and trade
tracking.

Modes (all evaluated on closed candles; a signal fires on the bar the
conditions first turn true):
- "full": 4-rule momentum system.  Long = Supertrend(10,3) bullish AND
  RSI(14) >= rsi_long AND close > previous-period pivot R1 AND close >
  Bollinger(20,2) mid.  Short = mirror (st_dir -1, RSI <= rsi_short,
  close < S1, close < mid).  Every parameter is configurable.
- "rsi": RSI(14) crossing above rsi_long (default 50) = long; below
  rsi_short = short.
- "ema": EMA(fast) crossing above EMA(slow) = long; below = short.
  `candles_held` counts bars since the cross.

Trade tracking to the scan end: entry = signal candle close; initial
stop = Supertrend line at the signal (ema mode: the slow EMA); the
stop trails with the line each bar while the trade stays valid; exit
= first close through the trailing stop (long) / above it (short), or
the trend flip.  P&L % is entry -> last close (or exit price).
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from .indicators import bollinger, ema, pivots, rsi, supertrend

MODES = ("full", "rsi", "ema")

DEFAULT_PARAMS = {
    "full": {"st_period": 10, "st_mult": 3.0, "rsi_period": 14,
             "rsi_long": 55.0, "rsi_short": 45.0, "bb_period": 20,
             "bb_std": 2.0},
    "rsi": {"rsi_period": 14, "rsi_long": 50.0, "rsi_short": 50.0},
    "ema": {"fast": 10, "slow": 30},
}


def merge_params(mode: str, overrides: dict | None) -> dict:
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; one of {MODES}")
    params = dict(DEFAULT_PARAMS[mode])
    params.update({k: v for k, v in (overrides or {}).items()
                   if k in params})
    return params


def _with_indicators(df: pd.DataFrame, mode: str,
                     params: dict) -> pd.DataFrame:
    out = df.copy()
    if mode == "full":
        st = supertrend(out, params["st_period"], params["st_mult"])
        out = out.join(st[["st", "st_dir"]])
        out["rsi"] = rsi(out["close"], params["rsi_period"])
        out = out.join(bollinger(out["close"], params["bb_period"],
                                 params["bb_std"]))
        prev = out[["high", "low", "close"]].shift(1)
        out = out.join(pivots(prev["high"], prev["low"], prev["close"],
                              shift=0))
    elif mode == "rsi":
        out["rsi"] = rsi(out["close"], params["rsi_period"])
        # Supertrend doubles as the trailing-stop line in rsi mode.
        st = supertrend(out, 10, 3.0)
        out = out.join(st[["st", "st_dir"]])
    else:
        out["ema_fast"] = ema(out["close"], params["fast"])
        out["ema_slow"] = ema(out["close"], params["slow"])
    return out


def _signals_and_trades(symbol: str, ind: pd.DataFrame, mode: str,
                        params: dict) -> list[dict]:
    long_raw, short_raw = _raw_conditions(ind, mode, params)
    rows = []
    open_side = None
    open_entry = open_stop = None
    open_ts = None
    stop_series = _stop_line(ind, mode)

    def close_trade(ts, price, exit_reason):
        nonlocal open_side
        pnl = ((price - open_entry) / open_entry * 100.0
               if open_side == "long" else
               (open_entry - price) / open_entry * 100.0)
        rows.append({
            "symbol": symbol, "side": open_side,
            "entry_ts": open_ts, "entry": round(open_entry, 2),
            "exit_ts": ts, "exit_price": round(price, 2),
            "status": "exited", "pnl_pct": round(pnl, 2),
            "stop_initial": round(open_stop, 2),
            "exit_reason": exit_reason,
        })
        open_side = None

    for i in range(len(ind)):
        ts = ind.index[i]
        close = ind["close"].iloc[i]
        long_now = bool(long_raw.iloc[i]) if not pd.isna(long_raw.iloc[i]) \
            else False
        short_now = bool(short_raw.iloc[i]) if not pd.isna(
            short_raw.iloc[i]) else False
        stop = stop_series.iloc[i]

        # manage the open trade first
        if open_side == "long":
            if stop == stop and open_side == "long":
                open_stop = max(open_stop, stop)  # trail up only
            if close < open_stop:
                close_trade(ts, open_stop, "trailing stop")
            elif mode == "ema" and short_raw.iloc[i]:
                close_trade(ts, close, "opposite cross")
        elif open_side == "short":
            if stop == stop:
                open_stop = min(open_stop, stop)  # trail down only
            if close > open_stop:
                close_trade(ts, open_stop, "trailing stop")
            elif mode == "ema" and long_raw.iloc[i]:
                close_trade(ts, close, "opposite cross")

        # fresh signal only when flat and conditions newly true
        if open_side is None:
            prev_long = bool(long_raw.iloc[i - 1]) if i > 0 and not pd.isna(
                long_raw.iloc[i - 1]) else False
            prev_short = bool(short_raw.iloc[i - 1]) if i > 0 and not \
                pd.isna(short_raw.iloc[i - 1]) else False
            for side, now, prev in (("long", long_now, prev_long),
                                    ("short", short_now, prev_short)):
                if now and not prev:
                    entry = close
                    init_stop = stop if stop == stop else entry
                    if side == "short" and stop == stop:
                        init_stop = stop
                    open_side, open_entry, open_stop, open_ts = \
                        side, entry, init_stop, ts
                    rows.append({
                        "symbol": symbol, "side": side,
                        "entry_ts": ts, "entry": round(entry, 2),
                        "exit_ts": None, "exit_price": None,
                        "status": "open", "pnl_pct": None,
                        "stop_initial": round(init_stop, 2),
                        "exit_reason": None,
                    })
                    break

    # close any trade still open at the last bar: report as open with
    # trailing stop and running P&L
    if open_side is not None:
        last = ind.index[-1]
        last_close = ind["close"].iloc[-1]
        running = ((last_close - open_entry) / open_entry * 100.0
                   if open_side == "long" else
                   (open_entry - last_close) / open_entry * 100.0)
        for r in rows:
            if r["symbol"] == symbol and r["status"] == "open":
                r["pnl_pct"] = round(running, 2)
                r["stop_current"] = round(open_stop, 2)
                r["last_close"] = round(last_close, 2)
                r["last_ts"] = last
    # dedupe: keep signal rows (status open) and exit rows; a signal
    # row that later got an exit becomes the exit row's counterpart
    return _merge_rows(rows, symbol)


def _merge_rows(rows: list[dict], symbol: str) -> list[dict]:
    """Collapse open+exited pairs into one row per trade."""
    out: list[dict] = []
    pending = None
    for r in rows:
        if r["status"] == "open":
            if pending is not None:
                out.append(pending)
            pending = r
        else:
            if pending is not None:
                merged = pending | {
                    "exit_ts": r["exit_ts"],
                    "exit_price": r["exit_price"],
                    "status": "exited",
                    "pnl_pct": r["pnl_pct"],
                    "exit_reason": r["exit_reason"],
                }
                out.append(merged)
                pending = None
            else:
                out.append(r)
    if pending is not None:
        out.append(pending)
    return out


def _raw_conditions(ind: pd.DataFrame, mode: str,
                    params: dict) -> tuple[pd.Series, pd.Series]:
    if mode == "full":
        long = ((ind["st_dir"] == 1) & (ind["rsi"] >= params["rsi_long"])
                & (ind["close"] > ind["pivot_r1"])
                & (ind["close"] > ind["bb_mid"]))
        short = ((ind["st_dir"] == -1) & (ind["rsi"] <= params["rsi_short"])
                 & (ind["close"] < ind["pivot_s1"])
                 & (ind["close"] < ind["bb_mid"]))
        return long, short
    if mode == "rsi":
        long = (ind["rsi"] >= params["rsi_long"]) & (
            ind["rsi"].shift(1) < params["rsi_long"])
        short = (ind["rsi"] <= params["rsi_short"]) & (
            ind["rsi"].shift(1) > params["rsi_short"])
        return long, short
    cross_up = (ind["ema_fast"] > ind["ema_slow"]) & (
        ind["ema_fast"].shift(1) <= ind["ema_slow"].shift(1))
    cross_dn = (ind["ema_fast"] < ind["ema_slow"]) & (
        ind["ema_fast"].shift(1) >= ind["ema_slow"].shift(1))
    return cross_up, cross_dn


def _stop_line(ind: pd.DataFrame, mode: str) -> pd.Series:
    if mode == "ema":
        return ind["ema_slow"]
    return ind["st"]


def _indicator_row(ind: pd.DataFrame, mode: str, ts) -> dict:
    row = ind.loc[ts]
    out = {}
    if mode == "full":
        out.update({"rsi": round(row["rsi"], 2) if pd.notna(row["rsi"])
                    else None,
                    "pivot_r1": round(row["pivot_r1"], 2)
                    if pd.notna(row["pivot_r1"]) else None,
                    "pivot_s1": round(row["pivot_s1"], 2)
                    if pd.notna(row["pivot_s1"]) else None})
    elif mode == "rsi":
        out["rsi"] = round(row["rsi"], 2) if pd.notna(row["rsi"]) else None
    else:
        out.update({"ema_fast": round(row["ema_fast"], 2),
                    "ema_slow": round(row["ema_slow"], 2)})
    return out


def scan_symbol(symbol: str, df: pd.DataFrame, mode: str = "full",
                overrides: dict | None = None) -> list[dict]:
    """Return one row per trade (open trades carry stop_current, pnl)."""
    params = merge_params(mode, overrides)
    ind = _with_indicators(df, mode, params)
    trades = _signals_and_trades(symbol, ind, mode, params)
    stop_line = _stop_line(ind, mode)
    for t in trades:
        entry_row = ind.loc[t["entry_ts"]]
        t["volume"] = int(entry_row["volume"]) if "volume" in ind else None
        t["change_pct"] = None
        t.update(_indicator_row(ind, mode, t["entry_ts"]))
        if mode in ("full", "rsi"):
            t["stop_initial"] = t["stop_initial"]
        if mode == "ema":
            held = len(ind.loc[t["entry_ts"]:])
            t["candles_held"] = held - 1
        # trailing stop & risk at entry
        stop0 = stop_line.loc[t["entry_ts"]]
        if stop0 == stop0:
            t["risk_pct"] = round(
                abs(t["entry"] - stop0) / t["entry"] * 100.0, 2)
        else:
            t["risk_pct"] = None
        last_close = ind["close"].iloc[-1]
        if t["status"] == "open":
            t["change_pct"] = round(
                ((last_close - t["entry"]) / t["entry"] * 100.0)
                if t["side"] == "long" else
                ((t["entry"] - last_close) / t["entry"] * 100.0), 2)
        elif t["exit_ts"] is not None:
            exit_close = ind["close"].iloc[-1] if t["exit_ts"] == \
                ind.index[-1] else t["exit_price"]
            t["change_pct"] = round(
                ((exit_close - t["entry"]) / t["entry"] * 100.0)
                if t["side"] == "long" else
                ((t["entry"] - exit_close) / t["entry"] * 100.0), 2)
        t["mode"] = mode
    return trades


def run_scan(data: dict[str, pd.DataFrame], mode: str = "full",
             overrides: dict | None = None) -> dict:
    """Scan a prepared universe.  Returns {signals, params, meta}."""
    params = merge_params(mode, overrides)
    signals: list[dict] = []
    failed: dict[str, str] = {}
    for symbol, df in data.items():
        try:
            signals.extend(scan_symbol(symbol, df, mode, overrides))
        except Exception as exc:  # noqa: BLE001 - report, keep scanning
            failed[symbol] = str(exc)
    signals.sort(key=lambda r: (r["entry_ts"], r["symbol"]))
    return {"signals": signals, "params": params, "mode": mode,
            "scanned": len(data), "failed": failed,
            "generated": dt.datetime.now(dt.UTC)
            .strftime("%Y-%m-%d %H:%M UTC")}
