"""Validate the predictive intraday path against historical NIFTY intraday data."""
import argparse
import json
import os
import sys
import tempfile
import time
from datetime import date as dtdate
from datetime import timedelta

sys.path.append(".")

import numpy as np
import pandas as pd
import yfinance as yf

os.environ.setdefault("SBC_SERIES_CACHE_DB",
                      os.path.join(tempfile.gettempdir(), "sbc_validate_series_cache.db"))

from app import app  # noqa: E402

REPORT_MD = "docs/INTRADAY_PATH_VALIDATION.md"
REPORT_CSV = "data/output/intraday_path_validation.csv"


def fetch_intraday(start: str, end: str) -> pd.DataFrame:
    df = yf.download("^NSEI", start=start, end=end, interval="5m",
                     progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if df.empty:
        raise SystemExit("No yfinance intraday data for the requested range")
    return df


def collect_paths(dates):
    client = app.test_client()
    paths = {}
    for d in dates:
        resp = client.get(f"/api/engine/intraday_path?date={d}&instrument=NIFTY")
        if resp.status_code == 429:
            time.sleep(2)
            resp = client.get(f"/api/engine/intraday_path?date={d}&instrument=NIFTY")
        if resp.status_code != 200:
            print(f"  skip {d}: HTTP {resp.status_code}")
            continue
        paths[d] = json.loads(resp.data)
    return paths


def window_move(bars: pd.DataFrame, t0: str, t1: str):
    b = bars.between_time(t0, t1, inclusive="left")
    if b.empty:
        return None
    return float(b["Close"].iloc[-1] - b["Open"].iloc[0])


def sign(x):
    return 1 if x > 0 else (-1 if x < 0 else 0)


def pearson(x, y):
    if len(x) < 2:
        return None
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if np.std(x) == 0 or np.std(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def hit_rate(scores, returns):
    pairs = [(s, r) for s, r in zip(scores, returns) if s != 0 and r != 0]
    if not pairs:
        return None, 0
    hits = sum(1 for s, r in pairs if sign(s) == sign(r))
    return hits / len(pairs), len(pairs)


def validate_day(day: str, path: dict, bars: pd.DataFrame):
    series = path.get("series", [])
    if not series:
        return None
    times = [s["time"] for s in series]
    scores, cum_deltas, returns, rows = [], [], [], []
    cum_prev = 0.0
    for i, s in enumerate(series):
        t0 = times[i]
        t1 = times[i + 1] if i + 1 < len(times) else "15:30"
        move = window_move(bars, t0, t1)
        if move is None:
            continue
        open0 = bars.between_time(t0, t1, inclusive="left")["Open"].iloc[0]
        ret = (move / open0) * 100.0
        cum_delta = s["cumulative"] - cum_prev
        scores.append(s["score"])
        cum_deltas.append(cum_delta)
        cum_prev = s["cumulative"]
        returns.append(ret)
        rows.append({
            "date": day, "time": t0, "score": s["score"],
            "cumulative_delta": round(cum_delta, 4),
            "return_pct": round(ret, 4),
            "hora_lord": s.get("hora_lord"),
            "dl_hora": s.get("dl_hora"), "dahan": s.get("dahan"),
            "chand_vat": s.get("chand_vat"),
        })

    day_open = bars["Open"].iloc[0]
    day_ret = float(bars["Close"].iloc[-1] - day_open)
    day_hit = None
    final_cum = None
    if series:
        final_cum = series[-1]["cumulative"]
        if final_cum != 0 and day_ret != 0:
            day_hit = sign(final_cum) == sign(day_ret)

    r_score = pearson(scores, returns)
    r_cum = pearson(cum_deltas, returns)
    sr, n_score = hit_rate(scores, returns)
    cr, n_cum = hit_rate(cum_deltas, returns)

    regime = []
    for rs in path.get("regime_shifts", []):
        t0 = rs["time"]
        h, m = map(int, t0.split(":"))
        t1_dt = (dtdate(2000, 1, 1)
                 + timedelta(hours=h, minutes=m) + timedelta(minutes=60))
        cap = dtdate(2000, 1, 1) + timedelta(hours=15, minutes=30)
        t1 = min(t1_dt, cap).strftime("%H:%M")
        move = window_move(bars, t0, t1)
        if move is None or move == 0:
            continue
        direction = (rs.get("direction") or "").upper()
        if direction == "NEUTRAL":
            continue
        expected = 1 if direction == "BULLISH" else -1
        regime.append(sign(move) == expected)

    strongest = {"bullish": None, "bearish": None}
    for key in ("strongest_bullish", "strongest_bearish"):
        w = path.get(key)
        if not w:
            continue
        move = window_move(bars, w["start"], w["end"])
        if move is None or move == 0:
            continue
        expected = 1 if key == "strongest_bullish" else -1
        strongest["bullish" if key == "strongest_bullish" else "bearish"] = \
            sign(move) == expected

    return {
        "day": day,
        "rows": rows,
        "r_score_return": r_score,
        "r_cumdelta_return": r_cum,
        "score_hit_rate": sr,
        "score_windows": n_score,
        "cumdelta_hit_rate": cr,
        "cumdelta_windows": n_cum,
        "day_direction_hit": day_hit,
        "final_cumulative": final_cum,
        "day_return_pct": round(day_ret, 2),
        "regime_hits": sum(regime),
        "regime_total": len(regime),
        "strongest_bullish_hit": strongest["bullish"],
        "strongest_bearish_hit": strongest["bearish"],
    }


def fmt_rate(rate):
    return f"{rate * 100:.1f}%" if rate is not None else "n/a"


def fmt_corr(r):
    return f"{r:+.3f}" if r is not None else "n/a"


def fmt_bool(v):
    if v is None:
        return "n/a"
    return "yes" if v else "no"


def write_reports(results, period):
    pooled_scores, pooled_returns = [], []
    for res in results:
        for row in res["rows"]:
            pooled_scores.append(row["score"])
            pooled_returns.append(row["return_pct"])
    pooled_r = pearson(pooled_scores, pooled_returns)
    pooled_sr, pooled_n = hit_rate(pooled_scores, pooled_returns)

    regime_hits = sum(r["regime_hits"] for r in results)
    regime_total = sum(r["regime_total"] for r in results)
    day_hits = sum(1 for r in results if r["day_direction_hit"])
    day_eval = sum(1 for r in results if r["day_direction_hit"] is not None)
    bull_hits = sum(1 for r in results if r["strongest_bullish_hit"])
    bull_total = sum(1 for r in results if r["strongest_bullish_hit"] is not None)
    bear_hits = sum(1 for r in results if r["strongest_bearish_hit"])
    bear_total = sum(1 for r in results if r["strongest_bearish_hit"] is not None)

    # Chance baseline for the day-direction hit: a model that calls bearish on
    # a share q of days, in a period with a share p of down days, hits
    # q*p + (1-q)*(1-p) of the time with no skill at all.
    called = [r for r in results if r["day_direction_hit"] is not None]
    q = sum(1 for r in called if r["final_cumulative"] < 0) / len(called) if called else 0
    p = sum(1 for r in called if r["day_return_pct"] < 0) / len(called) if called else 0
    day_baseline = q * p + (1 - q) * (1 - p)

    r_scores = [r["r_score_return"] for r in results if r["r_score_return"] is not None]
    mean_r = float(np.mean(r_scores)) if r_scores else None

    lines = [
        "# Predictive Intraday Path – Historical Validation",
        "",
        f"Period: {period}  |  Days evaluated: {len(results)}",
        "",
        "Model: `/api/engine/intraday_path` hourly series vs NIFTY 5m bars (^NSEI, yfinance).",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Mean per-day corr (score vs hourly return) | {fmt_corr(mean_r)} |",
        f"| Pooled corr (score vs hourly return) | {fmt_corr(pooled_r)} |",
        f"| Pooled score direction hit rate | {fmt_rate(pooled_sr)} ({pooled_n} windows) |",
        f"| Regime-shift direction hit rate | {fmt_rate(regime_hits / regime_total if regime_total else None)} ({regime_total} shifts) |",
        f"| Day-direction hit (final cumulative vs day range) | {day_hits}/{day_eval} |",
        f"| ↳ chance baseline (model bearish {q:.0%} of days, market down {p:.0%}) | {fmt_rate(day_baseline)} |",
        f"| Strongest bullish window hit | {bull_hits}/{bull_total} |",
        f"| Strongest bearish window hit | {bear_hits}/{bear_total} |",
        "",
        "## Per-Day Detail",
        "",
        "| Date | r(score,ret) | score hit | day dir | day ret % | regime hit | bull win | bear win |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for res in results:
        lines.append(
            f"| {res['day']} | {fmt_corr(res['r_score_return'])} "
            f"| {fmt_rate(res['score_hit_rate'])} "
            f"| {fmt_bool(res['day_direction_hit'])} | {res['day_return_pct']:+.2f} "
            f"| {res['regime_hits']}/{res['regime_total']} "
            f"| {fmt_bool(res['strongest_bullish_hit'])} "
            f"| {fmt_bool(res['strongest_bearish_hit'])} |"
        )
    lines += [
        "",
        "Note: correlation and hit rates on hourly buckets are noisy (7 points/day); "
        "treat pooled metrics as the primary signal.",
        "",
    ]
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    all_rows = [row for res in results for row in res["rows"]]
    pd.DataFrame(all_rows).to_csv(REPORT_CSV, index=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2026-08-03")
    ap.add_argument("--end", default="2026-09-16")
    args = ap.parse_args()

    print("Fetching NIFTY 5m bars from yfinance...")
    df = fetch_intraday(args.start, args.end)
    days = sorted({d.isoformat() for d in df.index.date})
    print(f"  {len(df)} bars, {len(days)} trading days: {days[0]}..{days[-1]}")

    print("Generating intraday paths (KP + engine)...")
    paths = collect_paths(days)
    print(f"  {len(paths)} paths generated")

    results = []
    for day in days:
        if day not in paths:
            continue
        bars = df[df.index.date == dtdate.fromisoformat(day)]
        res = validate_day(day, paths[day], bars)
        if res:
            results.append(res)

    period = f"{days[0]} to {days[-1]}"
    write_reports(results, period)
    print(f"Wrote {REPORT_MD} and {REPORT_CSV}")


if __name__ == "__main__":
    main()
