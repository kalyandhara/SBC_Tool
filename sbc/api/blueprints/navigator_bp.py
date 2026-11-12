"""AstroTrade Navigator routes.

Birth data stays out of logs and URLs: failures are logged by exception type only,
because a message can quote the values. chart_hash is a cache key, never a response
field. Postgres is touched on first request only, so the app boots without it.
"""
from __future__ import annotations

import datetime as dt
import hmac
import logging
import os
import re
import threading
import time
from collections import OrderedDict
from dataclasses import asdict
from functools import lru_cache
from typing import Any, cast
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from flask import Blueprint, jsonify, request
from werkzeug.exceptions import HTTPException

from sbc import market_store
from sbc import nakshatra as N
from sbc.engine_version import module_version
from sbc.navigator import analogs as A
from sbc.navigator import backtest as B
from sbc.navigator import scoring as S
from sbc.navigator import signature as G
from sbc.navigator import store
from sbc.navigator.ephemeris import build_sky
from sbc.navigator.profile import Profile, chart_hash, natal_points, validate
from sbc.navigator.weights import WEIGHTS_VERSION

log = logging.getLogger(__name__)
navigator_bp = Blueprint("navigator", __name__, url_prefix="/api/navigator")

INSTRUMENT, VIX_SYMBOL = "NIFTY", "INDIAVIX"
STATUS = "unvalidated research output"
DISCLAIMER = ("Action labels are unvalidated research output, not personal financial advice. "
              "Scores use hand-set weights.")
RUN_FAILED = "The backtest failed. Check the server and start a new run."
_DOWN = "Navigator database is unavailable. Start Postgres and retry."
_NO_MARKET = "Market data is unavailable. Refresh market data and retry."
RUN_NOT_STARTED = "The backtest could not start. Try again."
_PROXY = ("X-Forwarded-For", "X-Forwarded-Proto", "X-Forwarded-Host", "X-Forwarded-Server",
          "X-Real-IP", "Forwarded", "Via", "True-Client-IP", "CF-Connecting-IP", "X-Client-IP",
          "X-Cluster-Client-IP", "X-Original-Forwarded-For", "Fastly-Client-IP")
_LOCAL_AUTHORITY = r"(?:localhost|127\.0\.0\.1|\[::1\])(?::([0-9]{1,5}))?"
_HOST_RE = re.compile(_LOCAL_AUTHORITY, re.ASCII)
_ORIGIN_RE = re.compile(r"https?://" + _LOCAL_AUTHORITY, re.ASCII)
_RUN_FIELDS = ("id", "profile_id", "instrument", "weights_version", "data_asof", "status",
               "error", "params", "folds", "results", "created_at")
_DAY_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_ID_RE = re.compile(r"[0-9]{1,18}")     # 18 digits always fit Postgres BIGINT
_MAX_ID = 10 ** 18
_MAX_DAY = dt.date(2100, 12, 31)        # the Vimshottari and ephemeris range the app supports

_migrated = False
_migrate_lock = threading.Lock()


class _BadRequest(Exception):
    """Fixed-message 400; never carries client input."""


class _NotFound(Exception):
    pass


class _NoMarketData(Exception):
    pass


class _Expired(Exception):
    """The run was marked failed while this thread still held it."""


def _local_authority(pattern: re.Pattern, value: str) -> bool:
    match = pattern.fullmatch(value.lower())
    return match is not None and int(match.group(1) or 0) <= 65535


def _local_browser_context() -> bool:
    """Refuses DNS rebinding: a rebound name reaches the loopback listener from a
    hostile page, so the peer address alone proves nothing. Same-origin GETs send
    no Origin, so an absent one passes."""
    origin = request.headers.get("Origin")
    return (_local_authority(_HOST_RE, request.headers.get("Host", ""))
            and (origin is None or _local_authority(_ORIGIN_RE, origin)))


