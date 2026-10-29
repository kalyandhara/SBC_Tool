"""Sector rotation around the core planetary events (phase 1, SBC_Tool-5fy.7).

  python scripts/sector_rotation_report.py    # writes reports/sector_rotation_<date>.md + .json

The CLI refuses to run until the pre-registration records a sector-set decision
(addendum 1 leaves the Media, Healthcare and Oil & Gas indices open).
build() takes its series as an argument, so tests can run on a frozen fixture.
"""

import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc import market_store as ms  # noqa: E402
from sbc import sector_rotation as sr  # noqa: E402
from sbc import stats as st  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREREG = os.path.join(ROOT, "docs", "research", "sector_rotation_preregistration_2026-10-29.md")
REPORTS = os.path.join(ROOT, "reports")
SECTOR_KEYS = list(ms.SECTOR_SYMBOLS)
HORIZONS = (5, 10, 20)
ERA_OOS_START = "2021-10-01"
SHORT_HISTORY_SESSIONS = 2500  # sectors with fewer sessions are flagged in the report
SECTOR_SET_MARKER = "Sector set decision:"


def sector_set_decided(prereg_text: str) -> bool:
    """True once the pre-registration records a sector-set decision line."""
    return any(line.strip().startswith(SECTOR_SET_MARKER) for line in prereg_text.splitlines())


def _aligned(bars: list[dict], sessions: list[str]) -> np.ndarray:
    """Close on each NIFTY session; NaN where the series has no positive close."""
    by_day = {b["date"]: b["close"] for b in bars if b["close"] and b["close"] > 0}
    return np.array([by_day.get(d, np.nan) for d in sessions], dtype=float)


def _mean(values: list) -> float | None:
    """Mean of the finite values; None when there are none."""
    x = [v for v in values if v is not None and np.isfinite(v)]
    return float(np.mean(x)) if x else None


def _price_hash(series: dict[str, list[dict]]) -> str:
    h = hashlib.sha256()
    for key in sorted(series):
        for b in series[key]:
            h.update(f"{key}|{b['date']}|{b['close']!r}\n".encode())
    return h.hexdigest()


