"""Sector Heatmap blueprint."""

import datetime

from flask import Blueprint, jsonify, request

from sbc.api.errors import internal_error

sectors_bp = Blueprint('sectors', __name__, url_prefix='')

@sectors_bp.route('/api/monthly_heatmap')
def monthly_heatmap_endpoint():
    from sbc.monthly_heatmap import monthly_heatmap
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    tz_name = request.args.get("tz") or "Asia/Kolkata"
    anchor = request.args.get("anchor") or "nse"
    try:
        days = int(request.args.get("days", "30"))
    except ValueError:
        days = 30
    days = max(7, min(90, days))
    try:
        datetime.date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    try:
        result = monthly_heatmap(start_date=date_str, days=days, tz_name=tz_name, anchor_key=anchor)
    except Exception:
        return internal_error()
    return jsonify(result)

@sectors_bp.route('/api/sector_vedha')
def sector_vedha():
    from sbc.sector_signals import scan_sector_vedhas
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    return jsonify(scan_sector_vedhas(date_str))

@sectors_bp.route('/api/lunar_forecast')
def lunar_forecast():
    from sbc.lunar_forecast import (
        format_card_for_clipboard,
        format_card_for_social_media,
        generate_infographic_card,
        generate_lunar_sector_forecast,
    )
    from sbc.planets import positioned_planets
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    planets, ayanamsa, sun, moon, tithi = positioned_planets(date_str)
    forecast = generate_lunar_sector_forecast(date_str, planets, tithi, sun, moon)
    card = generate_infographic_card(forecast)
    return jsonify({
        "forecast": forecast,
        "card": card,
        "clipboard_text": format_card_for_clipboard(card),
        "social_text": format_card_for_social_media(card),
    })
