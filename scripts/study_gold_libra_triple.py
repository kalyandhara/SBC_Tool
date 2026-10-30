"""COMEX gold during Sun+Mercury+Venus triple conjunction in sidereal Libra.

Backtests the "When Sun, Mercury and Venus are together in Libra" COMEX
gold table (12 completed periods 2001-2022, 2026 ongoing):

1. Independent ephemeris scan (Swiss Ephemeris Moshier, sidereal Lahiri,
   same pipeline as sbc.transits) of every period in which all three
   planets occupy sidereal Libra, 2000-2035.  This includes the years the
   shared table omits (2004, 2005, 2007, 2008, ...) - the honest sample -
   and every upcoming recurrence (2026, 2027, 2030, 2033, ...).
2. Verification of the image rows against cached GC=F OHLC using the
   repo convention: open = first trading day on/after window start,
   close = last trading day on/before window end.
3. Statistics for the curated image sample vs the full ephemeris sample,
   plus a random-window bootstrap significance test.
4. Crash coverage: overlap of windows with named crash regimes,
   intra-window adverse excursion, and forward returns after windows.
5. Status of the ongoing 2026 window, current market context, and the
   repo crash-window tool's read of every upcoming window.

Example:
    python scripts/study_gold_libra_triple.py
"""

import argparse
import datetime
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc import crash_windows  # noqa: E402
from sbc.market_data import get_ohlc  # noqa: E402
from sbc.transits import (  # noqa: E402
    _bisect,
    _from_jd,
    _planet_lon,
    _scan,
)

LIBRA = 6
PLANETS = ["Sun", "Mercury", "Venus"]
IST_OFFSET = datetime.timedelta(hours=5, minutes=30)
RNG_SEED = 42
BOOTSTRAP_ITERS = 10_000

# Rows transcribed from the shared infographic (year, start, end,
# image_open, image_close, image_return_pct).
IMAGE_TABLE = [
    (2001, "2001-11-04", "2001-11-16", 280.00, 274.90, -1.82),
    (2002, "2002-10-29", "2002-11-15", 315.70, 320.90, 1.65),
    (2003, "2003-10-21", "2003-10-29", 374.30, 387.00, 3.39),
    (2006, "2006-10-20", "2006-10-24", 601.80, 587.60, -2.36),
    (2006, "2006-11-02", "2006-11-12", 620.40, 630.10, 1.56),
    (2009, "2009-11-04", "2009-11-12", 1085.60, 1106.60, 1.93),
    (2010, "2010-10-18", "2010-11-05", 1371.00, 1397.70, 1.95),
    (2011, "2011-10-18", "2011-10-28", 1672.50, 1747.20, 4.47),
    (2014, "2014-11-05", "2014-11-12", 1168.40, 1159.10, -0.80),
    (2018, "2018-10-18", "2018-10-26", 1225.50, 1235.80, 0.84),
    (2019, "2019-10-18", "2019-10-23", 1495.60, 1495.70, 0.01),
    (2022, "2022-10-27", "2022-11-11", 1668.80, 1769.40, 6.03),
]

# Named crash / stress regimes (gold- or equity-driven) used to test
# whether the conjunction sample actually touches crash conditions.
CRASH_REGIMES = [
    ("Dot-com bust", "2000-09-01", "2002-10-09"),
    ("2008 GFC", "2007-10-09", "2009-03-09"),
    ("2011 gold blow-off top", "2011-09-01", "2011-12-31"),
    ("2013 gold crash (taper)", "2013-04-01", "2013-12-31"),
    ("2020 COVID crash", "2020-02-19", "2020-03-23"),
    ("2022 rate shock", "2022-01-01", "2022-11-10"),
    ("2025 Oct gold correction", "2025-10-01", "2025-11-30"),
    ("2026 Oct pullback", "2026-09-15", "2026-11-10"),
]