@navigator_bp.before_request
def _guard():
    from sbc.app_factory import _LOCAL_ADDRS  # app_factory imports this module's package

    token = os.environ.get("SBC_API_TOKEN", "").strip()
    if token:
        supplied = request.headers.get("X-API-Token", "")
        # Bytes: compare_digest raises TypeError on non-ASCII str.
        if supplied and hmac.compare_digest(supplied.encode(), token.encode()):
            return None
        return jsonify({"error": "a valid X-API-Token header is required"}), 401
    if (request.remote_addr in _LOCAL_ADDRS and not any(h in request.headers for h in _PROXY)
            and _local_browser_context()):
        return None
    return jsonify({"error": "navigator is local-only until SBC_API_TOKEN is set"}), 403


@navigator_bp.before_request
def _ensure_migrated():
    global _migrated
    if _migrated:
        return
    with _migrate_lock:
        if not _migrated:
            store.migrate()
            _migrated = True


@navigator_bp.errorhandler(store.StoreUnavailable)
def _store_down(_):
    return jsonify({"error": _DOWN}), 503


@navigator_bp.errorhandler(_NoMarketData)
def _market_down(_):
    return jsonify({"error": _NO_MARKET}), 503


@navigator_bp.errorhandler(_BadRequest)
def _bad_request(exc):
    return jsonify({"error": str(exc)}), 400


@navigator_bp.errorhandler(_NotFound)
def _not_found(exc):
    return jsonify({"error": str(exc)}), 404


@navigator_bp.errorhandler(Exception)
def _failed(exc):
    if isinstance(exc, HTTPException):
        return exc
    log.error("navigator request failed: %s", type(exc).__name__)
    return jsonify({"error": "The navigator request failed."}), 500


@lru_cache(maxsize=1)
def _version() -> str:
    # The navigator closure, which includes sbc.engine. engine_version() would hash
    # the prediction series instead and miss a change to the scoring code.
    return module_version("sbc.navigator.backtest")


def _arg_id() -> int:
    raw = request.args.get("profile_id", "")
    if not _ID_RE.fullmatch(raw) or int(raw) == 0:
        raise _BadRequest("profile_id must be a positive integer")
    return int(raw)


def _json_body(message: str) -> dict[str, Any] | None:
    try:
        body = request.get_json(silent=True)
    except RecursionError:  # silent covers ValueError only
        raise _BadRequest(message) from None
    return body if isinstance(body, dict) else None


def _require_profile(profile_id: int) -> Profile:
    # Checked first: a bad id would otherwise reach a foreign key and read as a 503.
    profile = store.get_profile(profile_id)
    if profile is None:
        raise _NotFound("Profile not found")
    return profile


def _result_label(profile: Profile) -> str:
    return B.label_for(profile.is_sample)


def _market() -> tuple[pd.DataFrame, dict[str, Any]]:
    """(daily bars, VIX closes), each only up to the last NIFTY session with a close."""
    bars = market_store.get_daily(INSTRUMENT)
    if not bars:
        raise _NoMarketData
    ohlc = pd.DataFrame(bars)
    closed = ohlc.index[ohlc["close"].notna()]
    if closed.empty:
        raise _NoMarketData
    ohlc = ohlc.loc[:closed[-1]].copy()
    ohlc["date"] = ohlc["date"].str[:10]
    asof = ohlc["date"].iloc[-1]
    # Every close: the first sessions need VIX history from before them.
    vix = {r["date"][:10]: r["close"] for r in market_store.get_daily(VIX_SYMBOL)
           if r["close"] is not None and r["date"][:10] <= asof}
    return ohlc, vix


def _parse_day() -> str:
    raw = request.args.get("day")
    if raw is None:
        return dt.datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    day = None
    if _DAY_RE.fullmatch(raw):
        try:
            day = dt.date.fromisoformat(raw)
        except ValueError:
            pass
    if day is None or day > _MAX_DAY:
        raise _BadRequest("day must be a valid YYYY-MM-DD date")
    return raw


