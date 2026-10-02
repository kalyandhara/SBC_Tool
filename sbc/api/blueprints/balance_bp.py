"""Monthly Projection / Daily Indication Balance blueprint."""

import datetime

from flask import Blueprint, jsonify, request

balance_bp = Blueprint('balance', __name__, url_prefix='')

# In-process cache: (start_iso, anchor) -> payload.
_balance_cache = {}

@balance_bp.route('/api/daily_indication_balance')
def daily_indication_balance():
    """30-day daily indication balance: blended bias bars + three school lines.

    Schools: Jyotish (classical single-ray), KP (all-three Narasimha Rao rays)
    and Western (zodiac-dignity synthetic line). Each day is scored on the
    Vedic net, mapped to a 0..6 bias scale.
    """
    from app import ANCHORS, build_response
    from sbc.metrics import _bias_scale, _western_bias
    start = request.args.get("start")
    try:
        start_d = datetime.date.fromisoformat(start) if start else datetime.date.today()
    except ValueError:
        return jsonify({"error": "invalid start date"}), 400

    anchor_key = request.args.get("anchor") or "nifty"
    if anchor_key not in ANCHORS:
        return jsonify({"error": "unknown anchor"}), 400

    key = (start_d.isoformat(), anchor_key)
    if key in _balance_cache:
        return jsonify(_balance_cache[key])

    jyotish = []
    kp = []
    western = []
    blend = []
    dates = []

    d = start_d
    for _ in range(30):
        ds = d.isoformat()
        dates.append(ds)
        try:
            # Jyotish (classical) and KP (allthree) both reuse build_response.
            rj = build_response(ds, "09:15", "Asia/Kolkata", anchor_key, "classical")
            rk = build_response(ds, "09:15", "Asia/Kolkata", anchor_key, "allthree")

            jyotish_net = rj.get("net", 0.0)
            kp_net = rk.get("net", 0.0)
            western_net = _western_bias(rj.get("planets", []))

            jb = _bias_scale(jyotish_net)
            kb = _bias_scale(kp_net)
            wb = _bias_scale(western_net)
        except Exception:
            jb = kb = wb = 3.0

        jyotish.append(jb)
        kp.append(kb)
        western.append(wb)
        blend.append(round((jb + kb + wb) / 3.0, 4))
        d += datetime.timedelta(days=1)

    out = {
        "days": list(range(1, 31)),
        "dates": dates,
        "blend_bias": blend,
        "jyotish_line": jyotish,
        "kp_line": kp,
        "western_line": western,
        "bullish_threshold": 4.0,
        "bearish_threshold": 2.0,
        "neutral_range": [2.0, 4.0],
        "anchor": anchor_key,
        "start": start_d.isoformat(),
    }
    _balance_cache[key] = out
    return jsonify(out)
