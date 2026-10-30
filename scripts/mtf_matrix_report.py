"""Live EMA 9/21 multi-timeframe Heikin-Ashi trend matrix.

Builds the screenshot-style matrix for a universe on CLOSED candles
(the repo convention): for every timeframe the running bar, if any, is
split off and shown only as a provisional reading.  Output is a
markdown table (the screenshot's layout) saved under reports/.

Definitions are frozen in sbc/screener/mtf_matrix.py (module docstring);
the gap analysis is reports/mtf_ema_matrix_gap_analysis_2026-10-27.md.

Examples:
    python scripts/mtf_matrix_report.py
    python scripts/mtf_matrix_report.py --universe nifty50 --out reports/mtf_matrix_today.md
"""

import argparse
import datetime as dt
import os
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from sbc.screener import data as screener_data  # noqa: E402
from sbc.screener.indicators import heikin_ashi  # noqa: E402
from sbc.screener.mtf_matrix import (  # noqa: E402
    MATRIX_TIMEFRAMES,
    compute_matrix,
    to_markdown,
)
from sbc.screener.universes import load  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")
BAR_MINUTES = {"5m": 5, "10m": 10, "15m": 15, "30m": 30, "1h": 60}


def split_closed(df: pd.DataFrame, timeframe: str,
                 now: dt.datetime) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """(closed bars, running bar or None) for one downloaded frame."""
    if df is None or df.empty:
        return df, None
    ts = pd.to_datetime(df.index)
    if timeframe in BAR_MINUTES:
        # Yahoo stamps intraday bars at their START.
        end = ts + pd.Timedelta(minutes=BAR_MINUTES[timeframe])
        cutoff = pd.Timestamp(now.astimezone(ZoneInfo("UTC")).replace(tzinfo=None))
        running_mask = np.asarray(end > cutoff)
    elif timeframe == "1d":
        # today's daily bar is provisional until the 15:30 close settles
        # (16:00 gives the same margin the market store uses).
        today = now.date()
        running_mask = np.asarray(
            [t.date() == today and now.time() < dt.time(16, 0) for t in ts])
    else:  # 1wk: the bar of the still-open ISO week is provisional
        cur_week = now.isocalendar()[:2]
        running_mask = np.asarray(
            [t.isocalendar()[:2] == cur_week
             and not (t.date().isoweekday() == 5
                      and now.time() >= dt.time(16, 0))
             for t in ts])
    if len(running_mask) == 0 or not running_mask[-1]:
        return df, None
    return df.iloc[:-1], df.iloc[[-1]]


