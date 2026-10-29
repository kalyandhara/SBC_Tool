"""Study: Rahu sign-change and Jupiter-in-Ketu-nakshatra event windows.

Grades the video claims that (a) Rahu-Ketu sign changes mark durable
bottoms ("Rahu-Ketu bottom formation; the April 4 low was never
broken"), and (b) declines cluster while Jupiter transits Ketu-ruled
nakshatras (Ashwini/Magha/Mula; "Guru enters Ketu's nakshatra 31 Oct,
decline begins after").

Method:
- Rahu ingresses from sbc.transits.sign_ingresses (mean node, Lahiri);
  entry = first open on/after the IST ingress date; forward returns
  +5/+10/+21 sessions; plus a bottom-hold check: does the 21-session
  low after ingress stay above the 10-session low before it
  (event rate vs 10,000 random-date baseline)?
- Jupiter stays in Ketu nakshatras from sbc.transits.nakshatra_periods;
  regime move = first-open to last-close of the stay, then forward
  +21 sessions; bootstrap vs random same-length windows.  Jupiter
  visits a Ketu nakshatra only every ~4-5 years, so n is small by
  construction.

Example:
    python scripts/study_node_jupiter_events.py
"""

import argparse
import datetime
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from sbc.transits import nakshatra_periods, sign_ingresses  # noqa: E402
from scripts.study_mars_node_conjunction import (  # noqa: E402
    bootstrap,
    event_returns,
    load_series,
)

ASSETS = ("nifty", "gold", "silver", "crude", "INDIAVIX")
KETU_NAKSHATRAS = {"Ashwini", "Magha", "Mula"}
BASELINE_DRAWS = 10_000
RNG_SEED = 42


def study_ingress_asset(asset, events, start_date, end_date):
    rows = load_series(asset, start_date, end_date)
    if len(rows) < 100:
        return None
    idx_of = {r["time"]: i for i, r in enumerate(rows)}
    per_event = []
    for ev in events:
        got = event_returns(rows, ev["ist_date"])
        if got is None:
            continue
        per_event.append({"ev": ev, "entry": rows[got[0]]["time"],
                          "rets": got[1]})
    if len(per_event) < 5:
        return None
    stats = {}
    for n in (5, 10, 21):
        moves = [p["rets"][n] for p in per_event]
        obs = float(np.mean(moves))
        boot = bootstrap(rows, [n + 1] * len(moves), obs)
        stats[n] = {"mean": obs, "median": float(np.median(moves)),
                    "win": float(np.mean([m > 0 for m in moves]) * 100),
                    "boot": boot}

    # bottom-hold check
    def holds(i):
        if i < 10 or i + 21 >= len(rows):
            return None
        pre_low = min(r["low"] for r in rows[i - 10:i + 1])
        post_low = min(r["low"] for r in rows[i:i + 22])
        return post_low >= pre_low

    hold_idx = [idx_of[p["entry"]] for p in per_event
                if p["entry"] in idx_of]
    holds_ev = [h for h in (holds(i) for i in hold_idx) if h is not None]
    rate_ev = float(np.mean(holds_ev)) * 100.0 if holds_ev else float("nan")
    rng = np.random.default_rng(RNG_SEED)
    n_rows = len(rows)
    rates = []
    for _ in range(BASELINE_DRAWS):
        picks = rng.integers(10, n_rows - 22, size=len(hold_idx))
        vals = [h for h in (holds(int(i)) for i in picks) if h is not None]
        rates.append(np.mean(vals) * 100.0)
    p_hold = float(np.mean(np.abs(np.asarray(rates) - 50.0)
                           >= abs(rate_ev - 50.0)))
    return {"asset": asset, "per_event": per_event, "stats": stats,
            "n": len(per_event), "rate_ev": rate_ev,
            "rate_base": float(np.mean(rates)), "p_hold": p_hold}


