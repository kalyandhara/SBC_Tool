"""Navigator chart-view, dasha, decision, timeline and rule-backtest routes.
Registered on navigator_bp, so the blueprint's access guard, migration hook and
error handlers cover every route here. Birth data stays out of logs and URLs."""
from __future__ import annotations

import datetime as dt
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
from flask import jsonify, request

from sbc import market_holidays as MH
from sbc.api.blueprints.navigator_bp import (DISCLAIMER, INSTRUMENT, STATUS, _MAX_ID, _BadRequest,
                                             _NotFound, _arg_id, _json_body, _market, _only_args,
                                             _parse_day, _record_failure, _require_profile,
                                             _result_label, _rule_version, _run_body, _version,
                                             navigator_bp)
from sbc.intraday_forecast import build_forecast
from sbc.navigator import chart_view as CV
from sbc.navigator import context as C
from sbc.navigator import decision as D
from sbc.navigator import rule_backtest as R
from sbc.navigator import scoring as S
from sbc.navigator import store
from sbc.navigator.decision import RULE_VERSION
from sbc.navigator.ephemeris import build_sky
from sbc.navigator.profile import chart_hash, natal_points
from sbc.navigator.weights import WEIGHTS_VERSION
from sbc.transit_natal import scan

log = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


def _now_ist() -> dt.datetime:
    return dt.datetime.now(IST).replace(tzinfo=None)


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
        "data_asof": ohlc["date"].iloc[-1], "engine_version": f"{_rule_version()}+{RULE_VERSION}",
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


_CACHE: OrderedDict = OrderedDict()
_CACHE_LOCK = threading.Lock()
_CACHE_MAX, _CACHE_TTL = 32, 900.0
_SIDE = {D.LONG: "long", D.SHORT: "short"}
_NO_WINDOWS = "windows unavailable"


def _cached(key: tuple, build: Callable[[], dict]) -> dict:
    """In-process only: future scores never reach the database (Phase 1 rule)."""
    now = time.monotonic()
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
        if hit and now - hit[0] < _CACHE_TTL:
            _CACHE.move_to_end(key)
            return hit[1]
    value = build()
    with _CACHE_LOCK:
        _CACHE[key] = (now, value)
        _CACHE.move_to_end(key)
        while len(_CACHE) > _CACHE_MAX:
            _CACHE.popitem(last=False)
    return value


@lru_cache(maxsize=16)
def _forecast_ok(day: str) -> dict:
    return C.time_windows(build_forecast(dt.date.fromisoformat(day)))


def _windows(day: str) -> dict:
    try:
        out = _forecast_ok(day)          # failures raise, so they are never cached
    except Exception as exc:
        log.warning("navigator intraday windows unavailable: %s", type(exc).__name__)
        return {"available": False, "text": _NO_WINDOWS}
    if not out.get("available") and not out.get("text"):
        return {**out, "text": _NO_WINDOWS}
    return out


def _view_key(kind: str, profile_id: int, profile, t: str, ohlc, vix) -> tuple:
    """Cache key for a per-day view. VIX can land after NIFTY (as in /score's key) and
    chart_hash drops the label, so both date and label are part of it."""
    return (kind, profile_id, chart_hash(profile), profile.label, t, ohlc["date"].iloc[-1],
            max(vix, default="none"), WEIGHTS_VERSION, D.RULE_VERSION, _version())


def _session_arg() -> str:
    if "day" not in request.args:
        return D.session_for(_now_ist()).isoformat()
    day = _parse_day()
    if not MH.is_trading_day(dt.date.fromisoformat(day)):
        raise _BadRequest("day is not a trading session")
    return day


def _session_series(profile, ohlc, vix, t: str, extra_days: tuple[str, ...] = ()):
    """Rows strictly before t, then t and any later days as unknown sessions. When
    T-1 is the last row, its VIX close is a real input; otherwise Vol is neutral,
    as for any future day (scoring.vol_term reads the previous day's close).
    For a past day already in the data, /score keeps its Phase-1 path (HistVal sees
    T's close only through forward returns, NaN for T); /decision is defined for
    session T, and agreement with /score is required only for T."""
    days_all = ohlc["date"].tolist()
    k = int(np.searchsorted(np.array(days_all), t, side="left"))
    days = days_all[:k]
    fresh = bool(days) and days[-1] == D.previous_trading_day(t)
    vix_in = {d: c for d, c in vix.items() if d < t and (fresh or not days or d != days[-1])}
    tail = [t, *extra_days]
    opens = np.append(ohlc["open"].to_numpy(float)[:k], np.full(len(tail), np.nan))
    closes = np.append(ohlc["close"].to_numpy(float)[:k], np.full(len(tail), np.nan))
    all_days = days + tail
    return S.score_series(build_sky(all_days), profile, opens, closes, vix_in), all_days


