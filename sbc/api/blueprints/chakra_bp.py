"""SBC Chakra blueprint."""

import datetime
from datetime import UTC

from flask import Blueprint, current_app, jsonify, request

from sbc.api.errors import internal_error

chakra_bp = Blueprint('chakra', __name__, url_prefix='')

@chakra_bp.route('/api/bhadra_calendar')
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

    result = bhadra_overlap_result(date_str, tz_name, offset)
    return jsonify(result)


def bhadra_overlap_result(date_str, tz_name, offset):
    from sbc.bhadra import bhadra_calendar

    result = bhadra_calendar(date_str, tz_name, offset)

    # Compute reversal-watch overlap for the same month so the Bhadra
    # windows can be cross-referenced against the reversal calendar.
    windows = result["windows"]
    if windows:
        try:
            from sbc.backtest import _julian_at_noon
            from sbc.market_calendar import reversal_alert
            from sbc.nakshatra import tithi_of
            from sbc.planets import positions

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
        except Exception:
            current_app.logger.exception("bhadra/reversal overlap failed")
            result["reversal_overlap"] = {"error": "unavailable"}

    return result

def _tithi_summary(tithi):
    """Name + paksha + Moon nature for build_response()['tithi']."""
    from sbc.panchang_signals import TITHI_NAMES
    n = tithi.get("tithi")
    if not isinstance(n, int) or not 1 <= n <= 30:
        return None
    return {
        "number": n,
        "name": TITHI_NAMES[n - 1],
        "paksha": tithi.get("paksha"),
        "group": tithi.get("group"),
        "group_weekdays": tithi.get("group_weekdays"),
        "moon_note": tithi.get("moon_note"),
        "moon_benefic": (tithi.get("moon_note") or "").startswith("shubha"),
    }


def _bhadra_for_day(date_str, tz_name):
    """Bhadra (Vishti karana) windows touching the given local day, plus the next one."""
    from zoneinfo import ZoneInfo

    from sbc.bhadra import bhadra_windows
    try:
        tz = ZoneInfo(tz_name)
        day = datetime.date.fromisoformat(date_str)
        day_start = datetime.datetime(day.year, day.month, day.day, tzinfo=tz)
        day_end = day_start + datetime.timedelta(days=1)
        nxt_month = (day.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
        windows = bhadra_windows(day_start.replace(day=1), tz)
        windows += bhadra_windows(datetime.datetime(nxt_month.year, nxt_month.month, 1, tzinfo=tz), tz)
    except Exception:
        return None
    fmt = lambda w: {"begin": w["begin"].isoformat(timespec="minutes"),
                     "end": w["end"].isoformat(timespec="minutes")}
    today = [fmt(w) for w in windows if w["begin"] < day_end and w["end"] > day_start]
    upcoming = [w for w in windows if w["begin"] >= day_end]
    return {
        "active_today": bool(today),
        "windows_today": today,
        "next": fmt(upcoming[0]) if upcoming else None,
    }


@chakra_bp.route('/api/astro/personal')
def api_astro_personal():
    from sbc.engine import _julday, _utc_from_local, build_response
    from sbc.planets import positions
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
            from datetime import datetime, timedelta
            y, m, d = (int(x) for x in date_str.split("-"))
            hh, mm = (int(x) for x in time_str.split(":"))
            local_dt = datetime(y, m, d, hh, mm)
            offset = timedelta(hours=int(tz_hours), minutes=int(tz_mins))
            # Local time is UTC + offset
            utc = (local_dt - offset).replace(tzinfo=UTC).replace(tzinfo=None)
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
        signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
                 "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

        def sign_from_lon(lon):
            if lon is None:
                return None
            idx = int((lon % 360) // 30)
            return signs[idx]

        tithi = market_confluence.get("tithi") or {}
        alert = market_confluence.get("market_alert") or {}

        return jsonify({
            "date": date_str,
            "time": time_str,
            "timezone": tz_name,
            "ayanamsa": round(ayanamsa, 4),
            "tithi": _tithi_summary(tithi),
            "weekday": market_confluence.get("weekday"),
            "bhadra": _bhadra_for_day(date_str, tz_name),
            "reversal_windows": [{
                "title": w.get("title", ""),
                "level": w.get("level", ""),
                "bias": w.get("bias", ""),
            } for w in (alert.get("windows") or [])[:4]],
            "sun": {"longitude": sun.get("longitude"), "sign": sign_from_lon(sun.get("longitude")), "nakshatra": sun.get("nakshatra")},
            "moon": {"longitude": moon.get("longitude"), "sign": sign_from_lon(moon.get("longitude")), "nakshatra": moon.get("nakshatra")},
            "rahu": {"longitude": rahu.get("longitude"), "sign": sign_from_lon(rahu.get("longitude"))},
            "ketu": {"longitude": ketu.get("longitude"), "sign": sign_from_lon(ketu.get("longitude"))},
            "vedha_net": market_confluence["net"],
            "sector_reads": market_confluence["sectors"],
            "planets": planets,
        })
    except Exception:
        return internal_error()
