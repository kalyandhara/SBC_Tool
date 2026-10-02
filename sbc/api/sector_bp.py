"""Sector API blueprint."""

import datetime

from flask import Blueprint, jsonify, request

sector_bp = Blueprint("sector", __name__, url_prefix="/api/sector")


@sector_bp.route("/planet_read")
def planet_read():
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    time_str = request.args.get("time") or "09:15"
    tz_name = request.args.get("tz") or "Asia/Kolkata"

    from sbc.planets import positioned_planets
    from sbc.prediction import planet_sector_read

    planets, _, _, _, _ = positioned_planets(date_str, time_str, tz_name)
    data = planet_sector_read(planets)
    return jsonify({
        "date": date_str,
        "time": time_str,
        "tz": tz_name,
        "read": data,
    }), 200


@sector_bp.route("/vedha_read")
def vedha_read():
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    time_str = request.args.get("time") or "09:15"
    tz_name = request.args.get("tz") or "Asia/Kolkata"
    school = request.args.get("school") or "classical"

    from sbc.planets import positioned_planets
    from sbc.prediction import compute_vedhas, sector_read

    planets, _, _, _, _ = positioned_planets(date_str, time_str, tz_name)
    vedha_map, _ = compute_vedhas(planets, school=school)
    data = sector_read(vedha_map, planets)
    return jsonify({
        "date": date_str,
        "time": time_str,
        "tz": tz_name,
        "school": school,
        "read": data,
    }), 200
