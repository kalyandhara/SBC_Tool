"""Forward calendar: the next few weeks of NIFTY sessions with the evidence behind each.

    build(start=None, weeks=4) -> {
      generated_at, start, end, data_as_of, model_version, caveat,
      headline      next session's forecast at 1/5/20 sessions (probability, base, 68% band)
      validation    how many rule/analog tests each report found with an edge
      track_record  the daily ledger's live record per horizon
      weeks         per week: VIX-implied 68% range at the week's last session, and its days
      days          per calendar day: sky events; trading days add rule/analog leans and flags
    }

Events come from consecutive daily fingerprints (09:15 IST), so an ingress or
station is dated to the first 09:15 after it. Exact aspects are the day whose
orb is the local minimum (< 1 deg); the Moon is left out.

render_markdown / render_html turn the result into a report, and write()
stores both under reports/calendar/. The run_app.py loop calls generate_if_due()
so a new calendar appears every Saturday morning.
"""

from __future__ import annotations

import datetime as dt
import html
import math
from pathlib import Path

from sbc import analogs as an
from sbc import daily_ledger, fingerprint_store, market_store, research_reports
from sbc import forecast as fc
from sbc.market_holidays import holiday_name, is_trading_day, next_trading_day

IST = market_store.IST
REPORT_DIR = Path(__file__).resolve().parent.parent / "reports" / "calendar"
PREFIX = "forward_calendar"
INGRESS = ("Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu")
NAKSHATRA_CHANGE = ("Jupiter", "Saturn", "Rahu")
STATIONS = ("Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto")
EXACT_ORB = 1.0
WEEKLY_HOUR = 8  # Saturday 08:00 IST


# ── sky events ─────────────────────────────────────────────────────────────

def _fingerprints(start: dt.date, end: dt.date) -> list[dict]:
    """Current-version fingerprints for every day in [start, end], computing any gaps."""
    have = {fp["date"]: fp for fp in fingerprint_store.get_range(start.isoformat(), end.isoformat())}
    days = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
    return [have.get(d.isoformat()) or fingerprint_store.get(d.isoformat()) for d in days]


def _aspect_orbs(fp: dict) -> dict[tuple, float]:
    return {(a["a"], a["b"], a["aspect"]): a["orb"] for a in fp["aspects"]
            if "Moon" not in (a["a"], a["b"])}


def events_between(prev: dict, cur: dict, nxt: dict | None) -> list[str]:
    """Sky events dated to `cur` (compared with the day before and, for exact aspects, after)."""
    out = []
    pp, cp = prev["planets"], cur["planets"]
    for n in INGRESS:
        if pp[n]["sign"] != cp[n]["sign"]:
            out.append(f"{n} enters {cp[n]['sign_name']}")
    for n in NAKSHATRA_CHANGE:
        if pp[n]["nakshatra"] != cp[n]["nakshatra"]:
            out.append(f"{n} enters {cp[n]['nakshatra_name']} nakshatra")
    for n in STATIONS:
        if pp[n]["retrograde"] != cp[n]["retrograde"]:
            out.append(f"{n} stations {'retrograde' if cp[n]['retrograde'] else 'direct'}")
    if nxt is not None:
        before, after = _aspect_orbs(prev), _aspect_orbs(nxt)
        for key, orb in sorted(_aspect_orbs(cur).items()):
            if orb < EXACT_ORB and orb <= before.get(key, 99) and orb < after.get(key, 99):
                out.append(f"{key[0]} {key[2]} {key[1]} exact ({orb:.2f}°)")
    ecl = cur["eclipse"]
    if ecl["days_to"] is not None and ecl["days_to"] < 1:
        out.append(f"{ecl['to_type'].capitalize()} eclipse")
    t, tp = cur["panchang"]["tithi"], prev["panchang"]["tithi"]
    if t != tp and t in (15, 30):
        out.append("Purnima (full Moon)" if t == 15 else "Amavasya (new Moon)")
    return out


# ── the calendar ───────────────────────────────────────────────────────────

