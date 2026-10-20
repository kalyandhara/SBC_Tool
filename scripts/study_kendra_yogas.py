"""Study: kendra-yogas on the 9:15 IST Mumbai opening chart vs NIFTY day.

Grades the video claim that Gaja-Kesari / Lakshmi / many-planets-in-
kendra open-chart setups make the session bullish (with a possible
positive open that then fades).

Definitions (whole-sign houses from the 9:15 IST Mumbai lagna, Lahiri
sidereal - same chart machinery as sbc.crash_windows):
- kendra houses: 1, 4, 7, 10 from the lagna.
- kendra_count: classical 7 planets (Sun..Saturn) occupying kendras.
- gaja_kesari: Jupiter in a kendra house counted from the Moon.
- benefics_kendra: Venus AND Jupiter both in kendra from the lagna
  (Lakshmi-style proxy: both natural benefics on the pillars).
- high_kendra: kendra_count >= 5 (the video showed a 6-planet kendra).

Tests per flag vs the all-days baseline: intraday NIFTY return
(open 09:15 -> close 15:30), next-day close-to-close return, red-candle
frequency (the "positive open then fade" sub-claim).  Significance by
10,000-draw label permutation on the mean intraday return.

Example:
    python scripts/study_kendra_yogas.py
"""

import argparse
import datetime
import os
import sys

import numpy as np
import swisseph as swe

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from sbc.market_data import get_ohlc  # noqa: E402

MUMBAI = (18.9750, 72.8258)
FLAGS = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
KENDRA_HOUSES = {1, 4, 7, 10}
CLASSICAL = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
PERMUTATIONS = 10_000
RNG_SEED = 42


def jd_ist(day, hh, mm):
    ist = (datetime.datetime(day.year, day.month, day.day, hh, mm)
           - datetime.timedelta(hours=5, minutes=30))
    return swe.julday(ist.year, ist.month, ist.day,
                      ist.hour + ist.minute / 60.0)


def lon(jd, pid):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    xx, _ = swe.calc_ut(jd, pid, FLAGS)
    return xx[0] % 360