def _prereg_commit() -> str | None:
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%h", "--", PREREG],
                             cwd=ROOT, capture_output=True, text=True, check=True)
        return out.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def build(n_perm: int = st.N_PERMUTATIONS, seed: int = 0, series: dict | None = None) -> dict:
    """Full descriptive result. Raises FileNotFoundError if the pre-registration is missing."""
    with open(PREREG, encoding="utf-8") as f:  # the registration must exist before any output
        prereg_text = f.read()
    if series is None:
        series = {k: ms.get_daily(k) for k in ["NIFTY"] + SECTOR_KEYS}
    nifty_bars = series["NIFTY"]
    sessions = [b["date"] for b in nifty_bars]
    nifty = _aligned(nifty_bars, sessions)
    sector_close = {k: _aligned(series[k], sessions) for k in SECTOR_KEYS}

    events = sr.core_events(int(sessions[0][:4]), int(sessions[-1][:4]))
    anchored = []
    for e in events:
        a = sr.anchor_session(sessions, e["date"])
        if a is not None:
            anchored.append({**e, "anchor": a})
    clusters_list = sr.cluster([e["anchor"] for e in anchored])
    cluster_of = {}
    for cid, members in enumerate(clusters_list):
        for a in members:
            cluster_of[a] = cid
    cluster_id = np.full(len(sessions), -1)
    for a, cid in cluster_of.items():
        cluster_id[a] = cid

    rows, occurrence = [], []
    daily_sector = defaultdict(list)  # (event, h, sector) -> daily returns inside each window
    daily_excess = defaultdict(list)  # (event, h, sector) -> daily sector minus NIFTY
    particip = defaultdict(list)      # (event, h) -> per-occurrence share of sectors up
    for e in anchored:
        for h in HORIZONS:
            nret = sr.window_return(nifty, e["anchor"], h)
            nifty_daily = sr.daily_returns(nifty, e["anchor"], h)
            rets = {k: sr.window_return(sector_close[k], e["anchor"], h) for k in SECTOR_KEYS}
            share = sr.participation(rets)
            if share is not None:
                particip[(e["event"], h)].append(share)
            for k in SECTOR_KEYS:
                sec_daily = sr.daily_returns(sector_close[k], e["anchor"], h)
                daily_sector[(e["event"], h, k)].append(sec_daily)
                daily_excess[(e["event"], h, k)].append(sec_daily - nifty_daily)
            ranked = sr.rank_sectors(rets)
            top5 = [s for s, _ in ranked[:5]]
            label, _ = sr.rotation_pattern(top5) if len(top5) == 5 else ("insufficient", top5)
            occurrence.append({"date": e["date"], "event": e["event"], "h": h,
                               "cluster": int(cluster_of[e["anchor"]]), "nifty": nret,
                               "label": label, "top5": top5, "top": top5[0] if top5 else None})
            rank_of = {s: i + 1 for i, (s, _) in enumerate(ranked)}
            for k in SECTOR_KEYS:
                if np.isfinite(rets[k]) and np.isfinite(nret):
                    rows.append({"sector": k, "event": e["event"], "h": h, "ret": rets[k],
                                 "nifty": nret, "cluster": int(cluster_of[e["anchor"]]),
                                 "rank": rank_of.get(k)})

    era_oos = np.array([s >= ERA_OOS_START for s in sessions])
    # sr.CONFIRMATORY is empty, so there is nothing to grade. grade_confirmatory is
    # only called when the pre-registration lists a hypothesis.
    confirmatory = []

    events_out = {}
    for name in sorted({e["event"] for e in anchored}):
        raw = sum(1 for e in anchored if e["event"] == name)
        cl = len({cluster_of[e["anchor"]] for e in anchored if e["event"] == name})
        events_out[name] = {"raw": raw, "clusters": cl}

    descriptive, rotation, forecast = {}, {}, {}
    for name in events_out:
        descriptive[name], rotation[name], forecast[name] = {}, {}, {}
        for h in HORIZONS:
            sub = [r for r in rows if r["event"] == name and r["h"] == h]
            per_sector = []
            for k in SECTOR_KEYS:
                ks = [r for r in sub if r["sector"] == k]
                if not ks:
                    continue
                summ = sr.descriptive_summary(ks)
                rel = [r["ret"] - r["nifty"] for r in ks]
                key = (name, h, k)
                per_sector.append({"sector": k, "n_raw": summ["n_raw"],
                                   "n_clusters": summ["n_clusters"],
                                   "mean_relative": float(np.mean(rel)),
                                   "volatility": sr.volatility(np.concatenate(daily_sector[key])),
                                   "sharpe": sr.sharpe(np.concatenate(daily_excess[key])),
                                   "top5_rate": summ["top5_rate"], "beat_rate": summ["beat_rate"]})
            descriptive[name][str(h)] = sorted(per_sector, key=lambda r: r["mean_relative"], reverse=True)
            occ = [o for o in occurrence if o["event"] == name and o["h"] == h]
            rotation[name][str(h)] = {"labels": dict(Counter(o["label"] for o in occ)), "occurrences": len(occ)}
            forecast[name][str(h)] = sr.forecast_confidence({"passed": False})

    # Event-level radar values: each axis averages the event's sectors (descriptive, not graded).
    event_summary = {}
    for name in events_out:
        event_summary[name] = {}
        for h in HORIZONS:
            ps = descriptive[name][str(h)]
            event_summary[name][str(h)] = {
                "return": _mean([r["mean_relative"] for r in ps]),
                "volatility": _mean([r["volatility"] for r in ps]),
                "win_rate": _mean([r["beat_rate"] for r in ps]),
                "sharpe": _mean([r["sharpe"] for r in ps]),
                "participation": _mean(particip[(name, h)]),
            }

    # Heatmap colour: z-score of mean relative strength across every event x sector cell at that horizon.
    for h in HORIZONS:
        cells = [r for name in events_out for r in descriptive[name][str(h)]]
        vals = np.array([r["mean_relative"] for r in cells], dtype=float)
        mu, sd = np.nanmean(vals), np.nanstd(vals, ddof=1) if len(vals) > 1 else float("nan")
        for r in cells:
            z = (r["mean_relative"] - mu) / sd if sd and np.isfinite(sd) else float("nan")
            r["heat"] = sr.heat_bucket(z)

    # Rotation wheel: mean relative return per capital-flow group (descriptive, not graded).
    wheel = {}
    for name in events_out:
        wheel[name] = {}
        for h in HORIZONS:
            by_key = {r["sector"]: r["mean_relative"] for r in descriptive[name][str(h)]}
            wheel[name][str(h)] = {g: _mean([by_key.get(k) for k in ks])
                                   for g, ks in sr.WHEEL_GROUPS.items()}

    # Sankey: event -> strongest sector (occurrences where it ranked first) -> NIFTY outcome over the window.
    flows = {}
    for name in events_out:
        flows[name] = {}
        for h in HORIZONS:
            occ = [o for o in occurrence if o["event"] == name and o["h"] == h]
            ranked = [o for o in occ if o["top"]]
            links = Counter()
            nifty_missing = 0
            for o in ranked:
                links[(name, o["top"])] += 1
                if o["nifty"] is not None and np.isfinite(o["nifty"]):
                    links[(o["top"], "NIFTY up" if o["nifty"] > 0 else "NIFTY down")] += 1
                else:
                    nifty_missing += 1
            flows[name][str(h)] = {
                "links": [{"source": s_, "target": t_, "value": v} for (s_, t_), v in sorted(links.items())],
                "unranked": len(occ) - len(ranked),  # no sector had a finite return in the window
                "nifty_missing": nifty_missing,
            }

    coverage = {}
    for k in SECTOR_KEYS:
        bars = [b for b in series[k] if b["close"] and b["close"] > 0]
        coverage[k] = {"first": bars[0]["date"] if bars else None,
                       "last": bars[-1]["date"] if bars else None, "sessions": len(bars),
                       "short_history": len(bars) < SHORT_HISTORY_SESSIONS}

    return {
        "preregistration": os.path.relpath(PREREG, ROOT).replace(os.sep, "/"),
        "preregistration_commit": _prereg_commit(),
        "sector_set_decided": sector_set_decided(prereg_text),
        "era_boundary": ERA_OOS_START,
        "oos_sessions": int(era_oos.sum()),
        "n_permutations": n_perm,
        "seed": seed,
        "input": {"last_session": {k: series[k][-1]["date"] if series[k] else None
                                   for k in ["NIFTY"] + SECTOR_KEYS},
                  "price_sha256": _price_hash(series),
                  "sessions": len(sessions)},
        "events": events_out,
        "coverage": coverage,
        "descriptive": descriptive,
        "event_summary": event_summary,
        "wheel": wheel,
        "flows": flows,
        "rotation": rotation,
        "forecast": forecast,
        "confirmatory": confirmatory,
        "breadth": "not computed",
    }


