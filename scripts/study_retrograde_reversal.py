"""Study: does a trend reverse at the START of retrograde motion?

Pre-registered grades (frozen before the run) of the Mercury-retrograde
video claims (2026-10-25) and the follow-up request: "a historical
analysed summary of every start of planetary retrograde motion and its
impact on the market".

Definitions (frozen):
- Events: retrograde stations - geocentric sidereal (Lahiri) speed sign
  flips + -> - (hourly scan, IST dates) - of Mercury, Venus, Mars,
  Jupiter, Saturn.  Direct stations are used only to close windows.
- Entry: open of the first session on/after the station date (house
  convention, as in study_mercury_retrograde / study_mars_node_*).
- Pre-trend: sign of the K-session close-to-close return ending at the
  last close BEFORE entry (K = 10 primary; 5/20 sensitivity).  A zero
  pre-return is excluded.
- Outcome: forward return over M sessions from the entry open
  (M = 21 primary; 5/10 secondary).  "Rebound" = fwd > 0 after a
  downtrend; "flip" = fwd < 0 after an uptrend; "reversal" =
  sign(fwd) = -sign(pre).
- Window: entry open -> last close on/before the direct-station date
  (the video's "+0.55% average return, 65.1% positive" reading).
- Matched baseline: 10,000 permutations.  For each cell, draw the same
  number of random days from ALL sessions in the asset span carrying
  the SAME pre-trend sign (downtrend days for the rebound cell,
  uptrend days for the flip cell) and recompute the rate.  This is the
  honest comparison: after ANY 10-session downtrend the market tends
  to bounce; the question is whether station days beat that base rate.
  Two-sided p = 2*min(P(rand>=obs), P(rand<=obs)), capped at 1.

Video claim cells (computed under these frozen definitions, not tuned):
- Mercury x NIFTY: rebound-after-downtrend vs claimed 19/29 (65.5%);
  overall reversal vs 31/63 (49.2%); window mean/win vs +0.55%/65.1%.
- Mercury x gold: rebound-after-downtrend vs 22/31 (71%);
  negative-after-uptrend vs 11/32 (34.4%).
- Count check: 63 Mercury retro stations 2006-10..2026-07 (validator).

Examples:
    python scripts/study_retrograde_reversal.py
    python scripts/study_retrograde_reversal.py --asset gold
"""

import argparse
import datetime
import os
import sys

import numpy as np
import swisseph as swe

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from scripts.study_mars_node_conjunction import load_series  # noqa: E402

FLAGS = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
PLANETS = {
    "Mercury": swe.MERCURY, "Venus": swe.VENUS, "Mars": swe.MARS,
    "Jupiter": swe.JUPITER, "Saturn": swe.SATURN,
}
K_LIST = (5, 10, 20)          # pre-trend lookback (sessions)
M_LIST = (5, 10, 21)          # forward horizon (sessions)
K0, M0 = 10, 21               # primary cell
ITERS = 10_000
SEED = 42
VIDEO_SPAN = (datetime.date(2006, 10, 1), datetime.date(2026, 7, 31))


def to_ist_date(jd):
    y, m, d, _h = swe.revjul(jd + 5.5 / 24.0)
    return f"{y:04d}-{m:02d}-{d:02d}"


def retro_windows(planet, start_date, end_date):
    """[{station_r, station_d}] retrograde episodes of one planet (IST)."""
    pid = PLANETS[planet]
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd0 = swe.julday(start_date.year, start_date.month, start_date.day, 0)
    jd1 = swe.julday(end_date.year, end_date.month, end_date.day, 0)

    def speed(jd):
        return float(swe.calc_ut(jd, pid, FLAGS)[0][3])

    windows, station_r = [], None
    jd, prev = jd0, speed(jd0)
    while jd <= jd1:
        jd += 1.0 / 24.0
        cur = speed(jd)
        if prev * cur < 0:
            if cur < 0:
                station_r = jd
            elif station_r is not None:
                windows.append({"station_r": to_ist_date(station_r),
                                "station_d": to_ist_date(jd)})
                station_r = None
        prev = cur
    return windows


def event_indices(rows):
    closes = np.array([r["close"] for r in rows])
    opens = np.array([r["open"] for r in rows])
    return closes, opens


def build_events(rows, windows, k, m):
    """Per-event records; skips events without K days of history or M
    sessions of forward data, or with a zero pre-return."""
    closes, opens = event_indices(rows)
    n = len(rows)
    times = [r["time"] for r in rows]
    out = []
    for w in windows:
        idx = next((i for i, t in enumerate(times) if t >= w["station_r"]),
                   None)
        if idx is None or idx < k + 1 or idx + m >= n:
            continue
        ret_pre = (closes[idx - 1] / closes[idx - 1 - k] - 1.0) * 100.0
        if ret_pre == 0.0:
            continue
        last_i = idx
        for i in range(idx, n):
            if times[i] > w["station_d"]:
                break
            last_i = i
        out.append({
            "idx": idx, "date": w["station_r"], "ret_pre": ret_pre,
            "fwd": {mm: (closes[idx + mm] / opens[idx] - 1.0) * 100.0
                    for mm in (5, 10, 21)},
            "win": (closes[last_i] / opens[idx] - 1.0) * 100.0
            if w["station_d"] <= times[-1] else None,
            "open_window": w["station_d"] > times[-1],
        })
    return out