def _decision_body(profile, ohlc, vix, t: str) -> dict[str, Any]:
    days = ohlc["date"].tolist()
    closes = ohlc["close"].to_numpy(float)
    inputs = D.inputs_before(days, closes, vix, t)
    series, all_days = _session_series(profile, ohlc, vix, t)
    score = int(series.score[all_days.index(t)])
    band = S.band_of(score)
    covered = MH.is_covered(dt.date.fromisoformat(t))
    stance = D.stance(band, inputs["trend"], inputs["vix"]) if covered else None
    natal = natal_points(profile)
    running = CV.dasha_tree(profile, t)["running"]
    asof = [d for d in days if d < t]
    return {"day": t, "label": _result_label(profile), "is_sample": profile.is_sample,
            "covered": covered,
            "coverage_note": None if covered else f"holiday calendar not covered for {t}",
            "t_minus_1": inputs["t_minus_1"], "data_asof": asof[-1] if asof else None,
            "stale": inputs["stale"], "provisional": inputs["stale"],
            "score": score, "band": band, "stance": stance,
            "side": _SIDE.get(stance["stance"]) if stance else None,
            "confluence": C.rule_items(band, inputs["trend"], inputs["vix"])
                          + C.context_items(natal, t, running),
            "status": STATUS, "disclaimer": DISCLAIMER, "short_cost_note": D.SHORT_COST_NOTE}


def _rule_evidence(profile_id: int, side: str | None) -> dict[str, Any]:
    """Shown on the card. A store failure degrades to "evidence unavailable"."""
    head = f"Rule {D.RULE_VERSION}"
    try:
        run = store.latest_run(profile_id, kind="rule")
    except Exception as exc:  # type only: a message can quote row values
        log.warning("navigator rule evidence unavailable: %s", type(exc).__name__)
        return {"run_id": None, "verdicts": {}, "text": f"{head}: evidence unavailable"}
    if run is None:
        return {"run_id": None, "verdicts": {}, "text": f"{head}: unvalidated: no rule backtest run yet"}
    results = run.get("results") if run.get("status") == "done" else None
    if not isinstance(results, dict):
        return {"run_id": run["id"], "verdicts": {},
                "text": f"{head}: unvalidated: run {run['id']} {run.get('status')}"}
    sides = results.get("sides")
    sides = sides if isinstance(sides, dict) else {}
    verdicts = {s: (v.get("verdict", "unvalidated") if isinstance(v, dict) else "unvalidated")
                for s, v in sides.items()}
    shown = [side] if side else list(verdicts)
    parts = "; ".join(f"{s} side: {verdicts.get(s, 'unvalidated')}" for s in shown)
    text = f"{head}, {parts} (run {run['id']}, data through {run.get('data_asof')})"
    if (run.get("engine_version") != f"{_rule_version()}+{RULE_VERSION}"
            or results.get("rule_version") != D.RULE_VERSION):
        text += ". This run is stale: the rule or its backtest code has changed since"
    return {"run_id": run["id"], "verdicts": verdicts, "text": text}


@navigator_bp.route("/decision", methods=["GET"])
def decision() -> Any:
    _only_args({"profile_id", "day"})
    profile_id = _arg_id()
    profile = _require_profile(profile_id)
    t = _session_arg()
    ohlc, vix = _market()
    key = _view_key("decision", profile_id, profile, t, ohlc, vix)
    body = _cached(key, lambda: _decision_body(profile, ohlc, vix, t))
    return jsonify({**body, "profile_id": profile_id, "windows": _windows(t),
                    "evidence": _rule_evidence(profile_id, body["side"])})


TIMELINE_SESSIONS = 10
_SAV_EVENT = {"highest": max, "lowest": min}


def _next_sessions(t: str, n: int) -> list[str]:
    out, d = [], dt.date.fromisoformat(t)
    while len(out) < n:
        d += dt.timedelta(days=1)
        if MH.is_trading_day(d):
            out.append(d.isoformat())
    return out


def _attach(rows: list[dict], when: str, text: str, t: str) -> None:
    """Into the first row on or after `when`; events on or before T belong to the card."""
    if when <= t:
        return
    for row in rows:
        if row["date"] >= when:
            row["events"].append(text)
            return


SCAN_MARGIN_DAYS = 45


