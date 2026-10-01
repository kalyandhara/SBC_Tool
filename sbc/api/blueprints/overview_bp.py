"""Executive Overview blueprint."""

from flask import Blueprint, jsonify, request
import datetime

overview_bp = Blueprint('overview', __name__, url_prefix='')

@overview_bp.route('/api/presets')
def presets():
    from app import ANCHORS
    from sbc.nakshatra import NAKSHATRAS_27
    return jsonify({
        "anchors": [
            {"key": k, **{kk: vv for kk, vv in v.items() if kk != "date"}}
            for k, v in ANCHORS.items()
        ],
        "nakshatras": NAKSHATRAS_27,
    })

@overview_bp.route('/api/prediction')
def prediction():
    from app import build_response, ANCHORS
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    time_str = request.args.get("time", "09:15")
    tz_name = request.args.get("tz", "Asia/Kolkata")
    anchor_key = request.args.get("anchor") or "nse"
    school = request.args.get("school", "classical")
    try:
        if anchor_key not in ANCHORS:
            return jsonify({"error": "unknown anchor"}), 400
        if school not in ("classical", "allthree"):
            return jsonify({"error": "unknown school"}), 400
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
        datetime.datetime.strptime(time_str, "%H:%M")
    except ValueError:
        return jsonify({"error": "invalid date/time"}), 400
    resp = build_response(date_str, time_str, tz_name, anchor_key, school)
    return jsonify(resp)

@overview_bp.route('/api/weekly_commentary')
def weekly_commentary():
    from app import build_response
    from sbc.weekly_commentary import generate_weekly_commentary, format_commentary_text
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    try:
        date = datetime.date.fromisoformat(date_str)
        start = date - datetime.timedelta(days=date.weekday())
        commentary = generate_weekly_commentary(start)
        return jsonify({
            "week": commentary["week"],
            "start_date": commentary["start_date"],
            "end_date": commentary["end_date"],
            "text": format_commentary_text(commentary),
            "data": {
                "main_cycle": commentary["main_cycle"],
                "configurations": commentary["all_configurations"],
                "planetary_positions": commentary["planetary_positions"],
                "moon_transits": [
                    {
                        "date": mt["date"].isoformat(),
                        "weekday": mt["weekday"],
                        "nakshatra": mt["nakshatra"],
                        "sign": mt["sign"],
                        "degree": mt["degree"],
                        "meaning": mt["meaning"],
                        "lord": mt["lord"],
                    } for mt in commentary["moon_transits"]
                ],
                "active_windows": commentary["active_windows"],
                "upcoming_windows": commentary["upcoming_windows"],
                "transits": commentary["transits"],
                "lunar_phase": commentary["lunar_phase"],
                "jupiter_analysis": commentary["jupiter_analysis"],
                "confluence": commentary["confluence"],
                "bullish_futurecast": commentary["bullish_futurecast"],
                "bearish_futurecast": commentary["bearish_futurecast"],
                "market_bias": commentary["market_bias"],
                "bullish_factors": commentary["bullish_factors"],
                "bearish_factors": commentary["bearish_factors"],
                "sector_outlook": commentary.get("sector_outlook", []),
                "general_strategy": commentary.get("general_strategy", ""),
                "nifty_levels": commentary.get("nifty_levels", ""),
            }
        })
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