def triple_libra_periods(start_date, end_date):
    """Periods where Sun, Mercury and Venus all sit in sidereal Libra.

    Same flip/bisect logic as sbc.transits.same_sign_periods, extended to
    three bodies pinned to one target sign.
    """

    def state(jd):
        signs = {int(_planet_lon(jd, p) // 30) for p in PLANETS}
        return LIBRA if signs == {LIBRA} else -1

    scan = _scan(PLANETS, start_date, end_date)
    periods = []
    start_jd = None
    prev_jd = scan[0][0]
    prev_state = state(prev_jd)
    if prev_state >= 0:
        start_jd = prev_jd
    for jd, _lons in scan[1:]:
        s = state(jd)
        if s != prev_state:
            flip = _bisect(prev_jd, jd, state, prev_state)
            if prev_state >= 0:
                periods.append((start_jd, flip))
            start_jd = flip if s >= 0 else None
            prev_state = s
        prev_jd = jd
    if prev_state >= 0 and start_jd is not None:
        periods.append((start_jd, scan[-1][0]))

    out = []
    for a, b in periods:
        utc_a, utc_b = _from_jd(a), _from_jd(b)
        out.append({
            "start": (utc_a + IST_OFFSET).date().isoformat(),
            "end": (utc_b + IST_OFFSET).date().isoformat(),
            "start_utc": utc_a.date().isoformat(),
            "end_utc": utc_b.date().isoformat(),
            "days": round(b - a, 1),
        })
    return out


def open_on_or_after(rows, d):
    for r in rows:
        if r["time"] >= d:
            return r
    return None


def close_on_or_before(rows, d):
    result = None
    for r in rows:
        if r["time"] > d:
            break
        result = r
    return result


def study_window(rows, dstart, dend):
    """Repo convention: first open on/after start, last close on/before end."""
    first = open_on_or_after(rows, dstart)
    last = close_on_or_before(rows, dend)
    if first is None or last is None or first["time"] > last["time"]:
        return None
    idx = next(i for i, r in enumerate(rows) if r["time"] == last["time"])
    fidx = next(i for i, r in enumerate(rows) if r["time"] == first["time"])
    seg = rows[fidx:idx + 1]
    entry = first["open"]
    hi52 = max(r["close"] for r in rows[max(0, fidx - 252):fidx + 1])
    move = (last["close"] - entry) / entry * 100.0
    worst_low = min(r["low"] for r in seg)
    best_high = max(r["high"] for r in seg)
    peak, mdd = -1e9, 0.0
    for r in seg:
        peak = max(peak, r["close"])
        mdd = min(mdd, (r["close"] - peak) / peak * 100.0)
    fwd5 = fwd21 = None
    if idx + 5 < len(rows):
        fwd5 = (rows[idx + 5]["close"] - last["close"]) / last["close"] * 100.0
    if idx + 21 < len(rows):
        fwd21 = (rows[idx + 21]["close"] - last["close"]) / last["close"] * 100.0
    return {
        "first": first["time"], "last": last["time"],
        "entry": entry, "exit": last["close"], "move": move,
        "dd_entry": (entry - hi52) / hi52 * 100.0,
        "mae": (worst_low - entry) / entry * 100.0,
        "mfe": (best_high - entry) / entry * 100.0,
        "mdd": mdd, "fwd5": fwd5, "fwd21": fwd21,
    }


def stats(moves):
    arr = np.asarray(moves, dtype=float)
    n = len(arr)
    mean = float(arr.mean())
    std = float(arr.std(ddof=1)) if n > 1 else float("nan")
    tstat = mean / (std / np.sqrt(n)) if n > 1 and std > 0 else float("nan")
    return {"n": n, "mean": mean, "median": float(np.median(arr)),
            "std": std, "win": float((arr > 0).mean() * 100.0),
            "worst": float(arr.min()), "best": float(arr.max()),
            "t": float(tstat)}


def bootstrap(rows, lengths, observed_mean, iters=BOOTSTRAP_ITERS, seed=RNG_SEED):
    """Distribution of the mean return of len(lengths) random windows
    with matching trading-day lengths, drawn over the full data span."""
    opens = np.asarray([r["open"] for r in rows])
    closes = np.asarray([r["close"] for r in rows])
    n = len(rows)
    rng = np.random.default_rng(seed)
    means = np.empty(iters)
    lens = np.asarray(lengths)
    for i in range(iters):
        starts = rng.integers(0, n - lens.max(), size=len(lens))
        moves = closes[starts + lens - 1] / opens[starts] - 1.0
        means[i] = moves.mean() * 100.0
    p_le = float((means <= observed_mean).mean())
    return {"random_mean": float(means.mean()),
            "random_p05": float(np.percentile(means, 5)),
            "random_p95": float(np.percentile(means, 95)),
            "p_one_sided": p_le,
            "p_two_sided": float(min(p_le, 1.0 - p_le) * 2.0)}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--save", default=os.path.join("reports",
                        "gold_libra_triple_backtest.md"))
    args = parser.parse_args()

    today = datetime.date.today().isoformat()
    rows = get_ohlc("gold", "2000-01-01", today)
    if not rows:
        raise SystemExit("no gold price data available")
    print(f"gold data: {rows[0]['time']} .. {rows[-1]['time']} "
          f"({len(rows)} sessions)")

    periods = triple_libra_periods(datetime.date(2000, 9, 1),
                                   datetime.date(2035, 12, 31))
    print(f"\nephemeris windows (Sun+Mercury+Venus in sidereal Libra, "
          f"Lahiri): {len(periods)}")

    lines = []
    lines.append("# Gold: Sun+Mercury+Venus in sidereal Libra - backtest")
    lines.append(f"\nGenerated {today}. Data: COMEX GC=F "
                 f"({rows[0]['time']} .. {rows[-1]['time']}).")
    lines.append("Convention: entry = first session open on/after window "
                 "start, exit = last session close on/before window end.")

    # ---- 1. window inventory ------------------------------------------
    lines.append("\n## 1. Ephemeris windows (Lahiri sidereal)\n")
    lines.append("| # | start | end | days | status |")
    lines.append("|---|-------|-----|------|--------|")
    for i, p in enumerate(periods, 1):
        status = ("ongoing" if p["end"] >= today and p["start"] <= today
                  else "upcoming" if p["start"] > today else "completed")
        lines.append(f"| {i} | {p['start']} | {p['end']} | {p['days']} "
                     f"| {status} |")

    # ---- 2. verify the image table ------------------------------------
    lines.append("\n## 2. Image table verification\n")
    lines.append("| year | image window | computed open | image open | "
                 "computed ret % | image ret % | diff pp |")
    lines.append("|------|--------------|---------------|------------|"
                 "----------------|-------------|---------|")
    matched = 0
    for year, dstart, dend, iopen, iclose, iret in IMAGE_TABLE:
        got = study_window(rows, dstart, dend)
        if got is None:
            lines.append(f"| {year} | {dstart}..{dend} | - | {iopen:.2f} "
                         f"| no data | {iret:+.2f} | - |")
            continue
        diff = got["move"] - iret
        ok = abs(diff) < 0.20
        matched += ok
        flag = "" if ok else " **MISMATCH**"
        lines.append(f"| {year} | {dstart[-5:]}..{dend[-5:]} "
                     f"| {got['entry']:.2f}/{got['exit']:.2f} | {iopen:.2f}/"
                     f"{iclose:.2f} | {got['move']:+.2f} | {iret:+.2f} "
                     f"| {diff:+.2f}{flag} |")
    lines.append(f"\n{matched}/{len(IMAGE_TABLE)} rows reproduce within "
                 "0.20pp using GC=F.")

    # ---- 3. curated vs full sample ------------------------------------
    def collect(period_list, upto=None):
        done = []
        for p in period_list:
            if upto and p["start"] > upto:
                continue
            got = study_window(rows, p["start"], p["end"])
            if got:
                done.append((p, got))
        return done

    last_completed = f"{datetime.date.today().year - 1}-12-31"
    all_done = collect(periods, upto=last_completed)
    img_done = collect([{"start": r[1], "end": r[2]} for r in IMAGE_TABLE])

    def fmt_stats(label, pairs):
        s = stats([g["move"] for _, g in pairs])
        mae = min(g["mae"] for _, g in pairs)
        return (f"{label}: n={s['n']}, mean={s['mean']:+.2f}%, "
                f"median={s['median']:+.2f}%, std={s['std']:.2f}, "
                f"win={s['win']:.0f}%, worst={s['worst']:+.2f}%, "
                f"best={s['best']:+.2f}%, t={s['t']:+.2f}, "
                f"deepest intra-window adverse={mae:+.2f}%")

    lines.append("\n## 3. Curated image sample vs complete ephemeris "
                 "sample\n")
    lines.append("```\n" + fmt_stats("IMAGE rows (curated)   ", img_done)
                 + "\n" + fmt_stats("ALL windows (complete) ", all_done)
                 + "\n```")

    omitted = [p for p, _ in all_done
               if int(p["start"][:4]) not in {r[0] for r in IMAGE_TABLE}]
    if omitted:
        lines.append("\nWindows in years the table omits:\n")
        lines.append("| start | end | move % | adverse % |")
        lines.append("|-------|-----|--------|-----------|")
        for p, g in all_done:
            if p in omitted:
                lines.append(f"| {p['start']} | {p['end']} "
                             f"| {g['move']:+.2f} | {g['mae']:+.2f} |")
        om_s = stats([g["move"] for p, g in all_done if p in omitted])
        lines.append(f"\nOmitted-years subset: n={om_s['n']}, "
                     f"mean={om_s['mean']:+.2f}%, win={om_s['win']:.0f}%")

    # ---- 4. bootstrap significance ------------------------------------
    lengths = []
    idx_of = {r["time"]: i for i, r in enumerate(rows)}
    for _p, g in all_done:
        lengths.append(idx_of[g["last"]] - idx_of[g["first"]] + 1)
    boot = bootstrap(rows, lengths, stats([g["move"] for _, g in all_done])["mean"])
    lines.append("\n## 4. Random-window bootstrap (10,000 draws, same "
                 "window lengths, 2000-2026 span)\n")
    lines.append(f"- observed mean (all windows): "
                 f"{stats([g['move'] for _, g in all_done])['mean']:+.2f}%")
    lines.append(f"- random-window mean: {boot['random_mean']:+.2f}% "
                 f"(90% range {boot['random_p05']:+.2f}% .. "
                 f"{boot['random_p95']:+.2f}%)")
    lines.append(f"- one-sided p(random mean >= observed): "
                 f"{1.0 - boot['p_one_sided']:.3f}; two-sided "
                 f"{boot['p_two_sided']:.3f}")

    # ---- 5. crash coverage --------------------------------------------
    lines.append("\n## 5. Crash-regime coverage\n")
    lines.append("| regime | regime window | overlapping conjunction "
                 "windows | covered? |")
    lines.append("|--------|---------------|--------------------------------|----------|")
    for name, rs, re_ in CRASH_REGIMES:
        hits = [p for p in periods
                if p["start"] <= re_ and p["end"] >= rs]
        if hits:
            txt = "; ".join(f"{p['start']}..{p['end']}" for p in hits)
            lines.append(f"| {name} | {rs}..{re_} | {txt} | yes |")
        else:
            lines.append(f"| {name} | {rs}..{re_} | none | **NO** |")

    # ---- 6. per-window risk table --------------------------------------
    lines.append("\n## 6. Per-window detail (all completed windows)\n")
    lines.append("| start | end | entry | exit | move % | dd from 52w high "
                 "at entry % | adverse (low vs entry) % | max close dd % | "
                 "fwd 5d % | fwd 21d % |")
    lines.append("|-------|-----|-------|------|--------|-------"
                 "------------------|-------"
                 "----------------|----------------|----------|-----------|")
    for p, g in all_done:
        f5 = f"{g['fwd5']:+.2f}" if g["fwd5"] is not None else "-"
        f21 = f"{g['fwd21']:+.2f}" if g["fwd21"] is not None else "-"
        lines.append(f"| {p['start']} | {p['end']} | {g['entry']:.2f} "
                     f"| {g['exit']:.2f} | {g['move']:+.2f} "
                     f"| {g['dd_entry']:+.1f} | {g['mae']:+.2f} "
                     f"| {g['mdd']:+.2f} | {f5} | {f21} |")

    s_all = stats([g["move"] for _, g in all_done])
    lines.append("\nMean forward returns after window exit: "
                 f"5d {np.nanmean([g['fwd5'] for _, g in all_done]):+.2f}%, "
                 f"21d {np.nanmean([g['fwd21'] for _, g in all_done]):+.2f}% "
                 f"(n={s_all['n']}).")

    deep = [(p, g) for p, g in all_done if g["dd_entry"] <= -10.0]
    if deep:
        ds = stats([g["move"] for _, g in deep])
        dfwd = np.nanmean([g["fwd21"] for _, g in deep])
        lines.append("\n### Windows entered with gold >=10% below its "
                     "52-session high (crash/bear entries)\n")
        lines.append("| start | dd at entry % | move % | fwd 21d % |")
        lines.append("|-------|---------------|--------|-----------|")
        for p, g in deep:
            f21 = f"{g['fwd21']:+.2f}" if g["fwd21"] is not None else "-"
            lines.append(f"| {p['start']} | {g['dd_entry']:+.1f} "
                         f"| {g['move']:+.2f} | {f21} |")
        lines.append(f"\nDeep-drawdown entries: n={ds['n']}, "
                     f"mean window move={ds['mean']:+.2f}%, "
                     f"win={ds['win']:.0f}%, mean fwd 21d={dfwd:+.2f}%")

    # ---- 7. ongoing 2026 window + context ------------------------------
    lines.append("\n## 7. Ongoing 2026 window and current market context\n")
    future = [p for p in periods if p["start"] > rows[-1]["time"]]
    ongoing = [p for p in periods if p["start"] >= f"{today[:4]}-10-01"]
    for p in ongoing:
        first = open_on_or_after(rows, p["start"])
        if first and first["time"] <= rows[-1]["time"]:
            got = study_window(rows, p["start"], rows[-1]["time"])
            lines.append(f"- window {p['start']}..{p['end']}: trading since "
                         f"{first['time']}, entry {got['entry']:.2f}, "
                         f"last {got['exit']:.2f} "
                         f"({got['move']:+.2f}% so far)")
        else:
            lines.append(f"- window {p['start']}..{p['end']}: first "
                         "tradable session has not occurred yet")
    if not ongoing and future:
        p = future[0]
        lines.append(f"- next window: {p['start']}..{p['end']}")

    tail = rows[-15:]
    hi52 = max(r["close"] for r in rows[-252:])
    last = rows[-1]["close"]
    peak = max(rows[-252:], key=lambda r: r["close"])
    lines.append(f"- last close {last:.2f} ({rows[-1]['time']}); "
                 f"52-session-high {hi52:.2f} on {peak['time']}; drawdown "
                 f"from that high {(last - hi52) / hi52 * 100:+.2f}%")
    lines.append("- the 2026 window's entry drawdown is the deepest of any "
                 "window in the sample (see section 6)")

    # ---- 8. current + upcoming windows: repo crash-window tool view ----
    lines.append("\n## 8. Current and upcoming windows - what "
                 "sbc.crash_windows says\n")
    lines.append("Day scores come from the repo's fixed 26-crash-day study "
                 "(in-sample, not a validated signal). Thresholds: "
                 f"elevated {crash_windows.ELEVATED} (top ~10% of days), "
                 f"high {crash_windows.HIGH} (top ~3%).\n")
    forward = [p for p in periods if p["end"] >= today]
    lines.append("| window | peak score | level | flagged days | slow "
                 "backdrop active |")
    lines.append("|--------|-----------|-------|--------------|"
                 "-----------------|")
    for p in forward:
        data = crash_windows.build(
            datetime.date.fromisoformat(p["start"]),
            datetime.date.fromisoformat(p["end"]))
        series = data["series"]
        peak = max(series, key=lambda d: d["score"])
        flagged = ", ".join(d["date"] for d in series if d["level"])
        backdrops = ", ".join(data["strong_slow_active"]) or "-"
        lines.append(f"| {p['start']}..{p['end']} | {peak['score']:.2f} "
                     f"({peak['date']}) | {peak['level'] or 'normal'} "
                     f"| {flagged or '-'} | {backdrops} |")
    for p in forward:
        data = crash_windows.build(
            datetime.date.fromisoformat(p["start"]),
            datetime.date.fromisoformat(p["end"]))
        for per in data["periods"]:
            tops = sorted(per["reasons"], key=lambda r: -r["weight"])[:4]
            why = "; ".join(f"{r['label']} ({r['position']})"
                            for r in tops)
            lines.append(f"\n- **{per['level']} day {per['peak_date']} "
                         f"(score {per['peak_score']:.2f}) in window "
                         f"{p['start']}..{p['end']}:** {why}")
    lines.append("\nNote: the tool's own header warns these combos are "
                 "in-sample and none passed a multiple-testing correction - "
                 "a research prompt, not a signal.")
    lines.append("\n- last sessions: " + ", ".join(
        f"{r['time']} {r['close']:.1f}" for r in tail[-10:]))

    report = "\n".join(lines) + "\n"
    print("\n" + report)
    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        with open(args.save, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"saved: {args.save}")


if __name__ == "__main__":
    main()