def _scan_range(t: str, last: str) -> tuple[str, str]:
    """Wide enough that the edges of most windows fall inside it (see _timeline_events)."""
    start = dt.date.fromisoformat(t) + dt.timedelta(days=1) - dt.timedelta(days=SCAN_MARGIN_DAYS)
    end = dt.date.fromisoformat(last) + dt.timedelta(days=SCAN_MARGIN_DAYS)
    return start.isoformat(), end.isoformat()


def _timeline_events(rows: list[dict], windows: list[dict], dasha: list[tuple[str, str]],
                     t: str, last: str) -> None:
    """Attach transit and dasha events to `rows` for dates in (t, last].

    A window clipped by the scan range reports the range edge as its entry (00:00) or exit
    (23:59), so a clipped start never yields "enters orb", a clipped end never yields
    "leaves orb", and an exact sitting on a clipped edge is not a true closest approach.
    """
    r0, r1 = _scan_range(t, last)

    def put(when: str, text: str) -> None:
        if when <= last:
            _attach(rows, when, text, t)

    for w in windows:
        name = f"{w['planet']} {w['aspect_name']} natal {w['natal']}"
        if not w["starts_before_range"]:
            put(w["entry_date"], f"{name} enters orb")
        at_start = w["starts_before_range"] and w["exact_date"] == r0 and w["exact_time"] == "00:00"
        at_end = w["ends_after_range"] and w["exact_date"] == r1 and w["exact_time"] == "23:59"
        if not (at_start or at_end):
            put(w["exact_date"], f"{name} exact")
        if not w["ends_after_range"]:
            put(w["exit_date"], f"{name} leaves orb")
    for when, text in dasha:
        put(when, text)


def _dasha_starts(profile, t: str, end: str) -> list[tuple[str, str]]:
    out = []
    for maha in CV.dasha_tree(profile, t)["periods"]:
        for antar in maha["children"]:
            if t < antar["start"] <= end:
                out.append((antar["start"], f"Antardasha {maha['lord']}/{antar['lord']} begins"))
            for praty in antar["children"]:
                if t < praty["start"] <= end:
                    out.append((praty["start"], f"Pratyantar {antar['lord']}/{praty['lord']} begins"))
    return out


def _moon_sign(day: str) -> int:
    moon = next(p["longitude"] for p in C.sky_at(day) if p["name"] == "Moon")
    return int(moon % 360 // 30)


def _timeline_body(profile, ohlc, vix, t: str) -> dict[str, Any]:
    days = ohlc["date"].tolist()
    inputs = D.inputs_before(days, ohlc["close"].to_numpy(float), vix, t)
    sessions = _next_sessions(t, TIMELINE_SESSIONS)
    series, all_days = _session_series(profile, ohlc, vix, t, tuple(sessions))
    rows = []
    for d in sessions:
        score = int(series.score[all_days.index(d)])
        band = S.band_of(score)
        covered = MH.is_covered(dt.date.fromisoformat(d))
        # Stance shows on uncovered rows because the timeline is provisional and each row is
        # labelled; the Today card withholds the stance instead.
        st = D.stance(band, inputs["trend"], inputs["vix"])
        rows.append({"date": d, "score": score, "band": band, "stance": st["stance"],
                     "multiplier": st["multiplier"],
                     "provisional_note": f"provisional: trend as of {inputs['t_minus_1']}",
                     "covered": covered,
                     "coverage_note": None if covered else "holiday calendar not covered: assumed a session",
                     "events": []})
    natal = natal_points(profile)
    _timeline_events(rows, scan(natal, *_scan_range(t, sessions[-1])),
                     _dasha_starts(profile, t, sessions[-1]), t, sessions[-1])
    sav = C.chart_sav(natal)
    marks = {kind: {s for s in range(12) if sav[s] == pick(sav)} for kind, pick in _SAV_EVENT.items()}
    previous = _moon_sign(t)
    for row in rows:
        sign = _moon_sign(row["date"])
        for kind, signs in marks.items():
            if sign in signs and sign != previous:
                row["events"].append(f"Moon in {CV.RASHIS[sign]} (SAV {sav[sign]}, {kind})")
        previous = sign
    return {"day": t, "frozen_asof": inputs["t_minus_1"], "rows": rows, "disclaimer": DISCLAIMER}


@navigator_bp.route("/timeline", methods=["GET"])
def timeline() -> Any:
    _only_args({"profile_id", "day"})
    profile_id = _arg_id()
    profile = _require_profile(profile_id)
    t = _session_arg()
    ohlc, vix = _market()
    key = _view_key("timeline", profile_id, profile, t, ohlc, vix)
    return jsonify({**_cached(key, lambda: _timeline_body(profile, ohlc, vix, t)), "profile_id": profile_id})
