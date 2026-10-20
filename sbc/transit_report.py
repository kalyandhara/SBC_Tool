"""Planet Transit Report: multi-sheet Excel workbook builder.

Builds the "exact transit timings" workbook: Report Info (settings,
ayanamsa value, start positions, legend), Zodiac Transits, Nakshatra
Transits, Pada Transits, an All-Transits Timeline (merged, date-wise,
ready to line up against Nifty/Bank Nifty data) and a Stations (R-D)
sheet.  All times are shown in the selected city's local time
(cities.db timezones); every transit carries motion (D/R/S), re-entry
and gandanta flags.

Engine: sbc.transits (Swiss Ephemeris, selectable ayanamsa and
mean/true node) + sbc.stations for the stations sheet.

    build_workbook(config) -> (BytesIO, filename)

Example config:
    {"city": "Mumbai", "start": "2026-01-01", "end": "2026-12-31",
     "planets": ["Sun", "Mercury"], "types": ["sign", "nakshatra"],
     "ayanamsa": "lahiri", "node_mode": "mean"}
"""

from __future__ import annotations

import datetime as dt
import io

import swisseph as swe
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from . import cities, stations, transits
from .market_calendar import NAKSHATRA_LORDS
from .nakshatra import nakshatra_of

PLANET_NAMES = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter",
                "Saturn", "Rahu", "Ketu", "Uranus", "Neptune", "Pluto")
TRANSIT_TYPES = ("sign", "nakshatra", "pada")
STATION_BODIES = ("Mercury", "Venus", "Mars", "Jupiter", "Saturn",
                  "Uranus", "Neptune", "Pluto", "Rahu")

RASHI_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

MAX_RANGE_DAYS = 3660  # stations.py limit

_HEADER_FILL = PatternFill("solid", fgColor="1F2937")
_HEADER_FONT = Font(bold=True, color="FFFFFF")


def default_config() -> dict:
    today = dt.date.today()
    return {
        "city": "Mumbai",
        "start": today.isoformat(),
        "end": (today + dt.timedelta(days=365)).isoformat(),
        "planets": list(PLANET_NAMES),
        "types": list(TRANSIT_TYPES),
        "ayanamsa": "lahiri",
        "node_mode": "mean",
    }


def normalize_config(cfg: dict) -> dict:
    out = default_config() | (cfg or {})
    out["planets"] = [p for p in (out.get("planets") or PLANET_NAMES)
                      if p in PLANET_NAMES] or list(PLANET_NAMES)
    out["types"] = [t for t in (out.get("types") or TRANSIT_TYPES)
                    if t in TRANSIT_TYPES]
    if not out["types"]:
        out["types"] = list(TRANSIT_TYPES)
    out["ayanamsa"] = (out["ayanamsa"] if out["ayanamsa"] in
                       transits.AYANAMSA_MODES else "lahiri")
    out["node_mode"] = (out["node_mode"] if out["node_mode"] in
                        transits.NODE_MODES else "mean")
    start = dt.date.fromisoformat(str(out["start"]))
    end = dt.date.fromisoformat(str(out["end"]))
    if end <= start:
        end = start + dt.timedelta(days=365)
    if (end - start).days > MAX_RANGE_DAYS:
        end = start + dt.timedelta(days=MAX_RANGE_DAYS)
    out["start"], out["end"] = start.isoformat(), end.isoformat()
    city = cities.resolve(str(out["city"])) or cities.resolve("Mumbai")
    out["city_info"] = city
    return out


def _fmt_local(utc_iso: str, tz_name: str) -> str:
    utc = dt.datetime.fromisoformat(utc_iso)
    local = cities.local_time(utc, tz_name)
    return local.strftime("%Y-%m-%d %H:%M:%S")


def _ayanamsa_value(jd: float, ayanamsa: str) -> float:
    swe.set_sid_mode(transits.AYANAMSA_MODES[ayanamsa])
    return float(swe.get_ayanamsa_ut(jd))