def _compute(profile: Profile, ohlc: pd.DataFrame, vix: dict[str, Any], day: str, future: bool) -> dict[str, Any]:
    days = ohlc["date"].tolist()
    opens, closes = ohlc["open"].to_numpy(float), ohlc["close"].to_numpy(float)
    if future:
        # Appended next to the last session, so T-1 would read as data_asof however
        # far ahead the day is. Dropping that close leaves Vol neutral and flagged.
        vix = {d: c for d, c in vix.items() if d != days[-1]}
        days = days + [day]
        opens, closes = np.append(opens, np.nan), np.append(closes, np.nan)
    series = S.score_series(build_sky(days), profile, opens, closes, vix)
    i = days.index(day)
    score = int(series.score[i])
    band = S.band_of(score)
    return cast(dict[str, Any], B.clean_json({"score": score, "band": band,
                                               "action": S.action_of(band),
                                               "lineage": S.day_lineage(series, i)}))


def _latest_verdict(profile_id: int) -> dict[str, Any]:
    """The verdict shown beside the action label. A store failure here must not
    fail the score, so it degrades to "verdict unavailable". chart_hash stays out."""
    try:
        run = store.latest_run(profile_id)
    except Exception as exc:  # type only: a message can quote row values
        log.warning("navigator latest verdict unavailable: %s", type(exc).__name__)
        return {"available": False, "run_id": None, "verdict": None, "status": None,
                "data_asof": None, "stale": False, "text": "verdict unavailable"}
    if run is None:
        return {"available": True, "run_id": None, "verdict": None, "status": None,
                "data_asof": None, "stale": False, "text": "no backtest yet"}
    results: dict[str, Any] = (cast(dict[str, Any], run.get("results"))
                                if isinstance(run.get("results"), dict) else {})
    verdict = results.get("verdict") if run.get("status") == "done" else None
    stale = (run.get("weights_version") != WEIGHTS_VERSION
             or run.get("engine_version") != _version())
    text = (f"Latest backtest (run {run['id']}, data through {run.get('data_asof')}): "
            + (verdict if verdict else f"no verdict, run {run.get('status')}"))
    if stale:
        text += ". This run is stale: the weights or engine have changed since"
    return {"available": True, "run_id": run["id"], "verdict": verdict,
            "status": run.get("status"), "data_asof": run.get("data_asof"),
            "stale": bool(stale), "text": text}


def _vol_neutral(lineage: dict[str, Any]) -> bool:
    return any(f.get("neutral") for c in lineage["contributions"] if c["term"] == "vol"
               for f in c.get("factors", []))


@navigator_bp.route("/profile", methods=["GET"])
def profile_read() -> Any:
    if "profile_id" in request.args:
        profile = _require_profile(_arg_id())
        return jsonify(asdict(profile))
    store.ensure_sample()
    return jsonify({"profiles": store.list_profiles()})


@navigator_bp.route("/profile", methods=["POST"])
def profile_create() -> Any:
    body = _json_body("invalid birth data")
    if not isinstance(body, dict):
        raise _BadRequest("invalid birth data")
    # Only the seeded chart is a sample: is_sample is never taken from a client.
    fields = {k: v for k, v in body.items() if k != "is_sample"}
    try:
        profile = validate(fields)
    except ValueError:
        profile = None
    if profile is None:
        raise _BadRequest("invalid birth data")
    return jsonify({"id": store.create_profile(profile), "label": profile.label,
                    "is_sample": False}), 201


