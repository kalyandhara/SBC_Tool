"""US data releases for the Bullion Week tab, from the agencies' own calendars (B-59).

    parse_ics(text, source) -> [{date, time, name, source, et}]   times in IST
    merge(existing, fetched) -> rows for data/econ_events.json

BLS (CPI, PPI, Employment Situation, JOLTS) and BEA (GDP, Personal Income and Outlays,
International Trade) publish iCalendar files. Times are US Eastern, converted to IST with
the US daylight-time rules, so an 8:30 ET release is 18:00 IST in summer and 19:00 IST in
winter. Rows marked "source": "manual" in the JSON (e.g. Census retail sales, which has no
iCalendar feed) are kept as they are.
"""

from __future__ import annotations

import datetime as dt
import re
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
IST = ZoneInfo("Asia/Kolkata")
FEEDS = {
    "BLS": "https://www.bls.gov/schedule/news_release/bls.ics",
    "BEA": "https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics",
}
# Releases that move bullion; matched case-insensitively against SUMMARY. Order sets the label.
WATCH = [
    (r"^consumer price index", "US CPI"),
    (r"^producer price index", "US PPI"),
    (r"^employment situation", "US Nonfarm Payrolls"),
    (r"^job openings and labor turnover", "US JOLTS"),
    (r"^gdp|gross domestic product", "US GDP"),
    (r"^personal income and outlays", "US PCE / Personal Income"),
    (r"international trade in goods and services", "US Trade Balance"),
]

# FOMC decision days = day 2 of each scheduled two-day meeting; the
# statement lands 14:00 ET. 2026 is the Fed's published schedule; 2027
# is the provisional calendar (marked tentative). No official ICS feed
# exists, so these rows are generated here ("source": "static") and
# merged into data/econ_events.json by scripts/refresh_econ_calendar.py.
FOMC_2026 = ["2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
             "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09"]
FOMC_2027_TENTATIVE = ["2027-01-27", "2027-03-17", "2027-04-28",
                       "2027-06-16", "2027-07-28", "2027-09-22",
                       "2027-10-27", "2027-12-08"]
STATEMENT_ET = "14:00"


def static_rows() -> list[dict]:
    """FOMC rate decisions + election days as calendar rows (times in IST)."""
    out = []
    for dates, tentative in ((FOMC_2026, False), (FOMC_2027_TENTATIVE, True)):
        for date in dates:
            y, m, d = (int(x) for x in date.split("-"))
            et = dt.datetime(y, m, d, 14, 0, tzinfo=ET)
            ist = et.astimezone(IST)
            out.append({
                "date": ist.date().isoformat(),
                "time": ist.strftime("%H:%M"),
                "name": "US FOMC Rate Decision",
                "source": "static",
                "et": f"{STATEMENT_ET} ET",
                "title": "FOMC statement and rate decision"
                         + (" (provisional calendar)" if tentative else ""),
            })
    # US midterm elections: first Tuesday after the first Monday of November.
    out.append({
        "date": "2026-11-03", "time": "19:00",
        "name": "US Midterm Elections", "source": "static",
        "et": "-", "title": "US midterm elections (polls close through the "
                            "evening ET; results overnight IST)",
    })
    return sorted(out, key=lambda r: (r["date"], r["time"], r["name"]))


def _unfold(text: str) -> list[str]:
    """RFC 5545 line unfolding: a line starting with a space continues the previous one."""
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _when(prop: str, value: str) -> dt.datetime | None:
    if re.fullmatch(r"\d{8}", value):
        return None  # all-day entries have no release time
    if value.endswith("Z"):
        return dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.UTC)
    t = dt.datetime.strptime(value[:15], "%Y%m%dT%H%M%S")
    # BLS uses TZID=US-Eastern, BEA America/New_York; both are US Eastern time.
    return t.replace(tzinfo=ET)


def parse_ics(text: str, source: str) -> list[dict]:
    out, ev = [], None
    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            ev = {}
        elif line == "END:VEVENT" and ev is not None:
            when, summary = ev.get("when"), ev.get("summary", "")
            label = next((lab for pat, lab in WATCH if re.search(pat, summary, re.I)), None)
            if when and label:
                ist = when.astimezone(IST)
                period = ev.get("description", "")
                out.append({"date": ist.date().isoformat(), "time": ist.strftime("%H:%M"),
                            "name": label, "source": source,
                            "et": when.astimezone(ET).strftime("%H:%M ET"), "title": summary,
                            **({"detail": period} if period else {})})
            ev = None
        elif ev is not None and ":" in line:
            prop, value = line.split(":", 1)
            key = prop.split(";")[0].upper()
            if key == "DTSTART":
                ev["when"] = _when(prop, value.strip())
            elif key == "SUMMARY":
                ev["summary"] = value.strip().replace("\\,", ",")
    return out


def merge(existing: list[dict], fetched: list[dict]) -> list[dict]:
    """Keep manual rows; replace feed rows with the fresh fetch; drop duplicates."""
    feed_slots = {(r["date"], r["time"], r["name"]) for r in fetched}

    def superseded(r: dict) -> bool:  # "US CPI (Sep)" by hand vs "US CPI" from the feed, same slot
        return any((r["date"], r["time"], n) in feed_slots for n in {r["name"].split(" (")[0]})

    keep = [r for r in existing if r.get("source") == "manual" and not superseded(r)]
    seen, rows = set(), []
    for r in keep + fetched:
        key = (r["date"], r["time"], r["name"])
        if key not in seen:
            seen.add(key)
            rows.append(r)
    return sorted(rows, key=lambda r: (r["date"], r["time"], r["name"]))