def _lean_counts(components: list[dict]) -> dict:
    rules = [c for c in components if c["kind"] == "directional" and not c["name"].startswith("analog_")]
    return {"up": sum(1 for c in rules if (c["lean"] or 0) > 0),
            "down": sum(1 for c in rules if (c["lean"] or 0) < 0),
            "flat": sum(1 for c in rules if not c["lean"])}


def _band(close: float, vix: float | None, sessions: int) -> list[float] | None:
    if not vix or not math.isfinite(vix):
        return None
    sigma = vix / 100.0 / math.sqrt(252) * math.sqrt(sessions)
    return [round(close * (1 - sigma), 1), round(close * (1 + sigma), 1)]


def build(start: str | None = None, weeks: int = 4, now: dt.datetime | None = None,
          history: an.History | None = None) -> dict:
    """Forward calendar from `start` (default: the next trading day) for `weeks` weeks."""
    if not 1 <= weeks <= 8:
        raise ValueError("weeks must be 1-8")
    now = (now or dt.datetime.now(IST)).astimezone(IST)
    first = (dt.date.fromisoformat(start) if start
             else next_trading_day(now.date(), inclusive=now.time() < dt.time(9, 15)))
    first = next_trading_day(first)
    end = first + dt.timedelta(days=7 * weeks - 1)
    history = history or an.load_nifty_history()

    fps = _fingerprints(first - dt.timedelta(days=1), end + dt.timedelta(days=1))
    entry_close = float(history.closes[-1])
    vix_rows = market_store.get_daily("INDIAVIX", end=history.dates[-1])
    vix = vix_rows[-1]["close"] if vix_rows else None

    days, sessions = [], 0
    for i in range(1, len(fps) - 1):
        day = dt.date.fromisoformat(fps[i]["date"])
        row: dict = {"date": day.isoformat(), "weekday": day.strftime("%a"),
                     "trading": is_trading_day(day), "holiday": holiday_name(day),
                     "events": events_between(fps[i - 1], fps[i], fps[i + 1])}
        if row["trading"]:
            sessions += 1
            f = fc.forecast(day.isoformat(), 1, history=history)
            comps = {c["name"]: c for c in f["components"]}
            row.update({
                "session": sessions,
                "rules": _lean_counts(f["components"]),
                "analogs": {n[len("analog_"):]: comps[n]["lean"] for n in comps if n.startswith("analog_")},
                "flags": [c["name"] for c in f["components"] if c["kind"] == "event" and c["flag"]],
                "validated": f["validated"],
                "moon": f["sky"]["moon"],
                "tithi": f["sky"]["tithi"],
            })
        days.append(row)

    week_rows = []
    for w in range(weeks):
        span = [d for d in days if first + dt.timedelta(days=7 * w) <= dt.date.fromisoformat(d["date"])
                < first + dt.timedelta(days=7 * (w + 1))]
        last = max((d["session"] for d in span if d["trading"]), default=None)
        week_rows.append({"start": span[0]["date"], "end": span[-1]["date"],
                          "sessions": sum(1 for d in span if d["trading"]),
                          "band_68": _band(entry_close, vix, last) if last else None,
                          "events": sum(len(d["events"]) for d in span)})

    headline = {}
    for h in fc.HORIZONS:
        f = fc.forecast(first.isoformat(), h, history=history)
        headline[str(h)] = {"probability_up": f["probability_up"], "base_up": f["base"]["up_share"],
                            "band_68": f["expected_range"].get("band_68"),
                            "validated": f["validated"]}

    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "start": first.isoformat(),
        "end": end.isoformat(),
        "data_as_of": history.dates[-1],
        "entry_close": entry_close,
        "vix": vix,
        "model_version": fc.model_version(),
        "headline": headline,
        "validation": research_reports.counts(),
        "track_record": {str(h): daily_ledger.summary(h) for h in fc.HORIZONS},
        "weeks": week_rows,
        "days": days,
        "caveat": fc.CAVEAT,
    }


# ── rendering ──────────────────────────────────────────────────────────────

def _pct(x: float | None) -> str:
    return "–" if x is None else f"{100 * x:.1f}%"


def _band_text(b: list[float] | None) -> str:
    return "–" if not b else f"{b[0]:,.0f} – {b[1]:,.0f}"


