"""Ontology blueprint: SBC Market Ontology Framework endpoints.

Implements the framework pipeline:

    Daily SBC Chart → Ontology Extraction → Sector Scorecard →
    Historical Analog → Probability Matrix → Market Regime →
    Actionable Watchlist → Confidence Scores

Endpoints:
  GET /api/ontology/planetary   -> Level 1 planetary event extraction
  GET /api/ontology/sectors     -> Sector scorecard with scoring breakdown
  GET /api/ontology/report      -> Full report (all 10 deliverables)
  GET /api/ontology/certificate -> Raw certificate (asserted + derivations)
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from sbc import ontology as ont
from sbc.ontology_scoring import (
    build_report,
    compute_readings,
    compute_sector_scores,
    report_to_dict,
)

ontology_bp = Blueprint("ontology", __name__, url_prefix="/api/ontology")

HEAVY = (
    "/api/ontology/planetary", "/api/ontology/sectors",
    "/api/ontology/report", "/api/ontology/certificate",
)


def _date_params() -> tuple[str, str, str]:
    date = request.args.get("date") or ""
    time = request.args.get("time") or "09:15"
    tz = request.args.get("tz") or "Asia/Kolkata"
    return date, time, tz


@ontology_bp.get("/planetary")
def planetary():
    """Level 1: Planetary Event Extraction.

    Returns planet -> nakshatra mapping plus sensitive stars (the JSON the
    framework feeds to an LLM).
    """
    date, time, tz = _date_params()
    if not date:
        return jsonify({"error": "date (YYYY-MM-DD) is required"}), 400
    try:
        readings = compute_readings(date, time, tz)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({
        "date": date, "time": time, "tz": tz,
        "planets": [
            {
                "planet": r.name,
                "nakshatra": r.nakshatra,
                "sign": r.sign,
                "nature": r.nature,
                "strength": round(r.signed_strength, 2),
                "retrograde": r.retrograde,
                "sectors": r.sectors,
                "sensitive": r.is_sensitive,
            }
            for r in readings
        ],
        "sensitive_stars": sorted(
            {r.nakshatra for r in readings if r.is_sensitive}),
    })


@ontology_bp.get("/sectors")
def sectors():
    """Sector scorecard: every sector's score with per-planet breakdown."""
    date, time, tz = _date_params()
    if not date:
        return jsonify({"error": "date (YYYY-MM-DD) is required"}), 400
    try:
        readings = compute_readings(date, time, tz)
        scores = compute_sector_scores(readings)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    from sbc.ontology_scoring import SECTOR_GROUPS
    return jsonify({
        "date": date,
        "sectors": [
            {
                "sector": s.sector,
                "score": round(s.score, 2),
                "group": SECTOR_GROUPS.get(s.sector, "Other"),
                "planets": s.planets,
                "breakdown": s.breakdown,
            }
            for s in scores
        ],
    })


@ontology_bp.get("/report")
def report():
    """Full ontology report: all 10 framework deliverables in one payload."""
    date, time, tz = _date_params()
    if not date:
        return jsonify({"error": "date (YYYY-MM-DD) is required"}), 400
    try:
        report = build_report(date, time, tz)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(report_to_dict(report))


@ontology_bp.get("/certificate")
def certificate():
    """Raw derivation certificate for auditability (asserted + derivations).

    Mirrors the Open Ontologies certificate format so an independent
    checker (or the Lean oo-cert binary) can re-verify line by line.
    """
    date, time, tz = _date_params()
    if not date:
        return jsonify({"error": "date (YYYY-MM-DD) is required"}), 400
    try:
        readings = compute_readings(date, time, tz)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    triples = []
    for r in readings:
        planet_iri = ont.iri(f"http://sbc.tool/ont/{r.name}")
        nak_iri = ont.iri(
            f"http://sbc.tool/ont{r.nakshatra.replace('.', '')}")
        triples.append(ont.Triple(planet_iri, ont.iri(
            "http://sbc.tool/ont#inNakshatra"), nak_iri))
    user_rules = ont.load_user_rules(ont.USER_RULES)
    reasoner = ont.Reasoner(triples, user_rules)
    reasoner.run()
    written = reasoner.write_certificate(
        f"/tmp/ontology_cert_{date}")
    checked = ont.check_certificate(written["directory"], user_rules)
    return jsonify({
        "date": date,
        "certificate": written,
        "valid": checked.get("ok", False),
        "check": checked,
        "derivations": [d.text() for d in reasoner.derivations],
    })


# Mark these as heavy endpoints so the SPA uses the longer timeout.
for _p in HEAVY:
    pass  # referenced by static/app.js HEAVY_ENDPOINTS
