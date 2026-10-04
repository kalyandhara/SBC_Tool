"""Chart & Timing blueprint."""

import datetime

from flask import Blueprint, jsonify, request

chart_bp = Blueprint('chart', __name__, url_prefix='')

# L1 in-process cache: (date_iso, anchor, school) -> payload.
# Error results are intentionally NOT cached here, so a transient failure
# (SQLite lock, ephemeris hiccup) is retried on the next request.
_series_cache = {}

# Every key a /api/prediction_series row carries; the chart's risk bands and
# hover cards read all of them.
SERIES_KEYS = frozenset({
    "date", "score", "net", "verdict", "strength", "rec", "alert",
    "alert_level", "risk_rank", "risk_label", "alerts_total", "drivers",
    "windows", "confluence", "lunar_phase",
})

_LEVEL_RANK = {"LOW": 1, "MODERATE": 2, "MODERATE-HIGH": 3,
               "HIGH": 4, "VERY HIGH": 5, "EXTREME": 6,
               "CRITICAL": 7}


@chart_bp.route('/api/intraday_projection')
def intraday_projection_endpoint():
    from sbc.intraday_projection import intraday_projection
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    tz_name = request.args.get("tz") or "Asia/Kolkata"
    anchor_key = request.args.get("anchor") or "nse"
    try:
        days = int(request.args.get("days", "5"))
    except ValueError:
        days = 5
    days = max(1, min(10, days))
    try:
        datetime.date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    return jsonify(intraday_projection(date_str, tz_name, days, anchor_key))

