"""Study: the video device "note the low of date D; trend flips when broken".

The AstroZ crash video (and week-ahead videos like it) repeatedly anchors a
single session's low and calls the start of a downtrend when that low breaks.
As stated the device is unfalsifiable - no validity window, no definition of
"break".  This study fixes both and measures whether the device has ever
carried information on NIFTY:

- Anchor: every session's low (K=1, the literal device) and the lowest low
  of the last 5 sessions (K=5, the swing-low variant).
- Break: close below the anchor low (close basis, decision at the close) or
  an intraday low below it (low basis), within N sessions of the anchor.
- Outcome: close-to-close forward returns from the break-day close over
  +5/+10/+21 sessions, bootstrapped against random same-length windows.

Example:
    python scripts/study_low_break_trigger.py
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

WINDOWS = (5, 10, 21)
PRIMARY_WINDOW = 10
BOOTSTRAP_ITERS = 10_000
RNG_SEED = 42


def bootstrap_closes(rows, lens, observed, iters=BOOTSTRAP_ITERS,
                     seed=RNG_SEED):
    """Two-sided p for mean close->close window returns vs random."""
    closes = np.asarray([r["close"] for r in rows])
    n = len(rows)
    lens_arr = np.asarray(lens)
    rng = np.random.default_rng(seed)
    means = np.empty(iters)
    for i in range(iters):
        s = rng.integers(0, n - lens_arr.max(), size=len(lens_arr))
        means[i] = (closes[s + lens_arr - 1] / closes[s] - 1.0).mean() * 100.0
    p_le = float((means <= observed).mean())
    return {"random_mean": float(means.mean()),
            "p_two_sided": float(min(p_le, 1.0 - p_le) * 2.0)}


def break_indices(rows, k, window, low_basis):
    """Row indices where the K-session anchor low breaks within `window`.

    Returns (n_anchors, [break_row_index per qualifying anchor]); only
    breaks with a full +21-session forward window are kept for scoring.
    """
    lows = np.asarray([r["low"] for r in rows])
    closes = np.asarray([r["close"] for r in rows])
    n = len(rows)
    anchors = 0
    hits = []
    for i in range(n - max(WINDOWS) - window):
        anchors += 1
        anchor_low = lows[max(0, i - k + 1):i + 1].min()
        for j in range(i + 1, i + window + 1):
            crossed = (lows[j] < anchor_low if low_basis
                       else closes[j] < anchor_low)
            if crossed:
                if j + max(WINDOWS) < n:
                    hits.append(j)
                break
    return anchors, hits


def forward_table(rows, hits, lines, label):
    """Close-basis forward returns from break-day closes vs random."""
    if len(hits) < 30:
        lines.append(f"\n### {label}: {len(hits)} events (too few)\n")
        return
    closes = np.asarray([r["close"] for r in rows])
    hits_arr = np.asarray(hits)
    lines.append(f"\n### {label} (n={len(hits)} breaks)\n")
    lines.append("| horizon | mean % | median % | win % | random % | p |")
    lines.append("|---------|--------|----------|-------|----------|---|")
    for h in WINDOWS:
        rets = (closes[hits_arr + h] / closes[hits_arr] - 1.0) * 100.0
        obs = float(np.mean(rets))
        boot = bootstrap_closes(rows, [h + 1] * len(rets), obs)
        lines.append(f"| +{h}d | {obs:+.2f} "
                     f"| {float(np.median(rets)):+.2f} "
                     f"| {float(np.mean(rets > 0)) * 100:.0f} "
                     f"| {boot['random_mean']:+.2f} "
                     f"| {boot['p_two_sided']:.3f} |")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", default="2007-01-01")
    parser.add_argument("--end", default=datetime.date.today().isoformat())
    parser.add_argument("--save", default=os.path.join(
        "reports", "low_break_trigger_study_2026-10-23.md"))
    args = parser.parse_args()

    rows = load_series("nifty", datetime.date.fromisoformat(args.start),
                       datetime.date.fromisoformat(args.end))
    lines = ["# 'Note the low of date D; trend flips when broken'",
             "",
             f"NIFTY {args.start} .. {args.end}, close-basis outcomes; "
             "anchor = every session; break within N sessions; entry at "
             "the break-day close; p = two-sided bootstrap vs random "
             "same-length close windows."]

    lines.append("\n## How often does the anchor low break at all?\n")
    lines.append("| anchor | basis | P(break in 5) | P(break in 10) | "
                 "P(break in 21) |")
    lines.append("|--------|-------|---------------|----------------|"
                 "----------------|")
    for k, klabel in ((1, "1-day low (literal device)"),
                      (5, "lowest low of 5 sessions")):
        for low_basis, basis in ((False, "close"), (True, "intraday")):
            probs = []
            for window in WINDOWS:
                anchors, hits = break_indices(rows, k, window, low_basis)
                probs.append(f"{len(hits) / anchors * 100:.0f}%")
            lines.append(f"| {klabel} | {basis} | {probs[0]} "
                         f"| {probs[1]} | {probs[2]} |")

    for k, klabel in ((1, "1-day low (literal device)"),
                      (5, "lowest low of 5 sessions")):
        for low_basis, basis in ((False, "close basis"),
                                 (True, "intraday basis")):
            _anchors, hits = break_indices(rows, k, PRIMARY_WINDOW,
                                           low_basis)
            forward_table(rows, hits, lines,
                          f"Break of {klabel}, {basis}, "
                          f"within {PRIMARY_WINDOW} sessions")

    lines.append(
        "\nVideo mapping: 'note the low of the market on November 1, 2026; "
        "when that day's low is broken, a negative trend begins.' Nov 1, "
        "2026 is a Sunday - no session anywhere; the nearest anchors are "
        "Oct 30 and Nov 2. The device only becomes falsifiable with a "
        "validity window (this study uses 10 sessions) and a break "
        "definition (close or intraday).")
    lines.append(
        "\nCaveat: five variant grids were checked, so treat any single "
        "small p with a multiple-testing eye. Event means are also "
        "tail-sensitive (2008, 2020); medians and p-values are the "
        "honest read.")

    report = "\n".join(lines) + "\n"
    print(report)
    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        with open(args.save, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"saved: {args.save}")


if __name__ == "__main__":
    main()