def permuted_rate(population, n_draw, observed, rng):
    """Two-sided p for a rate observed on event days vs the same number
    of random days drawn from the matched population (same pre-trend
    sign), plus the population's own rate."""
    pop = np.asarray(population, dtype=bool)
    if len(pop) == 0 or n_draw == 0:
        return None
    rates = np.empty(ITERS)
    for i in range(ITERS):
        pick = rng.integers(0, len(pop), size=n_draw)
        rates[i] = pop[pick].mean()
    p_ge = float((rates >= observed).mean())
    p_le = float((rates <= observed).mean())
    return {"pop_rate": float(pop.mean()), "p": min(1.0, 2 * min(p_ge, p_le)),
            "rand_mean": float(rates.mean())}


def cell_stats(events, m):
    """Rebound / flip / reversal rates for one (planet, asset, K, M)."""
    down = [e for e in events if e["ret_pre"] < 0]
    up = [e for e in events if e["ret_pre"] > 0]
    rev = [e for e in events if (e["fwd"][m] > 0) == (e["ret_pre"] < 0)]
    pos = [e for e in events if e["fwd"][m] > 0]
    return {"down": down, "up": up, "reversals": len(rev),
            "positive": len(pos), "n": len(events)}


def fmt_rate(num, den):
    return f"{num}/{den} ({num / den * 100:.1f}%)" if den else "-"


class _Tee:
    """Mirror prints into the report file when --save is given."""

    def __init__(self, *streams):
        self._streams = streams

    def write(self, text):
        for s in self._streams:
            s.write(text)

    def flush(self):
        for s in self._streams:
            s.flush()


def run_asset(asset, start, end, planets=PLANETS, per_event=True):
    rows = load_series(asset, start, end)
    if len(rows) < 300:
        print(f"  {asset}: insufficient data ({len(rows)} rows)")
        return None
    closes, opens = event_indices(rows)
    n = len(rows)

    # Pre-compute per-day pre-trend signs and fwd returns for the
    # matched populations (all sessions with K history and M forward).
    def pre_series(k):
        # ret_pre at session i uses closes[i-1]/closes[i-1-k]
        pre = np.full(n, np.nan)
        for i in range(k + 1, n):
            pre[i] = (closes[i - 1] / closes[i - 1 - k] - 1.0) * 100.0
        return pre

    def fwd_series(m):
        fwd = np.full(n, np.nan)
        for i in range(n - m):
            fwd[i] = (closes[i + m] / opens[i] - 1.0) * 100.0
        return fwd

    pre0 = pre_series(K0)
    fwd0 = fwd_series(M0)
    valid = ~np.isnan(pre0) & ~np.isnan(fwd0) & (pre0 != 0)
    pop_down = np.where(valid & (pre0 < 0))[0]
    pop_up = np.where(valid & (pre0 > 0))[0]
    rng = np.random.default_rng(SEED)

    print(f"\n## {asset}  ({rows[0]['time']} .. {rows[-1]['time']}, "
          f"n={n})")
    print(f"\nBase rates over ALL sessions: P(fwd{M0}>0 | 10-session "
          f"downtrend) = {fwd0[pop_down].mean():+.2f}% mean, "
          f"{(fwd0[pop_down] > 0).mean() * 100:.1f}% positive "
          f"(n={len(pop_down)}); P(fwd{M0}<0 | uptrend) = "
          f"{(fwd0[pop_up] < 0).mean() * 100:.1f}% (n={len(pop_up)})")

    hdr = ("| planet | n | down: rebound (p) | up: flip (p) | "
           "reversal | positive | window mean % | window win % |")
    sep = ("|---|---|---|---|---|---|---|---|")
    print(f"\n{hdr}\n{sep}")
    tables = {}
    for planet in planets:
        windows = retro_windows(planet, start, end)
        events = build_events(rows, windows, K0, M0)
        if len(events) < 5:
            print(f"| {planet} | {len(events)} | too few | - | - | - "
                  "| - | - |")
            continue
        st = cell_stats(events, M0)
        nd, nu = len(st["down"]), len(st["up"])
        reb = sum(e["fwd"][M0] > 0 for e in st["down"])
        flip = sum(e["fwd"][M0] < 0 for e in st["up"])
        rb = permuted_rate(fwd0[pop_down] > 0, nd, reb / nd, rng) \
            if nd else None
        fp = permuted_rate(fwd0[pop_up] < 0, nu, flip / nu, rng) \
            if nu else None
        rev_rate = st["reversals"] / st["n"]
        base_all = np.concatenate([fwd0[pop_down], fwd0[pop_up]])
        pre_all = np.concatenate([pre0[pop_down], pre0[pop_up]])
        rev_pop = (base_all > 0) == (pre_all < 0)
        rv = permuted_rate(rev_pop, st["n"], rev_rate, rng)
        pos_rate = st["positive"] / st["n"]
        ps = permuted_rate(fwd0[valid] > 0, st["n"], pos_rate, rng)
        wins = [e["win"] for e in events if e["win"] is not None]
        wmean = float(np.mean(wins)) if wins else float("nan")
        wwin = float(np.mean([w > 0 for w in wins])) * 100 if wins else float("nan")
        print(f"| {planet} | {st['n']} "
              f"| {reb}/{nd} ({rb['p']:.3f}) "
              f"| {flip}/{nu} ({fp['p']:.3f}) "
              f"| {fmt_rate(st['reversals'], st['n'])} ({rv['p']:.3f}) "
              f"| {fmt_rate(st['positive'], st['n'])} ({ps['p']:.3f}) "
              f"| {wmean:+.2f} | {wwin:.0f} |")
        tables[planet] = events
    if per_event:
        for planet, events in tables.items():
            print(f"\n### {asset} x {planet} - every retrograde start "
                  f"(K={K0}, M={M0})\n")
            print("| station | pre % | fwd5 % | fwd10 % | fwd21 % | "
                  "window % | reversal? |")
            print("|---|---|---|---|---|---|---|")
            for e in events:
                rev = "Y" if (e["fwd"][M0] > 0) == (e["ret_pre"] < 0) else "."
                win = f"{e['win']:+.2f}" if e["win"] is not None else (
                    "open" if e["open_window"] else "-")
                print(f"| {e['date']} | {e['ret_pre']:+.2f} "
                      f"| {e['fwd'][5]:+.2f} | {e['fwd'][10]:+.2f} "
                      f"| {e['fwd'][21]:+.2f} | {win} | {rev} |")
    return rows, pre_series, fwd_series


