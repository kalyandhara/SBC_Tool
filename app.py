"""Sarvatobhadra Chakra market prediction - Flask app."""

import os
import hmac
import datetime
import time
import sqlite3
import json
from io import BytesIO
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Flask, Response, jsonify, render_template, request, send_file

from sbc.chakra import GRID
from sbc.nakshatra import (
    GROUP_OF_TITHI, GROUP_WEEKDAYS, NAKSHATRAS_27, paksha_of,
    tithi_of,
)
from sbc.planets import all_planets_with_natures, positions
from sbc.prediction import (
    analyze, compute_vedhas, place_planets, planet_sector_read,
    recommendation, sector_read, summarize_vedhas,
)
from sbc.market_calendar import reversal_alert, upcoming_yoga_alerts
from sbc.bhadra import bhadra_calendar
from sbc.intraday_projection import intraday_projection
from sbc.monthly_heatmap import monthly_heatmap
from sbc.backtest import run_backtest, run_futurecast, run_bullish_futurecast, run_bearish_futurecast
from sbc.backtest import _bearish_future_score, _julian_at_noon, run_saturn_macro_analysis
from sbc.trade_setups import TRADE_SETUPS
from sbc.crash_analyzer import analyze_crash_risk, daily_crash_briefing, backtest_crashes
from sbc.astro_plot import generate_astro_plot, serialize_plot_data
from sbc.weekly_commentary import generate_weekly_commentary, format_commentary_text
from sbc.market_data import get_nifty_ohlc, moon_rashi
from sbc.metrics import _bias_scale, _western_bias
from sbc.config import RASHI_TREND, SECTOR_NAME_MAP
from sbc import series_cache
from werkzeug.exceptions import HTTPException
from sbc.sector_keywords import keywords_for
from sbc.bullion_vedha import scan_bullion_vedha_matrix, scan_bullion_vedha_week, format_bullion_vedha_for_ui
from sbc.transit_vedha import scan_transit_vedha_matrix, scan_transit_vedha_week, format_transit_vedha_for_ui
from sbc.sector_signals import scan_sector_vedhas
from sbc.cgsp_framework import generate_cgsp_report
from sbc.kp_intraday import (
    generate_kp_intraday_report, generate_sample_kp_csv,
    KPIntradayReport, KPDataParser, KPRuleEngine, KPReportGenerator
)
from sbc.kp_config import get_config, get_instrument_config
from sbc.market_events import lunar_phase_event, planetary_aspect_events
from research.astro_research import (
    astro_lab,
    walk_forward_validation,
    canonical_market_event_model,
    new_moon_efficiency_study,
    planetary_aspect_grid,
    solar_lunar_cycle_explorer,
    bradley_barometer_overlay,
    regime_aware_reports,
    research_export,
    unified_daily_forecast_contract,
)

from sbc.db import _bootstrap
from sbc.api.engine_bp import engine_bp
from sbc.api.sector_bp import sector_bp

app = Flask(__name__)
_bootstrap()  # Ensure DB schema exists
app.register_blueprint(engine_bp)
app.register_blueprint(sector_bp)
_daily_confluence_cache = {}
# Always render the current template from disk (avoids stale HTML during dev iteration)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True
app.jinja_env.cache = {}

# Simple in-memory rate limiter
_request_times = defaultdict(list)


# A page load fires ~30 requests, so the old 60/min ceiling throttled the
# second refresh in a minute. nginx.conf enforces the real limit in production.
_RATE_LIMIT_PER_MIN = 240


@app.before_request
def _rate_limit():
    if app.testing:
        return None
    ip = request.remote_addr
    now = time.time()
    _request_times[ip] = [t for t in _request_times[ip] if now - t < 60]
    if len(_request_times[ip]) > _RATE_LIMIT_PER_MIN:
        return jsonify({"error": "rate limit"}), 429
    _request_times[ip].append(now)


_API_TOKEN = os.environ.get("SBC_API_TOKEN", "").strip()
_LOCAL_ADDRS = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}


