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
_intraday_path_cache: dict = {}
_CACHE_TTL_SECONDS = 24 * 60 * 60

# Kota cache
_kota_cache: dict = {}
_KOTA_TTL_SECONDS = 24 * 60 * 60


@engine_bp.route("/version")
def version():
    from flask import current_app

    from sbc import __version__
    return jsonify({
        "version": __version__,
        "engine": "Sarvatobhadra Chakra",
        "endpoints": len([r for r in current_app.url_map.iter_rules() if r.endpoint != 'static'])
    }), 200


@engine_bp.route("/market/ohlc")
def market_ohlc():
    from sbc.market_ohlc import load_week_ohlc
    symbol = request.args.get("symbol", "NIFTY").upper()
    try:
        days = int(request.args.get("days", "7"))
    except ValueError:
        return jsonify({"error": "invalid days"}), 400
    days = max(1, min(60, days))
    from sbc import data_freshness
    data = load_week_ohlc(symbol, days)
    last = data[-1].get("date") if data else None
    return jsonify({"symbol": symbol, "days": days, "bars": data,
                    "freshness": data_freshness.stamp(last),
                    "note": None if data else "no 3-minute bar source is configured; "
                                              "data/ohlc/ is empty"}), 200


@engine_bp.route("/market/freshness")
def market_freshness():
    """Coverage and staleness of data/market.db (NIFTY, SENSEX, VIX, FII/DII)."""
    from sbc import market_store
    return jsonify(market_store.freshness()), 200


@engine_bp.route("/fingerprint")
def fingerprint():
    """Astro fingerprint at 09:15 IST: ?date=YYYY-MM-DD (default today), &vector=1 adds features."""
    from sbc import fingerprint as fpmod
    from sbc import fingerprint_store

    raw = request.args.get("date") or datetime.date.today().isoformat()
    try:
        day = datetime.date.fromisoformat(raw).isoformat()
    except ValueError:
        return jsonify({"error": "date must be YYYY-MM-DD"}), 400
    fp = fingerprint_store.get(day)
    if request.args.get("vector") in ("1", "true"):
        fp = {**fp, "vector": [{"name": n, "tier": t, "value": round(v, 4)}
                               for n, t, v in fpmod.feature_vector(fp)]}
    return jsonify(fp), 200


@engine_bp.route("/analogs")
def analogs():
    """Past NIFTY sessions whose sky most resembles ?date (default today).

    &horizon=1|5|20 (default 5), &variant=overall|slow|medium|fast,
    &k=5..100 (default 30), &min_similarity=0..1 (optional; default top-k only).
    Only sessions whose outcome was known before `date` are used.
    """
    from sbc import analog_validation as av
    from sbc import analogs as an
    from sbc import data_freshness, fingerprint_store

    raw = request.args.get("date") or datetime.date.today().isoformat()
    try:
        day = datetime.date.fromisoformat(raw).isoformat()
        horizon = int(request.args.get("horizon", "5"))
        k = int(request.args.get("k", str(an.TOP_K)))
        raw_sim = request.args.get("min_similarity")
        min_sim = float(raw_sim) if raw_sim else None
    except ValueError:
        return jsonify({"error": "invalid date, horizon, k or min_similarity"}), 400
    variant = request.args.get("variant", "overall")
    if (horizon not in an.HORIZONS or f"analog_{variant}" not in av.VARIANTS
            or not 5 <= k <= 100 or (min_sim is not None and not 0 <= min_sim <= 1)):
        return jsonify({"error": f"horizon in {list(an.HORIZONS)}, variant in "
                                 "overall/slow/medium/fast, k 5-100, min_similarity 0-1"}), 400

    from sbc.market_store import MarketDataMissing
    try:
        history = an.load_nifty_history()
    except MarketDataMissing:
        return jsonify({"error": "no NIFTY history yet; run scripts/refresh_market_data.py --full"}), 404
    result = an.find_analogs(history, fingerprint_store.get(day), horizon, min_sim, k,
                             weights=av.VARIANTS[f"analog_{variant}"])
    result.update({
        "variant": variant,
        "data_as_of": history.dates[-1],
        "freshness": data_freshness.stamp(history.dates[-1]),
        "track_record": av.track_record(variant, horizon),
        "status": "experimental",
        "caveat": ("Research output, not investment advice. In the walk-forward test "
                   "(2012-2026) no analog variant beat the market's drift after correction."),
    })
    return jsonify(result), 200


