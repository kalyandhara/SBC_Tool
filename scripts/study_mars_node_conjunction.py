"""Mars-Rahu/Ketu conjunction tracker + multi-asset event study.

Tracks every episode in which Mars sits close to a lunar node (mean
node, Lahiri sidereal - repo convention) and measures what crude, gold,
silver, NIFTY and India VIX do afterwards.  This grades the recurring
claim that "Mars joining Rahu/Ketu brings a strike/conflict: crude
spikes, markets fall".

Method:
- Episodes: consecutive days with Mars-node separation < 2.5 deg; the
  event date is the day of minimum separation; label = closer node.
- Entry: open of the first trading day on/after the event date.
- Windows: close of entry+N trading days for N in (5, 10, 21); MFE/MAE
  over the 21-day window.
- Significance: 10,000-draw bootstrap of random same-length windows
  over the same span; p-values are two-sided.

Examples:
    python scripts/study_mars_node_conjunction.py
    python scripts/study_mars_node_conjunction.py --end 2030-12-31
"""

import argparse
import datetime
import os
import sys

import numpy as np
import swisseph as swe

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from sbc import market_store  # noqa: E402
from sbc.market_data import get_ohlc  # noqa: E402

FLAGS = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
EPISODE_ORB = 2.5
WINDOWS = (5, 10, 21)
HORIZON = 21
BOOTSTRAP_ITERS = 10_000
RNG_SEED = 42
ASSETS = ("crude", "gold", "silver", "nifty", "INDIAVIX")


def lon(jd, pid):
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    xx, _ = swe.calc_ut(jd, pid, FLAGS)
    return xx[0] % 360


def to_ist_date(jd):
    y, m, d, _h = swe.revjul(jd + 5.5 / 24.0)
    return f"{y:04d}-{m:02d}-{d:02d}"


def find_episodes(start_date, end_date):
    """Return [{date, node, orb_deg}] for Mars-node episodes."""
    jd0 = swe.julday(start_date.year, start_date.month, start_date.day, 0)
    jd1 = swe.julday(end_date.year, end_date.month, end_date.day, 0)
    episodes, current = [], []
    jd = jd0
    while jd <= jd1:
        m = lon(jd, swe.MARS)
        rahu = lon(jd, swe.MEAN_NODE)
        sep_r = abs((m - rahu + 180.0) % 360.0 - 180.0)
        sep_k = abs((m - ketu(rahu) + 180.0) % 360.0 - 180.0)
        if min(sep_r, sep_k) < EPISODE_ORB:
            node = "Rahu" if sep_r <= sep_k else "Ketu"
            current.append((jd, node, min(sep_r, sep_k)))
        elif current:
            episodes.append(current)
            current = []
        jd += 1.0
    if current:
        episodes.append(current)

    events = []
    for ep in episodes:
        jd_min, node, orb = min(ep, key=lambda t: t[2])
        events.append({"date": to_ist_date(jd_min), "node": node,
                       "orb": round(orb, 2)})
    return events


def ketu(rahu):
    return (rahu + 180.0) % 360.0


def load_series(asset, start_date, end_date):
    """Normalize get_ohlc / market_store rows to sorted OHLC dicts."""
    if asset == "INDIAVIX":
        rows = market_store.get_daily(asset, start_date.isoformat(),
                                      end_date.isoformat())
        out = [{"time": r["date"], "open": r["open"], "high": r["high"],
                "low": r["low"], "close": r["close"]} for r in rows]
    else:
        out = get_ohlc(asset, start_date.isoformat(), end_date.isoformat())
    return sorted(out, key=lambda r: r["time"])


def event_returns(rows, event_date, horizon=HORIZON):
    """(entry_idx, {N: open-to-close+N return}, mfe, mae) or None."""
    idx = next((i for i, r in enumerate(rows)
                if r["time"] >= event_date), None)
    if idx is None or idx + horizon >= len(rows):
        return None
    entry = rows[idx]["open"]
    rets = {n: (rows[idx + n]["close"] - entry) / entry * 100.0
            for n in WINDOWS}
    seg = rows[idx:idx + horizon + 1]
    mfe = (max(r["high"] for r in seg) - entry) / entry * 100.0
    mae = (min(r["low"] for r in seg) - entry) / entry * 100.0
    return idx, rets, mfe, mae


def bootstrap(rows, lengths, observed, iters=BOOTSTRAP_ITERS, seed=RNG_SEED):
    """Two-sided p for the mean of random same-length open-to-close+N
    windows over the full span."""
    opens = np.asarray([r["open"] for r in rows])
    closes = np.asarray([r["close"] for r in rows])
    n = len(rows)
    lens = np.asarray(lengths)
    rng = np.random.default_rng(seed)
    means = np.empty(iters)
    for i in range(iters):
        starts = rng.integers(0, n - lens.max(), size=len(lens))
        means[i] = (closes[starts + lens - 1] / opens[starts] - 1.0
                    ).mean() * 100.0
    p_le = float((means <= observed).mean())
    return {"random_mean": float(means.mean()),
            "p_two_sided": float(min(p_le, 1.0 - p_le) * 2.0)}


