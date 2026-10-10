"""Sector signal panels: bullion and transit vedha, large-cap divergence, sector syntax signals, vedha daily.

Moved out of app.py (B-16).
"""

import datetime
from functools import lru_cache

from flask import Blueprint, current_app, jsonify, request

from sbc.api.errors import internal_error
from sbc.bullion_vedha import (
    format_bullion_vedha_for_ui,
    scan_bullion_vedha_matrix,
    scan_bullion_vedha_week,
)
from sbc.transit_vedha import (
    format_transit_vedha_for_ui,
    scan_transit_vedha_matrix,
    scan_transit_vedha_week,
)

signals_bp = Blueprint('signals', __name__)


@signals_bp.route("/api/bullion_vedha")
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


@signals_bp.route("/api/bullion_vedha_week")
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


@signals_bp.route("/api/transit_vedha")
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


@signals_bp.route("/api/transit_vedha_week")
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


@signals_bp.route("/api/largecap_divergence")
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
        if is_new_moon(tithi) or is_full_moon(tithi):
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
        }
        # A 10th config, "Adhik Masa + Rahu Fire + Moon Water", was removed: it never
        # checked Adhik Masa (no lunar-month calendar here) yet could show as active.
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
        "summary": f"{len(active)}/{len(configs)} configurations active · {len(high_conviction)} HIGH · {len(medium_conviction)} MEDIUM"
    })


@signals_bp.route("/api/tourism_signals")
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


@signals_bp.route("/api/chemical_signals")
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


@signals_bp.route("/api/alcohol_signals")
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


@signals_bp.route("/api/fmcg_signals")
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


@lru_cache(maxsize=64)
def _heatmap_month_row(month_start: str, row: str) -> dict[str, float]:
    """{date: net} for one sector row of the monthly heatmap (cached per month)."""
    import calendar

    from sbc.monthly_heatmap import monthly_heatmap
    first = datetime.date.fromisoformat(month_start)
    days = calendar.monthrange(first.year, first.month)[1]
    data = monthly_heatmap(start_date=first, days=days, tz_name="Asia/Kolkata", anchor_key="nse")
    return {day: float(net) for day, net in (data.get("matrix", {}).get(row) or {}).items()
            if net is not None}


@signals_bp.route("/api/vedha_daily", methods=["GET"])
def api_vedha_daily():
    try:
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
        if end_date_req < start_date_req or (end_date_req - start_date_req).days > 731:
            return jsonify({"error": "end must be on/after start, at most 2 years"}), 400
        from sbc.monthly_heatmap import NIFTY_SECTOR_ROWS
        target_row = None
        for display_name, tags in NIFTY_SECTOR_ROWS:
            if (sector_name.lower() in display_name.lower()
                    or any(sector_name.lower() in tag.lower() for tag in tags)):
                target_row = display_name
                break
        scores: dict[str, float] = {}
        if target_row:
            # Only the months the range covers, each computed once per process.
            month = datetime.date(start_date_req.year, start_date_req.month, 1)
            while month <= end_date_req:
                try:
                    scores.update(_heatmap_month_row(month.isoformat(), target_row))
                except Exception:
                    current_app.logger.exception("vedha_daily heatmap failed for %s %s", sector_name, month)
                month = (month + datetime.timedelta(days=32)).replace(day=1)
        else:
            current_app.logger.warning("vedha_daily: no heatmap row matches sector %r", sector_name)
        from sbc import fingerprint_store
        out = []
        d = start_date_req
        while d <= end_date_req:
            iso = d.isoformat()
            score = scores.get(iso)
            # The Moon's nakshatra (0 = Ashwini) at the 09:15 IST open.
            nak_idx = fingerprint_store.get(iso)["planets"]["Moon"]["nakshatra"]
            out.append({"date": iso, "score": score, "nakshatra_idx": int(nak_idx),
                        "source": "real" if score is not None else "missing"})
            d += datetime.timedelta(days=1)
        return jsonify(out)
    except Exception:
        return internal_error()