@engine_bp.route("/forecast")
def forecast():
    """NIFTY forecast for ?date (a trading day; default the next one) over &horizon=1|5|20."""
    from sbc import forecast as fc
    from sbc.market_holidays import next_trading_day
    from sbc.market_store import MarketDataMissing

    raw = request.args.get("date")
    try:
        day = (datetime.date.fromisoformat(raw) if raw
               else next_trading_day(datetime.date.today(), inclusive=False))
        horizon = int(request.args.get("horizon", "5"))
    except ValueError:
        return jsonify({"error": "date must be YYYY-MM-DD and horizon an integer"}), 400
    try:
        return jsonify(fc.forecast(day.isoformat(), horizon)), 200
    except MarketDataMissing:
        return jsonify({"error": "no NIFTY history yet; run scripts/refresh_market_data.py --full"}), 404
    except ValueError as exc:  # our own validation messages (horizon, trading day)
        return jsonify({"error": str(exc)}), 400


@engine_bp.route("/forecast/ledger")
def forecast_ledger():
    """Live record of the daily forecast: &horizon=1|5|20, &kind=live|late|backfill."""
    from sbc import daily_ledger

    try:
        horizon = int(request.args.get("horizon", "5"))
    except ValueError:
        return jsonify({"error": "horizon must be an integer"}), 400
    kind = request.args.get("kind", "live")
    if horizon not in daily_ledger.HORIZONS or kind not in ("live", "late", "backfill"):
        return jsonify({"error": "horizon in 1/5/20, kind in live/late/backfill"}), 400
    return jsonify({"summary": daily_ledger.summary(horizon, kind),
                    "recent": daily_ledger.recent(horizon)}), 200


