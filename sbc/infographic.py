"""Per-tab infographic cards (PNG), one per research page.

Each card is a summary of the JSON its tab already shows: the numbers come from
the same payload, so the picture and the screen cannot disagree. Nothing here
adds analysis. The layout follows the Crash Windows design: a header, a row of
key figures, then strips, bars or tables, and a method line at the foot.

    render(page, payload, stamp) -> PNG bytes
    PAGES[page].endpoint   the existing JSON endpoint the card is built from
    defaults(page, today)  query args used when the tab has no date picker
"""

from __future__ import annotations

import datetime as dt
import io
import textwrap
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

BG = "#F6F4EF"
INK = "#1C1B19"
MUTED = "#5C5850"
RULE = "#C9C3B4"
BAR = "#3A3731"
TRACK = "#E4DFD2"
NONE = "#EEEAE0"
# Score 2 to 7+, light to dark. Same ramp as the Crash Windows design.
HEAT = ["#ECE7DB", "#F1D3A0", "#E9A96A", "#D9824A", "#B9502E", "#7E2A1C"]
UP = "#2E7D5B"
DOWN = "#B9502E"

DISCLAIMER = "Research tool, not investment advice."
W_IN, H_IN, DPI = 10.8, 13.5, 100  # 1080 x 1350 px, 4:5 for sharing
M = 0.05  # side margin, figure fraction
FLOOR = 0.13  # blocks stop above the footer


@dataclass(frozen=True)
class Source:
    endpoint: str
    defaults: Callable[[dt.date], dict]


def _kp_args(today):
    # NSE is closed on weekends and holidays; the KP report refuses those days.
    from sbc.market_holidays import holiday_name, next_trading_day
    day = today if not holiday_name(today) else next_trading_day(today)
    return {"date": day.isoformat(), "instrument": "NIFTY"}


PAGES: dict[str, Source] = {
    "crash": Source("/api/crash_score_series",
                    lambda t: {"start": t.isoformat(),
                               "end": (t + dt.timedelta(days=82)).isoformat()}),
    "monthly": Source("/api/engine/monthly_projection",
                      lambda t: {"month": t.strftime("%Y-%m")}),
    "analog": Source("/api/engine/analogs", lambda t: {"date": t.isoformat()}),
    "calendar": Source("/api/engine/calendar", lambda t: {}),
    "kp": Source("/api/kp_intraday_report",
                 _kp_args),
    "kp_chart": Source("/api/kp_intraday_report",
                       _kp_args),
    "kp_report": Source("/api/kp_intraday_report",
                        _kp_args),
}


def defaults(page: str, today: dt.date) -> dict:
    return PAGES[page].defaults(today)


# ---------------------------------------------------------------- builders
# Each builder returns a spec: kicker, title, subtitle, kpis, blocks, notes, footer.

def _score_colour(score):
    if score is None:
        return NONE
    return HEAT[min(max(int(score) - 2, 0), len(HEAT) - 1)]


def _build_crash(p):
    series = p.get("series", [])
    scored = [s for s in series if "score" in s]
    scores = [s["score"] for s in scored]
    peak = max(scores) if scores else None
    peak_days = [s["date"] for s in scored if s["score"] == peak]
    reasons = Counter(r for s in scored for r in s.get("reasons", []))
    first, last = (series[0]["date"], series[-1]["date"]) if series else ("", "")
    return {
        "kicker": "NIFTY · engine crash-trigger score",
        "title": f"Crash-trigger window, {_fmt_range(first, last)}",
        "subtitle": "Daily score from the engine's bearish trigger sum, computed at noon. "
                    "Triggers are listed as the engine names them.",
        "kpis": [("Days scanned", len(series)),
                 ("Peak score", peak if peak is not None else "–"),
                 ("Days at peak", len(peak_days)),
                 ("Lowest score", min(scores) if scores else "–")],
        "blocks": [
            {"type": "strip", "heading": "Daily score",
             "values": [s.get("score") for s in series],
             "labels": (_short(first), _short(last))},
            {"type": "bars", "heading": "Trigger frequency (days active)",
             "items": [(k, v) for k, v in reasons.most_common(8)],
             "fmt": lambda v: str(v)},
            {"type": "text", "heading": "Peak days",
             "text": ", ".join(_short(d) for d in peak_days) or "none in this window"},
        ],
        "notes": ["Score range " + (f"{min(scores)} to {peak}" if scores else "n/a")
                  + ". The engine publishes no HIGH or ELEVATED thresholds, so none are shown."],
        "footer": "Method: _bearish_future_score at noon each day. " + DISCLAIMER,
    }


