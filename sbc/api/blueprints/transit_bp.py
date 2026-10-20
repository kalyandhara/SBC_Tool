"""Transit report endpoints: city autocomplete and the Excel workbook.

    GET /api/transits/cities?q=dubai            -> {results: [...]}
    GET /api/transits/report?city=Mumbai&...    -> xlsx download

Report query params: city, start, end (YYYY-MM-DD), planets (csv),
types (csv: sign,nakshatra,pada), ayanamsa (lahiri|kp|raman),
node_mode (mean|true).  Bad input is normalized; unparseable dates
return 400.
"""

from flask import Blueprint, jsonify, request, send_file

from sbc import cities
from sbc.transit_report import build_workbook

XLSX_MIME = ("application/vnd.openxmlformats-officedocument."
             "spreadsheetml.sheet")

transit_bp = Blueprint("transits", __name__, url_prefix="/api/transits")


@transit_bp.get("/cities")
def cities_lookup():
    q = (request.args.get("q") or "").strip()
    try:
        limit = int(request.args.get("limit", 8))
    except ValueError:
        limit = 8
    return jsonify({"results": cities.search(q, limit=limit)})


@transit_bp.get("/report")
def report():
    def csv_list(key, allowed=None):
        raw = (request.args.get(key) or "").strip()
        if not raw:
            return None
        items = [x.strip() for x in raw.split(",") if x.strip()]
        if allowed is not None:
            items = [x for x in items if x in allowed]
        return items or None

    try:
        config = {
            "city": request.args.get("city", "Mumbai"),
            "start": request.args.get("start", ""),
            "end": request.args.get("end", ""),
            "planets": csv_list("planets"),
            "types": csv_list("types"),
            "ayanamsa": request.args.get("ayanamsa", "lahiri"),
            "node_mode": request.args.get("node_mode", "mean"),
        }
        buf, name = build_workbook(config)
    except (ValueError, KeyError) as exc:
        return jsonify({"error": f"bad report request: {exc}"}), 400
    return send_file(buf, as_attachment=True, download_name=name,
                     mimetype=XLSX_MIME)
