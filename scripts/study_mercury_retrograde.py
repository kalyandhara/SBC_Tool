"""Study: market behaviour through Mercury retrograde windows.

Grades the recurring claim (video, 2026-10-18: "after Mercury goes
retrograde on 24 Oct, the market can turn") that Mercury retrograde
periods flip or hurt markets.  Analog of venus_station_validation:
window = Mercury retrograde station to direct station (Lahiri sidereal,
Swiss Ephemeris).

Method:
- Windows: all Mercury retrograde episodes in range (speed sign flips
  at 1-hour resolution).
- Entry: open of the first trading day on/after the station date;
  exit: close of the last trading day on/before the direct-station
  date (repo window convention, as in study_gold_libra_triple).
- Assets: nifty, gold, silver, crude; forward +5d/+21d after exit.
- Significance: 10,000-draw bootstrap of random same-length windows
  over the same span; p-values two-sided.
- Also reports the around-station sub-windows the video emphasises:
  -5..+5 sessions around the retrograde station (the "turn" window).

Example:
    python scripts/study_mercury_retrograde.py
"""

import argparse
import datetime
import os
import sys

import numpy as np
import swisseph as swe

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from scripts.study_mars_node_conjunction import (  # noqa: E402
    bootstrap,
    load_series,
    to_ist_date,
)

IST = datetime.timedelta(hours=5, minutes=30)
BOOTSTRAP_ITERS = 10_000
RNG_SEED = 42
ASSETS = ("nifty", "gold", "silver", "crude")


def mercury_retro_windows(start_date, end_date):
    """[{station_r, station_d}] Mercury retrograde episodes (IST dates)."""
    jd0 = swe.julday(start_date.year, start_date.month, start_date.day, 0)
    jd1 = swe.julday(end_date.year, end_date.month, end_date.day, 0)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

    def speed(jd):
        xx, _ = swe.calc_ut(jd, swe.MERCURY, flags)
        return xx[3]

    windows = []
    jd = jd0
    prev = speed(jd)
    station_r = None
    while jd <= jd1:
        jd += 1 / 24.0
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


def window_returns(rows, d_start, d_end, horizons=(0, 5, 21)):
    """Repo window convention + forward returns after the window."""
    first = next((i for i, r in enumerate(rows) if r["time"] >= d_start),
                 None)
    last_i = first
    for i, r in enumerate(rows):
        if r["time"] > d_end:
            break
        last_i = i
    if first is None or first > last_i:
        return None
    entry = rows[first]["open"]
    out = {"move": (rows[last_i]["close"] - entry) / entry * 100.0,
           "first": rows[first]["time"], "last": rows[last_i]["time"]}
    for h in horizons[1:]:
        if last_i + h < len(rows):
            out[f"fwd{h}"] = (rows[last_i + h]["close"]
                              / rows[last_i]["close"] - 1.0) * 100.0
        else:
            out[f"fwd{h}"] = None
    # around-station window: -5..+5 sessions from the first session
    around = None
    if first >= 5 and first + 5 < len(rows):
        around = (rows[first + 5]["close"] / rows[first - 5]["close"]
                  - 1.0) * 100.0
    out["around"] = around
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", default="2000-01-01")
    parser.add_argument("--end", default="2030-12-31")
    parser.add_argument("--save", default=os.path.join(
        "reports", "mercury_retrograde_study_2026-10-18.md"))
    args = parser.parse_args()

    start_date = datetime.date.fromisoformat(args.start)
    end_date = datetime.date.fromisoformat(args.end)
    today = datetime.date.today()
    today_str = today.isoformat()
    windows = mercury_retro_windows(start_date, end_date)
    upcoming = [w for w in windows if w["station_r"] >= today_str]

    lines = []
    lines.append("# Mercury retrograde - market study")
    lines.append(f"\nRange {start_date} .. {end_date}: "
                 f"{len(windows)} retrograde episodes "
                 f"({len(upcoming)} upcoming).")
    lines.append("\nUpcoming stations (retrograde -> direct, IST): "
                 + "; ".join(f"{w['station_r']} -> {w['station_d']}"
                             for w in upcoming))
    lines.append("\nEntry = first open on/after retrograde station, "
                 "exit = last close on/before direct station; 'around' "
                 "= -5..+5 sessions centred on the station.")

    study_end_date = min(end_date, today)
    lines.append("\n| asset | n | window mean % | window win % | "
                 "around % (p) | fwd 5d % | fwd 21d % | random % | p |")
    lines.append("|-------|---|---------------|--------------|"
                 "--------------|----------|-----------|----------|---|")
    for asset in ASSETS:
        rows = load_series(asset, start_date, study_end_date)
        if len(rows) < 100:
            lines.append(f"| {asset} | - | insufficient data | - | - | "
                         "- | - | - | - |")
            continue
        moves, arounds, f5s, f21s, lens = [], [], [], [], []
        for w in windows:
            got = window_returns(rows, w["station_r"], w["station_d"])
            if got is None:
                continue
            moves.append(got["move"])
            lens.append(next(i for i, r in enumerate(rows)
                             if r["time"] == got["last"])
                        - next(i for i, r in enumerate(rows)
                               if r["time"] == got["first"]) + 1)
            if got["around"] is not None:
                arounds.append(got["around"])
            if got["fwd5"] is not None:
                f5s.append(got["fwd5"])
            if got["fwd21"] is not None:
                f21s.append(got["fwd21"])
        if len(moves) < 10:
            lines.append(f"| {asset} | {len(moves)} | too few | - | - | "
                         "- | - | - | - |")
            continue
        obs = float(np.mean(moves))
        boot = bootstrap(rows, lens, obs)
        a_boot = (bootstrap(rows, [11] * len(arounds),
                            float(np.mean(arounds)))
                  if len(arounds) >= 10 else None)
        a_txt = (f"{np.mean(arounds):+.2f} ({a_boot['p_two_sided']:.3f})"
                 if a_boot else "-")
        lines.append(f"| {asset} | {len(moves)} | {obs:+.2f} "
                     f"| {np.mean([m > 0 for m in moves]) * 100:.0f} "
                     f"| {a_txt} | {np.nanmean(f5s):+.2f} "
                     f"| {np.nanmean(f21s):+.2f} "
                     f"| {boot['random_mean']:+.2f} "
                     f"| {boot['p_two_sided']:.3f} |")

    lines.append("\nVideo mapping: 'Mercury goes retrograde 24 Oct 2026; "
                 "things start changing after that; November-February "
                 "poor.' Ephemeris: Mercury R 2026-10-24 13:29 IST "
                 "(Lib 26.75), direct 2026-11-13 21:29 IST (Lib 10.80).")
    lines.append("\nCaveat: retrograde windows recur ~3x/year and their "
                 "length varies (~3.5 weeks); the bootstrap holds window "
                 "lengths fixed. Means are drift-sensitive; medians and "
                 "p-values are the honest read.")

    report = "\n".join(lines) + "\n"
    print(report)
    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        with open(args.save, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"saved: {args.save}")


if __name__ == "__main__":
    main()