@engine_bp.route("/forecast/card")
def forecast_card():
    """Evidence card for ?date (default the next trading day): 1/5/20-session forecast,
    every component's lean with its verdicts, the range and the live record."""
    from sbc import forecast as fc
    from sbc.market_holidays import is_trading_day, next_trading_day
    from sbc.market_store import MarketDataMissing

    raw = request.args.get("date")
    try:
        day = (datetime.date.fromisoformat(raw) if raw
               else next_trading_day(datetime.date.today(), inclusive=False))
    except ValueError:
        return jsonify({"error": "date must be YYYY-MM-DD"}), 400
    if not is_trading_day(day):
        return jsonify({"error": f"{day} is not an NSE trading day"}), 400
    try:
        card = fc.card(day.isoformat())
    except MarketDataMissing:
        return jsonify({"error": "no NIFTY history yet; run scripts/refresh_market_data.py --full"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    from sbc import data_freshness
    card["freshness"] = data_freshness.stamp(card.get("data_as_of"), before=day)
    return jsonify(card), 200


@engine_bp.route("/calendar")
def forward_calendar():
    """Forward calendar from ?start (default the next trading day) for &weeks=1..8 (default 4).

    &format=json (default) | html | md.
    """
    from flask import Response

    from sbc import forward_calendar as fcal
    from sbc.market_store import MarketDataMissing

    start = request.args.get("start") or None
    fmt = request.args.get("format", "json")
    try:
        if start:
            datetime.date.fromisoformat(start)
        weeks = int(request.args.get("weeks", "4"))
        if fmt not in ("json", "html", "md"):
            raise ValueError
        cal = fcal.build(start, weeks)
    except MarketDataMissing:
        return jsonify({"error": "no NIFTY history yet; run scripts/refresh_market_data.py --full"}), 404
    except ValueError:
        return jsonify({"error": "start must be YYYY-MM-DD, weeks 1-8, format json/html/md"}), 400
    if fmt == "html":
        return Response(fcal.render_html(cal), mimetype="text/html")
    if fmt == "md":
        return Response(fcal.render_markdown(cal), mimetype="text/markdown")
    from sbc import data_freshness
    return jsonify({**cal, "freshness": data_freshness.stamp(cal.get("data_as_of"))}), 200


def _date_range_args(default_days: int) -> tuple[datetime.date, datetime.date]:
    """?start (default: the 1st of this month) and ?end (default: start + default_days - 1)."""
    today = datetime.date.today()
    start = datetime.date.fromisoformat(request.args.get("start") or today.replace(day=1).isoformat())
    raw_end = request.args.get("end")
    end = (datetime.date.fromisoformat(raw_end) if raw_end
           else start + datetime.timedelta(days=default_days - 1))
    return start, end


@engine_bp.route("/planet_series")
def planet_series():
    """Daily declination, ecliptic latitude or speed per planet at 09:15 IST (B-45).

    ?metric=declination|latitude|speed (default declination) &start=&end= (max 400 days;
    default the 35 days from the 1st of this month).
    """
    from sbc import planet_series as ps

    try:
        start, end = _date_range_args(35)
        result = ps.series(request.args.get("metric", "declination"), start, end)
    except ValueError as exc:
        msg = str(exc) if "metric" in str(exc) or "days" in str(exc) else "start and end must be YYYY-MM-DD"
        return jsonify({"error": msg}), 400
    return jsonify(result), 200


@engine_bp.route("/stations")
def stations():
    """Planetary stations to the minute, IST, true-node Rahu included (B-42).

    ?start=&end= (inclusive, max 10 years; default the 35 days from the 1st of this month).
    """
    from sbc import stations as st

    try:
        start, end = _date_range_args(35)
        rows = st.between(start, end + datetime.timedelta(days=1))
    except ValueError:
        return jsonify({"error": "start and end must be YYYY-MM-DD, end on or after start, "
                                 "at most ten years"}), 400
    return jsonify({"start": start.isoformat(), "end": end.isoformat(), "zodiac": "sidereal (Lahiri)",
                    "count": len(rows), "stations": rows}), 200


@engine_bp.route("/monthly_projection")
def monthly_projection():
    """Monthly projection score line from own composite.

    ?month=YYYY-MM required. Returns one value per calendar day from sbc composite,
    trading flag, and NIFTY closes so far. Hypothetical, unvalidated.
    """
    import calendar
    from sbc import fingerprint_store, market_store
    from sbc.market_holidays import is_trading_day
    from sbc import data_freshness

    month_str = request.args.get("month")
    if not month_str:
        return jsonify({"error": "month is required, format YYYY-MM"}), 400
    try:
        year, mon = map(int, month_str.split("-"))
        start = datetime.date(year, mon, 1)
        last_day = calendar.monthrange(year, mon)[1]
        end = datetime.date(year, mon, last_day)
    except Exception:
        return jsonify({"error": "month must be YYYY-MM"}), 400

    # Load NIFTY closes for the month
    closes = {}
    try:
        rows = market_store.get_daily("NIFTY", start.isoformat(), end.isoformat())
        closes = {r["date"]: r["close"] for r in rows}
    except Exception:
        closes = {}

    days = []
    for i in range((end - start).days + 1):
        d = start + datetime.timedelta(days=i)
        trading = is_trading_day(d)
        # Composite score: SBC classical net from fingerprint, scaled to ~-10..+10 range
        try:
            fp = fingerprint_store.get(d.isoformat())
            score_raw = fp.get("sbc", {}).get("classical", {}).get("net", 0.0)
            # Keep raw net; it's already a small integer-ish value
            score = float(score_raw)
        except Exception:
            score = None
        nifty_close = closes.get(d.isoformat())
        # Do not expose future closes
        today = datetime.date.today()
        if d > today:
            nifty_close = None
        days.append({
            "date": d.isoformat(),
            "trading": bool(trading),
            "score": score,
            "nifty_close": nifty_close,
        })

    # Freshness badge
    latest_price_date = max(closes.keys()) if closes else None
    freshness = data_freshness.stamp(latest_price_date)

    # Ledger live hit rate for disclaimer
    from sbc import daily_ledger
    try:
        tr = daily_ledger.summary(5)
        forward = tr.get("groups", {}).get("forward", {})
        live_hit_rate = forward.get("hit_rate")
    except Exception:
        live_hit_rate = None

    return jsonify({
        "month": month_str,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "days": days,
        "freshness": freshness,
        "disclaimer": "hypothetical, unvalidated",
        "live_hit_rate_5h": live_hit_rate,
        "source": "sbc composite: fingerprint sbc classical net",
    }), 200


@engine_bp.route("/calendar/reports")
def calendar_reports():
    """Weekly calendars written by the scheduler, newest first."""
    from sbc import forward_calendar as fcal
    return jsonify({"reports": fcal.reports()}), 200


@engine_bp.route("/calendar/reports/<name>")
def calendar_report_file(name):
    """One stored calendar file (forward_calendar_<key>.html|md)."""
    from flask import send_from_directory

    from sbc import forward_calendar as fcal
    known = {n for r in fcal.reports() for n in (r["html"], r["md"])}
    if name not in known:
        return jsonify({"error": "no such report"}), 404
    return send_from_directory(fcal.REPORT_DIR, name)


_MAX_SWING_DAYS = 5 * 366


def _swing_args():
    """(start, end, planets, aspects) from the query string; raises ValueError."""
    from sbc import helio_aspects as ha

    today = datetime.date.today()
    start = datetime.date.fromisoformat(request.args.get("start") or (today - datetime.timedelta(days=365)).isoformat())
    end = datetime.date.fromisoformat(request.args.get("end") or (today + datetime.timedelta(days=90)).isoformat())
    if end < start or (end - start).days > _MAX_SWING_DAYS:
        raise ValueError("end must be after start, at most 5 years")
    planets = [p for p in (request.args.get("planet") or "").split(",") if p] or None
    aspects = [a.upper() for a in (request.args.get("aspect") or "").split(",") if a] or None
    bad = [p for p in planets or [] if p not in ha.PLANETS] + [a for a in aspects or [] if a not in ha.ASPECTS]
    if bad:
        raise ValueError(f"unknown planet/aspect: {', '.join(bad)}")
    return start.isoformat(), end.isoformat(), planets, aspects


@engine_bp.route("/aspect_windows")
def aspect_windows():
    """Heliocentric Earth-planet aspect windows (B-39 ENTRY layer).

    ?start=&end= (max 5 years) &planet=Jupiter[,Saturn] &aspect=SS[,SQ]
    &format=json (default, full windows) | tv (TradingView payload: {dates, label, skip_holidays}).
    """
    from sbc import helio_aspects as ha

    try:
        start, end, planets, aspects = _swing_args()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    windows = ha.scan(start, end, planets, aspects)
    if request.args.get("format") == "tv":
        label = request.args.get("label") or None
        return jsonify(ha.tv_payload(windows, label)), 200
    return jsonify({"start": start, "end": end, "orb": ha.ORB, "count": len(windows), "windows": windows}), 200


@engine_bp.route("/swing_windows")
def swing_windows():
    """B-39 swing model: aspect ENTRY -> Gann/Fibonacci/indicator confluence EXIT on NIFTY.

    Same filters as /aspect_windows, plus &confluence=3 (strict, default) | 2.
    """
    from sbc import research_reports
    from sbc import swing_model as sm
    from sbc.market_store import MarketDataMissing

    try:
        start, end, planets, aspects = _swing_args()
        need = int(request.args.get("confluence", "3"))
        if need not in (2, 3):
            raise ValueError("confluence must be 2 or 3")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    try:
        out = sm.build(start, end, planets, aspects, need)
    except MarketDataMissing:
        return jsonify({"error": "no NIFTY history yet; run scripts/refresh_market_data.py --full"}), 404
    from sbc import data_freshness
    out["freshness"] = data_freshness.stamp(out.get("data_as_of"))
    report = research_reports.latest("swing_validation")
    if report:
        res = report["model"]["models"].get("strict (3 of 3)" if need == 3 else "2 of 3", {})
        out["validation"] = {"report": report["_file"], "verdict": res.get("verdict"),
                             "model": res.get("model"), "baselines": res.get("baselines"),
                             "random": res.get("random"),
                             "entry_tests": len(report["results"]),
                             "entry_edges": sum(r["verdict"] == "edge" for r in report["results"])}
    return jsonify(out), 200


@engine_bp.route("/fingerprint/status")
def fingerprint_status():
    from sbc import fingerprint_store
    return jsonify(fingerprint_store.status()), 200


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
    from sbc.market_holidays import holiday_name
    closed = holiday_name(trading_day)
    if closed:
        return jsonify({"error": f"NSE is closed on {trading_day.isoformat()} ({closed})",
                        "holiday": closed}), 400

    # Load KP report
    from pathlib import Path

    from sbc.kp_config import get_config, get_instrument_config
    from sbc.kp_intraday import (
        EXPERIMENTAL_NOTICE,
        EXPERIMENTAL_VALIDATION,
        generate_kp_intraday_report,
    )

    kp_data_dir = Path(__file__).resolve().parents[2] / "data" / "kp"
    kp_data_dir.mkdir(parents=True, exist_ok=True)
    month_file = kp_data_dir / f"KP_Data_{trading_day.strftime('%b%Y')}.csv"
    if not month_file.exists():
        return jsonify({
            "error": (
                f"KP data unavailable for {trading_day.strftime('%B %Y')}. "
                "Use 'Generate KP Data' (Swiss Ephemeris) to create it."
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
    hora_slots = list(report.day_signature.hora_slots)

    def hora_slot_at(clock):
        # Horas start at real (sunrise-based) times, not on series ticks:
        # pick the slot whose [start, end) contains the clock time.
        try:
            t = datetime.datetime.strptime(clock, "%H:%M").time()
        except ValueError:
            return None
        for slot in hora_slots:
            if slot.start <= t < slot.end or (slot.end <= slot.start and t >= slot.start):
                return slot
        return None

    from sbc.planets import positioned_planets
    # Nadi mapping for 27 nakshatras – simplified; keys spelled as sbc.nakshatra does ("P.Phalguni")
    NADI_MAP = {
        "Ashwini":"Antya","Bharani":"Madhya","Krittika":"Aadi","Rohini":"Aadi","Mrigashira":"Madhya","Ardra":"Antya",
        "Punarvasu":"Antya","Pushya":"Aadi","Ashlesha":"Madhya","Magha":"Antya","P.Phalguni":"Aadi","U.Phalguni":"Madhya",
        "Hasta":"Antya","Chitra":"Aadi","Swati":"Madhya","Vishakha":"Antya","Anuradha":"Aadi","Jyeshtha":"Madhya",
        "Mula":"Antya","P.Ashadha":"Aadi","U.Ashadha":"Madhya","Shravana":"Antya","Dhanishta":"Aadi",
        "Shatabhisha":"Madhya","P.Bhadrapada":"Antya","U.Bhadrapada":"Aadi","Revati":"Madhya"
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
        slot = hora_slot_at(time_str)
        if slot is not None:
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
        "data_quality": report.data_quality,
        # No validated edge: see docs/INTRADAY_PATH_VALIDATION.md.
        "status": "experimental",
        "validation": dict(EXPERIMENTAL_VALIDATION),
        "experimental_notice": EXPERIMENTAL_NOTICE,
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


def _kota_coverage(path):
    from sbc import data_freshness
    return data_freshness.kota_coverage(path)


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
        "records": filtered.to_dict(orient="records"),
        "coverage": _kota_coverage(excel_path),
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
        "records": filtered.to_dict(orient="records"),
        "coverage": _kota_coverage(excel_path),
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
        "summary": filtered.to_dict(orient="records"),
        "coverage": _kota_coverage(excel_path),
    }
    return jsonify(result), 200


@engine_bp.route("/aspect_table")
def aspect_table():
    """Exact-time geocentric sidereal aspect table B-43.

    ?start=YYYY-MM-DD&end=YYYY-MM-DD (inclusive).  Returns start, end, count, aspects.
    """
    from sbc.aspect_table import get_aspects
    start_str = request.args.get("start")
    end_str = request.args.get("end")
    if not start_str or not end_str:
        return jsonify({"error": "start and end query params required (YYYY-MM-DD)"}), 400
    try:
        start_dt = datetime.date.fromisoformat(start_str)
        end_dt = datetime.date.fromisoformat(end_str)
    except ValueError:
        return jsonify({"error": "dates must be YYYY-MM-DD"}), 400
    if end_dt < start_dt:
        return jsonify({"error": "end must be on or after start"}), 400
    try:
        aspects = get_aspects(start_dt, end_dt)
    except Exception as exc:
        return jsonify({"error": f"aspect generation failed: {exc}"}), 500
    return jsonify({
        "start": start_str,
        "end": end_str,
        "count": len(aspects),
        "aspects": aspects,
    }), 200


@engine_bp.route("/trade_journal", methods=["GET","POST"])
def trade_journal():
    """Trade journal CRUD for B-48.

    GET ?id=... or ?symbol=...&limit=...
    POST JSON {symbol, entry_date, entry_price, qty, direction, stop_price, risk_per_share, notes}
    """
    from sbc import trade_journal as tj
    if request.method == "GET":
        tid = request.args.get("id")
        if tid:
            try:
                trade = tj.get_trade(int(tid))
                return jsonify(trade), 200 if trade else 404
            except Exception as e:
                return jsonify({"error": str(e)}), 400
        symbol = request.args.get("symbol")
        limit = int(request.args.get("limit", "100"))
        trades = tj.list_trades(symbol, limit)
        return jsonify({"trades": trades, "count": len(trades)}), 200
    # POST create trade
    data = request.get_json(silent=True) or {}
    required = ["symbol","entry_date","entry_price","qty","direction"]
    if not all(k in data for k in required):
        return jsonify({"error": f"missing fields, need {required}"}), 400
    try:
        tid = tj.create_trade(
            symbol=data["symbol"],
            entry_date=data["entry_date"],
            entry_price=float(data["entry_price"]),
            qty=float(data["qty"]),
            direction=data["direction"],
            stop_price=float(data["stop_price"]) if data.get("stop_price") else None,
            risk_per_share=float(data["risk_per_share"]) if data.get("risk_per_share") else None,
            notes=data.get("notes","")
        )
        return jsonify({"id": tid, "status": "created"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400




@engine_bp.route("/transit-almanac")
def transit_almanac():
    """Yearly transit almanac (B-55): ?year=YYYY (default this year), &zodiac=sidereal|tropical."""
    from sbc import transit_almanac as ta

    try:
        year = int(request.args.get("year") or datetime.date.today().year)
        zodiac = request.args.get("zodiac", "sidereal")
        data = ta.build(year, zodiac)
    except ValueError:
        return jsonify({"error": f"year must be {ta.MIN_YEAR}-{ta.MAX_YEAR}, zodiac sidereal or tropical"}), 400
    return jsonify(data), 200


@engine_bp.route("/bullion-week")
def bullion_week():
    """Weekly bullion brief (B-56) for the Mon-Fri week containing ?start (default: next Monday
    on weekends, else this week's Monday)."""
    from sbc import bullion_week as bw

    raw = request.args.get("start")
    try:
        if raw:
            day = datetime.date.fromisoformat(raw)
        else:
            today = datetime.date.today()
            day = today + datetime.timedelta(days=(7 - today.weekday()) % 7) if today.weekday() >= 5 else today
        data = bw.build(day)
    except ValueError:
        return jsonify({"error": "start must be YYYY-MM-DD"}), 400
    return jsonify(data), 200