def _build_monthly(p):
    days = p.get("days", [])
    trading = [d for d in days if d.get("trading") and d.get("score") is not None]
    scores = [d["score"] for d in trading]
    closes = [d for d in days if d.get("nifty_close") is not None]
    last_close = closes[-1]["nifty_close"] if closes else None
    hi = max(trading, key=lambda d: d["score"]) if trading else None
    ranked = sorted(trading, key=lambda d: (-d["score"], d["date"]))
    rows = [[_short(d["date"]), _weekday(d["date"]), _num(d["score"], 1)]
            for d in ranked[:5] + ranked[-5:][::-1]] if trading else []
    return {
        "kicker": "Monthly projection · sbc composite",
        "title": f"Monthly projection, {p.get('month', '')}",
        "subtitle": "One composite score per calendar day from the sbc classical net. "
                    "Hypothetical and unvalidated.",
        "kpis": [("Trading days", len(trading)),
                 ("Average score", _num(sum(scores) / len(scores), 1) if scores else "–"),
                 ("Highest day", f"{_short(hi['date'])} ({_num(hi['score'], 1)})" if hi else "–"),
                 ("Last close", _num(last_close, 0) if last_close else "–")],
        "blocks": [
            {"type": "strip", "heading": "Daily score (grey = market closed)",
             "values": [d.get("score") if d.get("trading") else None for d in days],
             "labels": (_short(days[0]["date"]), _short(days[-1]["date"])) if days else ("", "")},
            {"type": "table", "heading": "Strongest and weakest sessions",
             "cols": ["Date", "Day", "Score"], "widths": [0.4, 0.3, 0.3],
             "rows": rows, "max_rows": 10},
        ],
        "notes": [],
        "footer": "Source: /api/engine/monthly_projection. " + DISCLAIMER,
    }


def _build_analog(p):
    s = p.get("summary", {})
    h = p.get("horizon", 5)
    lean = {1: "Up", -1: "Down", 0: "None"}.get(s.get("lean"), "–")
    tr = p.get("track_record", {})
    rows = [[d["date"], _num(d.get("similarity"), 3),
             _pct(d.get("forward", {}).get(str(h)))]
            for d in p.get("analogs", [])]
    return {
        "kicker": "Analog Lab · sky-similarity analogs",
        "title": f"Analogs for {p.get('target', '')}, {h}-session horizon",
        "subtitle": f"Past NIFTY sessions whose sky most resembles the target date "
                    f"({p.get('variant', 'overall')} tier). Only outcomes known before the target are used.",
        "kpis": [("Analogs used", s.get("n", "–")),
                 ("Lean", lean),
                 ("Median forward return", _pct(s.get("median"))),
                 ("Up share (base)", f"{_pct_plain(s.get('up_share'))} ({_pct_plain(s.get('base_up_share'))})")],
        "blocks": [
            {"type": "table", "heading": "Closest analogs",
             "cols": ["Date", "Similarity", f"Forward {h}s"], "widths": [0.4, 0.3, 0.3],
             "rows": rows, "max_rows": 10},
            {"type": "text", "heading": "Track record",
             "text": (f"Verdict: {tr.get('verdict', 'n/a')}. Hit rate {_pct_plain(tr.get('hit_rate'))} "
                      f"against a base of {_pct_plain(tr.get('baseline'))} over {tr.get('n', 0)} tests, "
                      f"right in {tr.get('years_right', 0)} of {tr.get('years', 0)} years.")},
        ],
        "notes": [p.get("caveat", "")],
        "footer": "Source: /api/engine/analogs. " + DISCLAIMER,
    }