def _arrow(lean: int | None) -> str:
    return {1: "▲", -1: "▼"}.get(lean or 0, "·")


def _record_text(r: dict) -> str:
    if not r.get("scored"):
        return f"{r.get('frozen', 0)} frozen, none scored yet"
    return (f"{r['scored']} scored · Brier {r['brier']:.3f} vs base rate {r['base_brier']:.3f}")


def _day_cells(d: dict) -> list[str]:
    name = f"{d['date']} {d['weekday']}"
    if not d["trading"]:
        status = d["holiday"] or "closed"
        return [name, status, "", "", "", "; ".join(d["events"])]
    r = d["rules"]
    analogs = " ".join(f"{k[0].upper()}{_arrow(v)}" for k, v in d["analogs"].items())
    return [name, f"{d['moon']} · {d['tithi']}", f"{r['up']}▲ {r['down']}▼",
            analogs, ", ".join(d["flags"]), "; ".join(d["events"])]


COLUMNS = ["Day", "Moon · tithi", "Rules", "Analogs (O/S/M/F)", "Volatility flags", "Sky events"]


def _intro(cal: dict) -> list[str]:
    v = cal["validation"]
    passed = sum(x["passed"] for x in v.values())
    tests = sum(x["tests"] for x in v.values())
    return [
        f"Generated {cal['generated_at']} · NIFTY data as of {cal['data_as_of']} "
        f"(close {cal['entry_close']:,.1f}, India VIX {'–' if cal['vix'] is None else format(cal['vix'], '.2f')}) · model {cal['model_version']}",
        f"Validation so far: {passed} of {tests} astro tests passed. "
        "Rule and analog leans are shown as evidence, not as a forecast: none has beaten the market's drift.",
    ]


