"""Engine API blueprint."""

import datetime
import os
from pathlib import Path

from flask import Blueprint, jsonify, request

_KOTA_DIR = Path(__file__).resolve().parents[2] / "data" / "kota"


def _kota_excel_path():
    """Locate the Kota Chakra workbook.

    SBC_KOTA_XLSX overrides; otherwise the newest Prediction_Kota_Chakra*.xlsx
    under data/kota/. Returns a Path that may not exist (callers 404 on that).
    """
    override = os.environ.get("SBC_KOTA_XLSX")
    if override:
        return Path(override)
    candidates = sorted(_KOTA_DIR.glob("Prediction_Kota_Chakra*.xlsx"),
                        key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else _KOTA_DIR / "Prediction_Kota_Chakra.xlsx"


engine_bp = Blueprint("engine", __name__, url_prefix="/api/engine")

# Simple in-memory cache for intraday_path: key -> (timestamp, data)
_intraday_path_cache = {}
_CACHE_TTL_SECONDS = 24 * 60 * 60

# Kota cache
_kota_cache = {}
_KOTA_TTL_SECONDS = 24 * 60 * 60

# Unified daily forecast contract cache
_confluence_cache = {}


@engine_bp.route("/version")
def version():
    from flask import current_app

    from sbc import __version__
    return jsonify({
        "version": __version__,
        "engine": "Sarvatobhadra Chakra",
        "endpoints": len([r for r in current_app.url_map.iter_rules() if r.endpoint != 'static'])
    }), 200


@engine_bp.route("/summary")
def summary():
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    time_str = request.args.get("time") or "09:15"
    tz_name = request.args.get("tz") or "Asia/Kolkata"
    anchor = request.args.get("anchor") or "nse"
    school = request.args.get("school") or "classical"

    from sbc.nakshatra import sensitive_stars
    from sbc.planets import positioned_planets
    from sbc.prediction import analyze, compute_vedhas, sentiment_of

    planets, ayanamsa, sun, moon, tithi = positioned_planets(date_str, time_str, tz_name)
    vedha_map, ray_paths = compute_vedhas(planets, school=school)

    anchor_map = {
        "nse": "Mula",
        "bse": "Ashwini",
        "nifty": "Mula",
        "sensex": "Ashwini",
        "india": "Mula",
    }
    birth_nakshatra = anchor_map.get(anchor, "Mula")

    points = sensitive_stars(birth_nakshatra)
    analysis = analyze(planets, vedha_map, birth_nakshatra, school)
    verdict, strength = sentiment_of(analysis["net"])

    summary_data = {
        "anchor": anchor,
        "birth_nakshatra": birth_nakshatra,
        "date": date_str,
        "time": time_str,
        "tz": tz_name,
        "school": school,
        "points": [{"name": p["name"], "nakshatra": p["nakshatra"], "offset": p["offset"], "description": p["description"]} for p in points],
        "planets": [{"name": p["name"], "nakshatra": p["nakshatra"], "sign": p["sign"], "nature": p["nature"],
                    "dignity_multiplier": p["dignity_multiplier"], "dignity_reasons": p["dignity_reasons"],
                    "motion": p.get("motion")} for p in planets],
        "vedha_hits": analysis["point_hits"],
        "scores": analysis["score"],
        "net": analysis["net"],
        "verdict": verdict,
        "strength": strength,
        "per_point": analysis["per_point"],
    }
    return jsonify(summary_data), 200


@engine_bp.route("/trace")
def trace():
    """Engine trace/explainability view: nature, dignity, ray strength per planet."""
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    time_str = request.args.get("time") or "09:15"
    tz_name = request.args.get("tz") or "Asia/Kolkata"
    anchor = request.args.get("anchor") or "nse"
    school = request.args.get("school") or "classical"

    from sbc.nakshatra import sensitive_stars
    from sbc.planets import positioned_planets
    from sbc.prediction import compute_vedhas, summarize_vedhas

    planets, ayanamsa, sun, moon, tithi = positioned_planets(date_str, time_str, tz_name)
    vedha_map, ray_paths = compute_vedhas(planets, school=school)

    anchor_map = {
        "nse": "Mula",
        "bse": "Ashwini",
        "nifty": "Mula",
        "sensex": "Ashwini",
        "india": "Mula",
    }
    birth_nakshatra = anchor_map.get(anchor, "Mula")
    points = sensitive_stars(birth_nakshatra)

    summary = summarize_vedhas(vedha_map, planets, points)

    trace_data = {
        "anchor": anchor,
        "birth_nakshatra": birth_nakshatra,
        "date": date_str,
        "time": time_str,
        "tz": tz_name,
        "school": school,
        "tithi": tithi,
        "ayanamsa": round(ayanamsa, 4),
        "planets": [
            {
                "name": p["name"],
                "symbol": p["symbol"],
                "nakshatra": p["nakshatra"],
                "sign": p["sign"],
                "degree": p["degree"],
                "nature": p["nature"],
                "nature_note": p.get("nature_note", ""),
                "retrograde": p["retrograde"],
                "speed": p["speed"],
                "dignity_multiplier": p["dignity_multiplier"],
                "dignity_reasons": p["dignity_reasons"],
                "signed_strength": p["signed_strength"],
            }
            for p in planets
        ],
        "vedha_summary": summary,
        "ray_paths": ray_paths,
    }
    return jsonify(trace_data), 200


@engine_bp.route("/market/ohlc")
def market_ohlc():
    from sbc.market_ohlc import load_week_ohlc
    symbol = request.args.get("symbol", "NIFTY").upper()
    try:
        days = int(request.args.get("days", "7"))
    except ValueError:
        return jsonify({"error": "invalid days"}), 400
    days = max(1, min(60, days))
    data = load_week_ohlc(symbol, days)
    return jsonify({"symbol": symbol, "days": days, "bars": data}), 200


@engine_bp.route("/intraday_path")
def intraday_path():
    """Predictive intraday path – cumulative KP composite score with overlays."""
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    instrument = request.args.get("instrument", "NIFTY")
    tz_name = request.args.get("tz", "Asia/Kolkata")

    cache_key = f"{date_str}-{instrument}-{tz_name}"
    now_ts = datetime.datetime.utcnow().timestamp()
    cached = _intraday_path_cache.get(cache_key)
    if cached:
        ts, data = cached
        if now_ts - ts < _CACHE_TTL_SECONDS:
            return jsonify(data), 200

    from datetime import date as dtdate
    trading_day = dtdate.fromisoformat(date_str)

    # Load KP report
    from pathlib import Path

    from sbc.kp_config import get_config, get_instrument_config
    from sbc.kp_intraday import generate_kp_intraday_report

    kp_data_dir = Path(__file__).resolve().parents[2] / "data" / "kp"
    kp_data_dir.mkdir(parents=True, exist_ok=True)
    month_file = kp_data_dir / f"KP_Data_{trading_day.strftime('%b%Y')}.csv"
    if not month_file.exists():
        return jsonify({
            "error": (
                f"KP data unavailable for {trading_day.strftime('%B %Y')}. "
                "Generate sample data explicitly to create it."
            )
        }), 404

    config = get_config()
    instrument_cfg = get_instrument_config(instrument, config)
    report = generate_kp_intraday_report(month_file, trading_day, instrument, instrument_cfg)

    # Build hourly series
    from sbc.intraday_projection import intraday_projection
    proj = intraday_projection(date_str, tz_name, days=1, anchor_key="nse")
    hours = proj.get("hours", [])

    # Simple cumulative composite score
    # Use hora quality + regime shifts as proxy
    series = []
    cumulative = 0.0
    # Map hora slots by time
    hora_map = {}
    for slot in report.day_signature.hora_slots:
        t = slot.start.strftime("%H:%M")
        hora_map[t] = slot

    from sbc.planets import positioned_planets
    # Nadi mapping for 27 nakshatras – simplified
    NADI_MAP = {
        "Ashwini":"Antya","Bharani":"Madhya","Krittika":"Aadi","Rohini":"Aadi","Mrigashira":"Madhya","Ardra":"Antya",
        "Punarvasu":"Antya","Pushya":"Aadi","Ashlesha":"Madhya","Magha":"Antya","Purva Phalguni":"Aadi","Uttara Phalguni":"Madhya",
        "Hasta":"Antya","Chitra":"Aadi","Swati":"Madhya","Vishakha":"Antya","Anuradha":"Aadi","Jyeshtha":"Madhya",
        "Mula":"Antya","Purva Ashadha":"Aadi","Uttara Ashadha":"Madhya","Shravana":"Antya","Dhanishta":"Aadi",
        "Shatabhisha":"Madhya","Purva Bhadrapada":"Antya","Uttara Bhadrapada":"Aadi","Revati":"Madhya"
    }
    NADI_MULTIPLIER = {"Neer":1.05,"Agni":0.95,"Vayu":1.0,"Prithvi":1.0}
    # Simplified Nadi element mapping
    NADI_ELEMENT_MAP = {
        "Aadi":"Agni","Madhya":"Vayu","Antya":"Neer"
    }

    def moon_vargottama_active(date_str, time_str, tz_name):
        planets, _, sun, moon, _ = positioned_planets(date_str, time_str, tz_name)
        moon_planet = next((p for p in planets if p["name"]=="Moon"), None)
        if not moon_planet:
            return False
        speed = abs(moon_planet.get("speed",0))
        return speed > 14.0

    def get_moon_nadi(date_str, time_str, tz_name):
        planets, _, _, _, _ = positioned_planets(date_str, time_str, tz_name)
        moon = next((p for p in planets if p["name"]=="Moon"), None)
        if not moon:
            return None, None, 1.0
        nakshatra = moon.get("nakshatra","")
        nadi_key = NADI_MAP.get(nakshatra,"Madhya")
        element = NADI_ELEMENT_MAP.get(nadi_key,"Vayu")
        # Map element to Nadi name used in doc
        nadi_name = {"Neer":"Neer","Agni":"Agni","Vayu":"Vayu","Prithvi":"Prithvi"}[element]
        mult = NADI_MULTIPLIER.get(nadi_name,1.0)
        return nakshatra, nadi_name, mult

    vargottama_flag = moon_vargottama_active(date_str, hours[0].get("clock","09:15") if hours else "09:15", tz_name)
    moon_nakshatra, nadi_name, nadi_mult = get_moon_nadi(date_str, hours[0].get("clock","09:15") if hours else "09:15", tz_name)

    # Rahu Moon-sub window Rule A-13 and Moon Affliction Gate Rule A-14
    moon_affliction_gate = getattr(getattr(report, "day_signature", None), "moon_affliction_gate", None)
    rahu_window_start = None
    rahu_window_end = None
    for rs in getattr(report, "regime_shifts", []):
        if rs.new_sublord == "Rahu":
            rahu_window_start = rs.timestamp.strftime("%H:%M")
            # Market close 15:30
            rahu_window_end = "15:30"
            break

    for h in hours:
        clock = h.get("clock", "")
        time_str = clock
        # Base SBC bias
        sbc_bias = h.get("projection", 0.0) * 0.2
        # Hora quality
        hora_quality = 0.0
        hora_lord = None
        hora_aspect_mod = 0.0
        if time_str in hora_map:
            slot = hora_map[time_str]
            q = slot.quality.name if hasattr(slot.quality, "name") else str(slot.quality)
            q_map = {"SLUGGISH": -0.5, "NEUTRAL": 0.0, "FRUITFUL": 0.5, "AGGRESSIVE": 0.8, "VOLATILE": 0.0}
            hora_quality = q_map.get(q, 0.0)
            hora_lord = slot.lord

            # Aspect modifiers for hora lord
            try:
                planets, _, _, _, _ = positioned_planets(date_str, clock, tz_name)
                def deg_diff(a,b):
                    d = abs(a-b) % 360
                    return min(d, 360-d)
                hora_planet = next((p for p in planets if p.get("symbol")==hora_lord or p.get("name")==hora_lord), None)
                if hora_planet:
                    hlon = hora_planet.get("longitude",0)
                    for p in planets:
                        pname = p.get("name")
                        if pname == hora_lord:
                            continue
                        d = deg_diff(hlon, p.get("longitude",0))
                        if pname in ("Moon","Mars") and d < 7:
                            hora_aspect_mod += 0.3  # trending/impulsive
                        if pname == "Rahu" and d in (90,150,180) or d < 7:
                            hora_aspect_mod -= 0.4  # trap/false-move
                        if pname == "Jupiter" and d < 10:
                            hora_aspect_mod += 0.25
            except Exception:
                pass

            hora_quality += hora_aspect_mod

        # Regime shift influence
        regime_delta = 0.0
        for rs in getattr(report, "regime_shifts", []):
            if rs.timestamp.strftime("%H:%M") == time_str:
                regime_delta = 1.5 if rs.direction.name == "BULLISH" else -1.5

        # Composite score for this hour
        score = sbc_bias * 0.4 + hora_quality * 1.0 + regime_delta
        cumulative += score

        # Flags – simplified heuristics
        dl_hora = hora_lord in ("Jupiter", "Venus") and hora_quality > 0.5
        dahan = hora_lord in ("Mars", "Saturn") and hora_quality < 0
        chand_vat = hora_lord in ("Moon", "Jupiter")

        series.append({
            "time": clock,
            "unix": h.get("time"),
            "sbc_bias": round(sbc_bias, 3),
            "hora_lord": hora_lord,
            "hora_quality": round(hora_quality, 3),
            "hora_aspect_mod": round(hora_aspect_mod, 3),
            "regime_delta": regime_delta,
            "score": round(score, 3),
            "cumulative": round(cumulative, 3),
            "dl_hora": bool(dl_hora),
            "dahan": bool(dahan),
            "chand_vat": bool(chand_vat),
            "vargottama_moon": bool(vargottama_flag),
            "nadi_multiplier": nadi_mult,
            "navamsa_moon_element": None,
        })

    # Build reversal / trend change payload
    trend_changes = []
    for tc in getattr(report, "trend_changes", []):
        trend_changes.append({
            "time": tc.timestamp.strftime("%H:%M"),
            "grade": tc.grade.value if hasattr(tc.grade, "value") else str(tc.grade),
            "direction": tc.direction.value if hasattr(tc.direction, "value") else str(tc.direction),
            "score": tc.score,
            "trigger": tc.trigger,
            "notes": tc.notes
        })

    regime_shifts = []
    for rs in getattr(report, "regime_shifts", []):
        regime_shifts.append({
            "time": rs.timestamp.strftime("%H:%M"),
            "planet": rs.planet,
            "old_sublord": rs.old_sublord,
            "new_sublord": rs.new_sublord,
            "house_set_strength": rs.house_set_strength,
            "regime_label": rs.regime_label,
            "direction": rs.direction.value if hasattr(rs.direction, "value") else str(rs.direction)
        })

    exhaustion_warnings = getattr(report, "exhaustion_warnings", [])

    strongest_bullish = None
    sb = getattr(report, "strongest_bullish", None)
    if sb:
        strongest_bullish = {
            "start": sb.start.strftime("%H:%M"),
            "end": sb.end.strftime("%H:%M"),
            "score": sb.score,
            "direction": sb.direction.value if hasattr(sb.direction, "value") else str(sb.direction)
        }

    strongest_bearish = None
    sbr = getattr(report, "strongest_bearish", None)
    if sbr:
        strongest_bearish = {
            "start": sbr.start.strftime("%H:%M"),
            "end": sbr.end.strftime("%H:%M"),
            "score": sbr.score,
            "direction": sbr.direction.value if hasattr(sbr.direction, "value") else str(sbr.direction)
        }

    response_data = {
        "date": date_str,
        "instrument": instrument,
        "tz": tz_name,
        "series": series,
        "regime_shifts": regime_shifts,
        "trend_changes": trend_changes,
        "exhaustion_warnings": exhaustion_warnings,
        "strongest_bullish": strongest_bullish,
        "strongest_bearish": strongest_bearish,
        "report_summary": {
            "day_lord": getattr(report.day_signature, "day_lord", None),
            "moon_sign": getattr(report.day_signature, "moon_sign", None),
            "regime_shifts_count": len(getattr(report, "regime_shifts", [])),
            "vargottama_moon": bool(vargottama_flag),
            "moon_nakshatra": moon_nakshatra,
            "nadi": nadi_name,
            "nadi_multiplier": nadi_mult,
            "navamsa_moon_element": None,
            "lagna_lord_navamsa": None,
            "day_bias_navamsa_confirmation": None,
            "moon_affliction_gate": moon_affliction_gate,
            "rahu_moon_sub_window_start": rahu_window_start,
            "rahu_moon_sub_window_end": rahu_window_end,
        }
    }
    _intraday_path_cache[cache_key] = (now_ts, response_data)
    return jsonify(response_data), 200


@engine_bp.route("/kota/daily")
def kota_daily():
    import datetime

    from sbc.kota_chakra import parse_kota_excel
    date_str = request.args.get("date")
    instrument = request.args.get("instrument", "NIFTY").upper()
    cache_key = f"kota_daily-{date_str}-{instrument}"
    now_ts = datetime.datetime.utcnow().timestamp()
    cached = _kota_cache.get(cache_key)
    if cached:
        ts, data = cached
        if now_ts - ts < _KOTA_TTL_SECONDS:
            return jsonify(data), 200
    # Default path
    excel_path = _kota_excel_path()
    if not excel_path.exists():
        return jsonify({"error": "Kota Excel not found"}), 404
    sheets = parse_kota_excel(excel_path)
    # Find dashboard sheet
    dashboard_key = next((k for k in sheets if "Dashboard" in k), None)
    if not dashboard_key:
        return jsonify({"error": "Dashboard sheet not found"}), 404
    df = sheets[dashboard_key]
    # Filter by date
    # Try to find date column
    date_col = next((c for c in df.columns if "Date" in str(c)), None)
    if not date_col:
        return jsonify({"error": "Date column not found"}), 404
    filtered = df[df[date_col].astype(str).str.contains(date_str, na=False)]
    result = {
        "date": date_str,
        "instrument": instrument,
        "records": filtered.to_dict(orient="records")
    }
    return jsonify(result), 200


@engine_bp.route("/kota/weekly")
def kota_weekly():
    from sbc.kota_chakra import parse_kota_excel
    week_start = request.args.get("week_start")
    if not week_start:
        return jsonify({"error": "week_start is required"}), 400
    excel_path = _kota_excel_path()
    if not excel_path.exists():
        return jsonify({"error": "Kota Excel not found"}), 404
    sheets = parse_kota_excel(excel_path)
    dashboard_key = next((k for k in sheets if "Dashboard" in k), None)
    if not dashboard_key:
        return jsonify({"error": "Dashboard sheet not found"}), 404
    df = sheets[dashboard_key]
    date_col = next((c for c in df.columns if "Date" in str(c)), None)
    if not date_col:
        return jsonify({"error": "Date column not found"}), 404
    # Simple weekly filter by week_start string presence
    filtered = df[df[date_col].astype(str).str.contains(week_start, na=False)]
    result = {
        "week_start": week_start,
        "records": filtered.to_dict(orient="records")
    }
    return jsonify(result), 200


@engine_bp.route("/kota/monthly")
def kota_monthly():
    from sbc.kota_chakra import parse_kota_excel
    month = request.args.get("month")
    if not month:
        return jsonify({"error": "month is required"}), 400
    excel_path = _kota_excel_path()
    if not excel_path.exists():
        return jsonify({"error": "Kota Excel not found"}), 404
    sheets = parse_kota_excel(excel_path)
    monthly_key = next((k for k in sheets if "Monthly" in k), None)
    if not monthly_key:
        return jsonify({"error": "Monthly sheet not found"}), 404
    df = sheets[monthly_key]
    # Filter by month string
    filtered = df[df.astype(str).apply(lambda row: row.str.contains(month, na=False)).any(axis=1)]
    result = {
        "month": month,
        "summary": filtered.to_dict(orient="records")
    }
    return jsonify(result), 200


@engine_bp.route("/confluence/daily")
def confluence_daily():
    """Unified daily forecast contract: SBC + KP + Kota confluence verdict.

    Shared source for current and forward confluence data. Components that
    fail (missing KP data, Kota workbook, ephemeris) are excluded and their
    weight is redistributed; the response carries cache metadata, data
    freshness, and the calculation version.
    """
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    instrument = request.args.get("instrument", "NIFTY").upper()
    now_ts = datetime.datetime.utcnow().timestamp()
    cache_key = f"confluence_daily-{date_str}-{instrument}"
    cached = _confluence_cache.get(cache_key)
    if cached:
        ts, data = cached
        if now_ts - ts < _CACHE_TTL_SECONDS:
            cache_meta = {"cached": True, "cache_age_seconds": round(now_ts - ts, 1)}
            return jsonify({**data, "cache": cache_meta}), 200

    components = {}

    # SBC daily net (normalised -1..1)
    try:
        from sbc.market_calendar import _anchor_nakshatra
        from sbc.planets import positioned_planets
        from sbc.prediction import analyze, compute_vedhas
        planets, ayanamsa, sun, moon, tithi = positioned_planets(date_str, "09:15", "Asia/Kolkata")
        vedha_map, _ = compute_vedhas(planets, school="classical")
        analysis = analyze(planets, vedha_map, _anchor_nakshatra("nse"), school="classical")
        sbc_net = float(analysis["net"])
        components["sbc"] = max(-1.0, min(1.0, sbc_net / 3.0))
    except Exception:
        components["sbc"] = None

    # KP intraday cumulative (final cumulative, normalised)
    kp_cumulative = None
    try:
        from pathlib import Path

        from sbc.kp_config import get_config, get_instrument_config
        from sbc.kp_intraday import build_cumulative_path, generate_kp_intraday_report
        trading_day = datetime.date.fromisoformat(date_str)
        kp_data_dir = Path(__file__).resolve().parents[2] / "data" / "kp"
        month_file = kp_data_dir / f"KP_Data_{trading_day.strftime('%b%Y')}.csv"
        if month_file.exists():
            config = get_config()
            instrument_cfg = get_instrument_config(instrument, config)
            report = generate_kp_intraday_report(month_file, trading_day, instrument, instrument_cfg)
            path = build_cumulative_path(report, step_minutes=60)
            if path:
                final = path[-1]["cumulative"]
                kp_cumulative = max(-1.0, min(1.0, final / 6.0))
        components["kp"] = kp_cumulative
    except Exception:
        components["kp"] = None

    # Kota daily score (normalised)
    kota_score = None
    try:
        import pandas as pd
        excel_path = _kota_excel_path()
        if excel_path.exists():
            from sbc.kota_chakra import parse_kota_excel
            sheets = parse_kota_excel(excel_path)
            dashboard_key = next((k for k in sheets if "Dashboard" in k), None)
            if dashboard_key:
                df = sheets[dashboard_key]
                date_col = next((c for c in df.columns if "Date" in str(c)), None)
                score_cols = [c for c in df.columns if "score" in str(c).lower()]
                if date_col and score_cols:
                    filtered = df[df[date_col].astype(str).str.contains(date_str, na=False)]
                    if not filtered.empty:
                        vals = pd.to_numeric(filtered[score_cols[0]], errors="coerce").dropna()
                        if not vals.empty:
                            value = float(vals.iloc[-1])
                            kota_score = max(-1.0, min(1.0, value / 100.0 if abs(value) > 1.5 else value))
        components["kota"] = kota_score
    except Exception:
        components["kota"] = None

    from sbc import __version__
    from sbc.confluence import blend_forecast_scores
    weights = {"sbc": 0.4, "kp": 0.4, "kota": 0.2}
    blended = blend_forecast_scores(components, weights)

    data = {
        "date": date_str,
        "instrument": instrument,
        **blended,
        "calculation_version": __version__,
        "weights_config": weights,
        "freshness": {
            "date": date_str,
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        },
        "cache": {"cached": False, "cache_age_seconds": 0},
    }
    _confluence_cache[cache_key] = (now_ts, data)
    return jsonify(data), 200
