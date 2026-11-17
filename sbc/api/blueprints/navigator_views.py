"""Navigator chart-view, dasha, decision, timeline and rule-backtest routes.
Registered on navigator_bp, so the blueprint's access guard, migration hook and
error handlers cover every route here. Birth data stays out of logs and URLs."""
from __future__ import annotations

import datetime as dt
import logging
from typing import Any
from zoneinfo import ZoneInfo

from flask import jsonify, request

from sbc.api.blueprints.navigator_bp import _BadRequest, _arg_id, _require_profile, navigator_bp
from sbc.navigator import chart_view as CV

log = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


def _now_ist() -> dt.datetime:
    return dt.datetime.now(IST).replace(tzinfo=None)


def _only_args(allowed: set[str]) -> None:
    for key in request.args:
        if key not in allowed or len(request.args.getlist(key)) != 1:
            raise _BadRequest("unexpected or repeated parameter")


@navigator_bp.route("/dasha", methods=["GET"])
def dasha() -> Any:
    _only_args({"profile_id"})
    profile_id = _arg_id()
    profile = _require_profile(profile_id)
    return jsonify({"profile_id": profile_id,
                    **CV.dasha_tree(profile, _now_ist().date().isoformat())})
