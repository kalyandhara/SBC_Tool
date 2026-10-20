"""Cross-asset crash-propagation study: does an equity crash drag
everything down?

Grades the video claim that "when equity markets crash, all asset
classes fall - we saw it in 2008", which underpins his silver and
bullion warnings.

Method:
- Crash episodes from NIFTY itself: an "alarm day" is the first day
  whose 21-session return is <= -10% with no alarm in the prior 40
  sessions (one episode per cluster).  The episode window runs from
  ~21 sessions before the alarm (approximate local peak) to the
  NIFTY trough within the following 40 sessions.
- Propagation: for each asset (gold, silver, crude, USDINR, India
  VIX), close-to-close return over the same calendar window, aligned
  with last-close-on-or-before.  USDINR up = rupee weaker = INR-quoted
  gold tailwind.
- Significance: per-asset 10,000-draw bootstrap of random same-length
  close-to-close windows over the same span (two-sided p).
- Stress-day lens: mean asset return on days when NIFTY falls >= 2%,
  vs all days, plus daily-return correlations.

Example:
    python scripts/study_crash_propagation.py
"""

import argparse
import datetime
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from scripts.study_mars_node_conjunction import load_series  # noqa: E402

ALARM_THRESHOLD = -10.0
ALARM_LOOKBACK = 21
QUIET_GAP = 40
TROUGH_SEARCH = 40
STRESS_DAY = -2.0
BOOTSTRAP_ITERS = 10_000
RNG_SEED = 42
ASSETS = ("gold", "silver", "crude", "usdinr", "INDIAVIX")


def close_on_or_before(rows, d):
    result = None
    for r in rows:
        if r["time"] > d:
            break
        result = r
    return result


def crash_episodes(rows):
    """Return [{alarm, start, trough, dd}] NIFTY crash episodes."""
    closes = [r["close"] for r in rows]
    times = [r["time"] for r in rows]
    alarms = []
    last_alarm = -QUIET_GAP
    for i in range(ALARM_LOOKBACK, len(rows)):
        ret = (closes[i] / closes[i - ALARM_LOOKBACK] - 1.0) * 100.0
        if ret <= ALARM_THRESHOLD and i - last_alarm > QUIET_GAP:
            alarms.append(i)
            last_alarm = i
    episodes = []
    for a in alarms:
        ws = a - ALARM_LOOKBACK
        te = min(a + TROUGH_SEARCH, len(rows) - 1)
        trough = ws + int(np.argmin(closes[ws:te + 1]))
        if trough <= ws:
            continue
        episodes.append({"alarm": times[a], "start": times[ws],
                         "trough": times[trough],
                         "dd": (closes[trough] / closes[ws] - 1.0) * 100.0})
    return episodes


def asset_window_return(rows, d_start, d_trough):
    r0 = close_on_or_before(rows, d_start)
    r1 = close_on_or_before(rows, d_trough)
    if r0 is None or r1 is None or r1["time"] < r0["time"]:
        return None
    return (r1["close"] / r0["close"] - 1.0) * 100.0


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