def _collect_events(cfg: dict) -> dict[tuple[str, str], list[dict]]:
    """events[(planet, type)] -> list of ingress events, with local
    entry/exit pairing (exit = next event's entry, last = range end)."""
    start = dt.date.fromisoformat(cfg["start"])
    end = dt.date.fromisoformat(cfg["end"])
    scanners = {"sign": transits.sign_ingresses,
                "nakshatra": transits.nakshatra_ingresses,
                "pada": transits.pada_ingresses}
    end_exclusive = end + dt.timedelta(days=1)
    out = {}
    for planet in cfg["planets"]:
        for kind in cfg["types"]:
            events = scanners[kind](planet, start, end_exclusive,
                                    node_mode=cfg["node_mode"],
                                    ayanamsa=cfg["ayanamsa"])
            for i, e in enumerate(events):
                nxt = (events[i + 1]["utc"] if i + 1 < len(events)
                       else end_exclusive.isoformat() + "T00:00:00+00:00")
                e["exit_utc"] = nxt
            out[(planet, kind)] = events
    return out


def _duration_days(e: dict) -> float:
    t0 = dt.datetime.fromisoformat(e["utc"])
    t1 = dt.datetime.fromisoformat(e["exit_utc"])
    return round((t1 - t0).total_seconds() / 86400.0, 3)


def _star_lord(longitude: float) -> str:
    nak, _pada = nakshatra_of(longitude)
    return NAKSHATRA_LORDS.get(nak, "-")