def study_asset(asset, events, start_date, end_date):
    rows = load_series(asset, start_date, end_date)
    if len(rows) < 60:
        return None
    per_event, used = [], []
    for ev in events:
        got = event_returns(rows, ev["date"])
        if got is None:
            continue
        idx, rets, mfe, mae = got
        used.append(ev)
        per_event.append({"ev": ev, "entry": rows[idx]["time"],
                          "rets": rets, "mfe": mfe, "mae": mae})
    if len(used) < 5:
        return None

    stats = {}
    for n in WINDOWS:
        moves = [p["rets"][n] for p in per_event]
        # window length in trading days: entry day + n closes -> n+1.
        lengths = [n + 1] * len(moves)
        obs = float(np.mean(moves))
        boot = bootstrap(rows, lengths, obs)
        stats[n] = {"mean": obs,
                    "median": float(np.median(moves)),
                    "win": float(sum(m > 0 for m in moves) / len(moves) * 100),
                    "boot": boot}
    return {"asset": asset, "per_event": per_event, "stats": stats,
            "n": len(used)}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", default="2000-01-01")
    parser.add_argument("--end", default="2030-12-31")
    parser.add_argument("--save", default=os.path.join(
        "reports", "mars_node_conjunction_study_2026-10-18.md"))
    args = parser.parse_args()

    start_date = datetime.date.fromisoformat(args.start)
    end_date = datetime.date.fromisoformat(args.end)
    today = datetime.date.today().isoformat()
    events = find_episodes(start_date, end_date)
    future = [e for e in events if e["date"] >= today]

    lines = []
    lines.append("# Mars-Rahu/Ketu conjunction tracker + event study")
    lines.append(f"\nRange {start_date} .. {end_date}; episodes = Mars-node"
                 f" separation < {EPISODE_ORB} deg (mean node, Lahiri); "
                 f"event date = minimum-separation day.")
    lines.append(f"\n## Tracker: {len(events)} episodes "
                 f"({len(future)} upcoming)\n")
    lines.append("| date | node | orb | status |")
    lines.append("|------|------|-----|--------|")
    for e in events:
        status = ("upcoming" if e["date"] >= today else "past")
        lines.append(f"| {e['date']} | {e['node']} | {e['orb']:.2f} | "
                     f"{status} |")

    study_start = datetime.date(2000, 1, 1)
    study_end = min(end_date, datetime.date.today())
    lines.append("\n## Event study (entry = first open on/after event "
                 "date; returns in %)\n")
    for asset in ASSETS:
        res = study_asset(asset, events, study_start, study_end)
        if res is None:
            lines.append(f"\n### {asset}: insufficient data/events\n")
            continue
        lines.append(f"\n### {asset} (n={res['n']} events)\n")
        lines.append("| window | mean | median | win % | random mean | p |")
        lines.append("|--------|------|--------|-------|-------------|---|")
        for n in WINDOWS:
            s = res["stats"][n]
            lines.append(f"| +{n}d | {s['mean']:+.2f} | {s['median']:+.2f} "
                         f"| {s['win']:.0f} | {s['boot']['random_mean']:+.2f} "
                         f"| {s['boot']['p_two_sided']:.3f} |")
        mfe = max(p["mfe"] for p in res["per_event"])
        mae = min(p["mae"] for p in res["per_event"])
        lines.append(f"\nWorst/best 21d excursion: MAE {mae:+.2f}% / "
                     f"MFE {mfe:+.2f}%")

    # recent-events detail for narrative
    lines.append("\n## Recent events detail (gold)\n")
    lines.append("| event | node | orb | entry | +5d | +10d | +21d |")
    lines.append("|-------|------|-----|-------|-----|------|------|")
    res = study_asset("gold", events, study_start, study_end)
    if res:
        for p in res["per_event"][-8:]:
            r = p["rets"]
            lines.append(f"| {p['ev']['date']} | {p['ev']['node']} "
                         f"| {p['ev']['orb']:.2f} | {p['entry']} "
                         f"| {r[5]:+.2f} | {r[10]:+.2f} | {r[21]:+.2f} |")

    lines.append("\nVideo mapping: claimed Mars-Ketu Jun 12-13 2025 "
                 "(attack Jun 22), Mars-Rahu Feb 23-28 2026 (attack), "
                 "Mars-Ketu Nov 12 2026 (attack after). Ephemeris: exact "
                 "conjunctions 2025-07-23 (Ketu), 2026-03-13 (Rahu), "
                 "2026-11-15 (Ketu) - see tracker above.")
    lines.append("\nCaveat: means are tail-sensitive - the 2020-02-24 "
                 "episode is the COVID crash onset (crude MAE -63%, VIX "
                 "MFE +532%) and 2026-03-13 saw gold -10%. Medians and "
                 "p-values are the honest read; treat this as an "
                 "event-study prompt, not a validated signal.")

    report = "\n".join(lines) + "\n"
    print(report)
    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        with open(args.save, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"saved: {args.save}")


if __name__ == "__main__":
    main()