def stress_lens(rows_nifty, rows_asset):
    """Mean asset daily return on NIFTY <= -2% days vs all common days."""
    by_date = {r["time"]: r for r in rows_asset}
    common = [(r["close"], by_date[r["time"]]["close"])
              for r in rows_nifty[1:] if r["time"] in by_date]
    rn = np.diff([c[0] for c in common]) / np.asarray(
        [c[0] for c in common[:-1]]) * 100.0
    ra = np.diff([c[1] for c in common]) / np.asarray(
        [c[1] for c in common[:-1]]) * 100.0
    stress = rn <= STRESS_DAY
    if stress.sum() < 10:
        return None
    corr_all = float(np.corrcoef(rn, ra)[0, 1])
    return {"n_stress": int(stress.sum()),
            "mean_stress": float(ra[stress].mean()),
            "mean_all": float(ra.mean()),
            "corr_stress": float(np.corrcoef(rn[stress], ra[stress])[0, 1]),
            "corr_all": corr_all,
            "down_share_stress": float((ra[stress] < 0).mean() * 100.0)}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", default="2000-01-01")
    parser.add_argument("--save", default=os.path.join(
        "reports", "crash_propagation_study_2026-10-19.md"))
    args = parser.parse_args()

    today = datetime.date.today()
    nifty = load_series("nifty", datetime.date.fromisoformat(args.start),
                        today)
    if len(nifty) < 200:
        raise SystemExit("insufficient NIFTY data")
    episodes = crash_episodes(nifty)
    lines = []
    lines.append("# Cross-asset crash-propagation study")
    lines.append(f"\nNIFTY episodes 2000-2026: 21-session return <= "
                 f"{ALARM_THRESHOLD}% alarms a crash; window = ~21 "
                 "sessions before the alarm to the NIFTY trough within "
                 f"40 sessions. {len(episodes)} episodes found.")
    lines.append("\n## Episodes\n")
    lines.append("| start | trough | NIFTY drawdown % |")
    lines.append("|-------|--------|------------------|")
    for e in episodes:
        lines.append(f"| {e['start']} | {e['trough']} | {e['dd']:+.1f} |")

    lines.append("\n## Propagation: asset return over each crash window\n")
    lines.append("| asset | n | mean % | median % | fell in % of episodes | "
                 "random % | p |")
    lines.append("|-------|---|--------|----------|------------------------|"
                 "----------|---|")
    start = datetime.date.fromisoformat(args.start)
    for asset in ASSETS:
        rows = load_series(asset, start, today)
        if len(rows) < 200:
            lines.append(f"| {asset} | - | insufficient data | - | - | - | - |")
            continue
        rets, lens = [], []
        for e in episodes:
            r = asset_window_return(rows, e["start"], e["trough"])
            if r is None:
                continue
            rets.append(r)
            d0 = close_on_or_before(rows, e["start"])
            d1 = close_on_or_before(rows, e["trough"])
            i0 = rows.index(d0)
            i1 = rows.index(d1)
            if i1 > i0:
                lens.append(i1 - i0 + 1)
        if len(rets) < 5:
            lines.append(f"| {asset} | {len(rets)} | too few | - | - | - | - |")
            continue
        obs = float(np.mean(rets))
        boot = close_bootstrap(rows, lens, obs)
        fell = float(np.mean([r < 0 for r in rets])) * 100.0
        lines.append(f"| {asset} | {len(rets)} | {obs:+.2f} "
                     f"| {np.median(rets):+.2f} | {fell:.0f}% "
                     f"| {boot['random_mean']:+.2f} "
                     f"| {boot['p_two_sided']:.3f} |")

    lines.append("\n## Stress days (NIFTY <= -2%)\n")
    lines.append("| asset | stress days | mean ret on stress days % | "
                 "all-days mean % | down on stress % | corr stress | corr all |")
    lines.append("|-------|-------------|---------------------------|"
                 "----------------|------------------|-------------|----------|")
    for asset in ASSETS:
        rows = load_series(asset, start, today)
        if len(rows) < 200:
            continue
        s = stress_lens(nifty, rows)
        if s is None:
            continue
        lines.append(f"| {asset} | {s['n_stress']} | {s['mean_stress']:+.2f} "
                     f"| {s['mean_all']:+.3f} | {s['down_share_stress']:.0f}% "
                     f"| {s['corr_stress']:+.2f} | {s['corr_all']:+.2f} |")

    # current drawdown readout
    closes = [r["close"] for r in nifty]
    hi = max(closes[-252:])
    dd_now = (closes[-1] / hi - 1.0) * 100.0
    lines.append(f"\nCurrent state: NIFTY last close {closes[-1]:.1f} "
                 f"({nifty[-1]['time']}), {dd_now:+.1f}% vs its "
                 "52-session high.")

    lines.append("\nVideo mapping: 'when equities crash all asset classes "
                 "fall - 2008; silver weak; protect capital.' USDINR up "
                 "= rupee weaker = INR gold tailwind (his rupee point "
                 "at 4:50 relies on the opposite move). Bootstrap "
                 "p-values are two-sided; episodes overlap major "
                 "regimes, so treat as a propagation profile, not a "
                 "signal.")

    report = "\n".join(lines) + "\n"
    print(report)
    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        with open(args.save, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"saved: {args.save}")


if __name__ == "__main__":
    main()
