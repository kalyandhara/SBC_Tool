"""Validate the B-39 swing-window model (sbc.swing_validation).

  python scripts/validate_swing.py               # writes docs/research/swing_validation_<date>.md + .json
  python scripts/validate_swing.py --perm 200 --sets 200
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc import swing_validation as sv  # noqa: E402
from scripts.validate_rules import _bps, _num, _pct, render, write  # noqa: E402

INTRO = [
    "Heliocentric Earth–planet aspects (conjunction, opposition, trine, square, sextile, quincunx, "
    "semi-square, sesquiquadrate; orb ±2°) as trend-reversal zones. Part A grades the *timing*: "
    "does NIFTY reverse its 10-session trend, or move more, on sessions inside a window? "
    "Part B (below) grades the full model with the Gann + Fibonacci + indicator exit.",
]


def _trade_row(label: str, s: dict) -> str:
    if not s.get("n"):
        return f"| {label} | 0 | – | – | – | – | – |"
    return (f"| {label} | {s['n']} | {_pct(s['mean_return'])} | {_pct(s['win_rate'], 0)} | "
            f"{_bps(s['mean_excess'])} | {s['mean_bars']:.1f} | {_pct(s['mean_mae'])} |")


def render_report(report: dict) -> str:
    text = render(report, title="Swing-window model (B-39) — entry timing",
                  generator="scripts/validate_swing.py", intro=INTRO)
    lines = [f"Sessions inside at least one window: {_pct(report['window_share'], 0)}.", "",
             "### Control: the same reversal rule on every session (no astro)", "",
             "| h | n | excess bps | hit | base | p | verdict |", "|---|---|---|---|---|---|---|"]
    for r in report["control"]:
        lines.append(f"| {r['horizon']} | {r['n']} | {_bps(r.get('excess'))} | {_pct(r.get('hit_rate'), 1)} | "
                     f"{_pct(r.get('baseline'), 1)} | {_num(r.get('p'))} | {r['verdict']} |")
    lines += ["", "### Beyond the market controls", "",
              "| signal | h | beta bps | beta raw bps | q | verdict |", "|---|---|---|---|---|---|"]
    for r in sorted(report["results"], key=lambda r: (r["rule"], r["horizon"])):
        b = r["beyond_market"]
        lines.append(f"| {r['rule']} | {r['horizon']} | {_bps(b['beta'])} | {_bps(b['beta_raw'])} | "
                     f"{_num(b['q'])} | {b['verdict']} |")

    m = report["model"]
    lines += ["", "## Part B — the full model (window entry → confluence exit), 2008 onward", "",
              f"{m['windows']} aspect windows. One position at a time; entry at the close of the window's first "
              f"session, direction = reversal of the 10-session trend. Excess = return minus the drift for the bars "
              f"held ({_bps(m['drift_per_bar'])} bps per session), in the trade's direction.", ""]
    for label, res in m["models"].items():
        rnd = res["random"]
        lines += [f"### Exit: {label} confluence", "",
                  "| exit | trades | mean return | win | excess bps | bars | mean MAE |",
                  "|---|---|---|---|---|---|---|",
                  _trade_row("**model (confluence)**", res["model"])]
        lines += [_trade_row(k, v) for k, v in res["baselines"].items()]
        lines += ["", f"Random entries ({rnd['sets']} sets, same size, same direction rule and exit): mean excess "
                  f"{_bps(rnd['mean'])} bps, 90% of sets between {_bps(rnd['p5'])} and {_bps(rnd['p95'])}. "
                  f"Model percentile p = {_num(rnd['p_value'])}. **Verdict: {res['verdict']}.**", ""]
    return text + "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--perm", type=int, default=1000)
    parser.add_argument("--sets", type=int, default=sv.RANDOM_SETS)
    args = parser.parse_args()
    t0 = time.perf_counter()
    report = sv.run(n_perm=args.perm, n_sets=args.sets)
    write(report, "swing_validation", render_report(report))
    print(f"wrote docs/research/swing_validation_*.md/.json in {time.perf_counter() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
