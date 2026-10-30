"""Sector rotation blueprint: read-only over the newest precomputed report JSON.

Never recomputes. Parameters are allow-listed; nothing from the request reaches a path or SQL.
"""

import glob
import json
import os

from flask import Blueprint, abort, jsonify, request

sector_rotation_bp = Blueprint("sector_rotation", __name__, url_prefix="")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
REPORTS = os.path.join(ROOT, "reports")
EVENTS = {"MERCURY_RETROGRADE_START", "SOLAR_ECLIPSE", "LUNAR_ECLIPSE",
          "JUPITER_INGRESS", "SATURN_INGRESS", "all"}
HORIZONS = {"5", "10", "20"}


@sector_rotation_bp.route("/api/sector_rotation")
def sector_rotation():
    event = request.args.get("event", "all")
    h = request.args.get("h", "5")
    if event not in EVENTS or h not in HORIZONS:
        abort(400)
    files = sorted(glob.glob(os.path.join(REPORTS, "sector_rotation_*.json")))
    if not files:
        abort(404)
    with open(files[-1], encoding="utf-8") as f:
        data = json.load(f)
    return jsonify({"event": event, "h": int(h), "data": data})


@sector_rotation_bp.route("/api/briefing_summary")
def briefing_summary():
    files = sorted(glob.glob(os.path.join(REPORTS, "sector_rotation_*.json")))
    if not files:
        abort(404)
    with open(files[-1], encoding="utf-8") as f:
        data = json.load(f)
    return jsonify({
        "current_events": {
            "description": "Active planetary transits and ingress anchors as of current session.",
            "era_boundary": data.get("era_boundary"),
            "oos_sessions": data.get("oos_sessions"),
        },
        "sectoral_impacts": {
            "description": "Mean relative sector returns across planetary event windows (T+5, T+10, T+20).",
            "active_sectors": list(data.get("coverage", {}).keys()),
            "missing_coverage": ["CNXMEDIA", "CNXHEALTH", "CNXOILGAS"],
        },
        "upcoming_events": {
            "description": "Upcoming core astrological events (Jupiter Ingress, Eclipses, Retrogrades).",
            "events_tracked": list(data.get("events", {}).keys()),
        },
        "past_outcomes": {
            "description": "Historical occurrence frequencies and window outcomes for NIFTY and sector leaders.",
            "event_counts": data.get("events"),
        },
        "horizon_guidance": {
            "description": "Investment Horizon Advisory",
            "short_term": "T+5 to T+20 windows show descriptive historical frequency patterns but 0/511 validated out-of-sample edge.",
            "medium_long_term": "6-month and 1-year investment horizons MUST rely on fundamental macro analysis, valuation, and business cycle indicators rather than transit models.",
            "sectors_to_avoid": "Cyclical or short-history sectors without robust multi-decade pricing history.",
        },
        "validation_status": {
            "descriptive_status": "EXPLORATORY / DESCRIPTIVE ONLY",
            "validated_edge": "NONE (0 out-of-sample passes)",
            "is_financial_advice": False,
        }
    })
