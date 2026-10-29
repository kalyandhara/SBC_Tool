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