def chart_flags(day):
    """Yoga flags + key longitudes for the 9:15 IST Mumbai open chart."""
    jd = jd_ist(day, 9, 15)
    _, ascmc = swe.houses_ex(jd, MUMBAI[0], MUMBAI[1], b"W",
                             swe.FLG_SIDEREAL)
    lagna_sign = int((ascmc[0] % 360.0) // 30)
    lons = {"Sun": lon(jd, swe.SUN), "Moon": lon(jd, swe.MOON),
            "Mercury": lon(jd, swe.MERCURY), "Venus": lon(jd, swe.VENUS),
            "Mars": lon(jd, swe.MARS), "Jupiter": lon(jd, swe.JUPITER),
            "Saturn": lon(jd, swe.SATURN)}
    house = {name: (int(lng // 30) - lagna_sign) % 12 + 1
             for name, lng in lons.items()}
    kendra_count = sum(1 for name in CLASSICAL
                       if house[name] in KENDRA_HOUSES)
    moon_sign = int(lons["Moon"] // 30)
    jup_from_moon = (int(lons["Jupiter"] // 30) - moon_sign) % 12 + 1
    return {
        "kendra_count": kendra_count,
        "gaja_kesari": jup_from_moon in KENDRA_HOUSES,
        "benefics_kendra": (house["Venus"] in KENDRA_HOUSES
                            and house["Jupiter"] in KENDRA_HOUSES),
        "high_kendra": kendra_count >= 5,
        "lagna_sign": lagna_sign,
        "houses": house,
    }


def perm_p(flagged, rest, iters=PERMUTATIONS, seed=RNG_SEED):
    """Two-sided label-permutation p for the difference in mean returns."""
    a = np.asarray(flagged, dtype=float)
    b = np.asarray(rest, dtype=float)
    observed = a.mean() - b.mean()
    pool = np.concatenate([a, b])
    n_flag = len(a)
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(iters):
        rng.shuffle(pool)
        diff = pool[:n_flag].mean() - pool[n_flag:].mean()
        hits += abs(diff) >= abs(observed)
    return observed, float(hits / iters)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", default="2007-09-17")
    parser.add_argument("--end", default=datetime.date.today().isoformat())
    parser.add_argument("--save", default=os.path.join(
        "reports", "kendra_yoga_study_2026-10-18.md"))
    args = parser.parse_args()

    rows = get_ohlc("nifty", args.start, args.end)
    rows = [r for r in rows if r["volume"] > 0 or r["open"] > 0]
    days = [datetime.date.fromisoformat(r["time"]) for r in rows]

    recs = []
    for i, day in enumerate(days):
        flags = chart_flags(day)
        rec = {"i": i, "day_ret": (rows[i]["close"] / rows[i]["open"]
                                   - 1.0) * 100.0}
        if i + 1 < len(rows):
            rec["next_ret"] = (rows[i + 1]["close"] / rows[i]["close"]
                               - 1.0) * 100.0
        rec["red"] = rows[i]["close"] < rows[i]["open"]
        rec.update(flags)
        recs.append(rec)

    base = [r["day_ret"] for r in recs]
    base_red = np.mean([r["red"] for r in recs]) * 100.0

    def flag_stats(pred):
        sub = [r for r in recs if pred(r)]
        if len(sub) < 30:
            return None
        flagged = [r["day_ret"] for r in sub]
        rest = [r["day_ret"] for r in recs if not pred(r)]
        obs, p = perm_p(flagged, rest)
        return {"n": len(sub), "mean": float(np.mean(flagged)),
                "win": float(np.mean([r["day_ret"] > 0 for r in sub]))
                * 100.0,
                "red": float(np.mean([r["red"] for r in sub])) * 100.0,
                "next": float(np.mean([r["next_ret"] for r in sub
                                       if "next_ret" in r])),
                "base_mean": float(np.mean(rest)),
                "base_red": float(np.mean([r["red"] for r in recs
                                           if not pred(r)])) * 100.0,
                "diff": obs, "p": p}

    groups = [
        ("Gaja-Kesari (Jupiter kendra from Moon)",
         lambda r: r["gaja_kesari"]),
        ("Benefics-in-kendra (Venus+Jupiter, Lakshmi proxy)",
         lambda r: r["benefics_kendra"]),
        ("High kendra (>=5 of 7)", lambda r: r["high_kendra"]),
    ]

    lines = []
    lines.append("# Kendra-yogas on the 9:15 Mumbai open chart - "
                 "NIFTY intraday study")
    lines.append(f"\nRange {days[0]} .. {days[-1]}, {len(recs)} sessions. "
                 "Definitions in the module docstring. Baseline = all "
                 f"other days (mean day return {np.mean(base):+.2f}%, "
                 f"red-candle share {base_red:.0f}%).")
    lines.append("\n| setup | n | day mean % | day win % | red candle % | "
                 "next-day mean % | baseline mean % | p |")
    lines.append("|-------|---|------------|-----------|--------------|"
                 "-----------------|-----------------|---|")
    for label, pred in groups:
        s = flag_stats(pred)
        if s is None:
            lines.append(f"| {label} | <30 | - | - | - | - | - | - |")
            continue
        lines.append(f"| {label} | {s['n']} | {s['mean']:+.2f} "
                     f"| {s['win']:.0f} | {s['red']:.0f} | {s['next']:+.2f} "
                     f"| {s['base_mean']:+.2f} | {s['p']:.3f} |")

    lines.append("\n## Tool read for the current week (9:15 IST Mumbai "
                 "charts)\n")
    lines.append("| date | lagna | kendra (7 / 9 incl. nodes) | "
                 "Gaja-Kesari | Venus+Jup kendra |")
    lines.append("|------|-------|----------------------------|"
                 "-------------|------------------|")
    sweep_end = days[-1] + datetime.timedelta(days=10)
    d = days[-1] + datetime.timedelta(days=1)
    while d <= sweep_end:
        f = chart_flags(d)
        jd = jd_ist(d, 9, 15)
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        rahu = lon(jd, swe.MEAN_NODE)
        ketu = (rahu + 180.0) % 360.0
        r_h = (int(rahu // 30) - f["lagna_sign"]) % 12 + 1
        k_h = (int(ketu // 30) - f["lagna_sign"]) % 12 + 1
        k9 = f["kendra_count"] + (r_h in KENDRA_HOUSES) \
            + (k_h in KENDRA_HOUSES)
        lines.append(f"| {d} | {f['lagna_sign'] + 1} "
                     f"| {f['kendra_count']} / {k9} "
                     f"| {'yes' if f['gaja_kesari'] else '-'} "
                     f"| {'yes' if f['benefics_kendra'] else '-'} |")
        d += datetime.timedelta(days=1)

    report = "\n".join(lines) + "\n"
    print(report)
    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        with open(args.save, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"saved: {args.save}")


if __name__ == "__main__":
    main()
