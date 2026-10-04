"""Birth-data profiles, habits, time zones and city search.

Moved out of app.py (B-16).
"""

import datetime
import json

from flask import Blueprint, jsonify, request

from sbc import db as profiles_db
from sbc.api.errors import internal_error

profile_bp = Blueprint('profile', __name__)


@profile_bp.route("/api/habits/log", methods=["POST"])
def api_habits_log():
    try:
        data = request.get_json() or {}
        user_key = request.headers.get("X-User-Key", "default")
        habit_type = data.get("habit_type")
        log_date = data.get("date")
        if not habit_type or not log_date:
            return jsonify({"error":"habit_type and date required"}),400
        import datetime
        conn = profiles_db.connect()
        cur = conn.cursor()
        cur.execute("INSERT INTO habit_logs(user_key, habit_type, log_date, created_at) VALUES(?,?,?,?)",
                    (user_key, habit_type, log_date, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({"status":"logged"})
    except Exception:
        return internal_error()


@profile_bp.route("/api/habits/streaks", methods=["GET"])
def api_habits_streaks():
    try:
        user_key = request.args.get("user_key","default")
        import datetime as dt
        conn = profiles_db.connect()
        cur = conn.cursor()
        cur.execute("SELECT habit_type, log_date FROM habit_logs WHERE user_key=?", (user_key,))
        rows = cur.fetchall()
        conn.close()
        from collections import defaultdict
        logs = defaultdict(set)
        for h,d in rows:
            logs[h].add(d)
        result = {}
        for h, dates_set in logs.items():
            dates = sorted(dates_set, reverse=True)
            dset = {dt.date.fromisoformat(d) for d in dates_set}
            streak = 0
            if dates:
                cur_day = max(dset)
                while cur_day in dset:
                    streak += 1
                    cur_day -= dt.timedelta(days=1)
            result[h] = {"streak": streak, "last": dates[0] if dates else None, "count": len(dates_set)}
        return jsonify(result)
    except Exception:
        return internal_error()


@profile_bp.route("/api/habits/history", methods=["GET"])
def api_habits_history():
    try:
        user_key = request.args.get("user_key","default")
        days = int(request.args.get("days","7"))
        import datetime as dt
        conn = profiles_db.connect()
        cur = conn.cursor()
        # Get logs for last N days
        start_date = (dt.date.today() - dt.timedelta(days=days-1)).isoformat()
        cur.execute("SELECT habit_type, log_date, COUNT(*) FROM habit_logs WHERE user_key=? AND log_date>=? GROUP BY habit_type, log_date", (user_key, start_date))
        rows = cur.fetchall()
        conn.close()
        history: dict = {}
        for h,d,c in rows:
            history.setdefault(h, {})[d] = c
        return jsonify(history)
    except Exception:
        return internal_error()


@profile_bp.route("/api/astro/profile/export", methods=["GET"])
def api_astro_profile_export():
    try:
        user_key = request.args.get("user_key", "default")
        conn = profiles_db.connect()
        cur = conn.cursor()
        cur.execute("SELECT id, data, created_at, name, is_default FROM profiles WHERE user_key=?", (user_key,))
        rows = cur.fetchall()
        conn.close()
        export = [{"id": r[0], "data": json.loads(r[1]), "created_at": r[2], "name": r[3], "is_default": bool(r[4])} for r in rows]
        return jsonify(export)
    except Exception:
        return internal_error()


@profile_bp.route("/api/astro/profile/import", methods=["POST"])
def api_astro_profile_import():
    try:
        user_key = request.headers.get("X-User-Key", "default")
        incoming = request.get_json() or []
        conn = profiles_db.connect()
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
    except Exception:
        return internal_error()


@profile_bp.route("/api/astro/profile", methods=["POST"])
def api_astro_profile_save():
    try:
        data = request.get_json() or {}
        user_key = request.headers.get("X-User-Key", "default")
        import datetime
        conn = profiles_db.connect()
        cur = conn.cursor()
        cur.execute("INSERT INTO profiles(user_key, data, created_at) VALUES(?,?,?)",
                    (user_key, json.dumps(data), datetime.datetime.utcnow().isoformat()))
        conn.commit()
        pid = cur.lastrowid
        conn.close()
        return jsonify({"id": pid, "status": "saved"})
    except Exception:
        return internal_error()


@profile_bp.route("/api/astro/profile/<int:pid>", methods=["PUT"])
def api_astro_profile_update(pid):
    try:
        data = request.get_json() or {}
        name = data.get("name")
        conn = profiles_db.connect()
        cur = conn.cursor()
        if name is not None:
            cur.execute("UPDATE profiles SET name=? WHERE id=?", (name, pid))
        conn.commit()
        conn.close()
        return jsonify({"status":"updated"})
    except Exception:
        return internal_error()


@profile_bp.route("/api/astro/profile/<int:pid>/default", methods=["POST"])
def api_astro_profile_set_default(pid):
    try:
        conn = profiles_db.connect()
        cur = conn.cursor()
        cur.execute("UPDATE profiles SET is_default=0 WHERE is_default=1")
        cur.execute("UPDATE profiles SET is_default=1 WHERE id=?", (pid,))
        conn.commit()
        conn.close()
        return jsonify({"status":"default_set"})
    except Exception:
        return internal_error()


@profile_bp.route("/api/astro/profile/<int:pid>", methods=["DELETE"])
def api_astro_profile_delete(pid):
    try:
        conn = profiles_db.connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM profiles WHERE id=?", (pid,))
        conn.commit()
        conn.close()
        return jsonify({"status":"deleted"})
    except Exception:
        return internal_error()


@profile_bp.route("/api/astro/profile", methods=["GET"])
def api_astro_profile_load():
    try:
        user_key = request.args.get("user_key", "default")
        conn = profiles_db.connect()
        cur = conn.cursor()
        cur.execute("SELECT id, data, created_at, name, is_default FROM profiles WHERE user_key=? ORDER BY is_default DESC, id DESC", (user_key,))
        rows = cur.fetchall()
        conn.close()
        profiles = [{"id": r[0], "data": json.loads(r[1]), "created_at": r[2], "name": r[3], "is_default": bool(r[4])} for r in rows]
        return jsonify(profiles)
    except Exception:
        return internal_error()


@profile_bp.route("/api/tz/offset", methods=["GET"])
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
        offset = dt_local.utcoffset() or datetime.timedelta(0)
        total_minutes = int(offset.total_seconds() // 60)
        hours = total_minutes // 60
        mins = abs(total_minutes % 60)
        return jsonify({"tz": tz_name, "offset_minutes": total_minutes, "offset_hours": hours, "offset_mins": mins if total_minutes>=0 else -mins})
    except (ValueError, KeyError):  # malformed date/time, unknown tz (ZoneInfoNotFoundError)
        return jsonify({"error": "invalid tz, date or time"}), 400
    except Exception:
        return internal_error()


@profile_bp.route("/api/tz/from_coords", methods=["GET"])
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
    except ValueError:  # non-numeric or out-of-range lat/lon
        return jsonify({"error": "invalid lat/lon"}), 400
    except Exception:
        return internal_error()


@profile_bp.route("/api/cities/search", methods=["GET"])
def api_cities_search():
    """City lookup for birth data: ?q= (2+ chars) &country= (name, ISO code or USA) &limit= (1-50).

    Backed by data/cities.db (GeoNames cities >= 15,000 people; scripts/seed_cities.py).
    """
    from sbc import cities

    try:
        limit = int(request.args.get("limit", "20"))
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400
    return jsonify(cities.search(request.args.get("q", ""), request.args.get("country", ""), limit))

