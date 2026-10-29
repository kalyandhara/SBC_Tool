"""Momentum screener Excel report: Long / Short / Scorecard / Params."""

from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

_HEADER_FILL = PatternFill("solid", fgColor="1F2937")
_HEADER_FONT = Font(bold=True, color="FFFFFF")

_LONG_COLS = [
    ("Symbol", "symbol"), ("First signal", "entry_ts"),
    ("Entry", "entry"), ("% change", "change_pct"), ("Volume", "volume"),
    ("RSI", "rsi"), ("Initial SL", "stop_initial"), ("Risk %", "risk_pct"),
    ("Pivot R1", "pivot_r1"), ("Trailing SL", "stop_current"),
    ("Status", "status"), ("Exit time", "exit_ts"),
    ("Exit price", "exit_price"), ("Exit reason", "exit_reason"),
    ("P&L %", "pnl_pct"),
]
_SHORT_COLS = [
    ("Symbol", "symbol"), ("First signal", "entry_ts"),
    ("Entry", "entry"), ("% change", "change_pct"), ("Volume", "volume"),
    ("RSI", "rsi"), ("Initial SL", "stop_initial"), ("Risk %", "risk_pct"),
    ("Pivot S1", "pivot_s1"), ("Trailing SL", "stop_current"),
    ("Status", "status"), ("Exit time", "exit_ts"),
    ("Exit price", "exit_price"), ("Exit reason", "exit_reason"),
    ("P&L %", "pnl_pct"),
]
_EMA_COLS = [
    ("Symbol", "symbol"), ("Side", "side"), ("Signal candle", "entry_ts"),
    ("Entry", "entry"), ("Fast EMA", "ema_fast"), ("Slow EMA", "ema_slow"),
    ("Candles held", "candles_held"), ("Status", "status"),
    ("Trailing SL", "stop_current"), ("Exit time", "exit_ts"),
    ("P&L %", "pnl_pct"),
]


def _fmt_ts(value):
    if value is None:
        return ""
    return str(value)[:19]


def _write_sheet(wb: Workbook, title: str, headers: list[str],
                 rows: list[list], first: bool = False) -> None:
    ws = wb.active if first else wb.create_sheet(title)
    if first:
        ws.title = title
    ws.append(headers)
    for cell in ws[1]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center")
    for row in rows:
        ws.append(row)
    ws.freeze_panes = "A2"
    for idx, header in enumerate(headers, 1):
        width = max(len(header) + 2,
                    *(len(str(r[idx - 1])) + 2 for r in rows)) \
            if rows else len(header) + 2
        ws.column_dimensions[get_column_letter(idx)].width = min(width, 26)


def _rows_for(signals, side, cols):
    out = []
    for s in signals:
        if s.get("side") != side:
            continue
        out.append([_fmt_ts(s.get(key)) if key.endswith(("_ts",))
                    else s.get(key) for _label, key in cols])
    return out


def build_report(scan: dict, meta: dict | None = None) -> tuple[io.BytesIO,
                                                                str]:
    """scan = engine.run_scan(...) output -> (xlsx bytes, filename)."""
    signals = scan.get("signals", [])
    mode = scan.get("mode", "full")
    meta = meta or {}

    wb = Workbook()
    long_cols = _EMA_COLS if mode == "ema" else _LONG_COLS
    short_cols = _EMA_COLS if mode == "ema" else _SHORT_COLS
    _write_sheet(wb, "Long Signals",
                 [label for label, _ in long_cols],
                 _rows_for(signals, "long", long_cols), first=True)
    _write_sheet(wb, "Short Signals",
                 [label for label, _ in short_cols],
                 _rows_for(signals, "short", short_cols))

    # Scorecard: one row per symbol, best open trade metrics
    by_symbol: dict[str, dict] = {}
    for s in signals:
        row = by_symbol.setdefault(s["symbol"], {
            "symbol": s["symbol"], "longs": 0, "shorts": 0,
            "open_longs": 0, "open_shorts": 0, "exited": 0,
            "best_pnl": None, "worst_pnl": None})
        if s["side"] == "long":
            row["longs"] += 1
            if s["status"] == "open":
                row["open_longs"] += 1
        else:
            row["shorts"] += 1
            if s["status"] == "open":
                row["open_shorts"] += 1
        if s["status"] == "exited":
            row["exited"] += 1
        pnl = s.get("pnl_pct")
        if pnl is not None:
            row["best_pnl"] = (pnl if row["best_pnl"] is None
                               else max(row["best_pnl"], pnl))
            row["worst_pnl"] = (pnl if row["worst_pnl"] is None
                                else min(row["worst_pnl"], pnl))
    score_rows = [[r["symbol"], r["longs"], r["shorts"], r["open_longs"],
                   r["open_shorts"], r["exited"],
                   r["best_pnl"] if r["best_pnl"] is not None else "",
                   r["worst_pnl"] if r["worst_pnl"] is not None else ""]
                  for r in sorted(by_symbol.values(),
                                  key=lambda x: x["symbol"])]
    _write_sheet(wb, "Scorecard",
                 ["Symbol", "Long signals", "Short signals", "Open longs",
                  "Open shorts", "Exited", "Best P&L %", "Worst P&L %"],
                 score_rows)

    params = scan.get("params", {})
    info = [
        ["Mode", mode],
        ["Generated", scan.get("generated", "")],
        ["Symbols scanned", scan.get("scanned", 0)],
        ["Errors", ", ".join(f"{k}: {v}" for k, v in
                             sorted(scan.get("failed", {}).items()))
         or "none"],
        ["Universe", meta.get("universe", "")],
        ["Timeframe", meta.get("timeframe", "")],
        ["Scan date", meta.get("scan_date", "")],
        ["Heikin Ashi", "yes" if meta.get("as_ha") else "no"],
        ["", ""],
        ["Parameters", ""],
    ] + [[f"  {k}", v] for k, v in params.items()]
    _write_sheet(wb, "Params", ["Item", "Value"], info)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    stamp = dt_stamp()
    name = f"nse_momentum_{mode}_{stamp}.xlsx"
    return buf, name


def dt_stamp() -> str:
    import datetime as dtm
    return dtm.date.today().isoformat()