def _build_calendar(p):
    head = p.get("headline", {})
    d1 = head.get("1", {})
    days = [d for d in p.get("days", []) if d.get("trading")]
    rows = [[_short(d["date"]), d.get("weekday", ""), d.get("tithi", ""),
             str(len(d.get("events", []))),
             f"{d['rules'].get('up', 0)}/{d['rules'].get('down', 0)}/{d['rules'].get('flat', 0)}"]
            for d in days]
    band = p.get("weeks", [{}])[0].get("band_68")
    return {
        "kicker": "Forward Calendar · sessions and sky events",
        "title": f"Forward calendar, {_fmt_range(p.get('start', ''), p.get('end', ''))}",
        "subtitle": "Next NIFTY sessions with sky events and each day's rule leans "
                    "(up / down / flat). Evidence, not a forecast.",
        "kpis": [("Next session up", _pct_plain(d1.get("probability_up"))),
                 ("5 sessions up", _pct_plain(head.get("5", {}).get("probability_up"))),
                 ("20 sessions up", _pct_plain(head.get("20", {}).get("probability_up"))),
                 ("Week 1 range (68%)", f"{_num(band[0], 0)}–{_num(band[1], 0)}" if band else "–")],
        "blocks": [
            {"type": "table", "heading": "Trading sessions",
             "cols": ["Date", "Day", "Tithi", "Events", "Rules ▲/▼/–"],
             "widths": [0.2, 0.1, 0.36, 0.12, 0.22], "rows": rows, "max_rows": 16},
        ],
        "notes": [p.get("caveat", "")],
        "footer": "Source: /api/engine/calendar. " + DISCLAIMER,
    }


def _kp_base(p):
    sig = p.get("day_signature", {})
    shifts = p.get("regime_shifts", [])
    down = sum(1 for s in shifts if s.get("direction") == "Bearish")
    up = sum(1 for s in shifts if s.get("direction") == "Bullish")
    return sig, shifts, up, down


def _kp_title(p, label):
    return f"{label}, {p.get('instrument', 'NIFTY')} {p.get('trading_day', '')}"


def _build_kp(p):
    sig, shifts, up, down = _kp_base(p)
    rows = [[h.get("time_range", ""), h.get("lord", ""), h.get("quality", ""),
             h.get("interpretation", "")] for h in sig.get("hora_slots", [])]
    return {
        "kicker": "KP Intraday · trend-change signals",
        "title": _kp_title(p, "KP Intraday"),
        "subtitle": "Day signature and hora slots from KP sub-lords. Experimental: no validated edge.",
        "kpis": [("Day lord", sig.get("day_lord", "–")),
                 ("Moon star", sig.get("moon_star", "–")),
                 ("Moon sign", sig.get("moon_sign", "–")),
                 ("Regime shifts", len(shifts))],
        "blocks": [
            {"type": "text", "heading": "Day bias", "text": sig.get("day_bias_label", "–")},
            {"type": "text", "heading": "Moon affliction gate",
             "text": sig.get("moon_affliction_gate", "–")},
            {"type": "table", "heading": "Hora slots",
             "cols": ["Time", "Lord", "Quality", "Reading"], "widths": [0.2, 0.14, 0.16, 0.5],
             "rows": rows, "max_rows": 9},
        ],
        "notes": [p.get("experimental_notice", "")],
        "footer": "Source: /api/kp_intraday_report. " + DISCLAIMER,
    }


def _build_kp_chart(p):
    _, shifts, up, down = _kp_base(p)
    counts = Counter(s.get("time", "")[:2] for s in shifts)
    hours = [f"{h:02d}" for h in range(9, 16)]
    first = shifts[0]["time"] if shifts else "–"
    return {
        "kicker": "KP Chart · NIFTY regime shifts by hour",
        "title": _kp_title(p, "KP Chart"),
        "subtitle": "Sub-lord regime changes in the session, counted by hour. "
                    "Bearish and bullish shifts are shown separately.",
        "kpis": [("Regime shifts", len(shifts)),
                 ("Bearish", down), ("Bullish", up), ("First shift", first)],
        "blocks": [
            {"type": "bars", "heading": "Shifts per hour (IST)",
             "items": [(f"{h}:00", counts.get(h, 0)) for h in hours],
             "fmt": lambda v: str(v)},
        ],
        "notes": [p.get("experimental_notice", "")],
        "footer": "Source: /api/kp_intraday_report. " + DISCLAIMER,
    }


