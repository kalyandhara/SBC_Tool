"""Sector rotation blueprint: read-only over the newest precomputed report JSON.

Statistics are never recomputed. The upcoming route computes only event dates (sr.core_events,
cached per year pair), which the report cannot know about. Parameters are allow-listed; nothing
from the request reaches a path or SQL.
"""

import datetime as dt
import glob
import json
import os
from functools import lru_cache

from flask import Blueprint, abort, jsonify, request

from sbc import market_store as ms
from sbc import sector_rotation as sr

sector_rotation_bp = Blueprint("sector_rotation", __name__, url_prefix="")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
REPORTS = os.path.join(ROOT, "reports")
EVENTS = {"MERCURY_RETROGRADE_START", "SOLAR_ECLIPSE", "LUNAR_ECLIPSE",
          "JUPITER_INGRESS", "SATURN_INGRESS", "all"}
HORIZONS = {"5", "10", "20"}
UPCOMING_WINDOWS = {30, 60, 90, 180}  # days ahead; a window of 180 days never leaves the next calendar year
EVENT_LABEL = {
    "MERCURY_RETROGRADE_START": "Mercury retrograde start",
    "SOLAR_ECLIPSE": "Solar eclipse",
    "LUNAR_ECLIPSE": "Lunar eclipse",
    "JUPITER_INGRESS": "Jupiter sign ingress",
    "SATURN_INGRESS": "Saturn sign ingress",
}


def _latest_report() -> dict | None:
    files = sorted(glob.glob(os.path.join(REPORTS, "sector_rotation_*.json")))
    if not files:
        return None
    with open(files[-1], encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=4)
def _core_event_dates(first_year: int, last_year: int) -> tuple[dict, ...]:
    return tuple(sr.core_events(first_year, last_year))


@sector_rotation_bp.route("/api/sector_rotation")
def sector_rotation():
    event = request.args.get("event", "all")
    h = request.args.get("h", "5")
    if event not in EVENTS or h not in HORIZONS:
        abort(400)
    data = _latest_report()
    if data is None:
        abort(404)
    return jsonify({"event": event, "h": int(h), "data": data})


@sector_rotation_bp.route("/api/sector_rotation/upcoming")
def sector_rotation_upcoming():
    try:
        days = int(request.args.get("days", 60))
    except ValueError:
        abort(400)
    if days not in UPCOMING_WINDOWS:
        abort(400)
    data = _latest_report()
    if data is None:
        abort(404)
    today = dt.datetime.now(ms.IST).date()
    events = sr.upcoming_events(list(_core_event_dates(today.year, today.year + 1)), today.isoformat(), days)
    out = []
    for e in events:
        outlook = sr.event_outlook(data["descriptive"], e["event"])
        out.append({"date": e["date"], "event": e["event"], "label": EVENT_LABEL.get(e["event"], e["event"]),
                    "window_end": e.get("window_end"),
                    "raw": data["events"].get(e["event"], {}).get("raw"),
                    "clusters": data["events"].get(e["event"], {}).get("clusters"),
                    "outlook": outlook})
    return jsonify({"as_of": today.isoformat(), "days": days,
                    "last_session": data["input"]["last_session"]["NIFTY"],
                    "events": out,
                    "caveat": "Descriptive, not graded. No pre-registered edge; forecast is No call. Not trading advice."})