def render(out: dict) -> str:
    lines = [
        "# Sector rotation around planetary events (phase 1)", "",
        f"Pre-registration: `{out['preregistration']}`"
        + (f" (commit {out['preregistration_commit']})" if out["preregistration_commit"] else ""),
        "",
        "**Confirmatory outcome: empty list. No pre-registered edge.** Every table below is descriptive, not graded.",
        "",
        "Forecast: each event carries \"No call\". This is a historical pattern, not trading advice.",
        "",
        "Breadth: not computed (needs constituent data, phase 2).",
        "",
        f"Out-of-sample era from {out['era_boundary']}: {out['oos_sessions']} sessions.",
        "",
        "## Coverage", "",
        "| Sector | First | Last | Sessions | Note |", "|---|---|---|---|---|",
    ]
    for k, c in out["coverage"].items():
        note = "short history" if c["short_history"] else ""
        lines.append(f"| {k} | {c['first']} | {c['last']} | {c['sessions']} | {note} |")
    lines += ["", "## Event counts", "", "| Event | Raw | Clusters |", "|---|---|---|"]
    for name, c in out["events"].items():
        lines.append(f"| {name} | {c['raw']} | {c['clusters']} |")
    lines += ["", "## Rotation labels (descriptive, not graded)", ""]
    for name, by_h in out["rotation"].items():
        for h, r in by_h.items():
            lines.append(f"- {name}, T+{h}: {r['occurrences']} occurrences, labels {r['labels']}")
    lines += ["", "## Sector mean relative return (descriptive, not graded)", ""]
    for name, by_h in out["descriptive"].items():
        for h, rows in by_h.items():
            lines += [f"### {name}, T+{h}", "", "| Sector | Raw | Clusters | Mean rel. | Top-5 rate | Beat rate |",
                      "|---|---|---|---|---|---|"]
            for r in rows:
                t5 = "–" if r["top5_rate"] is None else f"{r['top5_rate']:.2f}"
                br = "–" if r["beat_rate"] is None else f"{r['beat_rate']:.2f}"
                lines.append(f"| {r['sector']} | {r['n_raw']} | {r['n_clusters']} | "
                             f"{r['mean_relative']:+.4f} | {t5} | {br} |")
            lines.append("")
    lines += ["## Inputs", "", f"Price rows SHA-256: `{out['input']['price_sha256']}`", "",
              "Last session per series:", ""]
    for k, d in out["input"]["last_session"].items():
        lines.append(f"- {k}: {d}")
    return "\n".join(lines) + "\n"


def main() -> int:
    with open(PREREG, encoding="utf-8") as f:
        if not sector_set_decided(f.read()):
            print("Refusing to run: the pre-registration has no 'Sector set decision:' line. "
                  "Record the decision in an addendum first (addendum 1 leaves three sectors open).")
            return 1
    out = build()
    stamp = dt.date.today().isoformat()
    os.makedirs(REPORTS, exist_ok=True)
    with open(os.path.join(REPORTS, f"sector_rotation_{stamp}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
    with open(os.path.join(REPORTS, f"sector_rotation_{stamp}.md"), "w", encoding="utf-8") as f:
        f.write(render(out))
    print(f"wrote reports/sector_rotation_{stamp}.md and .json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