def _build_kp_report(p):
    _, shifts, up, down = _kp_base(p)
    rows = [[s.get("time", ""), s.get("planet", ""), s.get("direction", ""),
             s.get("regime_label", ""), f"{s.get('old_sublord', '')} → {s.get('new_sublord', '')}"]
            for s in shifts]
    return {
        "kicker": "KP Intraday Report · trend-change prediction",
        "title": _kp_title(p, "KP Intraday Report"),
        "subtitle": "Every regime shift in the session, in time order.",
        "kpis": [("Shifts", len(shifts)), ("Bearish", down), ("Bullish", up),
                 ("Data", "synthetic" if p.get("data_quality", {}).get("synthetic") else "Swiss Ephemeris")],
        "blocks": [
            {"type": "table", "heading": "Regime shifts",
             "cols": ["Time", "Planet", "Direction", "Regime", "Sub-lord"],
             "widths": [0.1, 0.16, 0.14, 0.2, 0.4], "rows": rows, "max_rows": 20},
        ],
        "notes": [p.get("experimental_notice", "")],
        "footer": "Source: /api/kp_intraday_report. " + DISCLAIMER,
    }


BUILDERS = {
    "crash": _build_crash,
    "monthly": _build_monthly,
    "analog": _build_analog,
    "calendar": _build_calendar,
    "kp": _build_kp,
    "kp_chart": _build_kp_chart,
    "kp_report": _build_kp_report,
}


def render(page: str, payload: dict, stamp: str) -> bytes:
    """Draw the card for `page` from its endpoint payload. `stamp` goes in the footer."""
    spec = BUILDERS[page](payload)
    spec["footer"] = f"{spec['footer']}  ·  Generated {stamp}"
    return _draw(spec)


# ----------------------------------------------------------------- drawing

def _draw(spec: dict) -> bytes:
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=DPI, facecolor=BG)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    y = 0.955
    ax.text(M, y, spec["kicker"].upper(), fontsize=11, color=MUTED, va="top")
    y -= 0.035
    ax.text(M, y, spec["title"], fontsize=24, weight="bold", color=INK, va="top")
    y -= 0.05
    for line in textwrap.wrap(spec["subtitle"], 92):
        ax.text(M, y, line, fontsize=11, color=MUTED, va="top")
        y -= 0.024
    y -= 0.008
    ax.plot([M, 1 - M], [y, y], color=RULE, lw=1)
    y -= 0.03

    n = max(len(spec["kpis"]), 1)
    col = (1 - 2 * M) / n
    for i, (label, value) in enumerate(spec["kpis"]):
        x = M + i * col
        ax.text(x, y, str(label).upper(), fontsize=9, color=MUTED, va="top")
        ax.text(x, y - 0.026, str(value), fontsize=17, weight="bold", color=INK, va="top")
    y -= 0.095

    truncated = False
    for block in spec["blocks"]:
        y, truncated = _block(ax, block, y)
        if truncated:
            break

    ax.plot([M, 1 - M], [FLOOR, FLOOR], color=RULE, lw=1)
    notes = [n for n in spec["notes"] if n]
    if notes:
        ax.text(M, FLOOR - 0.012, "\n".join(textwrap.fill(n, 120) for n in notes),
                fontsize=9, color=MUTED, va="top", linespacing=1.4)
    footer = textwrap.fill(spec["footer"], 120)
    ax.text(M, 0.035, footer, fontsize=8.5, color=MUTED, va="bottom", linespacing=1.4)
    if truncated:
        ax.text(1 - M, 0.035, "More rows on the page", fontsize=8.5, color=MUTED,
                ha="right", va="bottom")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, facecolor=BG)
    plt.close(fig)
    return buf.getvalue()


def _heading(ax, text, y):
    ax.text(M, y, text, fontsize=12.5, weight="bold", color=INK, va="top")
    return y - 0.034


def _block(ax, block, y):
    """Draw one block below y. Returns (next y, stopped_early)."""
    kind = block["type"]
    if y < FLOOR + 0.1:
        return y, True
    y = _heading(ax, block["heading"], y)
    if kind == "strip":
        return _strip(ax, block, y)
    if kind == "bars":
        return _bars(ax, block, y)
    if kind == "table":
        return _table(ax, block, y)
    if kind == "text":
        lines = textwrap.wrap(block["text"], 105) or ["–"]
        for line in lines:
            ax.text(M, y, line, fontsize=11, color=INK, va="top")
            y -= 0.026
        return y - 0.03, False
    raise ValueError(f"unknown block type {kind!r}")