def _resample_10m(df: pd.DataFrame) -> pd.DataFrame:
    """10-minute bars from 5-minute bars (yfinance has no native 10m)."""
    if df is None or df.empty:
        return df
    out = df.resample("10min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last",
         "volume": "sum"}).dropna(subset=["open", "high", "low", "close"])
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--universe", default="NIFTY 50")
    parser.add_argument("--timeframes", default=",".join(MATRIX_TIMEFRAMES))
    parser.add_argument("--out", default=None,
                        help="markdown output path (default reports/)")
    parser.add_argument("--fast", type=int, default=9)
    parser.add_argument("--slow", type=int, default=21)
    args = parser.parse_args()

    symbols = load(args.universe)
    timeframes = tuple(t for t in args.timeframes.split(",") if t)
    now = dt.datetime.now(IST)
    print(f"universe {args.universe}: {len(symbols)} symbols; "
          f"timeframes {', '.join(timeframes)}; as of "
          f"{now:%Y-%m-%d %H:%M} IST (closed candles only)")

    data_by_tf: dict[str, dict[str, pd.DataFrame]] = {}
    provisional_by_tf: dict[str, dict[str, pd.DataFrame]] = {}
    errors: dict[str, str] = {}
    resampled_from: dict[str, str] = {}
    for tf in timeframes:
        if tf == "10m":
            # yfinance serves no native 10m interval; build it from 5m.
            raw, errs = screener_data.batch(symbols, "5m", as_ha=False)
            errors.update({f"5m:{k}": v for k, v in errs.items()})
            raw = {sym: _resample_10m(df) for sym, df in raw.items()}
            resampled_from["10m"] = "5m"
        else:
            raw, errs = screener_data.batch(symbols, tf, as_ha=False)
            errors.update({f"{tf}:{k}": v for k, v in errs.items()})
        closed_map, prov_map = {}, {}
        for sym, df in raw.items():
            closed, running = split_closed(df, tf, now)
            if closed is not None and len(closed):
                closed_map[sym] = heikin_ashi(closed)
            if running is not None and len(running):
                prov_map[sym] = running
        data_by_tf[tf] = closed_map
        if prov_map:
            provisional_by_tf[tf] = prov_map
        print(f"  {tf}: {len(closed_map)} symbols with closed bars, "
              f"{len(prov_map)} with a running bar")

    rows = compute_matrix(data_by_tf, fast=args.fast, slow=args.slow,
                          timeframes=timeframes)
    # attach provisional readings per symbol
    for r in rows:
        prov_frames = {tf: provisional_by_tf[tf][r["symbol"]]
                       for tf in provisional_by_tf
                       if r["symbol"] in provisional_by_tf[tf]}
        if prov_frames:
            from sbc.screener.mtf_matrix import symbol_matrix
            merged = symbol_matrix(
                {tf: df for tf, df in
                 ((tf, data_by_tf[tf].get(r["symbol"]))
                  for tf in data_by_tf) if df is not None},
                provisional=prov_frames, fast=args.fast, slow=args.slow,
                timeframes=timeframes)
            r["provisional"] = merged.get("provisional")

    bias_counts: dict[str, int] = {}
    for r in rows:
        bias_counts[r["bias"]] = bias_counts.get(r["bias"], 0) + 1

    body = to_markdown(rows, timeframes)
    prov_lines = []
    for r in rows:
        prov = r.get("provisional") or {}
        if prov:
            txt = ", ".join(f"{tf}:{state}" for tf, state in prov.items()
                            if state)
            if txt:
                prov_lines.append(f"- {r['symbol']} (provisional running "
                                  f"bar): {txt}")
    head = (f"# EMA {args.fast}/{args.slow} multi-timeframe trend matrix "
            f"(Heikin Ashi, closed candles)\n\nAs of "
            f"{now:%Y-%m-%d %H:%M} IST | universe {args.universe} "
            f"({len(rows)} symbols) | running bars shown separately below, "
            f"never in the state.\n\n"
            + ("".join(f"Note: {' and '.join(f'{k} resampled from {v}' for k, v in resampled_from.items())} "
                       f"(yfinance serves no native interval).\n\n" if resampled_from else ""))
            + f"Bias rule (frozen): >= 6/7 bullish = "
              f"Strong Bullish, > 1/2 = Bullish, == 1/2 = Mixed, mirrored "
              f"for bearish; Weak = HA close not beyond both EMAs; "
              f"up/down arrows = crossed on the latest closed candle.\n\n")
    tail = "\n## Bias distribution\n\n" + ", ".join(
        f"{k}: {v}" for k, v in sorted(bias_counts.items(),
                                       key=lambda kv: -kv[1])) + "\n"
    if errors:
        tail += ("\n## Download errors\n\n"
                 + "; ".join(f"{k}: {v}" for k, v in
                             sorted(errors.items())[:12]) + "\n")
    out = args.out or os.path.join(
        "reports", f"mtf_matrix_{dt.date.today().isoformat()}.md")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(head + body)
        if prov_lines:
            fh.write("\n## Provisional running-bar readings\n\n"
                     + "\n".join(prov_lines) + "\n")
        fh.write(tail)
    print(f"saved: {out}")
    print(body.splitlines()[2] if len(body.splitlines()) > 2 else "")


if __name__ == "__main__":
    main()
