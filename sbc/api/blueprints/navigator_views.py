"""Navigator chart-view, dasha, decision, timeline and rule-backtest routes.
Registered on navigator_bp, so the blueprint's access guard, migration hook and
error handlers cover every route here. Birth data stays out of logs and URLs."""
from __future__ import annotations

import datetime as dt
import logging
import threading
from typing import Any
from zoneinfo import ZoneInfo

from flask import jsonify, request

from sbc.api.blueprints.navigator_bp import (INSTRUMENT, _MAX_ID, _BadRequest, _NotFound, _arg_id,
                                             _json_body, _market, _record_failure, _require_profile,
                                             _run_body, _version, navigator_bp)
from sbc.navigator import chart_view as CV
from sbc.navigator import rule_backtest as R
from sbc.navigator import store
from sbc.navigator.decision import RULE_VERSION
from sbc.navigator.profile import chart_hash
from sbc.navigator.weights import WEIGHTS_VERSION

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


class _Expired(Exception):
    """The run was marked failed while this thread still held it."""


def _rule_job(run_id: int, profile, ohlc, vix) -> None:
    def progress(_done, _total):
        if not store.heartbeat(run_id):
            raise _Expired

    try:
        progress(0, 0)
        results = R.run(profile, ohlc, vix, on_progress=progress)
        folds = results.pop("folds", [])
        store.finish_run(run_id, results, folds)
    except _Expired:
        log.info("navigator rule run %s stopped: no longer active", run_id)
    except Exception as exc:  # a thread has no caller: anything uncaught is a silent hang
        log.error("navigator rule run %s failed: %s", run_id, type(exc).__name__)
        _record_failure(run_id)


@navigator_bp.route("/rule-backtest", methods=["POST"])
def rule_backtest_start() -> Any:
    body = _json_body("profile_id must be a positive integer")
    profile_id = body.get("profile_id") if body is not None else None
    if isinstance(profile_id, bool) or not isinstance(profile_id, int) or not 0 < profile_id < _MAX_ID:
        raise _BadRequest("profile_id must be a positive integer")
    profile = _require_profile(profile_id)
    ohlc, vix = _market()
    store.expire_stale()
    run_id, is_new = store.start_run(profile_id, {
        "instrument": INSTRUMENT, "weights_version": WEIGHTS_VERSION,
        "data_asof": ohlc["date"].iloc[-1], "engine_version": f"{_version()}+{RULE_VERSION}",
        "chart_hash": chart_hash(profile), "params": R.DEFAULT_PARAMS}, kind="rule")
    if is_new:
        try:
            threading.Thread(target=_rule_job, args=(run_id, profile, ohlc, vix), daemon=True,
                             name=f"navigator-rule-run-{run_id}").start()
        except Exception as exc:  # left active, the run would block this profile until it expires
            log.error("navigator rule run %s did not start: %s", run_id, type(exc).__name__)
            _record_failure(run_id)
            return jsonify({"error": "The rule backtest could not start. Try again."}), 500
    return jsonify({"run_id": run_id, "is_new": is_new}), 202


@navigator_bp.route("/rule-backtest/<int:run_id>", methods=["GET"])
def rule_backtest_read(run_id: int) -> Any:
    if run_id >= _MAX_ID:
        raise _NotFound("Run not found")
    store.expire_stale()
    run = store.get_run(run_id)
    if run is None or run.get("kind") != "rule":
        raise _NotFound("Run not found")
    return _run_body(run)


# A static segment: <int:run_id> never matches "latest", so the two cannot clash.
@navigator_bp.route("/rule-backtest/latest", methods=["GET"])
def rule_backtest_latest() -> Any:
    _only_args({"profile_id"})
    profile_id = _arg_id()
    _require_profile(profile_id)
    store.expire_stale()
    run = store.latest_run(profile_id, kind="rule")
    if run is None:
        return jsonify({"run": None})
    return _run_body(run)