def study_jupiter_stays(asset, stays, start_date, end_date):
    rows = load_series(asset, start_date, end_date)
    if len(rows) < 100:
        return None
    moves, lens, fwd = [], [], []
    for stay in stays:
        i0 = next((i for i, r in enumerate(rows)
                   if r["time"] >= stay["start"]), None)
        if i0 is None:
            continue
        i1 = i0
        for i, r in enumerate(rows):
            if r["time"] > stay["end"]:
                break
            i1 = i
        if i1 <= i0:
            continue
        entry = rows[i0]["open"]
        moves.append((rows[i1]["close"] - entry) / entry * 100.0)
        lens.append(i1 - i0 + 1)
        if i1 + 21 < len(rows):
            fwd.append((rows[i1 + 21]["close"] / rows[i1]["close"]
                        - 1.0) * 100.0)
    if len(moves) < 5:
        return None
    obs = float(np.mean(moves))
    boot = bootstrap(rows, lens, obs)
    return {"asset": asset, "n": len(moves), "mean": obs,
            "median": float(np.median(moves)),
            "win": float(np.mean([m > 0 for m in moves]) * 100),
            "boot": boot,
            "fwd21": float(np.mean(fwd)) if fwd else float("nan")}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", default="2000-01-01")
    parser.add_argument("--end", default="2030-12-31")
    parser.add_argument("--save", default=os.path.join(
        "reports", "node_jupiter_event_study_2026-10-19.md"))
    args = parser.parse_args()

    start_date = datetime.date.fromisoformat(args.start)
    end_date = datetime.date.fromisoformat(args.end)
    today_str = datetime.date.today().isoformat()

    ingress = sign_ingresses("Rahu", start_date, end_date)
    lines = []
    lines.append("# Rahu sign-change and Jupiter-in-Ketu-nakshatra study")
    lines.append(f"\nRange {start_date} .. {end_date}; mean node, Lahiri; "
                 "entry = first open on/after event (repo convention).")
    lines.append(f"\n## Rahu sign ingresses: {len(ingress)} events\n")
    lines.append("| ist date | from -> to | status |")
    lines.append("|----------|-----------|--------|")
    for e in ingress:
        status = "upcoming" if e["ist_date"] >= today_str else "past"
        lines.append(f"| {e['ist_date']} | {e['from_label']} -> "
                     f"{e['label']} | {status} |")

    lines.append("\n## Forward returns after Rahu ingress\n")
    lines.append("| asset | n | +5d | +10d | +21d | p (+21d) | win 21d |")
    lines.append("|-------|---|-----|------|------|----------|---------|")
    for asset in ASSETS:
        res = study_ingress_asset(asset, ingress, start_date, end_date)
        if res is None:
            lines.append(f"| {asset} | - | insufficient data/events "
                         "| - | - | - | - |")
            continue
        s = res["stats"]
        lines.append(f"| {asset} | {res['n']} | {s[5]['mean']:+.2f} "
                     f"| {s[10]['mean']:+.2f} | {s[21]['mean']:+.2f} "
                     f"| {s[21]['boot']['p_two_sided']:.3f} "
                     f"| {s[21]['win']:.0f}% |")

    lines.append("\n## Bottom-hold check (21-session low after ingress "
                 "vs 10-session low before)\n")
    lines.append("| asset | event hold rate | random-date baseline | p |")
    lines.append("|-------|-----------------|----------------------|---|")
    for asset in ("nifty", "gold"):
        res = study_ingress_asset(asset, ingress, start_date, end_date)
        if res is None:
            continue
        lines.append(f"| {asset} | {res['rate_ev']:.0f}% "
                     f"| {res['rate_base']:.0f}% | {res['p_hold']:.3f} |")

    stays = [p for p in nakshatra_periods("Jupiter", start_date, end_date)
             if p["nakshatra"] in KETU_NAKSHATRAS and p["days"] >= 20.0]
    lines.append(f"\n## Jupiter in Ketu nakshatras "
                 f"(Ashwini/Magha/Mula): {len(stays)} stays\n")
    lines.append("| start | end | nakshatra |")
    lines.append("|-------|-----|-----------|")
    for p in stays:
        lines.append(f"| {p['start']} | {p['end']} | {p['nakshatra']} |")
    lines.append("\n| asset | n | stay mean % | stay win % | fwd 21d % | "
                 "random % | p |")
    lines.append("|-------|---|-------------|------------|-----------|"
                 "----------|---|")
    for asset in ("nifty", "gold", "silver", "crude"):
        res = study_jupiter_stays(asset, stays, start_date, end_date)
        if res is None:
            lines.append(f"| {asset} | - | too few events | - | - | - | - |")
            continue
        lines.append(f"| {asset} | {res['n']} | {res['mean']:+.2f} "
                     f"| {res['win']:.0f} | {res['fwd21']:+.2f} "
                     f"| {res['boot']['random_mean']:+.2f} "
                     f"| {res['boot']['p_two_sided']:.3f} |")

    lines.append("\nVideo mapping: 'Rahu-Ketu change 5-6 Dec 2026; big "
                 "planets bring the flood; falls historically happen "
                 "while Guru is in Ketu's nakshatras; Guru enters Magha "
                 "31 Oct 2026, decline begins after.' Small-n caveat: "
                 "Jupiter visits a Ketu nakshatra only every ~4-5 "
                 "years; node ingresses every ~18.6 months. Event "
                 "studies are research prompts, not validated signals.")

    report = "\n".join(lines) + "\n"
    print(report)
    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        with open(args.save, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"saved: {args.save}")


if __name__ == "__main__":
    main()