@chart_bp.route('/api/nifty_chart')
def nifty_chart():
    from sbc.market_data import get_nifty_ohlc
    start = request.args.get("start")
    end = request.args.get("end")
    try:
        for d in (start, end):
            if d:
                datetime.datetime.strptime(d, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    from sbc import data_freshness
    from sbc.market_data import _CACHE_PATH
    candles = get_nifty_ohlc(start, end)
    # As of the whole cached series (refreshed by the call above), not the range asked for.
    freshness = data_freshness.stamp(data_freshness.csv_last_date(_CACHE_PATH))
    return jsonify({"candles": candles, "symbol": "^NSEI", "freshness": freshness})

@chart_bp.route('/api/prediction_series')
def prediction_series():
    """Compact per-day astro prediction scores over a date range.

    Used to overlay bullish/bearish markers + sentiment bands on the
    NIFTY price chart. Works for past and future dates alike.

    L2: rows already computed by a previous process / worker (SQLite).
    """
    from sbc import series_cache
    from sbc.engine import ANCHORS, build_response
    start = request.args.get("start") or ""
    end = request.args.get("end") or ""
    anchor_key = request.args.get("anchor") or "nifty"
    school = request.args.get("school", "classical")
    try:
        start_d = datetime.date.fromisoformat(start)
        end_d = datetime.date.fromisoformat(end)
    except (TypeError, ValueError):
        return jsonify({"error": "invalid start/end date"}), 400
    if anchor_key not in ANCHORS:
        return jsonify({"error": "unknown anchor"}), 400
    # Allow up to ~31 months (950 days) to cover 24m history + 6m forecast + buffer
    if (end_d - start_d).days > 950:
        return jsonify({"error": "range too large (max 950 days)"}), 400

    wanted = []
    d = start_d
    while d <= end_d:
        if (d.isoformat(), anchor_key, school) not in _series_cache:
            wanted.append(d.isoformat())
        d += datetime.timedelta(days=1)
    for ds, payload in series_cache.get_many(wanted, anchor_key, school).items():
        # Rows missing the full shape (an old boot warm-up wrote trimmed ones)
        # count as misses, so they get rebuilt and overwritten below.
        if payload.keys() >= SERIES_KEYS:
            _series_cache[(ds, anchor_key, school)] = payload

    out = []
    fresh = {}
    d = start_d
    while d <= end_d:
        ds = d.isoformat()
        key = (ds, anchor_key, school)
        if key not in _series_cache:
            try:
                r = build_response(ds, "09:15", "Asia/Kolkata", anchor_key, school)
                alert = r.get("market_alert") or {}
                level = None
                for w in (alert.get("windows") or []):
                    level = w.get("level") or level

                # Crash-calendar severity: highest active window level this day
                rank = 0
                risk_label = None
                for w in (alert.get("windows") or []):
                    wl = (w.get("level") or "").upper()
                    wr = _LEVEL_RANK.get(wl, 0)
                    if wr > rank:
                        rank = wr
                        risk_label = w.get("level")

                # Compact vedha drivers for the NIFTY chart hover card
                hits = r.get("point_hits") or []
                benefics = sorted(
                    (h for h in hits if h["nature"] == "benefic"),
                    key=lambda x: -x["strength"])[:3]
                malefics = sorted(
                    (h for h in hits if h["nature"] == "malefic"),
                    key=lambda x: x["strength"])[:3]
                drivers = {
                    "benefic": [{
                        "planet": h["planet"], "symbol": h["symbol"],
                        "point": h["point"], "ray": h["ray"],
                        "strength": h["strength"],
                    } for h in benefics],
                    "malefic": [{
                        "planet": h["planet"], "symbol": h["symbol"],
                        "point": h["point"], "ray": h["ray"],
                        "strength": h["strength"],
                    } for h in malefics],
                }

                # Active reversal windows (compact) for the hover card
                windows = [{
                    "title": w.get("title", ""),
                    "level": w.get("level", ""),
                    "bias": w.get("bias", ""),
                } for w in (alert.get("windows") or [])[:4]]

                # Confluence snapshot (overall signal + agreeing sectors)
                conf = alert.get("confluence") or {}
                conf_overall = conf.get("overall") or {}
                conf_hl = conf.get("highlights") or {}
                confluence = {
                    "signal": conf_overall.get("signal"),
                    "bull": conf_overall.get("bullish_weight"),
                    "bear": conf_overall.get("bearish_weight"),
                    "net": conf_overall.get("net"),
                    "bull_sectors": conf_hl.get("bullish_confluence_sectors") or [],
                    "bear_sectors": conf_hl.get("bearish_confluence_sectors") or [],
                }

                # Add lunar phase info
                tithi_val = r.get("tithi", {}).get("tithi") if isinstance(r.get("tithi"), dict) else r.get("tithi")
                lunar_phase = None
                if tithi_val:
                    if tithi_val == 15:
                        lunar_phase = "PURNIMA"
                    elif tithi_val == 30:
                        lunar_phase = "AMAVASYA"
                    elif tithi_val in (14, 29):
                        lunar_phase = "PRE_PURNIMA" if tithi_val == 14 else "PRE_AMAVASYA"

                _series_cache[key] = {
                    "date": ds,
                    "score": r.get("score"),
                    "net": r.get("net"),
                    "verdict": r.get("sentiment", {}).get("verdict"),
                    "strength": r.get("sentiment", {}).get("strength"),
                    "rec": (r.get("recommendation") or {}).get("summary"),
                    "alert": bool(alert.get("active")),
                    "alert_level": level,
                    "risk_rank": rank,
                    "risk_label": risk_label,
                    "alerts_total": alert.get("total_alerts", 0),
                    "drivers": drivers,
                    "windows": windows,
                    "confluence": confluence,
                    "lunar_phase": lunar_phase,
                }
                fresh[ds] = _series_cache[key]
            except Exception:
                # Don't cache the error in L1: leaving the key absent makes
                # the next request retry instead of serving the failure forever.
                out.append({"date": ds, "error": "prediction failed"})
                d += datetime.timedelta(days=1)
                continue
        out.append(_series_cache[key])
        d += datetime.timedelta(days=1)
    if fresh:
        series_cache.put_many(fresh, anchor_key, school)
    return jsonify({"series": out, "anchor": anchor_key})
