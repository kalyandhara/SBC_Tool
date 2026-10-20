"""Momentum screener endpoints.

    GET /api/screener/universes        -> {universes, sectors, timeframes}
    GET /api/screener/scan?...         -> JSON preview or xlsx download

Scan params: universe (see /universes or "watchlist:TEXT"), mode
(full|rsi|ema), timeframe (5m|10m|15m|1h|1d|1wk), end (YYYY-MM-DD,
back-scan), lookback (days), as_ha (Heikin-Ashi), format (json|xlsx),
params (JSON object of mode overrides).
"""

import json as _json

from flask import Blueprint, jsonify, request, send_file

from sbc.screener import data, engine, report, universes

screener_bp = Blueprint("screener", __name__, url_prefix="/api/screener")

XLSX_MIME = ("application/vnd.openxmlformats-officedocument."
             "spreadsheetml.sheet")

# Guard rails: symbols per scan by timeframe bucket (intraday downloads
# are slow and rate-limited).
_MAX_SYMBOLS = {"intraday": 100, "daily": 600}


def _bucket(timeframe: str) -> str:
    return "intraday" if timeframe in ("5m", "10m", "15m", "1h") \
        else "daily"


@screener_bp.get("/universes")
def list_universes():
    return jsonify({
        "universes": universes.available(),
        "sectors": universes.sector_names(),
        "timeframes": sorted(data.TIMEFRAMES),
        "modes": list(engine.MODES),
    })


def _resolve_symbols(raw_universe: str) -> list[str]:
    raw = (raw_universe or "").strip()
    if raw.lower().startswith("watchlist:"):
        return universes.watchlist(raw.split(":", 1)[1])
    return universes.load(raw)


@screener_bp.get("/scan")
def scan():
    universe = request.args.get("universe", "NIFTY 50")
    mode = request.args.get("mode", "full")
    timeframe = request.args.get("timeframe", "1d")
    fmt = request.args.get("format", "json")
    as_ha = (request.args.get("as_ha", "0").lower() in ("1", "true", "yes"))
    try:
        end = (request.args.get("end") or "").strip()
        import datetime as dtm
        end_date = dtm.date.fromisoformat(end) if end else None
        lookback = int(request.args["lookback"]) if request.args.get(
            "lookback") else None
        overrides = (_json.loads(request.args["params"])
                     if request.args.get("params") else None)
        if mode not in engine.MODES:
            return jsonify({"error": f"mode must be one of "
                                     f"{list(engine.MODES)}"}), 400
        symbols = _resolve_symbols(universe)
        if not symbols:
            return jsonify({"error": f"universe {universe!r} is empty"}), 400
        bucket = _bucket(timeframe)
        if len(symbols) > _MAX_SYMBOLS[bucket]:
            return jsonify({"error": f"{len(symbols)} symbols exceed the "
                                     f"{_MAX_SYMBOLS[bucket]} cap for "
                                     f"{bucket} timeframes"}), 400
        frames, errors = data.batch(symbols, timeframe, end=end_date,
                                    lookback_days=lookback, as_ha=as_ha)
        if not frames:
            return jsonify({"error": "no price data for the universe",
                            "detail": errors}), 400
        scan_out = engine.run_scan(frames, mode, overrides)
        scan_out["errors"] = errors
    except (ValueError, KeyError, _json.JSONDecodeError) as exc:
        return jsonify({"error": f"bad scan request: {exc}"}), 400

    meta = {"universe": universe, "timeframe": timeframe,
            "scan_date": end_date.isoformat() if end_date else None,
            "as_ha": as_ha}
    if fmt == "xlsx":
        buf, name = report.build_report(scan_out, meta)
        return send_file(buf, as_attachment=True, download_name=name,
                         mimetype=XLSX_MIME)
    scan_out["meta"] = meta
    preview = {k: v for k, v in scan_out.items() if k != "errors"}
    # trim big JSON: cap signals in preview
    preview["signals"] = preview["signals"][:200]
    preview["signals_total"] = len(scan_out["signals"])
    return jsonify(preview)