def _strip(ax, block, y):
    values = block["values"] or [None]
    cw = (1 - 2 * M) / len(values)
    h = 0.04
    for i, v in enumerate(values):
        ax.add_patch(Rectangle((M + i * cw, y - h), cw, h, color=_score_colour(v), lw=0))
    lo, hi = block["labels"]
    ax.text(M, y - h - 0.008, lo, fontsize=9, color=MUTED, va="top")
    ax.text(1 - M, y - h - 0.008, hi, fontsize=9, color=MUTED, va="top", ha="right")
    return y - h - 0.06, False


def _bars(ax: "matplotlib.axes.Axes", block: dict, y: float) -> tuple[float, bool]:
    items = block["items"]
    if not items:
        ax.text(M, y, "No data for this window.", fontsize=10.5, color=MUTED, va="top")
        return y - 0.04, False
    top = max(v for _, v in items) or 1
    label_w, bar_w = 0.3, 0.5
    for label, v in items:
        if y < FLOOR + 0.05:
            return y, True
        ax.text(M, y, str(label), fontsize=10.5, color=INK, va="top")
        x0 = M + label_w
        ax.add_patch(Rectangle((x0, y - 0.018), bar_w, 0.02, color=TRACK, lw=0))
        ax.add_patch(Rectangle((x0, y - 0.018), bar_w * v / top, 0.02, color=BAR, lw=0))
        ax.text(x0 + bar_w + 0.01, y, block["fmt"](v), fontsize=10.5, color=INK, va="top")
        y -= 0.03
    return y - 0.02, False


def _table(ax, block, y):
    cols, widths, rows = block["cols"], block["widths"], block["rows"]
    span = 1 - 2 * M
    xs, x = [], M
    for w in widths:
        xs.append(x)
        x += w * span
    for c, xc in zip(cols, xs):
        ax.text(xc, y, c.upper(), fontsize=8.5, color=MUTED, va="top")
    y -= 0.026
    ax.plot([M, 1 - M], [y + 0.004, y + 0.004], color=RULE, lw=0.8)
    if not rows:
        ax.text(M, y, "No rows for this window.", fontsize=10.5, color=MUTED, va="top")
        return y - 0.04, False
    max_rows = block.get("max_rows", len(rows))
    shown = rows[:max_rows]
    for row in shown:
        if y < FLOOR + 0.05:
            return y, True
        for cell, xc, w in zip(row, xs, widths):
            limit = max(int(w * span * 95), 6)
            text = str(cell)
            if len(text) > limit:
                text = text[:limit - 1] + "…"
            ax.text(xc, y, text, fontsize=10, color=INK, va="top")
        y -= 0.024
    if len(rows) > len(shown):
        ax.text(M, y, f"+{len(rows) - len(shown)} more on the page", fontsize=9,
                color=MUTED, va="top")
        y -= 0.024
    return y - 0.02, False


# ----------------------------------------------------------------- helpers

def _num(x, nd=0):
    if x is None:
        return "–"
    return f"{float(x):,.{nd}f}"


def _pct(x):
    """Fractional return to a signed percentage: 0.0021 -> +0.21%."""
    if x is None:
        return "–"
    return f"{float(x) * 100:+.2f}%"


def _pct_plain(x):
    """Probability or share (0-1) to a percentage: 0.529 -> 52.9%."""
    if x is None:
        return "–"
    return f"{float(x) * 100:.1f}%"


def _short(iso):
    try:
        return dt.date.fromisoformat(iso).strftime("%d %b")
    except (TypeError, ValueError):
        return iso or ""


def _weekday(iso):
    try:
        return dt.date.fromisoformat(iso).strftime("%a")
    except (TypeError, ValueError):
        return ""


def _fmt_range(a, b):
    try:
        da, db = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
    except (TypeError, ValueError):
        return f"{a} to {b}"
    return f"{da.strftime('%d %b')} – {db.strftime('%d %b %Y')}"
