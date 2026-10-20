"""Study: market behaviour around nitya-yoga Vyatipata formation.

Tests the claim that markets (bullions especially) fall in the ~24 h
after Vyatipata forms.  Vyatipata is nitya yoga #17 (1-based): active
while (Sun+Moon sidereal longitudes) mod 360 lies in
[16 x 13deg20', 17 x 13deg20').  The sum advances ~14 deg/day, so the
yoga is active roughly one day in every 27.3 and "formation" is the
moment the sum enters the band.

Method:
- Formations located by 3-hour ephemeris scan + linear interpolation
  (same pipeline as sbc.transits).
- Entry model: close of the first trading session that STARTS after
  the formation (formations after 12:00 IST act on the next session).
- Forward returns: close-to-close +1 / +3 / +5 sessions after entry.
- Significance: 10,000-draw bootstrap of random same-length windows
  over the same span; p-values two-sided.

Example:
    python scripts/study_vyatipat_formation.py
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
from sbc.nakshatra import NAKSHATRA_SPAN, VYATIPATA_INDEX  # noqa: E402
from sbc.transits import _scan  # noqa: E402

IST = datetime.timedelta(hours=5, minutes=30)
BAND_LO = VYATIPATA_INDEX * NAKSHATRA_SPAN
BAND_HI = (VYATIPATA_INDEX + 1) * NAKSHATRA_SPAN
ACTION_CUTOFF = 12.0  # formations after 12:00 IST act on the next session
WINDOWS = (1, 3, 5)
BOOTSTRAP_ITERS = 10_000
RNG_SEED = 42


def formation_events(start_date, end_date):
    """Return [(utc_jd, ist_datetime)] for each Vyatipata band entry."""
    scan = _scan(["Sun", "Moon"], start_date, end_date, step_hours=3.0)
    sums = [(jd, (lo_s + lo_m) % 360.0) for jd, (lo_s, lo_m) in scan]
    events = []
    for (jd0, s0), (jd1, s1) in zip(sums, sums[1:]):
        in0, in1 = BAND_LO <= s0 < BAND_HI, BAND_LO <= s1 < BAND_HI
        if not in0 and in1:
            frac = (BAND_LO - s0) / ((s1 - s0) % 360.0)
            jd_ev = jd0 + frac * (jd1 - jd0)
            y, m, d, h = swe.revjul(jd_ev)
            ist = (datetime.datetime(y, m, d)
                   + datetime.timedelta(hours=h) + IST)
            events.append((jd_ev, ist))
    return events


def entry_dates(events, rows):
    """Map each formation to the first session that starts after it."""
    sessions = [datetime.date.fromisoformat(r["time"]) for r in rows]
    out = []
    for _jd, ist in events:
        cutoff = (ist.date() if ist.hour + ist.minute / 60.0
                  < ACTION_CUTOFF else ist.date() + datetime.timedelta(days=1))
        entry = next((d for d in sessions if d >= cutoff), None)
        if entry is not None:
            out.append(entry)
    return out


def close_bootstrap(rows, lengths, observed, iters=BOOTSTRAP_ITERS,
                    seed=RNG_SEED):
    closes = np.asarray([r["close"] for r in rows])
    n = len(rows)
    lens = np.asarray(lengths)
    rng = np.random.default_rng(seed)
    means = np.empty(iters)
    for i in range(iters):
        starts = rng.integers(0, n - lens.max(), size=len(lens))
        means[i] = (closes[starts + lens - 1] / closes[starts] - 1.0
                    ).mean() * 100.0
    p_le = float((means <= observed).mean())
    return {"random_mean": float(means.mean()),
            "p_two_sided": float(min(p_le, 1.0 - p_le) * 2.0)}


def study_asset(asset, events, start_date, end_date):
    rows = get_ohlc(asset, start_date.isoformat(), end_date.isoformat())
    if len(rows) < 60:
        return None
    entries = entry_dates(events, rows)
    idx_of = {r["time"]: i for i, r in enumerate(rows)}
    idxs = [idx_of[e.isoformat()] for e in entries
            if e.isoformat() in idx_of]
    idxs = [i for i in idxs if i + max(WINDOWS) < len(rows)]
    if len(idxs) < 5:
        return None

    stats = {}
    for n in WINDOWS:
        moves = [(rows[i + n]["close"] / rows[i]["close"] - 1.0) * 100.0
                 for i in idxs]
        obs = float(np.mean(moves))
        boot = close_bootstrap(rows, [n + 1] * len(moves), obs)
        stats[n] = {"mean": obs, "median": float(np.median(moves)),
                    "win": float(sum(m > 0 for m in moves) / len(moves) * 100),
                    "boot": boot}
    return {"asset": asset, "n": len(idxs), "stats": stats,
            "first": rows[idxs[0]]["time"], "last": rows[idxs[-1]]["time"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", default="2000-09-01")
    parser.add_argument("--end", default=datetime.date.today().isoformat())
    parser.add_argument("--save", default=os.path.join(
        "reports", "vyatipat_formation_study_2026-10-18.md"))
    args = parser.parse_args()

    start_date = datetime.date.fromisoformat(args.start)
    end_date = datetime.date.fromisoformat(args.end)
    events = formation_events(start_date, end_date)
    today = datetime.date.today()
    upcoming = [ist for _jd, ist in events if ist.date() >= today][:3]

    lines = []
    lines.append("# Vyatipata formation - forward-return study")
    lines.append(f"\nRange {start_date} .. {end_date}; "
                 f"{len(events)} formations found "
                 f"(band {BAND_LO:.2f}-{BAND_HI:.2f} deg of the Sun+Moon "
                 "sum; yoga active ~1 day per 27.3).")
    if upcoming:
        lines.append("\nUpcoming formations (IST): " + ", ".join(
            ist.strftime("%Y-%m-%d %H:%M") for ist in upcoming))
    lines.append("\nEntry = close of the first session starting after "
                 "formation (12:00 IST cutoff); returns close-to-close.")
    lines.append("\n| asset | n | window | mean % | median % | win % | "
                 "random % | p |")
    lines.append("|-------|---|--------|--------|----------|-------|"
                 "----------|---|")
    for asset in ("nifty", "gold", "silver", "crude"):
        res = study_asset(asset, events, start_date, end_date)
        if res is None:
            lines.append(f"| {asset} | - | - | insufficient data | - | - "
                         f"| - | - |")
            continue
        for n in WINDOWS:
            s = res["stats"][n]
            lines.append(f"| {asset} | {res['n']} | +{n}d | {s['mean']:+.2f} "
                         f"| {s['median']:+.2f} | {s['win']:.0f} "
                         f"| {s['boot']['random_mean']:+.2f} "
                         f"| {s['boot']['p_two_sided']:.3f} |")
    lines.append("\nVideo mapping: 'Vyatipat forms 21 Oct 2026 ~6 PM; "
                 "next 24 h critical; markets (bullions especially) "
                 "fall.' Ephemeris: the Oct 2026 Vyatipata actually "
                 "forms 2026-10-27 11:29 IST and ends 2026-10-28 07:29 "
                 "IST - the video's date was 6 days early.")

    report = "\n".join(lines) + "\n"
    print(report)
    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        with open(args.save, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"saved: {args.save}")


if __name__ == "__main__":
    main()
