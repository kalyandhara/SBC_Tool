"""Ashtakavarga blueprint: live, descriptive BAV/SAV for an anchor plus 09:15 IST transits.

Parameters are allow-listed (400 otherwise); nothing from the request reaches a path, SQL or a shell.
"""

import datetime as dt
import re

from flask import Blueprint, abort, jsonify, request

from sbc import ashtakavarga as av
from sbc.api.errors import internal_error
from sbc.engine import ANCHORS
from sbc.helio_aspects import IST
from sbc.nakshatra import RASHIS

ashtakavarga_bp = Blueprint("ashtakavarga", __name__, url_prefix="")

PARAMS = {"anchor", "date", "lagna_mode"}
DATE_MIN, DATE_MAX = dt.date(1900, 1, 1), dt.date(2100, 12, 31)


def _date(raw: str | None) -> dt.date:
    if raw is None:
        return dt.datetime.now(IST).date()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw, flags=re.ASCII):
        abort(400)
    try:
        day = dt.date.fromisoformat(raw)
    except ValueError:
        abort(400)
    if not DATE_MIN <= day <= DATE_MAX:
        abort(400)
    return day


@ashtakavarga_bp.route("/api/ashtakavarga")
def ashtakavarga():
    multi = request.args.to_dict(flat=False)
    if set(multi) - PARAMS or any(len(v) > 1 for v in multi.values()):
        abort(400)
    anchor = request.args.get("anchor", "nifty")
    lagna_mode = request.args.get("lagna_mode", "auto")
    if anchor not in ANCHORS or lagna_mode not in av.MODES:
        abort(400)
    day = _date(request.args.get("date"))
    try:
        res = av.transit_scores(anchor, day, lagna_mode)
        n = res["natal"]
        body = {
            "anchor": anchor, "anchor_name": ANCHORS[anchor]["name"],
            "anchor_note": ANCHORS[anchor]["note"], "anchors": list(ANCHORS),
            "date": res["date"], "transit_time": res["transit_time"],
            "mode": n["mode"], "lagna_reliable": n["lagna_reliable"],
            "lagna_reason": n["lagna_reason"],
            "ambiguous_contributors": n["ambiguous_contributors"],
            "status": "experimental", "signs": list(RASHIS),
            "natal": {"max_per_sign": n["max_per_sign"], "bav": n["bav"], "sav": n["sav"]},
            "transit": res["transit"],
        }
    except Exception:  # noqa: BLE001 - generic 500, traceback logged by internal_error
        return internal_error("ashtakavarga calculation failed")
    return jsonify(body)
