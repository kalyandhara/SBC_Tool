"""Intraday forecast (SBC + KP confluence) and its forecast ledger."""

import datetime

from flask import Blueprint, jsonify, request

forecast_bp = Blueprint("forecast", __name__, url_prefix="/api/engine/intraday_forecast")

_cache = {}  # (date, step, model_version) -> forecast payload


def _date_arg(name="date"):
    raw = request.args.get(name) or (request.get_json(silent=True) or {}).get(name)
    if not raw:
        from sbc.forecast_ledger import _now_ist
        return _now_ist().date()
    return datetime.date.fromisoformat(raw)


@forecast_bp.route("")
def forecast():
    from sbc import forecast_ledger as ledger
    from sbc.intraday_forecast import build_forecast, model_version
    try:
        day = _date_arg()
        step = int(request.args.get("step", 5))
    except ValueError:
        return jsonify({"error": "invalid date or step"}), 400
    from sbc.market_holidays import holiday_name
    closed = holiday_name(day)
    if closed:
        return jsonify({"error": f"NSE is closed on {day.isoformat()} ({closed})",
                        "holiday": closed}), 400
    if not 1 <= step <= 60:
        return jsonify({"error": "step must be 1..60"}), 400

    now = ledger._now_ist()
    frozen = ledger.get_frozen(day)
    # Asking for today's forecast before the open freezes it as a live record.
    # This GET writes, so (like the app's write gate) only for local callers;
    # run_app.py's ledger loop freezes it anyway.
    local = request.remote_addr in ("127.0.0.1", "::1", "::ffff:127.0.0.1")
    if (local and frozen is None and step == 5 and day == now.date()
            and ledger._kind_for(day, now) == "live"):
        frozen = ledger.freeze(day, now)

    key = (day.isoformat(), step, model_version())
    if key not in _cache:
        _cache[key] = build_forecast(day, step)
    payload = dict(_cache[key])
    payload["frozen"] = ({k: frozen[k] for k in ("kind", "frozen_at", "model_version")}
                         if frozen else None)
    if frozen and frozen["model_version"] != payload["model_version"]:
        payload["frozen"]["stale_model"] = True
    return jsonify(payload)


@forecast_bp.route("/actual")
def actual():
    from sbc.forecast_ledger import actual_bars
    try:
        day = _date_arg()
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    return jsonify(actual_bars(day))


@forecast_bp.route("/freeze", methods=["POST"])
def freeze():
    from sbc.forecast_ledger import freeze as do_freeze
    body = request.get_json(silent=True) or {}
    try:
        day = _date_arg()
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    try:
        row = do_freeze(day, backfill=bool(body.get("backfill")), force=bool(body.get("force")))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({k: row[k] for k in ("date", "kind", "frozen_at", "model_version")})


@forecast_bp.route("/score", methods=["POST"])
def score():
    from sbc.forecast_ledger import score_pending
    return jsonify({"scored": score_pending()})


@forecast_bp.route("/ledger")
def ledger_summary():
    from sbc.forecast_ledger import score_pending, summary
    try:
        days = max(1, min(365, int(request.args.get("days", 60))))
    except ValueError:
        return jsonify({"error": "invalid days"}), 400
    score_pending(limit=5)  # settle a few outstanding days lazily
    return jsonify(summary(days))
