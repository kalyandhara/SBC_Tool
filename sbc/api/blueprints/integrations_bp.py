"""TradingView webhook, the latest webhook signal, and the KP sample-data generator.

Moved out of app.py (B-16).
"""

import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request

from sbc.api.errors import internal_error

integrations_bp = Blueprint('integrations', __name__)


@integrations_bp.route("/webhook/sbc", methods=["POST"])
def webhook_sbc():
    try:
        if request.content_length and request.content_length > 64 * 1024:
            return jsonify({"error": "payload too large (64 KB max)"}), 413
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "body must be a JSON object"}), 400
        import json
        import os
        os.makedirs("data", exist_ok=True)
        with open("data/latest_sbc_signal.json", "w") as f:
            json.dump(data, f)
        return jsonify({"status":"ok","received":data})
    except Exception:
        return internal_error()


@integrations_bp.route("/api/sbc/latest", methods=["GET"])
def api_sbc_latest():
    try:
        import json
        import os
        path = "data/latest_sbc_signal.json"
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            return jsonify(data)
        return jsonify({})
    except Exception:
        return internal_error()


@integrations_bp.route("/api/kp_intraday_sample", methods=["POST"])
def kp_intraday_sample():
    """Generate the month's KP data from Swiss Ephemeris (sbc.kp_ephemeris).

    The route name is kept for the UI button; it no longer writes random
    sample data. An existing file is only replaced when it fails the KP
    sanity check (i.e. it is an old random sample) or force=true.
    """
    import csv as _csv

    from sbc.kp_ephemeris import generate_kp_month, month_file
    from sbc.kp_intraday import assess_kp_data

    data = request.get_json() or {}
    date_str = data.get("date") or datetime.date.today().isoformat()
    force = bool(data.get("force", False))
    try:
        day = datetime.date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "invalid date"}), 400

    kp_data_dir = Path(__file__).resolve().parents[3] / "data" / "kp"
    output_path = month_file(kp_data_dir, day.year, day.month)
    replaced = None
    if output_path.exists():
        with open(output_path, encoding="utf-8") as f:
            existing = assess_kp_data(list(_csv.DictReader(f)))
        if not existing["synthetic"] and not force:
            return jsonify({
                "error": f"{output_path.name} already holds ephemeris KP data. "
                         "Pass force=true to regenerate it.",
            }), 409
        replaced = "synthetic" if existing["synthetic"] else "ephemeris"
    info = generate_kp_month(day.year, day.month, output_path)
    return jsonify({**info, "month": day.strftime("%Y-%m"),
                    "source": "swiss_ephemeris", "replaced": replaced})