@navigator_bp.route("/chart", methods=["GET"])
def chart() -> Any:
    profile_id = _arg_id()
    profile = _require_profile(profile_id)
    points = []
    for name, lon in natal_points(profile).items():
        lon = float(lon) % 360.0
        nakshatra, pada = N.nakshatra_of(lon)
        points.append({"name": name, "longitude": round(lon, 4), "sign": N.RASHIS[int(lon // 30)],
                       "degree": round(lon % 30, 4), "nakshatra": nakshatra, "pada": pada})
    return jsonify({"profile_id": profile_id, "label": profile.label,
                    "is_sample": profile.is_sample, "points": points})


@navigator_bp.route("/score", methods=["GET"])
def score() -> Any:
    profile_id, day = _arg_id(), _parse_day()
    profile = _require_profile(profile_id)
    ohlc, vix = _market()
    asof = ohlc["date"].iloc[-1]
    future = day > asof
    if not future and day not in set(ohlc["date"]):
        raise _BadRequest("day is not a market session")
    # The VIX date sits in engine_version, the key's free text column: data_asof
    # follows NIFTY alone, so a VIX backfill would otherwise hit the old row.
    key = {"profile_id": profile_id, "day": day, "weights_version": WEIGHTS_VERSION,
           "data_asof": asof, "engine_version": f"{_version()}+vix:{max(vix, default='none')}",
           "chart_hash": chart_hash(profile)}
    row = None if future else store.cached_score(key)
    cached = row is not None
    if not cached:
        row = _compute(profile, ohlc, vix, day, future)
        if not future and not _vol_neutral(row["lineage"]):  # neutral may just mean VIX is late
            store.save_score(key, row)
    if row is None:
        raise RuntimeError("score computation returned no result")
    return jsonify({"profile_id": profile_id, "day": day, "data_asof": asof,
                    "weights_version": WEIGHTS_VERSION, "is_sample": profile.is_sample,
                    "label": _result_label(profile), "score": int(row["score"]),
                    "band": row["band"], "action": row["action"], "status": STATUS,
                    "disclaimer": DISCLAIMER, "lineage": row["lineage"], "future": future,
                    "vol_neutral": _vol_neutral(row["lineage"]), "cached": cached,
                    "latest_verdict": _latest_verdict(profile_id)})


def _record_failure(run_id: int) -> None:
    try:
        store.fail_run(run_id, RUN_FAILED)
    except Exception as exc:  # type only: a message can quote row values
        log.error("navigator run %s: could not record the failure: %s", run_id, type(exc).__name__)


def _job(run_id: int, profile: Profile, ohlc: pd.DataFrame, vix: dict) -> None:
    def progress(_done, _total):
        if not store.heartbeat(run_id):
            raise _Expired

    try:
        progress(0, 0)
        results = B.clean_json(B.run(profile, ohlc, vix, on_progress=progress))
        folds = results.pop("folds", [])
        store.finish_run(run_id, results, folds)
    except _Expired:
        log.info("navigator run %s stopped: no longer active", run_id)
    except Exception as exc:  # a thread has no caller: anything uncaught is a silent hang
        log.error("navigator run %s failed: %s", run_id, type(exc).__name__)
        _record_failure(run_id)


def _start_job(run_id: int, profile: Profile, ohlc: pd.DataFrame, vix: dict) -> None:
    threading.Thread(target=_job, args=(run_id, profile, ohlc, vix), daemon=True,
                     name=f"navigator-run-{run_id}").start()


@navigator_bp.route("/backtest", methods=["POST"])
def backtest_start() -> Any:
    body = _json_body("profile_id must be a positive integer")
    profile_id = body.get("profile_id") if body is not None else None
    if isinstance(profile_id, bool) or not isinstance(profile_id, int) or not 0 < profile_id < _MAX_ID:
        raise _BadRequest("profile_id must be a positive integer")
    profile = _require_profile(profile_id)
    ohlc, vix = _market()
    store.expire_stale()
    run_id, is_new = store.start_run(profile_id, {
        "instrument": INSTRUMENT, "weights_version": WEIGHTS_VERSION,
        "data_asof": ohlc["date"].iloc[-1], "engine_version": _version(),
        "chart_hash": chart_hash(profile), "params": B.DEFAULT_PARAMS})
    if is_new:
        try:
            _start_job(run_id, profile, ohlc, vix)
        except Exception as exc:  # left active, the run would block this profile until it expires
            log.error("navigator run %s did not start: %s", run_id, type(exc).__name__)
            _record_failure(run_id)
            return jsonify({"error": RUN_NOT_STARTED}), 500
    return jsonify({"run_id": run_id, "is_new": is_new}), 202


def _run_body(run: dict[str, Any]) -> Any:
    profile = _require_profile(int(run["profile_id"]))
    return jsonify({**{k: run[k] for k in _RUN_FIELDS}, "is_sample": profile.is_sample,
                    "label": _result_label(profile), "status_note": STATUS,
                    "disclaimer": DISCLAIMER})


@navigator_bp.route("/backtest/<int:run_id>", methods=["GET"])
def backtest_read(run_id: int) -> Any:
    if run_id >= _MAX_ID:
        raise _NotFound("Run not found")
    store.expire_stale()
    run = store.get_run(run_id)
    if run is None:
        raise _NotFound("Run not found")
    return _run_body(run)


# A static segment: <int:run_id> never matches "latest", so the two cannot clash.
@navigator_bp.route("/backtest/latest", methods=["GET"])
def backtest_latest() -> Any:
    profile_id = _arg_id()
    _require_profile(profile_id)
    store.expire_stale()
    run = store.latest_run(profile_id)
    if run is None:
        return jsonify({"run": None})   # a known profile with no run yet is not an error
    return _run_body(run)


ANALOGS_BUSY = "Another similar-dates computation is running. Try again shortly."
_BAD_DAYS = "days must be an integer from 5 to 60"
_DAYS_RE = re.compile(r"[0-9]{1,2}")
_ANALOG_CACHE_SIZE = 8
_analog_lock = threading.Lock()          # single flight: one computation per process
_analog_cache_lock = threading.Lock()   # short lock around cache reads and writes only
_analog_cache: OrderedDict = OrderedDict()   # only read or written while _analog_cache_lock is held


@lru_cache(maxsize=1)
def _analog_version() -> str:
    # Closure of analogs.py (includes signature.py); _version() covers only backtest.
    return module_version("sbc.navigator.analogs")


def _arg_days() -> int:
    raw = request.args.get("days", "30")
    if not _DAYS_RE.fullmatch(raw) or not 5 <= int(raw) <= 60:
        raise _BadRequest(_BAD_DAYS)
    return int(raw)


@navigator_bp.route("/analogs", methods=["GET"])
def analogs() -> Any:
    days = _arg_days()
    profile_id = _arg_id()
    profile = _require_profile(profile_id)
    try:
        market = A.load_market()
    except market_store.MarketDataMissing:
        raise _NoMarketData from None
    # chart_hash keys the cache only; it never enters the response.
    key = (profile_id, chart_hash(profile), market.dates[-1], G.ANALOG_VERSION, _version(), _analog_version(), days)
    with _analog_cache_lock:
        result = _analog_cache.get(key)
        if result is not None:
            _analog_cache.move_to_end(key)
    cached = result is not None
    if not cached:
        if not _analog_lock.acquire(blocking=False):
            # 202, not 429: the browser logs every 4xx as a console error and the page retries.
            return jsonify({"busy": True, "error": ANALOGS_BUSY}), 202
        try:
            t0 = time.perf_counter()
            result = cast(dict[str, Any], B.clean_json(A.build(profile, market, days)))
            result["notes"] = list(result.get("notes", []))
            result["_timing"] = time.perf_counter() - t0
            with _analog_cache_lock:     # only reached on success: errors are never cached
                _analog_cache[key] = result
                while len(_analog_cache) > _ANALOG_CACHE_SIZE:
                    _analog_cache.popitem(last=False)
        finally:
            _analog_lock.release()
    if result is None:
        raise RuntimeError("analog computation returned no result")
    body = {k: v for k, v in result.items() if k != "_timing"}
    body["notes"] = list(result["notes"]) + [
        f"Computed in {result['_timing']:.1f} seconds" + (" (cached result)." if cached else ".")]
    return jsonify({**body, "profile_id": profile_id, "is_sample": profile.is_sample,
                    "status": STATUS, "cached": cached})