@app.before_request
def _require_write_token():
    """Every non-GET route mutates state (profiles, habits, the webhook file).

    With SBC_API_TOKEN set, writes need a matching X-API-Token header.
    Without it, writes are accepted from this machine only, so binding to
    0.0.0.0 for a phone on the LAN no longer lets that phone rewrite data.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return None
    if _API_TOKEN:
        supplied = request.headers.get("X-API-Token", "")
        if supplied and hmac.compare_digest(supplied, _API_TOKEN):
            return None
        return jsonify({"error": "write endpoints require a valid X-API-Token header"}), 401
    if request.remote_addr in _LOCAL_ADDRS:
        return None
    return jsonify({"error": "write endpoints are local-only until SBC_API_TOKEN is set"}), 403


@app.errorhandler(Exception)
def _unhandled(exc):
    """Log the traceback and answer JSON, instead of Flask's HTML 500 page.

    Routes that catch their own exceptions are unaffected; this is the net
    under the ones that don't (contra_signals returned bare 500s for weeks).
    """
    if isinstance(exc, HTTPException):
        return exc
    app.logger.exception("Unhandled error on %s %s", request.method, request.path)
    return jsonify({"error": "internal error", "type": type(exc).__name__}), 500


@app.after_request
def _no_cache(response):
    """Prevent stale asset/HTML caching in the preview proxy."""
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "engine": "sbc"}), 200


@app.after_request
def _csp(response):
    """Basic Content Security Policy - relaxed for development."""
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self'"
    )
    return response

# Market anchors: entity -> (incorporation/base date, description).
# The Moon's nakshatra at that moment becomes the market's birth star.
ANCHORS = {
    "nse": {
        "name": "NSE (National Stock Exchange)",
        "date": "1992-11-27",
        "time": "00:00",
        "tz": "Asia/Kolkata",
        "note": "Incorporated 27 Nov 1992",
    },
    "bse": {
        "name": "BSE (Bombay Stock Exchange)",
        "date": "1875-07-09",
        "time": "00:00",
        "tz": "Asia/Kolkata",
        "note": "Founded 9 Jul 1875",
    },
    "nifty": {
        "name": "NIFTY 50 Index",
        "date": "1995-11-03",
        "time": "00:00",
        "tz": "Asia/Kolkata",
        "note": "Base date 3 Nov 1995",
    },
    "sensex": {
        "name": "SENSEX Index",
        "date": "1979-04-01",
        "time": "00:00",
        "tz": "Asia/Kolkata",
        "note": "Base date 1 Apr 1979",
    },
    "india": {
        "name": "India (national market)",
        "date": "1947-08-15",
        "time": "00:00",
        "tz": "Asia/Kolkata",
        "note": "Independence 15 Aug 1947",
    },
}

_anchor_cache = {}


def _utc_from_local(date_str, time_str, tz_name):
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("Asia/Kolkata")
    y, m, d = (int(x) for x in date_str.split("-"))
    hh, mm = (int(x) for x in time_str.split(":"))
    local = datetime.datetime(y, m, d, hh, mm, tzinfo=tz)
    return local.astimezone(datetime.timezone.utc).replace(tzinfo=None)


def _anchor_nakshatra(anchor_key):
    if anchor_key in _anchor_cache:
        return _anchor_cache[anchor_key]
    info = ANCHORS[anchor_key]
    utc = _utc_from_local(info["date"], info["time"], info["tz"])
    jul = _julday(utc)
    planets, _ = positions(jul)
    moon = next(p for p in planets if p["name"] == "Moon")
    _anchor_cache[anchor_key] = moon["nakshatra"]
    return _anchor_cache[anchor_key]


def _julday(utc_dt):
    import swisseph as swe
    h = utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
    return swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, h)


WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
            "Saturday", "Sunday"]


def _tithi_info(planets, tithi):
    from sbc.nakshatra import moon_nature
    group = GROUP_OF_TITHI.get(tithi, "Purna")
    pk = paksha_of(tithi)
    moon_n = moon_nature(tithi)
    return {
        "tithi": tithi,
        "paksha": pk,
        "group": group,
        "group_weekdays": GROUP_WEEKDAYS[group],
        "moon_note": (
            "ashubha Moon (Krishna Ekadashi through Shukla Chaturthi)"
            if moon_n == "malefic"
            else "shubha Moon (Shukla Panchami through Krishna Dashami)"
        ),
    }


def build_response(date_str, time_str, tz_name, anchor_key, school):
    utc = _utc_from_local(date_str, time_str, tz_name)
    jul = _julday(utc)
    planets, ayanamsa = positions(jul)

    sun = next(p for p in planets if p["name"] == "Sun")
    moon = next(p for p in planets if p["name"] == "Moon")
    tithi = tithi_of(sun["longitude"], moon["longitude"])
    tithi_info = _tithi_info(planets, tithi)

    planets = all_planets_with_natures(planets, tithi, sun["longitude"])

    anchor = ANCHORS[anchor_key]
    birth_nakshatra = _anchor_nakshatra(anchor_key)

    grid = place_planets(GRID, planets)
    vedha_map, ray_paths = compute_vedhas(planets, school=school)

    # Analysis
    analysis = analyze(planets, vedha_map, birth_nakshatra, school)

    weekday = WEEKDAYS[datetime.date.fromisoformat(date_str).weekday()]

    # mark points on grid
    for pt in analysis["points"]:
        cell = analysis["point_cells"][pt["name"]]
        if cell:
            r, c = cell
            grid[r - 1][c - 1].setdefault("points", []).append(pt["name"])

    for p in planets:
        for hit in vedha_map[p["name"]]:
            r, c = hit["row"], hit["col"]
            cell = grid[r - 1][c - 1]
            cell.setdefault("vedha", []).append({
                "planet": p["name"],
                "symbol": p["symbol"],
                "nature": p["nature"],
                "ray": hit["ray"],
            })

    rec = recommendation(analysis, anchor, date_str, weekday, tithi_info)
    calendar_alert = reversal_alert(date_str, planets, tithi)
    yoga_alerts = upcoming_yoga_alerts(date_str, time_str, tz_name)

    # Get applicable trade setups for current confluence
    trade_setups_data = []
    if calendar_alert.get("confluence"):
        from sbc.trade_setups import setups_for_confluence, format_setup_for_display
        applicable = setups_for_confluence(calendar_alert["confluence"])
        for setup in applicable:
            trade_setups_data.append({
                "name": setup.name,
                "direction": setup.direction,
                "trigger": setup.trigger,
                "entry": setup.entry,
                "stop": setup.stop,
                "target": setup.target,
                "sizing": setup.sizing,
                "filters": setup.filters,
                "historical": setup.historical,
                "markets": setup.applicable_markets,
                "timeframes": setup.timeframes,
                "formatted": format_setup_for_display(setup),
            })

    # attach ray paths for drawing
    for p in planets:
        p["rays"] = ray_paths.get(p["name"], [])

    def _serialize_cell(cell):
        out = {
            "row": cell["row"],
            "col": cell["col"],
            "type": cell["type"],
            "label": cell["label"],
            "weekdays": cell.get("weekdays"),
        }
        if "planets" in cell:
            out["planets"] = [{
                "name": p["name"],
                "symbol": p["symbol"],
                "nature": p["nature"],
            } for p in cell["planets"]]
        if "points" in cell:
            out["points"] = cell["points"]
        if "vedha" in cell:
            out["vedha"] = cell["vedha"]
        return out

    return {
        "date": date_str,
        "time": time_str,
        "timezone": tz_name,
        "weekday": weekday,
        "ayanamsa": round(ayanamsa, 4),
        "school": school,
        "anchor": {
            "key": anchor_key,
            "name": anchor["name"],
            "note": anchor["note"],
            "nakshatra": birth_nakshatra,
        },
        "tithi": tithi_info,
        "planets": planets,
        "grid": [[_serialize_cell(c) for c in row] for row in grid],
        "points": analysis["points"],
        "point_hits": analysis["point_hits"],
        "per_point": analysis["per_point"],
        "vedhas": summarize_vedhas(vedha_map, planets, analysis["points"]),
        "sectors": sector_read(vedha_map, planets),
        "planet_sectors": planet_sector_read(planets),
        "score": analysis["score"],
        "net": analysis["net"],
        "sentiment": {"verdict": rec["verdict"], "strength": rec["strength"]},
        "recommendation": rec,
        "market_alert": calendar_alert,
        "yoga_alerts": yoga_alerts,
        "trade_setups": trade_setups_data,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/presets")
def presets():
    return jsonify({
        "anchors": [
            {"key": k, **{kk: vv for kk, vv in v.items() if kk != "date"}}
            for k, v in ANCHORS.items()
        ],
        "nakshatras": NAKSHATRAS_27,
    })


@app.route("/api/backtest")
def backtest():
    return jsonify(run_backtest())


@app.route("/api/futurecast")
def futurecast():
    center_date = request.args.get("date")
    try:
        if center_date:
            datetime.datetime.strptime(center_date, "%Y-%m-%d")
        return jsonify(run_futurecast(center_date=center_date))
    except ValueError:
        return jsonify({"error": "invalid date"}), 400


@app.route("/api/bullish_futurecast")
def bullish_futurecast():
    center_date = request.args.get("date")
    years = request.args.get("years", type=int, default=1)
    try:
        if center_date:
            datetime.datetime.strptime(center_date, "%Y-%m-%d")
        years = min(max(years, 1), 10)
        return jsonify(run_bullish_futurecast(center_date=center_date, years=years))
    except ValueError:
        return jsonify({"error": "invalid date"}), 400


@app.route("/api/bearish_futurecast")
def bearish_futurecast():
    center_date = request.args.get("date")
    years = request.args.get("years", type=int, default=1)
    try:
        if center_date:
            datetime.datetime.strptime(center_date, "%Y-%m-%d")
        years = min(max(years, 1), 10)
        return jsonify(run_bearish_futurecast(center_date=center_date, years=years))
    except ValueError:
        return jsonify({"error": "invalid date"}), 400


@app.route("/api/saturn_macro")
def saturn_macro():
    center_date = request.args.get("date")
    years_back = request.args.get("years_back", type=int, default=100)
    years_forward = request.args.get("years_forward", type=int, default=10)
    try:
        if center_date:
            datetime.datetime.strptime(center_date, "%Y-%m-%d")
        years_back = min(max(years_back, 10), 150)
        years_forward = min(max(years_forward, 1), 30)
        return jsonify(run_saturn_macro_analysis(center_date=center_date, years_back=years_back, years_forward=years_forward))
    except ValueError:
        return jsonify({"error": "invalid date"}), 400


@app.route("/api/weekly_commentary")
def weekly_commentary():
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


@app.route("/api/intraday_projection")
def intraday_projection_endpoint():
    """Hourly NIFTY astro-projection with yoga windows for N days forward."""
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


@app.route("/api/bhadra_calendar")
def bhadra_calendar_endpoint():
    """Bhadra (Vishti Karana) calendar for a month, with reversal-watch overlap."""
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    tz_name = request.args.get("tz") or "Asia/Kolkata"
    try:
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        offset = 0
    # Allow only a bounded window of navigation.
    offset = max(-12, min(12, offset))

    try:
        datetime.date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "invalid date"}), 400

    result = bhadra_calendar(date_str, tz_name, offset)

    # Compute reversal-watch overlap for the same month so the Bhadra
    # windows can be cross-referenced against the reversal calendar.
    windows = result["windows"]
    if windows:
        try:
            from sbc.market_calendar import reversal_alert
            from sbc.planets import positions
            from sbc.backtest import _julian_at_noon
            from sbc.nakshatra import tithi_of

            # Days covered by this month's Bhadra windows, plus the muhurt
            # (begin/end local time) details for each overlapping window so
            # the reversal-day cross-reference can show the exact Bhadra
            # inauspicious span.
            covered_days = set()
            day_windows = {}  # date_str -> list of Bhadra window details
            for w in windows:
                b = datetime.date.fromisoformat(w["begin_iso"][:10])
                e = datetime.date.fromisoformat(w["end_iso"][:10])
                d = b
                while d <= e:
                    covered_days.add(d.isoformat())
                    # Determine the clipped in-window begin/end for this day.
                    day_begin = w["begin_iso"]
                    day_end = w["end_iso"]
                    day_str = d.isoformat()
                    if day_str > w["begin_iso"][:10]:
                        day_begin = f"{day_str}T00:00:00"
                    if day_str < w["end_iso"][:10]:
                        day_end = f"{day_str}T23:59:59"
                    day_windows.setdefault(day_str, []).append({
                        "begin_iso": day_begin,
                        "end_iso": day_end,
                        "begin_time": w["begin_time"],
                        "end_time": w["end_time"],
                        "begin_date": w["begin_date"],
                        "end_date": w["end_date"],
                        "spans_midnight": w.get("spans_midnight", False),
                        # Actual full-window start/end of the muhurt that
                        # overlaps this day.
                        "muhurt_begin_iso": w["begin_iso"],
                        "muhurt_end_iso": w["end_iso"],
                        "muhurt_begin_time": w["begin_time"],
                        "muhurt_end_time": w["end_time"],
                    })
                    d += datetime.timedelta(days=1)

            # Reversal windows for the first day of the month.
            month_first = f"{result['month_start']}"
            planets, _ = positions(_julian_at_noon(month_first))
            sun = next(p for p in planets if p["name"] == "Sun")
            moon = next(p for p in planets if p["name"] == "Moon")
            tithi = tithi_of(sun["longitude"], moon["longitude"])
            rev = reversal_alert(month_first, planets, tithi)

            month_end = datetime.date.fromisoformat(month_first).replace(
                day=28) + datetime.timedelta(days=4)
            month_end = month_end.replace(day=1) - datetime.timedelta(days=1)

            overlap = {
                "reversal_days": [],
            }
            for wd in rev.get("watch_days", []):
                if month_first <= wd["date"] <= month_end.isoformat() and wd["windows"]:
                    bhadra_overlap = wd["date"] in covered_days
                    entry = {
                        "date": wd["date"],
                        "bhadra_overlap": bhadra_overlap,
                        "reversal_count": len(wd["windows"]),
                        "titles": [x["title"] for x in wd["windows"]],
                    }
                    if bhadra_overlap:
                        # Attach the exact Bhadra muhurt span(s) for this day.
                        entry["bhadra_windows"] = day_windows.get(wd["date"], [])
                    overlap["reversal_days"].append(entry)
            overlap["bhadra_overlap_days"] = sorted(
                d for d in covered_days if month_first <= d <= month_end.isoformat())
            overlap["total_reversal_days"] = len(overlap["reversal_days"])
            overlap["overlap_count"] = sum(
                1 for d in overlap["reversal_days"] if d["bhadra_overlap"])
            result["reversal_overlap"] = overlap
        except Exception as exc:
            result["reversal_overlap"] = {"error": str(exc)}

    return jsonify(result)


@app.route("/api/monthly_heatmap")
def monthly_heatmap_endpoint():
    """Sector x day confluence heatmap + lunar timing strip."""
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
        from sbc.monthly_heatmap import monthly_heatmap as _mh
        result = _mh(start_date=date_str, days=days, tz_name=tz_name, anchor_key=anchor)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify(result)


@app.route("/api/bullion_vedha")
def bullion_vedha():
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    try:
        date = datetime.date.fromisoformat(date_str)
        result = scan_bullion_vedha_matrix(date)
        return jsonify({
            "date": result["date"],
            "ayanamsa": result["ayanamsa"],
            "text": format_bullion_vedha_for_ui(result),
            "data": {
                "summary": result["summary"],
                "signals": result["signals"],
                "matrix_reference": result["matrix_reference"],
            }
        })
    except ValueError:
        return jsonify({"error": "invalid date"}), 400


@app.route("/api/bullion_vedha_week")
def bullion_vedha_week():
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    try:
        date = datetime.date.fromisoformat(date_str)
        result = scan_bullion_vedha_week(date)
        return jsonify({
            "week_start": result["week_start"],
            "week_end": result["week_end"],
            "weekly_summary": result["weekly_summary"],
            "weekly_unique_signals": result["weekly_unique_signals"],
            "daily_scans": [
                {
                    "date": d["date"],
                    "summary": d["summary"],
                    "signal_count": len(d["signals"]),
                } for d in result["daily_scans"]
            ],
        })
    except ValueError:
        return jsonify({"error": "invalid date"}), 400


@app.route("/api/transit_vedha")
def transit_vedha():
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    try:
        date = datetime.date.fromisoformat(date_str)
        result = scan_transit_vedha_matrix(date)
        return jsonify({
            "date": result["date"],
            "ayanamsa": result["ayanamsa"],
            "text": format_transit_vedha_for_ui(result),
            "data": {
                "summary": result["signals"],  # reuse signals as summary
                "signals": result["signals"],
                "by_sector": result["by_sector"],
                "matrix_reference": result["matrix_reference"],
            }
        })
    except ValueError:
        return jsonify({"error": "invalid date"}), 400


@app.route("/api/transit_vedha_week")
def transit_vedha_week():
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    try:
        date = datetime.date.fromisoformat(date_str)
        result = scan_transit_vedha_week(date)
        return jsonify({
            "week_start": result["week_start"],
            "week_end": result["week_end"],
            "weekly_summary": result["weekly_summary"],
            "weekly_unique_signals": result["weekly_unique_signals"],
            "weekly_sector_summary": result["weekly_sector_summary"],
            "daily_scans": [
                {
                    "date": d["date"],
                    "signal_count": len(d["signals"]),
                } for d in result["daily_scans"]
            ],
        })
    except ValueError:
        return jsonify({"error": "invalid date"}), 400


@app.route("/api/trade_setups")
def trade_setups():
    from sbc.trade_setups import list_setups, get_setup, format_setup_for_display
    name = request.args.get("name")
    if name:
        setup = get_setup(name)
        if not setup:
            return jsonify({"error": "setup not found"}), 404
        return jsonify({
            "name": setup.name,
            "direction": setup.direction,
            "trigger": setup.trigger,
            "entry": setup.entry,
            "stop": setup.stop,
            "target": setup.target,
            "sizing": setup.sizing,
            "filters": setup.filters,
            "historical": setup.historical,
            "markets": setup.applicable_markets,
            "timeframes": setup.timeframes,
            "formatted": format_setup_for_display(setup),
        })
    return jsonify({
        "setups": [
            {
                "name": s.name,
                "direction": s.direction,
                "markets": s.applicable_markets,
                "timeframes": s.timeframes,
                "historical": s.historical,
            }
            for s in TRADE_SETUPS.values()
        ]
    })


@app.route("/api/prediction")
def prediction():
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


@app.route("/api/nifty_chart")
def nifty_chart():
    """NIFTY 50 daily OHLC candles for the chart (yfinance + local cache)."""
    start = request.args.get("start")
    end = request.args.get("end")
    try:
        for d in (start, end):
            if d:
                datetime.datetime.strptime(d, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    return jsonify({"candles": get_nifty_ohlc(start, end), "symbol": "^NSEI"})


@app.route("/api/nakshatra_chart")
def nakshatra_chart():
    """Render a native Python NIFTY chart with the selected forecast bias."""
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    try:
        center = datetime.date.fromisoformat(date_str)
        months = min(max(int(request.args.get("months", "3")), 1), 12)
    except (TypeError, ValueError):
        return jsonify({"error": "invalid date or chart range"}), 400

    start = center - datetime.timedelta(days=months * 31)
    candles = get_nifty_ohlc(start.isoformat(), center.isoformat())
    if not candles:
        return jsonify({"error": "NIFTY price data is unavailable"}), 503

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
        import pandas as pd

        frame = pd.DataFrame(candles)
        frame["date"] = pd.to_datetime(frame["time"])
        selected = build_response(date_str, "09:15", "Asia/Kolkata", "nifty", "allthree")
        score = float(selected.get("net", 0))
        verdict = selected.get("sentiment", {}).get("verdict", "NEUTRAL")

        fig, ax = plt.subplots(figsize=(12, 5.5), dpi=140)
        fig.patch.set_facecolor("#0b1220")
        ax.set_facecolor("#111a2e")
        ax.plot(frame["date"], frame["close"], color="#fbbf24", linewidth=1.8, label="NIFTY 50 close")
        ax.fill_between(frame["date"], frame["low"], frame["high"], color="#fbbf24", alpha=0.08, label="Daily range")
        ax.axvline(pd.Timestamp(center), color="#38bdf8", linestyle="--", linewidth=1, label="Forecast date")
        color = "#34d399" if score > 0 else "#f87171" if score < 0 else "#94a3b8"
        ax.scatter([pd.Timestamp(center)], [frame["close"].iloc[-1]], color=color, s=70, zorder=4)
        ax.annotate(f"{verdict}  {score:+.2f}", (pd.Timestamp(center), frame["close"].iloc[-1]),
                    xytext=(10, 12), textcoords="offset points", color=color, fontsize=9,
                    bbox={"boxstyle": "round,pad=0.3", "fc": "#0b1220", "ec": color, "alpha": 0.9})
        ax.set_title(f"NIFTY 50 · Daily Nakshatra + SBC Confluence · {center.isoformat()}", color="#f8fafc", loc="left", pad=14)
        ax.set_ylabel("Index level", color="#94a3b8")
        ax.grid(True, color="#334155", alpha=0.35)
        ax.tick_params(colors="#cbd5e1")
        for spine in ax.spines.values():
            spine.set_color("#334155")
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        fig.autofmt_xdate()
        ax.legend(facecolor="#111a2e", edgecolor="#334155", labelcolor="#e2e8f0", loc="upper left")
        fig.tight_layout()
        output = BytesIO()
        fig.savefig(output, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight")
        plt.close(fig)
        output.seek(0)
        return send_file(output, mimetype="image/png", max_age=0)
    except Exception:
        app.logger.exception("Native Nakshatra chart failed")
        return jsonify({"error": "native chart generation failed"}), 500


_series_cache = {}


@app.route("/api/prediction_series")
def prediction_series():
    """Compact per-day astro prediction scores over a date range.

    Used to overlay bullish/bearish markers + sentiment bands on the
    NIFTY price chart. Works for past and future dates alike.
    """
    start = request.args.get("start")
    end = request.args.get("end")
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

    # L2: rows already computed by a previous process / worker
    wanted = []
    d = start_d
    while d <= end_d:
        if (d.isoformat(), anchor_key, school) not in _series_cache:
            wanted.append(d.isoformat())
        d += datetime.timedelta(days=1)
    for ds, payload in series_cache.get_many(wanted, anchor_key, school).items():
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
                _LEVEL_RANK = {"LOW": 1, "MODERATE": 2, "MODERATE-HIGH": 3,
                               "HIGH": 4, "VERY HIGH": 5, "EXTREME": 6,
                               "CRITICAL": 7}
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
            except Exception as exc:
                _series_cache[key] = {"date": ds, "error": str(exc)}
        out.append(_series_cache[key])
        d += datetime.timedelta(days=1)
    if fresh:
        series_cache.put_many(fresh, anchor_key, school)
    return jsonify({"series": out, "anchor": anchor_key})


_balance_cache = {}


@app.route("/api/daily_indication_balance")
def daily_indication_balance():
    """30-day daily indication balance: blended bias bars + three school lines.

    Schools: Jyotish (classical single-ray), KP (all-three Narasimha Rao rays)
    and Western (zodiac-dignity synthetic line). Each day is scored on the
    Vedic net, mapped to a 0..6 bias scale.
    """
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

    days = []
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


# ---------------------------------------------------------------
# Contra Strategy Confluence endpoint
# Returns 3-layer confluence + cheat‑sheet signals for the given
# start date / anchor / school. Uses existing build_response data
# and synthesises the three layers from confluence, drivers, and
# planetary dignity.
# ---------------------------------------------------------------


@app.route("/api/contra_signals")
def contra_signals():
    """3‑layer contra‑investment confluence evaluation.

    Layer 1 — Market Structure: POC trap, distribution/accumulation,
      selling/buying exhaustion from confluence + driver analysis.
    Layer 2 — Astro Timing: Jyotish (classical), KP (allthree),
      Western (zodiac‑dignity synthetic) bias + reversal windows.
    Layer 3 — Price Confirmation: blend‑bias thresholds, VWAP‑style
      confirmations, reversal‑candle flags (synthetic, derived from
      blend bias crossing the bullish/bearish thresholds).
    """
    start = request.args.get("start")
    try:
        start_d = datetime.date.fromisoformat(start) if start else datetime.date.today()
    except ValueError:
        return jsonify({"error": "invalid start date"}), 400

    anchor_key = request.args.get("anchor") or "nifty"
    if anchor_key not in ANCHORS:
        return jsonify({"error": "unknown anchor"}), 400

    key = (start_d.isoformat(), anchor_key)
    # Simple in‑process cache (same pattern as _series_cache / _balance_cache)
    if key in _balance_cache:
        out = _balance_cache[key]
    else:
        r = build_response(start_d.isoformat(), "09:15", "Asia/Kolkata", anchor_key, "classical")
        # --- Layer 1: Market Structure ---
        confluence = r.get("confluence") or {}
        drivers_data = r.get("drivers") or {}
        confl_signal = confluence.get("signal") or ""
        bull_w = confluence.get("bull", 0) or 0
        bear_w = confluence.get("bear", 0) or 0
        net_c = confluence.get("net", 0) or 0
        # POC trap: extreme net + many bull/bear sectors
        poc_trap = abs(net_c) >= 3 and (bull_w >= 3 or bear_w >= 3)
        # Distribution/Accumulation
        dist_accum = "accumulation" if bull_w > bear_w else "distribution"
        # Selling exhaustion: many malefic drivers, low strength
        benefic_drivers = drivers_data.get("benefic", []) if isinstance(drivers_data, dict) else []
        malefic_drivers = drivers_data.get("malefic", []) if isinstance(drivers_data, dict) else []
        selling_exhaustion = len(malefic_drivers) >= 3 and all(h.get("strength", 0) < 1.5 for h in malefic_drivers[:3])
        buying_exhaustion = len(benefic_drivers) >= 3 and all(h.get("strength", 0) < 1.5 for h in benefic_drivers[:3])

        # --- Layer 2: Astro Timing ---
        # Jyotish = classical single‑ray, KP = allthree, Western = synthetic dignity
        rj = build_response(start_d.isoformat(), "09:15", "Asia/Kolkata", anchor_key, "classical")
        rk = build_response(start_d.isoformat(), "09:15", "Asia/Kolkata", anchor_key, "allthree")
        jyotish_net = rj.get("net", 0.0)
        kp_net = rk.get("net", 0.0)
        western_net = _western_bias(rj.get("planets", []))

        jyotish_bias = _bias_scale(jyotish_net)
        kp_bias = _bias_scale(kp_net)
        western_bias = _western_bias(rj.get("planets", []))

        # Reversal window flags
        jyotish_reversal = jyotish_net <= -2.0  # bearish net → possible reversal short
        kp_reversal = kp_net <= -2.0
        western_reversal = western_net <= 2.0  # western bearish‑ish → reversal candidate

        # --- Layer 3: Price Confirmation (synthetic from blend bias) ---
        # The daily_indication_balance endpoint provides blend_bias;
        # here we derive confirmation from crossing the bull/bear thresholds.
        blend = r.get("blend_bias", 0) if isinstance(r, dict) else 0
        bullish_threshold = 4.0
        bearish_threshold = 2.0
        blend_buy = blend > bullish_threshold
        blend_sell = blend < bearish_threshold
        blend_neutral = bearish_threshold <= blend <= bullish_threshold

        # -------------------------------------------------------------------------
        # Cheat‑Sheet generation (ultra‑short format per the spec)
        # -------------------------------------------------------------------------
        buy_signals = []
        sell_signals = []

        # Layer 1
        if poc_trap:
            buy_signals.append("POC trap holds")
        if selling_exhaustion:
            buy_signals.append("Selling exhaustion")
        if buying_exhaustion:
            sell_signals.append("Buying exhaustion")
        if dist_accum == "accumulation":
            buy_signals.append("Accumulation detected")
        else:
            sell_signals.append("Distribution detected")

        # Layer 2
        if jyotish_reversal:
            buy_signals.append("SBC benefic vedha on bearish day")
        if kp_reversal:
            buy_signals.append("KP reversal window")
        if western_reversal:
            buy_signals.append("Western bearish bias")
        if not jyotish_reversal and not kp_reversal and not western_reversal:
            # If none of the reversal flags fire, the contra‑sell conditions apply
            sell_signals.append("KP/SRC bullish window holds")

        # Layer 3
        if blend_buy:
            buy_signals.append("Blend > bullish threshold")
        if blend_sell:
            sell_signals.append("Blend < bearish threshold")

        # Deduplicate & limit
        buy_signals = list(dict.fromkeys(buy_signals))[:5]
        sell_signals = list(dict.fromkeys(sell_signals))[:5]

        out = {
            "layer1": {
                "poc_trap": poc_trap,
                "dist_accum": dist_accum,
                "selling_exhaustion": selling_exhaustion,
                "buying_exhaustion": buying_exhaustion,
            },
            "layer2": {
                "jyotish_bias": jyotish_bias,
                "kp_bias": kp_bias,
                "western_bias": western_bias,
                "jyotish_reversal": jyotish_reversal,
                "kp_reversal": kp_reversal,
                "western_reversal": western_reversal,
            },
            "layer3": {
                "blend_buy": blend_buy,
                "blend_sell": blend_sell,
                "blend_neutral": blend_neutral,
            },
            "cheat_sheet": {
                "buy": buy_signals,
                "sell": sell_signals,
            },
            "anchor": anchor_key,
            "date": start_d.isoformat(),
        }
        _balance_cache[key] = out
    return jsonify(out)


_crash_series_cache = {}

@app.route("/api/crash_score_series")
def crash_score_series():
    """Daily bearish/crash trigger scores (0-20+) for the NIFTY chart overlay.

    Uses the same _bearish_future_score engine as the Crash Futurecast panel.
    """
    start = request.args.get("start")
    end = request.args.get("end")
    try:
        start_d = datetime.date.fromisoformat(start)
        end_d = datetime.date.fromisoformat(end)
    except (TypeError, ValueError):
        return jsonify({"error": "invalid start/end date"}), 400
    if end_d < start_d:
        return jsonify({"error": "end before start"}), 400
    # Allow up to ~31 months (950 days) to cover 24m history + 6m forecast + buffer
    if (end_d - start_d).days > 950:
        return jsonify({"error": "range too large (max 950 days)"}), 400

    out = []
    d = start_d
    while d <= end_d:
        ds = d.isoformat()
        if ds not in _crash_series_cache:
            try:
                score, reasons, _ = _bearish_future_score(_julian_at_noon(ds))
                _crash_series_cache[ds] = {"date": ds, "score": score,
                                           "reasons": reasons}
            except Exception as exc:
                _crash_series_cache[ds] = {"date": ds, "error": str(exc)}
        out.append(_crash_series_cache[ds])
        d += datetime.timedelta(days=1)
    return jsonify({"series": out})


@app.route("/api/sector_vedha")
def sector_vedha():
    """Backtest-informed plantation/fertilizer vedha signals for a date."""
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    return jsonify(scan_sector_vedhas(date_str))


@app.route("/api/crash_analysis")
def crash_analysis():
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    
    analysis = analyze_crash_risk(date_str)
    return jsonify({
        "date": analysis.date,
        "crash_score": analysis.crash_score,
        "condition": analysis.market_condition,
        "signatures": analysis.signatures,
        "signature_details": analysis.signature_details,
        "jupiter_analysis": analysis.jupiter_analysis,
        "jupiter_saturn_angle": analysis.jupiter_saturn_angle,
        "jupiter_saturn_aspect": analysis.jupiter_saturn_aspect,
        "mars_ketu_angle": analysis.mars_ketu_angle,
        "confluence": analysis.confluence,
        "applicable_setups": analysis.applicable_setups,
        "tradingview_links": analysis.tradingview_links,
        "research_package": analysis.research_package,
        "briefing": daily_crash_briefing(date_str),
    })


@app.route("/api/crash_backtest")
def crash_backtest():
    results = backtest_crashes()
    return jsonify({
        "summary": {
            "total": len(results),
            "crash_risk": len([r for r in results if r["condition"] == "CRASH_RISK"]),
            "correction_risk": len([r for r in results if r["condition"] == "CORRECTION_RISK"]),
            "elevated_risk": len([r for r in results if r["condition"] == "ELEVATED_RISK"]),
            "normal": len([r for r in results if r["condition"] == "NORMAL"]),
        },
        "results": results,
    })


@app.route("/api/cgsp_framework")
def cgsp_framework():
    """Cruel-Gentle Sign-Pada (CGSP) framework prediction."""
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    price = request.args.get("price", type=float)
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid date"}), 400

    # Get positioned planets + tithi
    from sbc.planets import positioned_planets

    planets, ayanamsa, sun, moon, tithi = positioned_planets(date_str)

    report = generate_cgsp_report(date_str, planets, tithi, price)
    return jsonify(report)


@app.route("/api/largecap_divergence")
def largecap_divergence():
    """Check all 10 large-cap divergence configurations for a single date."""
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid date"}), 400

    # Get positioned planets + tithi
    from sbc.planets import positioned_planets

    planets, ayanamsa, sun, moon, tithi = positioned_planets(date_str)

    # Check all 10 configurations
    from sbc.cgsp_framework import angular_distance, get_planet
    
    FIRE_SIGNS = {"Aries", "Leo", "Sagittarius"}
    FIXED_SIGNS = {"Taurus", "Leo", "Scorpio", "Aquarius"}
    MUTABLE_SIGNS = {"Gemini", "Virgo", "Sagittarius", "Pisces"}
    WATER_SIGNS = {"Cancer", "Scorpio", "Pisces"}
    JUPITER_FRIENDLY = {"Cancer", "Libra", "Pisces", "Leo", "Sagittarius"}
    RAHU_WEAK = {"Virgo", "Libra", "Capricorn"}
    MERCURY_FRIENDLY = {"Gemini", "Virgo", "Libra"}
    SUN_FRIENDLY = {"Leo", "Aries", "Sagittarius"}
    MOON_UNFRIENDLY_NAKS = {"Ashlesha", "Anuradha", "Jyeshtha", "Revati", "Punarvasu"}

    def is_full_moon(t):
        return t == 15
    def is_new_moon(t):
        return t == 30
    def is_conj(lon1, lon2, orb=10):
        return angular_distance(lon1, lon2) <= orb
    def check_eclipse(sun, moon, rahu, ketu):
        if is_new_moon(tithi):
            return angular_distance(sun["longitude"], rahu["longitude"]) < 15 or angular_distance(sun["longitude"], ketu["longitude"]) < 15
        elif is_full_moon(tithi):
            return angular_distance(sun["longitude"], rahu["longitude"]) < 15 or angular_distance(sun["longitude"], ketu["longitude"]) < 15
        return False

    rahu = get_planet(planets, "Rahu")
    ketu = get_planet(planets, "Ketu")

    configs = [
        {
            "id": 1,
            "name": "Sun+Saturn in Capricorn/Aquarius",
            "active": sun["sign"] in {"Capricorn", "Aquarius"} and 
                      get_planet(planets, "Saturn") and get_planet(planets, "Saturn")["sign"] in {"Capricorn", "Aquarius"} and
                      is_conj(sun["longitude"], get_planet(planets, "Saturn")["longitude"], 15),
            "conviction": "HIGH",
            "summary": "Nifty beats SmallCap +8.85% over 20d (91.6% win, Sharpe 4.41)"
        },
        {
            "id": 2,
            "name": "Saturn Fixed + Moon Mutable",
            "active": get_planet(planets, "Saturn") and get_planet(planets, "Saturn")["sign"] in FIXED_SIGNS and
                      moon["sign"] in MUTABLE_SIGNS,
            "conviction": "LOW",
            "summary": "No significant edge (too frequent)"
        },
        {
            "id": 3,
            "name": "Jupiter Friendly + Rahu Weak",
            "active": get_planet(planets, "Jupiter") and rahu and
                      get_planet(planets, "Jupiter")["sign"] in JUPITER_FRIENDLY and
                      rahu["sign"] in RAHU_WEAK,
            "conviction": "MEDIUM",
            "summary": "Nifty beats SmallCap +1.19% over 20d (62.8% win)"
        },
        {
            "id": 4,
            "name": "Mercury Retro-End + Full Moon",
            "active": is_full_moon(tithi) and 
                      get_planet(planets, "Mercury") and not get_planet(planets, "Mercury")["retrograde"] and
                      get_planet(planets, "Mercury")["sign"] in MERCURY_FRIENDLY,
            "conviction": "MEDIUM",
            "summary": "Nifty beats SmallCap +1.57% over 3d (70.6% win, Sharpe 2.93)"
        },
        {
            "id": 5,
            "name": "Rahu-Ketu Fire-Air Axis",
            "active": rahu and ketu and
                      rahu["sign"] in FIRE_SIGNS and
                      ketu["sign"] in {"Gemini", "Libra", "Aquarius"},
            "conviction": "LOW",
            "summary": "No significant edge (too frequent)"
        },
        {
            "id": 6,
            "name": "Venus Taurus Pada 3/4 + Full Moon Unfriendly",
            "active": is_full_moon(tithi) and
                      get_planet(planets, "Venus") and get_planet(planets, "Venus")["sign"] == "Taurus" and
                      get_planet(planets, "Venus")["nakshatra"] in {"Krittika", "Rohini", "Mrigashira"} and
                      get_planet(planets, "Venus")["pada"] in (3, 4) and
                      moon["nakshatra"] in MOON_UNFRIENDLY_NAKS,
            "conviction": "LOW",
            "summary": "Insufficient events (rare)"
        },
        {
            "id": 7,
            "name": "Mars Capricorn Pada 1/2 + Mercury Mutable",
            "active": get_planet(planets, "Mars") and get_planet(planets, "Mercury") and
                      get_planet(planets, "Mars")["sign"] == "Capricorn" and
                      get_planet(planets, "Mars")["pada"] in (1, 2) and
                      get_planet(planets, "Mercury")["sign"] in MUTABLE_SIGNS,
            "conviction": "HIGH",
            "summary": "Nifty beats MidCap +6.49% over 20d (66.7% win, Sharpe 2.39)"
        },
        {
            "id": 8,
            "name": "Eclipse in Fixed Sign + Sun Friendly",
            "active": check_eclipse(sun, moon, rahu, ketu) and
                      sun["sign"] in FIXED_SIGNS and
                      sun["sign"] in SUN_FRIENDLY,
            "conviction": "HIGH",
            "summary": "Perfect 100% win rate 1-5d, +2-3% relative (ultra-rare)"
        },
        {
            "id": 9,
            "name": "Saturn+Jupiter in Krittika",
            "active": get_planet(planets, "Saturn") and get_planet(planets, "Jupiter") and
                      get_planet(planets, "Saturn")["nakshatra"] == "Krittika" and
                      get_planet(planets, "Jupiter")["nakshatra"] == "Krittika",
            "conviction": "LOW",
            "summary": "Insufficient events (rare)"
        },
        {
            "id": 10,
            "name": "Adhik Masa + Rahu Fire + Moon Water",
            "active": rahu and rahu["sign"] in FIRE_SIGNS and
                      moon["sign"] in WATER_SIGNS,
            "conviction": "LOW",
            "summary": "Placeholder needs real lunar calendar"
        }
    ]

    active = [c for c in configs if c["active"]]
    high_conviction = [c for c in active if c["conviction"] == "HIGH"]
    medium_conviction = [c for c in active if c["conviction"] == "MEDIUM"]

    return jsonify({
        "date": date_str,
        "configs": configs,
        "active_count": len(active),
        "high_conviction_count": len(high_conviction),
        "medium_conviction_count": len(medium_conviction),
        "summary": f"{len(active)}/10 configurations active · {len(high_conviction)} HIGH · {len(medium_conviction)} MEDIUM"
    })


@app.route("/api/tourism_signals")
def tourism_signals():
    """Tourism/Leisure/Hospitality sector bullish planetary syntax signals."""
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    price = request.args.get("price", type=float)
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid date"}), 400

    # Get positioned planets + tithi
    from sbc.planets import positioned_planets

    planets, ayanamsa, sun, moon, tithi = positioned_planets(date_str)

    from sbc.tourism_signals import scan_tourism_signals
    result = scan_tourism_signals(date_str, planets, tithi, sun, moon, price)
    return jsonify(result)


@app.route("/api/chemical_signals")
def chemical_signals():
    """Chemical sector bullish planetary syntax signals."""
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    price = request.args.get("price", type=float)
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid date"}), 400

    # Get positioned planets + tithi
    from sbc.planets import positioned_planets

    planets, ayanamsa, sun, moon, tithi = positioned_planets(date_str)

    from sbc.chemical_signals import scan_chemical_signals
    result = scan_chemical_signals(date_str, planets, tithi, sun, moon, price)
    return jsonify(result)


@app.route("/api/alcohol_signals")
def alcohol_signals():
    """Alcohol sector bullish planetary syntax signals."""
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    price = request.args.get("price", type=float)
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid date"}), 400

    # Get positioned planets + tithi
    from sbc.planets import positioned_planets

    planets, ayanamsa, sun, moon, tithi = positioned_planets(date_str)

    from sbc.alcohol_signals import scan_alcohol_signals
    result = scan_alcohol_signals(date_str, planets, tithi, sun, moon, price)
    return jsonify(result)


@app.route("/api/lunar_forecast")
def lunar_forecast():
    """Lunar cycle sector forecast with SBC vedha and planetary nakshatra confluence."""
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid date"}), 400

    # Get positioned planets + tithi
    from sbc.planets import positioned_planets

    planets, ayanamsa, sun, moon, tithi = positioned_planets(date_str)

    from sbc.lunar_forecast import generate_lunar_sector_forecast, generate_infographic_card, format_card_for_clipboard, format_card_for_social_media
    
    forecast = generate_lunar_sector_forecast(date_str, planets, tithi, sun, moon)
    card = generate_infographic_card(forecast)
    clipboard_text = format_card_for_clipboard(card)
    social_text = format_card_for_social_media(card)
    
    return jsonify({
        "forecast": forecast,
        "card": card,
        "clipboard_text": format_card_for_clipboard(card),
        "social_text": format_card_for_social_media(card),
    })


@app.route("/api/fmcg_signals")
def fmcg_signals():
    """FMCG/Food sector bullish planetary syntax signals."""
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    price = request.args.get("price", type=float)
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid date"}), 400

    # Get positioned planets + tithi
    from sbc.planets import positioned_planets

    planets, ayanamsa, sun, moon, tithi = positioned_planets(date_str)

    from sbc.fmcg_signals import scan_fmcg_signals
    result = scan_fmcg_signals(date_str, planets, tithi, sun, moon, price)
    return jsonify(result)


@app.route("/api/cgsp_backtest")
def cgsp_backtest():
    """Backtest CGSP framework over a date range."""
    start = request.args.get("start")
    end = request.args.get("end")
    try:
        if start:
            datetime.datetime.strptime(start, "%Y-%m-%d")
        if end:
            datetime.datetime.strptime(end, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    if not start or not end:
        return jsonify({"error": "start and end required"}), 400

    from sbc.cgsp_framework import backtest_cgsp
    result = backtest_cgsp(start, end)
    return jsonify(result)


@app.route("/api/astro_plot")
def astro_plot():
    center_date = request.args.get("date") or datetime.date.today().isoformat()
    window_days = request.args.get("window", 30, type=int)
    resolution = request.args.get("resolution", "daily")
    timezone = request.args.get("tz", "Asia/Kolkata")
    latitude = request.args.get("lat", 19.0760, type=float)
    longitude = request.args.get("lon", 72.8777, type=float)
    house_system = request.args.get("house_system", "whole_sign")
    
    try:
        datetime.datetime.strptime(center_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "invalid date"}), 400
    
    if resolution not in ("daily", "hourly"):
        return jsonify({"error": "resolution must be 'daily' or 'hourly'"}), 400
    
    if house_system not in ("whole_sign", "placidus", "equal", "koch", "regiomontanus", "campanus"):
        return jsonify({"error": "invalid house system"}), 400
    
    window_days = max(1, min(window_days, 180))
    
    plot_data = generate_astro_plot(
        center_date=center_date,
        window_days=window_days,
        resolution=resolution,
        timezone=timezone,
        latitude=latitude,
        longitude=longitude,
        house_system=house_system,
    )
    
    return jsonify(serialize_plot_data(plot_data))


# =============================================================================
# KP INTRADAY TREND CHANGE PREDICTION ENDPOINTS
# =============================================================================

@app.route("/api/kp_intraday_report")
def kp_intraday_report():
    """Generate KP Intraday Trend Change Prediction Report."""
    date_str = request.args.get("date") or datetime.date.today().isoformat()
    instrument = request.args.get("instrument", "NIFTY")
    format_type = request.args.get("format", "json")

    try:
        trading_day = datetime.date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "invalid date"}), 400

    if instrument not in ("NIFTY", "BANK NIFTY", "FINNIFTY"):
        return jsonify({"error": "invalid instrument"}), 400

    # Find or generate KP data file for the requested month
    kp_data_dir = Path("data/kp")
    kp_data_dir.mkdir(parents=True, exist_ok=True)
    
    month_file = kp_data_dir / f"KP_Data_{trading_day.strftime('%b%Y')}.csv"
    if not month_file.exists():
        try:
            generate_sample_kp_csv(month_file, trading_day.replace(day=1), 31)
        except Exception as e:
            pass

    if month_file.exists():
        csv_path = month_file
    else:
        csv_files = list(kp_data_dir.glob("*.csv"))
        if not csv_files:
            try:
                generate_sample_kp_csv(month_file, trading_day.replace(day=1), 31)
                csv_path = month_file
            except Exception as e:
                return jsonify({"error": f"No KP data file found and failed to generate sample: {e}"}), 404
        else:
            csv_path = csv_files[0]

    try:
        config = get_config()
        instrument_cfg = get_instrument_config(instrument, config)

        report = generate_kp_intraday_report(csv_path, trading_day, instrument, instrument_cfg)

        if format_type == "html":
            generator = KPReportGenerator(instrument_cfg)
            html = generator.generate_html(report)
            from flask import Response
            return Response(html, mimetype='text/html')

        # JSON response with structured data
        return jsonify({
            "trading_day": report.trading_day.isoformat(),
            "instrument": report.instrument,
            "market": report.market,
            "ayanamsa": report.ayanamsa,
            "source_file": report.source_file,
            "generated_at": report.generated_at.isoformat(),
            "brand": report.brand,
            "day_signature": {
                "day_lord": report.day_signature.day_lord,
                "moon_sign": report.day_signature.moon_sign,
                "moon_star": report.day_signature.moon_star,
                "opening_sublord": report.day_signature.opening_sublord,
                "moon_speed": report.day_signature.moon_speed,
                "day_bias_score": report.day_signature.day_bias_score,
                "day_bias_label": report.day_signature.day_bias_label,
                "moon_affliction_gate": report.day_signature.moon_affliction_gate,
                "hora_slots": [
                    {
                        "time_range": hs.time_range_str(),
                        "lord": hs.lord,
                        "quality": hs.quality.value,
                        "base_quality": getattr(hs, 'base_quality', hs.quality.value),
                        "aspects_received": getattr(hs, 'aspects_received', 'None'),
                        "interpretation": getattr(hs, 'interpretation', hs.aspect_notes),
                        "aspect_notes": hs.aspect_notes
                    } for hs in report.day_signature.hora_slots
                ]
            },
            "regime_shifts": [
                {
                    "time": rs.time_str(),
                    "planet": rs.planet,
                    "old_sublord": rs.old_sublord,
                    "new_sublord": rs.new_sublord,
                    "house_set_strength": rs.house_set_strength,
                    "regime_label": rs.regime_label,
                    "direction": rs.direction.value
                } for rs in report.regime_shifts
            ],
            "trend_changes": [
                {
                    "time": tc.time_str(),
                    "grade": tc.grade.value,
                    "direction": tc.direction.value,
                    "trigger": tc.trigger,
                    "asc_sub_house_set": tc.asc_sub_house_set,
                    "hora_lord": tc.hora_lord,
                    "score": tc.score,
                    "notes": tc.notes
                } for tc in report.trend_changes
            ],
            "bullish_windows": [
                {
                    "time_range": w.time_range_str(),
                    "score": w.score,
                    "signal_count": len(w.signals)
                } for w in report.bullish_windows
            ],
            "bearish_windows": [
                {
                    "time_range": w.time_range_str(),
                    "score": w.score,
                    "signal_count": len(w.signals)
                } for w in report.bearish_windows
            ],
            "strongest_bullish": {
                "time_range": report.strongest_bullish.time_range_str(),
                "score": report.strongest_bullish.score
            } if report.strongest_bullish else None,
            "strongest_bearish": {
                "time_range": report.strongest_bearish.time_range_str(),
                "score": report.strongest_bearish.score
            } if report.strongest_bearish else None,
            "exhaustion_warnings": report.exhaustion_warnings
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/kp_intraday_config")
def kp_intraday_config():
    """Get current KP Intraday configuration."""
    config = get_config()
    return jsonify(config.to_dict())


@app.route("/api/kp_intraday_sample", methods=["POST"])
def kp_intraday_sample():
    """Generate sample KP data CSV for testing."""
    data = request.get_json() or {}
    date_str = data.get("date") or datetime.date.today().isoformat()
    days = data.get("days", 31)

    try:
        start_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "invalid date"}), 400

    kp_data_dir = Path("data/kp")
    kp_data_dir.mkdir(parents=True, exist_ok=True)

    output_path = kp_data_dir / f"KP_Data_{start_date.strftime('%b%Y')}.csv"
    generate_sample_kp_csv(output_path, start_date, days)

    return jsonify({
        "file": str(output_path),
        "days_generated": days,
        "start_date": start_date.isoformat()
    })


@app.route("/api/habits/log", methods=["POST"])
def api_habits_log():
    try:
        data = request.get_json() or {}
        user_key = request.headers.get("X-User-Key", "default")
        habit_type = data.get("habit_type")
        log_date = data.get("date")
        if not habit_type or not log_date:
            return jsonify({"error":"habit_type and date required"}),400
        import sqlite3, datetime
        db_path = Path("data/profiles.db")
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("INSERT INTO habit_logs(user_key, habit_type, log_date, created_at) VALUES(?,?,?,?)",
                    (user_key, habit_type, log_date, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({"status":"logged"})
    except Exception as e:
        return jsonify({"error":str(e)}),500


@app.route("/api/habits/streaks", methods=["GET"])
def api_habits_streaks():
    try:
        user_key = request.args.get("user_key","default")
        import sqlite3, datetime as dt
        db_path = Path("data/profiles.db")
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT habit_type, log_date FROM habit_logs WHERE user_key=?", (user_key,))
        rows = cur.fetchall()
        conn.close()
        from collections import defaultdict
        logs = defaultdict(set)
        for h,d in rows:
            logs[h].add(d)
        today = dt.date.today().isoformat()
        result = {}
        for h, dates_set in logs.items():
            dates = sorted(dates_set, reverse=True)
            dset = set(dt.date.fromisoformat(d) for d in dates_set)
            streak = 0
            if dates:
                cur_day = max(dset)
                while cur_day in dset:
                    streak += 1
                    cur_day -= dt.timedelta(days=1)
            result[h] = {"streak": streak, "last": dates[0] if dates else None, "count": len(dates_set)}
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Astro Research Lab API endpoints

@app.route("/api/research/astro_lab")
def api_astro_lab():
    return jsonify(astro_lab())

@app.route("/api/research/walk_forward_validation")
def api_walk_forward_validation():
    return jsonify(walk_forward_validation())

@app.route("/api/research/canonical_market_event_model")
def api_canonical_market_event_model():
    return jsonify(canonical_market_event_model())

@app.route("/api/research/new_moon_efficiency_study")
def api_new_moon_efficiency_study():
    return jsonify(new_moon_efficiency_study())

@app.route("/api/research/planetary_aspect_grid")
def api_planetary_aspect_grid():
    return jsonify(planetary_aspect_grid())

@app.route("/api/research/solar_lunar_cycle_explorer")
def api_solar_lunar_cycle_explorer():
    return jsonify(solar_lunar_cycle_explorer())

@app.route("/api/research/bradley_barometer_overlay")
def api_bradley_barometer_overlay():
    return jsonify(bradley_barometer_overlay())

@app.route("/api/research/regime_aware_reports")
def api_regime_aware_reports():
    return jsonify(regime_aware_reports())

@app.route("/api/research/research_export")
def api_research_export():
    return jsonify(research_export())

@app.route("/api/research/unified_daily_forecast_contract")
def api_unified_daily_forecast_contract():
    return jsonify(unified_daily_forecast_contract())


@app.route("/api/habits/history", methods=["GET"])
def api_habits_history():
    try:
        user_key = request.args.get("user_key","default")
        days = int(request.args.get("days","7"))
        import sqlite3, datetime as dt
        db_path = Path("data/profiles.db")
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        # Get logs for last N days
        start_date = (dt.date.today() - dt.timedelta(days=days-1)).isoformat()
        cur.execute("SELECT habit_type, log_date, COUNT(*) FROM habit_logs WHERE user_key=? AND log_date>=? GROUP BY habit_type, log_date", (user_key, start_date))
        rows = cur.fetchall()
        conn.close()
        history = {}
        for h,d,c in rows:
            history.setdefault(h, {})[d] = c
        return jsonify(history)
    except Exception as e:
        return jsonify({"error":str(e)}),500


@app.route("/api/habits/summary", methods=["GET"])
def api_habits_summary():
    try:
        user_key = request.args.get("user_key","default")
        import sqlite3
        db_path = Path("data/profiles.db")
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT habit_type, COUNT(DISTINCT log_date) as days FROM habit_logs WHERE user_key=? GROUP BY habit_type", (user_key,))
        rows = cur.fetchall()
        conn.close()
        summary = {h: days for h,days in rows}
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error":str(e)}),500


@app.route("/webhook/sbc", methods=["POST"])
def webhook_sbc():
    try:
        if request.content_length and request.content_length > 64 * 1024:
            return jsonify({"error": "payload too large (64 KB max)"}), 413
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "body must be a JSON object"}), 400
        import json, os
        os.makedirs("data", exist_ok=True)
        with open("data/latest_sbc_signal.json", "w") as f:
            json.dump(data, f)
        return jsonify({"status":"ok","received":data})
    except Exception as e:
        return jsonify({"error":str(e)}),500

@app.route("/api/vedha_daily", methods=["GET"])
def api_vedha_daily():
    try:
        import pandas as pd, math
        sector_name = request.args.get("sector","Nifty Bank")
        days_str = request.args.get("days")
        start_str = request.args.get("start")
        end_str = request.args.get("end")
        if start_str and end_str:
            start_date_req = datetime.date.fromisoformat(start_str)
            end_date_req = datetime.date.fromisoformat(end_str)
        elif days_str:
            days = int(days_str)
            end_date_req = datetime.date.today()
            start_date_req = end_date_req - datetime.timedelta(days=days-1)
        else:
            end_date_req = datetime.date.today()
            start_date_req = end_date_req - datetime.timedelta(days=179)
        # Try real heatmap based scores
        real_scores_used = False
        try:
            from sbc.monthly_heatmap import monthly_heatmap, NIFTY_SECTOR_ROWS
            end = end_date_req
            # Build map of sector row name
            # NIFTY_SECTOR_ROWS is list of tuples (display_name, tags)
            target_row = None
            for display_name, tags in NIFTY_SECTOR_ROWS:
                if sector_name.lower() in display_name.lower():
                    target_row = display_name
                    break
                # also check tags
                if any(sector_name.lower() in tag.lower() for tag in tags):
                    target_row = display_name
                    break
                    target_row = k
                    break
            if target_row:
                cur = end
                collected = []
                shape_logs = []
                for _ in range(6):
                    # monthly_heatmap expects start_date and days
                    start_date = datetime.date(cur.year, cur.month, 1)
                    data = monthly_heatmap(start_date=start_date, days=31, tz_name='Asia/Kolkata', anchor_key='nse')
                    # Validate shape - monthly_heatmap returns dict with 'dates' and 'matrix'
                    if not isinstance(data, dict) or 'matrix' not in data:
                        shape_logs.append(f"{cur.year}-{cur.month}: unexpected return shape")
                        # move to previous month
                        if cur.month == 1:
                            cur = datetime.date(cur.year-1, 12, 1)
                        else:
                            cur = datetime.date(cur.year, cur.month-1, 1)
                        continue
                    matrix = data.get('matrix', {})
                    # matrix is sector -> {date: score}
                    for sector_name_key, day_map in matrix.items():
                        # find matching row
                        # We need row by display name. Simpler: use target_row as sector key
                        if isinstance(day_map, dict):
                            for day_str, score in day_map.items():
                                try:
                                    d = datetime.datetime.strptime(day_str,"%Y-%m-%d").date()
                                    # Only collect for target sector row
                                    # Map sector display name to key
                                    # Assume matrix keys are sector display names
                                    if sector_name_key == target_row:
                                        collected.append((d, float(score)))
                                except Exception as e:
                                    shape_logs.append(f"{day_str} parse error: {e}")
                    # move to previous month
                    if cur.month == 1:
                        cur = datetime.date(cur.year-1, 12, 1)
                    else:
                        cur = datetime.date(cur.year, cur.month-1, 1)
                if shape_logs:
                    app.logger.warning(f"vedha_daily shape logs for {sector_name}: {shape_logs}")
                if collected:
                    real_scores_used = True
                    collected.sort(key=lambda x:x[0])
                    # Generate output for requested date range
                    out = []
                    day_to_score = {d:s for d,s in collected}
                    d = start_date_req
                    while d <= end_date_req:
                        score = day_to_score.get(d,0)
                        # nakshatra index based on days since start
                        days_since = (d - start_date_req).days
                        nak_idx = days_since % 27
                        out.append({"date":d.isoformat(),"score":float(score),"nakshatra_idx":int(nak_idx),"source":"real"})
                        d += datetime.timedelta(days=1)
                    return jsonify(out)
        except Exception as e:
            app.logger.exception(f"vedha_daily real heatmap error for {sector_name}: {e}")
            # fallback synthetic
        
        # No real data available – return empty with warning instead of synthetic
        app.logger.warning(f"vedha_daily: no real heatmap data for sector {sector_name}, returning empty")
        out = []
        d = start_date_req
        while d <= end_date_req:
            out.append({"date":d.isoformat(),"score":None,"nakshatra_idx":None,"source":"missing"})
            d += datetime.timedelta(days=1)
        return jsonify(out)
    except Exception as e:
        return jsonify({"error":str(e)}),500


@app.route("/api/price", methods=["GET"])
def api_price():
    try:
        import yfinance as yf, pandas as pd
        ticker = request.args.get("ticker","^NSEBANK")
        days = request.args.get("days")
        start_str = request.args.get("start")
        end_str = request.args.get("end")
        if start_str and end_str:
            start = datetime.date.fromisoformat(start_str)
            end = datetime.date.fromisoformat(end_str) + datetime.timedelta(days=1)
        elif days:
            days = int(days)
            end = datetime.date.today()
            start = end - datetime.timedelta(days=days)
        else:
            end = datetime.date.today()
            start = end - datetime.timedelta(days=180)
        # Server-side fallback map
        fallback_map = {
            '^CNXIT':'^NSEIT',
            '^CNXAUTO':'^NSEAUTO',
            '^CNXMETAL':'^NSEMETAL',
            '^CNXFMCG':'^NSEFMCG',
            '^CNXPHARMA':'^NSEPHARMA',
            '^CNXENERGY':None,
            '^CNXREALTY':'^NSEREALTY'
        }
        df = yf.download(ticker, start=start, end=end, interval='1d', auto_adjust=True, progress=False)
        if df.empty:
            fb = fallback_map.get(ticker)
            if fb:
                df = yf.download(fb, start=start, end=end, interval='1d', auto_adjust=True, progress=False)
        if df.empty:
            return jsonify([])
        # yfinance may return MultiIndex columns; flatten
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join([str(c) for c in col if str(c)!='']).strip('_') for col in df.columns.values]
        # pick first Open/High/Low/Close columns
        col_map = {}
        for c in df.columns:
            if 'Open' in c: col_map['Open']=c
            if 'High' in c: col_map['High']=c
            if 'Low' in c: col_map['Low']=c
            if 'Close' in c: col_map['Close']=c
        candles = []
        for idx,row in df.iterrows():
            try:
                candles.append({
                    "time": int(pd.to_datetime(idx).timestamp()),
                    "open": float(row[col_map.get('Open','Open')]),
                    "high": float(row[col_map.get('High','High')]),
                    "low": float(row[col_map.get('Low','Low')]),
                    "close": float(row[col_map.get('Close','Close')])
                })
            except Exception:
                continue
        return jsonify(candles)
    except Exception as e:
        return jsonify({"error":str(e)}),500


@app.route("/api/sbc/latest", methods=["GET"])
def api_sbc_latest():
    try:
        import json, os
        path = "data/latest_sbc_signal.json"
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            return jsonify(data)
        return jsonify({})
    except Exception as e:
        return jsonify({"error":str(e)}),500



@app.route("/api/astro/profile/export", methods=["GET"])
def api_astro_profile_export():
    try:
        user_key = request.args.get("user_key", "default")
        import sqlite3
        db_path = Path("data/profiles.db")
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT id, data, created_at, name, is_default FROM profiles WHERE user_key=?", (user_key,))
        rows = cur.fetchall()
        conn.close()
        export = [{"id": r[0], "data": json.loads(r[1]), "created_at": r[2], "name": r[3], "is_default": bool(r[4])} for r in rows]
        return jsonify(export)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/astro/profile/import", methods=["POST"])
def api_astro_profile_import():
    try:
        user_key = request.headers.get("X-User-Key", "default")
        incoming = request.get_json() or []
        import sqlite3
        db_path = Path("data/profiles.db")
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        imported = 0
        for p in incoming:
            data = p.get("data")
            name = p.get("name")
            is_default = 1 if p.get("is_default") else 0
            if not data:
                continue
            cur.execute("INSERT INTO profiles(user_key, data, created_at, name, is_default) VALUES(?,?,?,?,?)",
                        (user_key, json.dumps(data), datetime.datetime.utcnow().isoformat(), name, is_default))
            imported += 1
        conn.commit()
        conn.close()
        return jsonify({"imported": imported})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/astro/profile", methods=["POST"])
def api_astro_profile_save():
    try:
        data = request.get_json() or {}
        user_key = request.headers.get("X-User-Key", "default")
        import sqlite3, datetime
        db_path = Path("data/profiles.db")
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("INSERT INTO profiles(user_key, data, created_at) VALUES(?,?,?)",
                    (user_key, json.dumps(data), datetime.datetime.utcnow().isoformat()))
        conn.commit()
        pid = cur.lastrowid
        conn.close()
        return jsonify({"id": pid, "status": "saved"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/astro/profile/<int:pid>", methods=["PUT"])
def api_astro_profile_update(pid):
    try:
        data = request.get_json() or {}
        name = data.get("name")
        import sqlite3
        db_path = Path("data/profiles.db")
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        if name is not None:
            cur.execute("UPDATE profiles SET name=? WHERE id=?", (name, pid))
        conn.commit()
        conn.close()
        return jsonify({"status":"updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/astro/profile/<int:pid>/default", methods=["POST"])
def api_astro_profile_set_default(pid):
    try:
        import sqlite3
        db_path = Path("data/profiles.db")
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("UPDATE profiles SET is_default=0 WHERE is_default=1")
        cur.execute("UPDATE profiles SET is_default=1 WHERE id=?", (pid,))
        conn.commit()
        conn.close()
        return jsonify({"status":"default_set"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/astro/profile/<int:pid>", methods=["DELETE"])
def api_astro_profile_delete(pid):
    try:
        import sqlite3
        db_path = Path("data/profiles.db")
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("DELETE FROM profiles WHERE id=?", (pid,))
        conn.commit()
        conn.close()
        return jsonify({"status":"deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/astro/profile", methods=["GET"])
def api_astro_profile_load():
    try:
        user_key = request.args.get("user_key", "default")
        import sqlite3
        db_path = Path("data/profiles.db")
        if not db_path.exists():
            return jsonify([])
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT id, data, created_at, name, is_default FROM profiles WHERE user_key=? ORDER BY is_default DESC, id DESC", (user_key,))
        rows = cur.fetchall()
        conn.close()
        profiles = [{"id": r[0], "data": json.loads(r[1]), "created_at": r[2], "name": r[3], "is_default": bool(r[4])} for r in rows]
        return jsonify(profiles)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tz/offset", methods=["GET"])
def api_tz_offset():
    try:
        tz_name = request.args.get("tz")
        date_str = request.args.get("date")
        time_str = request.args.get("time","00:00")
        if not tz_name or not date_str:
            return jsonify({"error":"tz and date required"}),400
        from zoneinfo import ZoneInfo
        y,m,d = (int(x) for x in date_str.split("-"))
        hh,mm = (int(x) for x in time_str.split(":")[:2])
        # Create naive datetime and localize
        dt_naive = datetime.datetime(y,m,d,hh,mm)
        tz = ZoneInfo(tz_name)
        dt_local = dt_naive.replace(tzinfo=tz)
        offset = dt_local.utcoffset()
        total_minutes = int(offset.total_seconds() // 60)
        hours = total_minutes // 60
        mins = abs(total_minutes % 60)
        return jsonify({"tz": tz_name, "offset_minutes": total_minutes, "offset_hours": hours, "offset_mins": mins if total_minutes>=0 else -mins})
    except Exception as e:
        return jsonify({"error": str(e)}),500


@app.route("/api/tz/from_coords", methods=["GET"])
def api_tz_from_coords():
    try:
        lat = float(request.args.get("lat", "0"))
        lon = float(request.args.get("lon", "0"))
        from timezonefinder import TimezoneFinder
        tf = TimezoneFinder()
        tz_name = tf.timezone_at(lng=lon, lat=lat)
        if not tz_name:
            return jsonify({"error": "timezone not found"}), 404
        return jsonify({"timezone": tz_name, "lat": lat, "lon": lon})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/astro/personal", methods=["GET"])
def api_astro_personal():
    date_str = request.args.get("date")
    time_str = request.args.get("time") or "09:15"
    tz_name = request.args.get("tz", "Asia/Kolkata")
    tz_hours = request.args.get("tz_hours")
    tz_mins = request.args.get("tz_mins")
    if not date_str:
        return jsonify({"error": "date required"}), 400
    try:
        if tz_hours is not None and tz_mins is not None:
            # Build UTC from local using offset
            from datetime import datetime, timezone, timedelta
            y,m,d = (int(x) for x in date_str.split("-"))
            hh,mm = (int(x) for x in time_str.split(":"))
            local_dt = datetime(y,m,d,hh,mm)
            offset = timedelta(hours=int(tz_hours), minutes=int(tz_mins))
            # Local time is UTC + offset
            utc = (local_dt - offset).replace(tzinfo=timezone.utc).replace(tzinfo=None)
        else:
            utc = _utc_from_local(date_str, time_str, tz_name)
        jul = _julday(utc)
        planets, ayanamsa = positions(jul)
        def find(name):
            return next((p for p in planets if p["name"] == name), {})
        moon = find("Moon")
        sun = find("Sun")
        rahu = find("Rahu")
        ketu = find("Ketu")
        market_confluence = build_response(date_str, time_str, tz_name, "nifty", "allthree")
        signs = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
        def sign_from_lon(lon):
            if lon is None: return None
            idx = int((lon % 360)//30)
            return signs[idx]
        result = {
            "date": date_str,
            "time": time_str,
            "timezone": tz_name,
            "ayanamsa": round(ayanamsa,4),
            "sun": {"longitude": sun.get("longitude"), "sign": sign_from_lon(sun.get("longitude")), "nakshatra": sun.get("nakshatra")},
            "moon": {"longitude": moon.get("longitude"), "sign": sign_from_lon(moon.get("longitude")), "nakshatra": moon.get("nakshatra")},
            "rahu": {"longitude": rahu.get("longitude"), "sign": sign_from_lon(rahu.get("longitude"))},
            "ketu": {"longitude": ketu.get("longitude"), "sign": sign_from_lon(ketu.get("longitude"))},
            "vedha_net": market_confluence["net"],
            "sector_reads": market_confluence["sectors"],
            "planets": planets
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/daily_confluence", methods=["GET"])
def api_daily_confluence():
    """Return one compact daily confluence result and its forward forecast."""
    date_str = request.args.get("date")
    try:
        start = datetime.date.fromisoformat(date_str) if date_str else datetime.date.today()
        days = min(max(int(request.args.get("days", "7")), 1), 14)
    except (TypeError, ValueError):
        return jsonify({"error": "invalid date or days"}), 400

    cache_key = (start.isoformat(), days)
    cached = _daily_confluence_cache.get(cache_key)
    if cached:
        payload = {key: value for key, value in cached.items() if key != "_cached_at"}
        payload["cache"] = {"hit": True, "age_seconds": max(0, int(time.time() - cached["_cached_at"]))}
        return jsonify(payload)

    forecast = []
    try:
        for offset in range(days):
            day = start + datetime.timedelta(days=offset)
            result = build_response(day.isoformat(), "09:15", "Asia/Kolkata", "nifty", "allthree")
            moon = next((planet for planet in result["planets"] if planet["name"] == "Moon"), {})
            net = float(result.get("net", 0))
            nakshatra = moon.get("nakshatra", "Unknown")
            forecast.append({
                "date": day.isoformat(),
                "nakshatra": nakshatra,
                "keywords": keywords_for(nakshatra),
                "vedha_net": net,
                "direction": "Bullish" if net > 0 else "Bearish" if net < 0 else "Neutral",
            })
        current = forecast[0]
        payload = {
            "date": start.isoformat(),
            "moon_nakshatra": current["nakshatra"],
            "keywords": current["keywords"],
            "vedha_net": current["vedha_net"],
            "direction": current["direction"],
            "forecast": forecast,
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "calculation_version": "daily-confluence-v3",
            "data_source": "Swiss Ephemeris",
            "cache": {"hit": False, "age_seconds": 0},
        }
        _daily_confluence_cache[cache_key] = {**payload, "_cached_at": time.time()}
        return jsonify(payload)
    except Exception:
        app.logger.exception("Daily confluence generation failed")
        return jsonify({"error": "daily confluence unavailable"}), 500


@app.route("/api/cities/search", methods=["GET"])
def api_cities_search():
    q = request.args.get("q", "").strip()
    country = request.args.get("country", "").strip()
    if not q or len(q) < 2:
        return jsonify([])
    db_path = Path("data/cities.db")
    if not db_path.exists():
        return jsonify([])
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # Simple LIKE search, case-insensitive
    pattern = f"%{q}%"
    if country.lower() in ("usa", "us", "united states", "united states of america"):
        sql = "SELECT name, country, lat, lon, admin_name FROM cities WHERE name LIKE ? AND lower(country) IN ('united states','usa')"
    elif country:
        sql = "SELECT name, country, lat, lon, admin_name FROM cities WHERE name LIKE ? AND lower(country) LIKE lower(?)"
        cur.execute(sql, (pattern, f"%{country}%"))
    else:
        sql = "SELECT name, country, lat, lon, admin_name FROM cities WHERE name LIKE ?"
        cur.execute(sql, (pattern,))
    if country and country.lower() not in ("usa","us","united states","united states of america"):
        # already executed above
        rows = cur.fetchall()
    else:
        if country and country.lower() not in ("usa","us","united states","united states of america"):
            pass
        else:
            # re-execute for generic
            if country.lower() in ("usa","us","united states","united states of america"):
                cur.execute("SELECT name, country, lat, lon, admin_name FROM cities WHERE name LIKE ? AND lower(country) IN ('united states','usa')", (pattern,))
            else:
                cur.execute("SELECT name, country, lat, lon, admin_name FROM cities WHERE name LIKE ?", (pattern,))
            rows = cur.fetchall()
    # Fallback for non-USA country param already handled
    results = []
    for r in rows:
        results.append({
            "name": r["name"],
            "country": r["country"],
            "admin": r["admin_name"],
            "lat": r["lat"],
            "lon": r["lon"]
        })
    conn.close()
    return jsonify(results)


@app.route("/api/gann/turbo_zones", methods=["GET"])
def api_gann_turbo_zones():
    try:
        ticker = request.args.get("ticker","^NSEI")
        days = int(request.args.get("days","60"))
        end = datetime.date.today()
        start = end - datetime.timedelta(days=days)
        import pandas as pd, yfinance as yf
        df = yf.download(ticker, start=start, end=end, interval='1d', auto_adjust=True, progress=False)
        if df.empty:
            return jsonify({"error":"no data"}),400
        df.columns = [c[0] if isinstance(c,tuple) else c for c in df.columns]
        high = float(df['High'].max())
        low = float(df['Low'].min())
        mid = (high+low)/2
        # Turbo zones: initiation at 0.5, target at 0.618/0.786, SL 1%
        zones = {
            "initiation_green": mid,
            "target_dotted": high - (high-low)*0.382,
            "stop_loss": mid * 0.99
        }
        return jsonify({"ticker":ticker,"zones":zones,"high":high,"low":low})
    except Exception as e:
        return jsonify({"error":str(e)}),500


@app.route("/api/gann/precision", methods=["GET"])
def api_gann_precision():
    try:
        ticker = request.args.get("ticker","^NSEI")
        days = int(request.args.get("days","90"))
        end = datetime.date.today()
        start = end - datetime.timedelta(days=days)
        import pandas as pd, yfinance as yf
        df = yf.download(ticker, start=start, end=end, interval='1d', auto_adjust=True, progress=False)
        if df.empty:
            return jsonify({"error":"no data"}),400
        df.columns = [c[0] if isinstance(c,tuple) else c for c in df.columns]
        high = float(df['High'].max())
        low = float(df['Low'].min())
        range_ = high - low
        # Gann precision levels: 0.618, 0.5, 0.382 etc
        levels = []
        for frac in [0.236,0.382,0.5,0.618,0.786]:
            price = low + range_*frac
            levels.append({"frac":frac,"price":price})
        return jsonify({"ticker":ticker,"high":high,"low":low,"range":range_,"levels":levels})
    except Exception as e:
        return jsonify({"error":str(e)}),500


@app.route("/api/signal/moon", methods=["GET"])
def api_signal_moon():
    try:
        ticker=request.args.get("ticker","^NSEI")
        days=int(request.args.get("days","30"))
        end=datetime.date.today()
        start=end-datetime.timedelta(days=days)
        import pandas as pd, yfinance as yf
        from sbc.market_data import moon_rashi, RASHI_TREND
        df=yf.download(ticker,start=start,end=end,interval='1d',auto_adjust=True,progress=False)
        if df.empty:
            return jsonify({"error":"no data"}),400
        df.columns=[c[0] if isinstance(c,tuple) else c for c in df.columns]
        df=df[['Close']].dropna()
        ist=ZoneInfo("Asia/Kolkata")
        signals=[]
        for idx in df.index:
            d=pd.to_datetime(idx).date()
            dt=datetime.datetime.combine(d,datetime.time(9,15),tzinfo=ist)
            rashi=moon_rashi(dt)
            trend=RASHI_TREND.get(rashi)
            signals.append({"date":d.isoformat(),"rashi":rashi,"trend":trend,"close":float(df.loc[idx,'Close'])})
        return jsonify({"ticker":ticker,"signals":signals})
    except Exception as e:
        return jsonify({"error":str(e)}),500


@app.route("/api/backtest/walkforward", methods=["GET"])
def api_backtest_walkforward():
    try:
        ticker = request.args.get("ticker","^NSEI")
        window = int(request.args.get("window","365"))
        step = int(request.args.get("step","90"))
        start_str = request.args.get("start")
        end_str = request.args.get("end")
        if start_str:
            start = datetime.date.fromisoformat(start_str)
        else:
            start = datetime.date.today() - datetime.timedelta(days=730)
        if end_str:
            end = datetime.date.fromisoformat(end_str)
        else:
            end = datetime.date.today()
        import pandas as pd, yfinance as yf
        from sbc.market_data import moon_rashi, RASHI_TREND
        df=yf.download(ticker,start=start,end=end,interval='1d',auto_adjust=True,progress=False)
        if df.empty:
            return jsonify({"error":"no data"}),400
        df.columns=[c[0] if isinstance(c,tuple) else c for c in df.columns]
        df=df[['Close']].dropna()
        ist=ZoneInfo("Asia/Kolkata")
        results=[]
        cur=start
        while cur<end:
            test_end=min(cur+datetime.timedelta(days=window+step), end)
            correct=total=0
            prev=None
            for idx in df.index:
                d=pd.to_datetime(idx).date()
                if d<cur or d>=test_end:
                    continue
                dt=datetime.datetime.combine(d,datetime.time(9,15),tzinfo=ist)
                monday=dt-datetime.timedelta(days=dt.weekday())
                daily=moon_rashi(dt)
                weekly=moon_rashi(datetime.datetime.combine(monday.date(),datetime.time(9,15),tzinfo=ist))
                if RASHI_TREND.get(daily)!=RASHI_TREND.get(weekly):
                    prev=float(df.loc[idx,'Close'])
                    continue
                close=float(df.loc[idx,'Close'])
                if prev is not None:
                    expected=RASHI_TREND[daily]
                    actual="bullish" if close>prev else "bearish" if close<prev else "neutral"
                    if actual!="neutral":
                        total+=1
                        if expected==actual:
                            correct+=1
                prev=close
            acc=correct/total if total else None
            results.append({"train_start":cur.isoformat(),"test_end":test_end.isoformat(),"samples":total,"accuracy":acc})
            cur=cur+datetime.timedelta(days=step)
        return jsonify({"ticker":ticker,"results":results})
    except Exception as e:
        return jsonify({"error":str(e)}),500


def _research_lunar_rows(ticker, start, end, horizon):
    import pandas as pd
    import yfinance as yf

    prices = yf.download(ticker, start=start.isoformat(), end=(end + datetime.timedelta(days=1)).isoformat(),
                         interval="1d", auto_adjust=True, progress=False)
    if prices.empty:
        return []
    if isinstance(prices.columns, pd.MultiIndex):
        prices.columns = [column[0] for column in prices.columns]
    frame = prices[["Open", "High", "Low", "Close"]].dropna()
    frame.index = pd.to_datetime(frame.index).tz_localize(None).normalize()
    rows = []
    for index in range(len(frame) - horizon):
        day = frame.index[index].date()
        utc = _utc_from_local(day.isoformat(), "09:15", "Asia/Kolkata")
        planets, _ = positions(_julday(utc))
        sun = next(planet for planet in planets if planet["name"] == "Sun")
        moon = next(planet for planet in planets if planet["name"] == "Moon")
        tithi = tithi_of(sun["longitude"], moon["longitude"])
        event_record = lunar_phase_event(day, tithi, sun["longitude"], moon["longitude"])
        base = float(frame["Close"].iloc[index])
        future = float(frame["Close"].iloc[index + horizon])
        forward = frame.iloc[index + 1:index + horizon + 1]
        daily_returns = frame["Close"].pct_change().iloc[index + 1:index + horizon + 1].dropna()
        trend_window = frame["Close"].iloc[max(0, index - 20):index + 1]
        trend_change = float(trend_window.iloc[-1] / trend_window.iloc[0] - 1) if len(trend_window) > 1 else 0.0
        regime = "bull" if trend_change >= 0.02 else "bear" if trend_change <= -0.02 else "range"
        rows.append({
            "date": day, "weekday": day.weekday(), "base": base,
            "return_pct": (future / base - 1) * 100,
            "event": event_record is not None,
            "event_record": event_record.to_dict() if event_record else None,
            "volatility_pct": float(daily_returns.std() * 100) if len(daily_returns) > 1 else 0.0,
            "mae_pct": float((forward["Low"].min() / base - 1) * 100) if not forward.empty else 0.0,
            "regime": regime,
        })
    return rows


@app.route("/api/research/event-study", methods=["GET"])
def api_research_event_study():
    """Measure forward returns around lunar phase events against all days."""
    ticker = request.args.get("ticker", "^NSEI")
    event = request.args.get("event", "new_moon")
    horizon = min(max(int(request.args.get("horizon", "5")), 1), 20)
    end = datetime.date.fromisoformat(request.args.get("end") or datetime.date.today().isoformat())
    start = datetime.date.fromisoformat(request.args.get("start") or (end - datetime.timedelta(days=3650)).isoformat())
    if event not in {"new_moon", "full_moon"} or start >= end:
        return jsonify({"error": "invalid event or date range"}), 400

    try:
        rows = _research_lunar_rows(ticker, start, end, horizon)
        if not rows:
            return jsonify({"error": "no market data available"}), 404
        event_rows = [row for row in rows if row["event"] and row["event_record"]["event_type"] == event]
        baseline = [row["return_pct"] for row in rows]
        event_returns = [row["return_pct"] for row in event_rows]
        available_controls = [row for row in rows if not row["event"]]
        controls = []
        used_control_dates = set()
        for event_row in event_rows:
            candidates = [row for row in available_controls
                          if row["weekday"] == event_row["weekday"] and row["date"] not in used_control_dates]
            if candidates:
                control = min(candidates, key=lambda row: abs((row["date"] - event_row["date"]).days))
                controls.append(control)
                used_control_dates.add(control["date"])
        control_returns = [row["return_pct"] for row in controls]
        costs_bps = min(max(float(request.args.get("cost_bps", "0")), 0), 1000)
        cost_pct = costs_bps / 100
        net_returns = [value - cost_pct for value in event_returns]
        equity = []
        running = 1.0
        for row, value in zip(event_rows, net_returns):
            running *= 1 + value / 100
            equity.append({"date": row["date"].isoformat(), "value": running})
        control_mean = sum(control_returns) / len(control_returns) if control_returns else 0.0
        import math
        import statistics
        mean = lambda values: sum(values) / len(values) if values else 0.0
        event_mean = mean(event_returns)
        event_std = statistics.stdev(event_returns) if len(event_returns) > 1 else 0.0
        margin = 1.96 * event_std / math.sqrt(len(event_returns)) if event_returns else 0.0
        result = {
            "ticker": ticker, "event": event, "horizon_days": horizon,
            "start": start.isoformat(), "end": end.isoformat(),
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "sample_size": len(event_returns), "baseline_sample_size": len(baseline),
            "event_mean_return_pct": event_mean, "event_median_return_pct": statistics.median(event_returns) if event_returns else 0.0,
            "event_stddev_pct": event_std, "event_ci95_low_pct": event_mean - margin, "event_ci95_high_pct": event_mean + margin,
            "baseline_mean_return_pct": mean(baseline),
            "event_win_rate_pct": (sum(value > 0 for value in event_returns) / len(event_returns) * 100) if event_returns else 0.0,
            "baseline_win_rate_pct": (sum(value > 0 for value in baseline) / len(baseline) * 100) if baseline else 0.0,
            "event_returns": [{**row, "date": row["date"].isoformat()} for row in event_rows],
            "matched_control_sample_size": len(control_returns),
            "matched_control_mean_return_pct": control_mean,
            "event_volatility_mean_pct": mean([row["volatility_pct"] for row in event_rows]),
            "baseline_volatility_mean_pct": mean([row["volatility_pct"] for row in rows]),
            "maximum_adverse_excursion_pct": min([row["mae_pct"] for row in event_rows], default=0.0),
            "cost_bps": costs_bps,
            "net_event_mean_return_pct": mean(net_returns),
            "equity_curve": equity,
        }
        export_format = request.args.get("format", "json").lower()
        if export_format == "csv":
            import csv
            from io import StringIO
            stream = StringIO()
            fields = ["date", "return_pct", "volatility_pct", "mae_pct", "event"]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for row in result["event_returns"]:
                writer.writerow({key: row.get(key) for key in fields})
            return Response(stream.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=event-study.csv"})
        if export_format in {"md", "markdown"}:
            markdown = "\n".join([
                f"# Event Study: {event}", "", f"- Ticker: `{ticker}`", f"- Window: {horizon} days",
                f"- Sample size: {result['sample_size']}", f"- Matched controls: {result['matched_control_sample_size']}",
                f"- Event mean return: {result['event_mean_return_pct']:.4f}%", f"- Baseline mean return: {result['baseline_mean_return_pct']:.4f}%",
                f"- Event volatility: {result['event_volatility_mean_pct']:.4f}%", f"- Maximum adverse excursion: {result['maximum_adverse_excursion_pct']:.4f}%",
                "", "Generated by SBC Research Lab.",
            ])
            return Response(markdown, mimetype="text/markdown", headers={"Content-Disposition": "attachment; filename=event-study.md"})
        return jsonify(result)
    except (TypeError, ValueError):
        return jsonify({"error": "invalid research parameters"}), 400
    except Exception:
        app.logger.exception("Event study failed")
        return jsonify({"error": "event study unavailable"}), 500


@app.route("/api/research/aspects", methods=["GET"])
def api_research_aspects():
    """Return filtered planetary aspect events with market response metrics."""
    ticker = request.args.get("ticker", "^NSEI")
    start = datetime.date.fromisoformat(request.args.get("start") or (datetime.date.today() - datetime.timedelta(days=3650)).isoformat())
    end = datetime.date.fromisoformat(request.args.get("end") or datetime.date.today().isoformat())
    horizon = min(max(int(request.args.get("horizon", "5")), 1), 20)
    planet_a = request.args.get("planet_a") or None
    planet_b = request.args.get("planet_b") or None
    aspect = request.args.get("aspect") or None
    try:
        import pandas as pd
        import yfinance as yf
        prices = yf.download(ticker, start=start.isoformat(), end=(end + datetime.timedelta(days=1)).isoformat(), interval="1d", auto_adjust=True, progress=False)
        if prices.empty:
            return jsonify({"error": "no market data available"}), 404
        if isinstance(prices.columns, pd.MultiIndex):
            prices.columns = [column[0] for column in prices.columns]
        close = prices["Close"].dropna()
        close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
        events = []
        for index in range(len(close) - horizon):
            day = close.index[index].date()
            planets, _ = positions(_julday(_utc_from_local(day.isoformat(), "09:15", "Asia/Kolkata")))
            matches = planetary_aspect_events(day, planets)
            for event_record in matches:
                event_name = event_record.metadata.get("aspect")
                pair = {event_record.planet_a, event_record.planet_b}
                if aspect and event_name != aspect:
                    continue
                if planet_a and planet_a not in pair:
                    continue
                if planet_b and planet_b not in pair:
                    continue
                base = float(close.iloc[index])
                future = float(close.iloc[index + horizon])
                events.append({**event_record.to_dict(), "return_pct": (future / base - 1) * 100})
        grouped = {}
        for event_record in events:
            key = (event_record["planet_a"], event_record["planet_b"], event_record["metadata"]["aspect"])
            grouped.setdefault(key, []).append(event_record["return_pct"])
        rows = [{"planet_a": key[0], "planet_b": key[1], "aspect": key[2], "samples": len(values),
                 "mean_return_pct": sum(values) / len(values),
                 "win_rate_pct": sum(value > 0 for value in values) / len(values) * 100}
                for key, values in grouped.items()]
        return jsonify({"ticker": ticker, "horizon_days": horizon, "start": start.isoformat(), "end": end.isoformat(),
                        "filters": {"planet_a": planet_a, "planet_b": planet_b, "aspect": aspect},
                        "events": events, "groups": rows,
                        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    except (TypeError, ValueError):
        return jsonify({"error": "invalid aspect research parameters"}), 400
    except Exception:
        app.logger.exception("Aspect research failed")
        return jsonify({"error": "aspect research unavailable"}), 500


@app.route("/api/research/cycles", methods=["GET"])
def api_research_cycles():
    """Return daily solar/lunar cycle observations and an experimental Bradley score."""
    start = datetime.date.fromisoformat(request.args.get("start") or (datetime.date.today() - datetime.timedelta(days=365)).isoformat())
    end = datetime.date.fromisoformat(request.args.get("end") or datetime.date.today().isoformat())
    rows = []
    day = start
    while day <= end:
        planets, _ = positions(_julday(_utc_from_local(day.isoformat(), "09:15", "Asia/Kolkata")))
        sun = next(planet for planet in planets if planet["name"] == "Sun")
        moon = next(planet for planet in planets if planet["name"] == "Moon")
        separation = (moon["longitude"] - sun["longitude"]) % 360
        phase = "new_moon" if separation < 12 or separation >= 348 else "full_moon" if 168 <= separation <= 192 else "waxing" if separation < 180 else "waning"
        rows.append({"date": day.isoformat(), "sun_sign": sun["sign"], "moon_sign": moon["sign"], "sun_moon_angle": round(separation, 2), "phase": phase,
                     "bradley_score": round(sum(1 if 30 <= separation <= 150 else -1 for _ in [day]), 2)})
        day += datetime.timedelta(days=1)
    return jsonify({"start": start.isoformat(), "end": end.isoformat(), "experimental": True, "rows": rows,
                    "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})


@app.route("/api/research/walk-forward", methods=["GET"])
def api_research_walk_forward():
    """Run rolling train/test lunar-event studies without mixing test data."""
    ticker = request.args.get("ticker", "^NSEI")
    event = request.args.get("event", "new_moon")
    horizon = min(max(int(request.args.get("horizon", "5")), 1), 20)
    train_days = min(max(int(request.args.get("train_days", "730")), 90), 3650)
    test_days = min(max(int(request.args.get("test_days", "180")), 30), 730)
    step_days = min(max(int(request.args.get("step_days", "180")), 30), 730)
    end = datetime.date.fromisoformat(request.args.get("end") or datetime.date.today().isoformat())
    requested_start = request.args.get("start")
    start = datetime.date.fromisoformat(requested_start) if requested_start else end - datetime.timedelta(days=3650)
    if event not in {"new_moon", "full_moon"} or start >= end:
        return jsonify({"error": "invalid event or date range"}), 400

    try:
        costs_bps = min(max(float(request.args.get("cost_bps", "0")), 0), 1000)
        rows = _research_lunar_rows(ticker, start, end, horizon)
        if not rows:
            return jsonify({"error": "no market data available"}), 404

        def in_range(row, lower, upper):
            return lower <= row["date"] < upper

        def metrics(sample):
            events = [row["return_pct"] - costs_bps / 100 for row in sample if row["event"] and row["event_record"]["event_type"] == event]
            baseline = [row["return_pct"] for row in sample]
            return {
                "event_samples": len(events),
                "baseline_samples": len(baseline),
                "event_mean_return_pct": sum(events) / len(events) if events else None,
                "baseline_mean_return_pct": sum(baseline) / len(baseline) if baseline else None,
                "event_win_rate_pct": sum(value > 0 for value in events) / len(events) * 100 if events else None,
                "event_mean_return_net_pct": sum(events) / len(events) if events else None,
            }

        folds = []
        training_start = start
        test_start = training_start + datetime.timedelta(days=train_days)
        while test_start < end:
            train_end = test_start
            test_end = min(test_start + datetime.timedelta(days=test_days), end)
            train = [row for row in rows if in_range(row, training_start, train_end)]
            test = [row for row in rows if in_range(row, test_start, test_end)]
            folds.append({
                "train_start": start.isoformat(), "train_end": train_end.isoformat(),
                "test_start": test_start.isoformat(), "test_end": test_end.isoformat(),
                "train": metrics(train), "test": metrics(test),
            })
            test_start += datetime.timedelta(days=step_days)

        test_events = []
        test_baseline = []
        for row in rows:
            date_key = row["date"].isoformat()
            if any(fold["test_start"] <= date_key < fold["test_end"] for fold in folds):
                test_baseline.append(row)
                if row["event"] and row["event_record"]["event_type"] == event:
                    test_events.append(row)
        regime_results = {}
        for regime_name in ("bull", "bear", "range"):
            regime_rows = [row for row in test_baseline if row["regime"] == regime_name]
            regime_results[regime_name] = metrics(regime_rows)
        gross_fold_means = [fold["test"]["event_mean_return_pct"] for fold in folds if fold["test"]["event_mean_return_pct"] is not None]
        accuracy_decay = (gross_fold_means[-1] - gross_fold_means[0]) if len(gross_fold_means) > 1 else None
        aggregate = {
            "event_samples": len(test_events),
            "baseline_samples": len(test_baseline),
            "event_mean_return_pct": sum(row["return_pct"] for row in test_events) / len(test_events) if test_events else None,
            "baseline_mean_return_pct": sum(row["return_pct"] for row in test_baseline) / len(test_baseline) if test_baseline else None,
            "event_win_rate_pct": sum(row["return_pct"] > 0 for row in test_events) / len(test_events) * 100 if test_events else None,
            "event_mean_return_net_pct": sum(row["return_pct"] - costs_bps / 100 for row in test_events) / len(test_events) if test_events else None,
            "cost_bps": costs_bps,
            "regime_results": regime_results,
            "accuracy_decay_pct_points": accuracy_decay,
        }
        return jsonify({
            "ticker": ticker, "event": event, "horizon_days": horizon,
            "train_days": train_days, "test_days": test_days, "step_days": step_days,
            "start": requested_start or (end - datetime.timedelta(days=3650)).isoformat(), "end": end.isoformat(),
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "folds": folds, "aggregate_test": aggregate,
        })
    except (TypeError, ValueError):
        return jsonify({"error": "invalid walk-forward parameters"}), 400
    except Exception:
        app.logger.exception("Research walk-forward failed")
        return jsonify({"error": "walk-forward study unavailable"}), 500


@app.route("/api/backtest/moon", methods=["GET"])
def api_backtest_moon():
    try:
        ticker = request.args.get("ticker", "^NSEI")
        start_str = request.args.get("start")
        end_str = request.args.get("end")
        multi_tf = request.args.get("multi_tf", "true").lower() == "true"
        regime = request.args.get("regime", "false").lower() == "true"
        volume = request.args.get("volume", "false").lower() == "true"
        vedha = request.args.get("vedha", "false").lower() == "true"
        if start_str:
            start = datetime.date.fromisoformat(start_str)
        else:
            start = datetime.date.today() - datetime.timedelta(days=730)
        if end_str:
            end = datetime.date.fromisoformat(end_str)
        else:
            end = datetime.date.today()
        # Import backtest engine logic inline
        import pandas as pd, yfinance as yf
        from sbc.market_data import moon_rashi, RASHI_TREND
        df=yf.download(ticker,start=start,end=end,interval='1d',auto_adjust=True,progress=False)
        if df.empty:
            return jsonify({"error":"no data"}),400
        df.columns=[c[0] if isinstance(c,tuple) else c for c in df.columns]
        df=df[['Open','High','Low','Close','Volume']].dropna()
        df['vol_ma']=df['Volume'].rolling(20).mean()
        ist=ZoneInfo("Asia/Kolkata")
        correct=total=0
        results=[]
        # vedha cache
        vedha_cache={}
        sector_name=SECTOR_NAME_MAP.get(ticker, "Nifty Large Caps")
        for i in range(1,len(df)-1):
            d=pd.to_datetime(df.index[i]).date()
            dt=datetime.datetime.combine(d,datetime.time(9,15),tzinfo=ist)
            daily_rashi=moon_rashi(dt)
            expected=RASHI_TREND.get(daily_rashi)
            if expected is None:
                continue
            if multi_tf:
                monday=dt-datetime.timedelta(days=dt.weekday())
                weekly=moon_rashi(datetime.datetime.combine(monday.date(),datetime.time(9,15),tzinfo=ist))
                if RASHI_TREND.get(weekly)!=expected:
                    continue
            if regime and d.day in [1,15]:
                continue
            if vedha:
                y,m=d.year,d.month
                key=(y,m)
                if key not in vedha_cache:
                    import calendar
                    from sbc.monthly_heatmap import monthly_heatmap
                    start_m=datetime.date(y,m,1)
                    days=calendar.monthrange(y,m)[1]+5
                    res=monthly_heatmap(start_date=start_m, days=days, tz_name='Asia/Kolkata', anchor_key='nse')
                    mat=res.get('matrix',{})
                    scores={}
                    if sector_name in mat:
                        for dd,s in mat[sector_name].items():
                            try: scores[dd]=float(s)
                            except: pass
                    vedha_cache[key]=scores
                v=vedha_cache[key].get(d.isoformat())
                if v is not None:
                    if (expected=="bullish" and v<=0) or (expected=="bearish" and v>=0):
                        continue
            entry_i=i+1
            if volume:
                if pd.isna(df['vol_ma'].iloc[entry_i]): continue
                if df['Volume'].iloc[entry_i] < df['vol_ma'].iloc[entry_i]: continue
                open_p=float(df['Open'].iloc[entry_i])
                prev_close=float(df['Close'].iloc[i])
                if expected=="bullish" and open_p<=prev_close: continue
                if expected=="bearish" and open_p>=prev_close: continue
            prev_close=float(df['Close'].iloc[i])
            close_next=float(df['Close'].iloc[entry_i])
            actual="bullish" if close_next>prev_close else "bearish" if close_next<prev_close else "neutral"
            if actual!="neutral":
                total+=1
                match=expected==actual
                if match: correct+=1
                results.append({"date":d.isoformat(),"expected":expected,"actual":actual,"match":bool(match)})
        acc=correct/total if total else 0
        return jsonify({"ticker":ticker,"samples":total,"correct":correct,"accuracy":acc,"results":results})
    except Exception as e:
        return jsonify({"error":str(e)}),500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8801, debug=False)