def sensitivity(rows, planet):
    """K x M grid for one planet on one asset (rebound-after-down rate
    and p in the primary-style matched baseline)."""
    closes, opens = event_indices(rows)
    n = len(rows)
    rng = np.random.default_rng(SEED)
    print(f"\n## Sensitivity grid - {planet}: rebound-after-downtrend "
          f"rate (p)\n")
    print("| K \ M | " + " | ".join(f"M={m}" for m in M_LIST) + " |")
    print("|---" * (len(M_LIST) + 1) + "|")
    for k in K_LIST:
        cells = []
        events_full = build_events(rows,
                                   retro_windows(planet, VIDEO_SPAN[0],
                                                 datetime.date.today()),
                                   k, max(M_LIST))
        for m in M_LIST:
            ev = [e for e in events_full if e["idx"] + m < n]
            down = [e for e in ev if e["ret_pre"] < 0]
            if len(down) < 5:
                cells.append("-")
                continue
            # recompute fwd at this m from stored idx
            fwd_m = np.full(n, np.nan)
            for i in range(n - m):
                fwd_m[i] = (closes[i + m] / opens[i] - 1.0) * 100.0
            pre = np.full(n, np.nan)
            for i in range(k + 1, n):
                pre[i] = (closes[i - 1] / closes[i - 1 - k] - 1.0) * 100.0
            valid = ~np.isnan(pre) & ~np.isnan(fwd_m) & (pre != 0)
            pop = np.where(valid & (pre < 0))[0]
            reb = sum(fwd_m[e["idx"]] > 0 for e in down)
            r = permuted_rate(fwd_m[pop] > 0, len(down), reb / len(down),
                              rng)
            cells.append(f"{reb}/{len(down)} = {reb / len(down) * 100:.0f}% "
                         f"({r['p']:.3f})")
        print(f"| K={k} | " + " | ".join(cells) + " |")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--asset", default="nifty")
    parser.add_argument("--start", default=None,
                        help="default: the asset's own first cached bar")
    parser.add_argument("--save", default=None)
    args = parser.parse_args()

    print("# Retrograde-station reversal study (pre-registered)")
    print("\nDefinitions frozen before the run (see module docstring): "
          "retrograde stations of Mercury..Saturn; entry = first open "
          "on/after the station; pre-trend = K-session return ending "
          "the close before entry (K=10 primary); outcome = M-session "
          "forward return from the entry open (M=21 primary); matched "
          "permutation baseline = same number of random days with the "
          "same pre-trend sign; two-sided p.")
    start = (datetime.date.fromisoformat(args.start)
             if args.start else datetime.date(2000, 1, 1))
    fh = None
    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        fh = open(args.save, "w", encoding="utf-8")
        sys.stdout = _Tee(sys.stdout, fh)
    try:
        got = run_asset(args.asset, start, datetime.date.today())
        if got and args.asset == "nifty":
            rows = got[0]
            sensitivity(rows, "Mercury")
            # the video's exact span, for the 63-episode claim set
            print("\n## Mercury on NIFTY restricted to the video's span "
                  "(2006-10 .. 2026-07; repo data starts 2007-09-17)\n")
            run_asset("nifty", datetime.date(2007, 9, 1), VIDEO_SPAN[1],
                      planets={"Mercury": PLANETS["Mercury"]},
                      per_event=False)
    finally:
        sys.stdout = sys.__stdout__
        if fh:
            fh.close()
            print(f"saved: {args.save}")


if __name__ == "__main__":
    main()
