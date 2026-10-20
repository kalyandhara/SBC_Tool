"""Flask app factory (B-16): blueprints, request guards, error handling, headers.

Every route lives in a blueprint under sbc/api/. This module only wires them
together and adds the cross-cutting pieces: the per-IP rate limit, the write
gate, the JSON error handler, cache and CSP headers, and /healthz.
"""

from __future__ import annotations

import hmac
import os
import time
from collections import defaultdict
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

ROOT = Path(__file__).resolve().parent.parent

# Simple in-memory rate limiter. A page load fires ~30 requests, so the old
# 60/min ceiling throttled the second refresh in a minute. nginx.conf enforces
# the real limit in production.
_request_times: defaultdict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_PER_MIN = 240
_RATE_LIMIT_MAX_CLIENTS = 1000  # sweep idle clients beyond this many

_API_TOKEN = os.environ.get("SBC_API_TOKEN", "").strip()
_LOCAL_ADDRS = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}

_CSP = ("default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self'")


def _blueprints() -> list:
    from sbc.api.blueprints.balance_bp import balance_bp
    from sbc.api.blueprints.chakra_bp import chakra_bp
    from sbc.api.blueprints.chart_bp import chart_bp
    from sbc.api.blueprints.forecast_bp import forecast_bp
    from sbc.api.blueprints.infographic_bp import infographic_bp
    from sbc.api.blueprints.integrations_bp import integrations_bp
    from sbc.api.blueprints.kp_bp import kp_bp
    from sbc.api.blueprints.overview_bp import overview_bp
    from sbc.api.blueprints.profile_bp import profile_bp
    from sbc.api.blueprints.research_bp import research_bp
    from sbc.api.blueprints.screener_bp import screener_bp
    from sbc.api.blueprints.sectors_bp import sectors_bp
    from sbc.api.blueprints.signals_bp import signals_bp
    from sbc.api.blueprints.timing_bp import timing_bp
    from sbc.api.blueprints.transit_bp import transit_bp
    from sbc.api.engine_bp import engine_bp
    return [engine_bp, overview_bp, chart_bp, sectors_bp, kp_bp, balance_bp, chakra_bp,
            forecast_bp, research_bp, signals_bp, timing_bp, profile_bp, integrations_bp,
            infographic_bp, transit_bp, screener_bp]


def _rate_limit():
    from flask import current_app
    if current_app.testing:
        return None
    ip = request.remote_addr or "unknown"
    now = time.time()
    if len(_request_times) > _RATE_LIMIT_MAX_CLIENTS:
        # Drop clients idle for a minute so the table can't grow without bound (B-26).
        for key in [k for k, ts in _request_times.items() if not ts or now - ts[-1] >= 60]:
            del _request_times[key]
    _request_times[ip] = [t for t in _request_times[ip] if now - t < 60]
    if len(_request_times[ip]) > _RATE_LIMIT_PER_MIN:
        return jsonify({"error": "rate limit"}), 429
    _request_times[ip].append(now)
    return None


def _require_write_token():
    """Every non-GET route mutates state (profiles, habits, the webhook file).

    With SBC_API_TOKEN set, writes need a matching X-API-Token header.
    Without it, writes are accepted from this machine only, so binding to
    0.0.0.0 for a phone on the LAN no longer lets that phone rewrite data.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return None
    if _API_TOKEN:
        supplied = request.headers.get("X-API-Token", "")
        if supplied and hmac.compare_digest(supplied, _API_TOKEN):
            return None
        return jsonify({"error": "write endpoints require a valid X-API-Token header"}), 401
    if request.remote_addr in _LOCAL_ADDRS:
        return None
    return jsonify({"error": "write endpoints are local-only until SBC_API_TOKEN is set"}), 403


def _unhandled(exc):
    """Log the traceback and answer JSON, instead of Flask's HTML 500 page.

    Routes that catch their own exceptions are unaffected; this is the net
    under the ones that don't.
    """
    from flask import current_app
    if isinstance(exc, HTTPException):
        return exc
    current_app.logger.exception("Unhandled error on %s %s", request.method, request.path)
    return jsonify({"error": "internal error", "type": type(exc).__name__}), 500


def _headers(response):
    # no-store: prevent stale asset/HTML caching in the preview proxy.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = _CSP
    return response


def healthz():
    return jsonify({"status": "ok", "engine": "sbc"}), 200


def index():
    return render_template("index.html")


def create_app() -> Flask:
    """Build the app: blueprints, guards, headers, boot-time setup."""
    from sbc.app_boot import boot

    app = Flask("app", root_path=str(ROOT))
    for bp in _blueprints():
        app.register_blueprint(bp)
    app.before_request(_rate_limit)
    app.before_request(_require_write_token)
    app.register_error_handler(Exception, _unhandled)
    app.after_request(_headers)
    app.add_url_rule("/healthz", "healthz", healthz)
    app.add_url_rule("/", "index", index)
    boot(app)  # DB schema, city-DB check
    return app