def _sign_of(longitude: float) -> str:
    return ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius",
            "Pisces"][int(longitude % 360.0 // 30)]


def _write_sheet(wb: Workbook, title: str, headers: list[str],
                 rows: list[list], first: bool = False) -> None:
    ws = wb.active if first else wb.create_sheet(title)
    if first:
        ws.title = title
    ws.append(headers)
    for cell in ws[1]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center")
    for row in rows:
        ws.append(row)
    ws.freeze_panes = "A2"
    for idx, header in enumerate(headers, 1):
        width = max(len(header) + 2,
                    *(len(str(row[idx - 1])) + 2 for row in rows)) \
            if rows else len(header) + 2
        ws.column_dimensions[get_column_letter(idx)].width = min(width, 28)


def _sheet_report_info(wb: Workbook, cfg: dict, events: dict) -> None:
    start = dt.date.fromisoformat(cfg["start"])
    jd_start = transits._to_jd(dt.datetime.combine(start, dt.time(0, 0)))
    ayan = _ayanamsa_value(jd_start, cfg["ayanamsa"])
    planets_pos, _ayan_positions = _start_positions(jd_start, cfg)
    rows = [
        ["City", cfg["city_info"]["name"] +
         f" ({cfg['city_info']['timezone']})"],
        ["Range", f"{cfg['start']} to {cfg['end']} (local dates)"],
        ["Planets", ", ".join(cfg["planets"])],
        ["Transit types", ", ".join(cfg["types"])],
        ["Ayanamsa", f"{cfg['ayanamsa']} = {ayan:.6f} deg at range start"],
        ["Node mode", cfg["node_mode"]],
        ["Engine", "Swiss Ephemeris (Moshier), ingress bisection to 1 s"],
        ["Generated", dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC")],
        ["", ""],
        ["Positions at range start", ""],
    ]
    rows += [[f"  {p['name']}",
              f"{p['sign']} {p['longitude'] % 30:.3f} deg, "
              f"nakshatra {p['nakshatra']} P{p['pada']}, "
              f"motion {'R' if p['speed'] < 0 else 'D'}"]
             for p in planets_pos]
    rows += [
        ["", ""],
        ["Legend", ""],
        ["Motion D/R/S", "direct / retrograde / stationary at ingress"],
        ["Re-entry", "planet moved back into the sign/nakshatra/pada "
                     "it left within 60 days (retrograde loop)"],
        ["Gandanta", "entry within 1.5 deg of a water-fire junction "
                     "(Pisces-Aries, Cancer-Leo, Scorpio-Sagittarius)"],
        ["Open exit", "last transit in the range ends at the range end"],
    ]
    _write_sheet(wb, "Report Info",
                 ["Item", "Value"], rows, first=True)


def _start_positions(jd_start: float, cfg: dict):
    from .planets import positions
    planets, _ayan = positions(jd_start)
    wanted = set(cfg["planets"])
    return [p for p in planets if p["name"] in wanted], _ayan


def _sheet_transits(wb: Workbook, cfg: dict, events: dict,
                    kind: str) -> None:
    tz = cfg["city_info"]["timezone"]
    rows = []
    for (planet, k), evs in sorted(events.items()):
        if k != kind:
            continue
        for e in evs:
            base = [planet]
            if kind == "sign":
                base += [e["from_label"], e["label"],
                         RASHI_LORDS.get(e["label"], "-")]
            elif kind == "nakshatra":
                base += [_star_lord(e["longitude"]), e["label"],
                         _sign_of(e["longitude"]), e["pada"]]
            else:
                nak = e["label"].rsplit(" P", 1)[0]
                base += [_star_lord(e["longitude"]), nak, e["pada"],
                         _sign_of(e["longitude"]), e["pada_index"]]
            entry_local = _fmt_local(e["utc"], tz)
            exit_local = _fmt_local(e["exit_utc"], tz)
            rows.append(base + [entry_local, exit_local,
                                _duration_days(e), e["motion"],
                                "yes" if e["re_entry"] else "",
                                "yes" if e["gandanta"] else ""])
    if kind == "sign":
        headers = ["Planet", "From sign", "To sign", "Sign lord",
                   "Entry (local)", "Exit (local)", "Duration (days)",
                   "Motion", "Re-entry", "Gandanta"]
    elif kind == "nakshatra":
        headers = ["Planet", "Star lord", "Nakshatra", "Sign", "Pada",
                   "Entry (local)", "Exit (local)", "Duration (days)",
                   "Motion", "Re-entry", "Gandanta"]
    else:
        headers = ["Planet", "Star lord", "Nakshatra", "Pada", "Sign",
                   "Pada index", "Entry (local)", "Exit (local)",
                   "Duration (days)", "Motion", "Re-entry", "Gandanta"]
    titles = {"sign": "Zodiac Transits", "nakshatra": "Nakshatra Transits",
              "pada": "Pada Transits"}
    _write_sheet(wb, titles[kind], headers, rows)


def _sheet_timeline(wb: Workbook, cfg: dict, events: dict) -> None:
    tz = cfg["city_info"]["timezone"]
    rows = []
    for (planet, kind), evs in events.items():
        for e in evs:
            local = cities.local_time(
                dt.datetime.fromisoformat(e["utc"]), tz)
            rows.append((local, [local.strftime("%Y-%m-%d %H:%M:%S"),
                                 planet, kind.title(),
                                 e["from_label"] + " -> " + e["label"],
                                 e["motion"],
                                 "yes" if e["re_entry"] else "",
                                 "yes" if e["gandanta"] else ""]))
    rows.sort(key=lambda t: t[0])
    _write_sheet(wb, "All Transits Timeline",
                 ["Local time", "Planet", "Type", "Transit", "Motion",
                  "Re-entry", "Gandanta"],
                 [r for _local, r in rows])


def _sheet_stations(wb: Workbook, cfg: dict) -> None:
    tz = cfg["city_info"]["timezone"]
    start = dt.date.fromisoformat(cfg["start"])
    end = dt.date.fromisoformat(cfg["end"])
    bodies = tuple(p for p in cfg["planets"] if p in STATION_BODIES)
    rows = []
    if bodies:
        for s in stations.between(start, end + dt.timedelta(days=1),
                                  bodies=bodies):
            when_ist = dt.datetime.fromisoformat(s["time"])
            jd = swe.julday(when_ist.year, when_ist.month, when_ist.day,
                            when_ist.hour + when_ist.minute / 60.0)
            planets, _ayan = _start_positions(jd, {"planets": [s["planet"]]})
            p = planets[0]
            local = cities.local_time(when_ist.replace(tzinfo=dt.UTC), tz)
            rows.append([s["planet"], s["direction"],
                         local.strftime("%Y-%m-%d %H:%M:%S"),
                         f"{p['sign']} {p['longitude'] % 30:.3f}",
                         p["nakshatra"], p["pada"],
                         _star_lord(p["longitude"])])
    _write_sheet(wb, "Stations (R-D)",
                 ["Planet", "Direction", "Station (local)", "Position",
                  "Nakshatra", "Pada", "Star lord"], rows)


def build_workbook(config: dict) -> tuple[io.BytesIO, str]:
    """Return (xlsx bytes, suggested filename)."""
    cfg = normalize_config(config)
    events = _collect_events(cfg)

    wb = Workbook()
    _sheet_report_info(wb, cfg, events)
    for kind in ("sign", "nakshatra", "pada"):
        if kind in cfg["types"]:
            _sheet_transits(wb, cfg, events, kind)
    _sheet_timeline(wb, cfg, events)
    _sheet_stations(wb, cfg)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    name = (f"transit_report_{cfg['start']}_{cfg['end']}_"
            f"{cfg['city_info']['name'].replace(' ', '_')}.xlsx")
    return buf, name