def render_markdown(cal: dict) -> str:
    lines = [f"# NIFTY forward calendar · {cal['start']} → {cal['end']}", ""]
    lines += [f"_{t}_  " for t in _intro(cal)] + [""]
    lines += ["## Next session", "", "| Horizon | P(up) | Base rate | 68% range | Live record |",
              "|---|---|---|---|---|"]
    for h, x in cal["headline"].items():
        lines.append(f"| {h} session{'s' if h != '1' else ''} | {_pct(x['probability_up'])} | "
                     f"{_pct(x['base_up'])} | {_band_text(x['band_68'])} | {_record_text(cal['track_record'][h])} |")
    lines += ["", "## Weekly range (VIX-implied, from the last close)", "",
              "| Week | Sessions | 68% range at week end | Sky events |", "|---|---|---|---|"]
    for w in cal["weeks"]:
        lines.append(f"| {w['start']} → {w['end']} | {w['sessions']} | {_band_text(w['band_68'])} | {w['events']} |")
    lines += ["", "## Day by day", "", "| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    for d in cal["days"]:
        lines.append("| " + " | ".join(c.replace("|", "/") for c in _day_cells(d)) + " |")
    lines += ["", "Rules: how many directional rules and factors lean up / down that day. Analogs: lean of the",
              "whole-sky, slow, medium and fast analog sets (▲ up, ▼ down, · none).", "", f"_{cal['caveat']}_", ""]
    return "\n".join(lines)


_CSS = """
:root{--bg:#fff;--fg:#1d2330;--muted:#5b6474;--line:#dfe3ea;--head:#f3f5f8;--up:#13795b;--down:#b42318}
@media (prefers-color-scheme:dark){:root{--bg:#12161d;--fg:#e6e9ef;--muted:#9aa3b2;--line:#2a313d;--head:#1a2029;--up:#4cc79a;--down:#f0786c}}
body{background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif;margin:0;padding:16px;max-width:1200px}
h1{font-size:20px}h2{font-size:16px;margin-top:24px}.muted{color:var(--muted)}
table{border-collapse:collapse;width:100%;margin:8px 0}th,td{border:1px solid var(--line);padding:4px 8px;text-align:left;vertical-align:top}
th{background:var(--head)}tr.closed td{color:var(--muted)}.wrap{overflow-x:auto}
"""


def _table(head: list[str], rows: list[list[str]], classes: list[str] | None = None) -> str:
    out = ["<div class='wrap'><table><tr>" + "".join(f"<th>{html.escape(h)}</th>" for h in head) + "</tr>"]
    for i, row in enumerate(rows):
        cls = f" class='{classes[i]}'" if classes and classes[i] else ""
        out.append(f"<tr{cls}>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>")
    return "".join(out) + "</table></div>"


def render_html(cal: dict) -> str:
    title = f"NIFTY forward calendar · {cal['start']} → {cal['end']}"
    head = [[f"{h} session{'s' if h != '1' else ''}", _pct(x["probability_up"]), _pct(x["base_up"]),
             _band_text(x["band_68"]), _record_text(cal["track_record"][h])] for h, x in cal["headline"].items()]
    weeks = [[f"{w['start']} → {w['end']}", w["sessions"], _band_text(w["band_68"]), w["events"]]
             for w in cal["weeks"]]
    days = [_day_cells(d) for d in cal["days"]]
    return "".join([
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        f"<title>{html.escape(title)}</title><style>{_CSS}</style></head><body>",
        f"<h1>{html.escape(title)}</h1>",
        *(f"<p class='muted'>{html.escape(t)}</p>" for t in _intro(cal)),
        "<h2>Next session</h2>",
        _table(["Horizon", "P(up)", "Base rate", "68% range", "Live record"], head),
        "<h2>Weekly range (VIX-implied, from the last close)</h2>",
        _table(["Week", "Sessions", "68% range at week end", "Sky events"], weeks),
        "<h2>Day by day</h2>",
        _table(COLUMNS, days, ["" if d["trading"] else "closed" for d in cal["days"]]),
        "<p class='muted'>Rules: how many directional rules and factors lean up / down that day. "
        "Analogs: lean of the whole-sky (O), slow (S), medium (M) and fast (F) analog sets.</p>",
        f"<p class='muted'><em>{html.escape(cal['caveat'])}</em></p></body></html>",
    ])


def write(cal: dict, key: str, directory: Path | None = None) -> dict:
    """Write forward_calendar_<key>.{md,html,json}; returns the paths."""
    import json
    directory = directory or REPORT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    paths = {}
    for ext, text in (("md", render_markdown(cal)), ("html", render_html(cal)),
                      ("json", json.dumps(cal, indent=1))):
        path = directory / f"{PREFIX}_{key}.{ext}"
        path.write_text(text, encoding="utf-8")
        paths[ext] = str(path)
    return paths


# ── schedule ───────────────────────────────────────────────────────────────

def week_key(now: dt.datetime) -> str:
    """The Saturday that owns `now`: the latest Saturday 08:00 IST at or before it."""
    now = now.astimezone(IST)
    sat = now.date() - dt.timedelta(days=(now.weekday() - 5) % 7)
    if sat == now.date() and now.hour < WEEKLY_HOUR:
        sat -= dt.timedelta(days=7)
    return sat.isoformat()


def reports(directory: Path | None = None) -> list[dict]:
    """Stored calendars, newest first."""
    directory = directory or REPORT_DIR
    out = []
    for path in sorted(directory.glob(f"{PREFIX}_*.html"), reverse=True):
        out.append({"key": path.stem[len(PREFIX) + 1:], "html": path.name,
                    "md": path.with_suffix(".md").name})
    return out


def generate_if_due(now: dt.datetime | None = None, directory: Path | None = None,
                    refresh_fingerprints: bool = True) -> dict | None:
    """Write this week's calendar unless it exists; returns the paths written or None.

    Before building it tops up data/fingerprints.db (stale rows are purged and the
    1990-2035 range rebuilt), so an astro code change can't leave the calendar on old data.
    """
    now = (now or dt.datetime.now(IST)).astimezone(IST)
    key = week_key(now)
    directory = directory or REPORT_DIR
    if (directory / f"{PREFIX}_{key}.html").exists():
        return None
    if refresh_fingerprints:
        fingerprint_store.purge_stale()
        fingerprint_store.build()
    return write(build(now=now), key, directory)
