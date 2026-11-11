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

import time

from flask import Blueprint, jsonify, request

from sbc import ontology as ont
from sbc.ontology_graph import build_graph_data
from sbc.ontology_scoring import (
    build_report,
    compute_readings,
    compute_sector_scores,
    report_to_dict,
)

# 15-minute TTL cache keyed by "date|time|tz"
_GRAPH_CACHE: dict[str, tuple[float, dict]] = {}
_GRAPH_TTL = 900  # seconds


def _cached_graph(date: str, time_str: str, tz: str) -> dict:
    key = f"{date}|{time_str}|{tz}"
    if key in _GRAPH_CACHE:
        ts, val = _GRAPH_CACHE[key]
        if time.monotonic() - ts < _GRAPH_TTL:
            return val
    val = build_graph_data(date, time_str, tz)
    _GRAPH_CACHE[key] = (time.monotonic(), val)
    return val

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


@ontology_bp.get("/catalogue")
def catalogue():
    """Ontology catalogue: metadata for every available starter ontology.

    Mirrors Microsoft Ontology-Playground's catalogue - a curated library of
    pre-built domain ontologies browseable by category, each with a shareable
    deep-link id and a metadata record (name, description, category, icon,
    tags, author, entity/relationship counts).
    """
    import json as _json
    import os as _os
    cat_path = _os.path.join(ont.DATA_DIR, "catalogue.json")
    try:
        with open(cat_path, encoding="utf-8") as fh:
            return _json.load(fh)
    except FileNotFoundError:
        return jsonify({"ontologies": []})


@ontology_bp.get("/catalogue/<ont_id>")
def catalogue_ontology(ont_id):
    """Return the RDF/Turtle source for a single catalogue ontology."""
    import json as _json
    import os as _os
    cat_path = _os.path.join(ont.DATA_DIR, "catalogue.json")
    try:
        with open(cat_path, encoding="utf-8") as fh:
            cat = _json.load(fh)
    except FileNotFoundError:
        return jsonify({"error": "catalogue unavailable"}), 500
    entry = next((o for o in cat.get("ontologies", []) if o["id"] == ont_id), None)
    if not entry:
        return jsonify({"error": "unknown ontology"}), 404
    src = _os.path.join(ont.DATA_DIR, entry["source"])
    try:
        with open(src, encoding="utf-8") as fh:
            ttl = fh.read()
    except FileNotFoundError:
        return jsonify({"error": "ontology source missing"}), 500
    return jsonify({
        "id": entry["id"],
        "name": entry["name"],
        "description": entry["description"],
        "category": entry["category"],
        "icon": entry["icon"],
        "tags": entry["tags"],
        "author": entry["author"],
        "entityCount": entry["entityCount"],
        "relationshipCount": entry["relationshipCount"],
        "ttl": ttl,
    })


@ontology_bp.post("/import")
def import_ontology():
    """Import an uploaded RDF/XML or Turtle file into the ontology model.

    Parses the file with the SBC restricted Turtle loader and runs the
    reasoner, returning the derived triples and certificate. Mirrors
    Ontology-Playground's RDF import (full round-trip, inert imports/SHACL).
    """
    from flask import request as _request
    if "file" not in _request.files:
        return jsonify({"error": "no file uploaded"}), 400
    up = _request.files["file"]
    if not up.filename:
        return jsonify({"error": "empty filename"}), 400
    raw = up.read().decode("utf-8", errors="replace")
    try:
        triples = ont.load_turtle_from_string(raw)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"parse failed: {exc}"}), 400
    user_rules = ont.load_user_rules(ont.USER_RULES)
    reasoner = ont.Reasoner(triples, user_rules)
    reasoner.run()
    written = reasoner.write_certificate(f"/tmp/ontology_import_{_request.remote_addr or 'anon'}")
    checked = ont.check_certificate(written["directory"], user_rules)
    return jsonify({
        "filename": up.filename,
        "asserted": len(triples),
        "valid": checked.get("ok", False),
        "check": checked,
        "derivations": [d.text() for d in reasoner.derivations],
        "certificate": written,
    })


@ontology_bp.get("/graph")
def graph():
    """7-layer impact lineage graph: Planet → Rasi → Nak → Aspect → Theme → Sector → Stock.

    Research-grade only. No validated edge. Dasha layer deferred to Phase 2.
    """
    date, time_str, tz = _date_params()
    if not date:
        return jsonify({"error": "date (YYYY-MM-DD) is required"}), 400
    # Validate tz
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, KeyError):
        return jsonify({"error": f"unknown time zone: {tz}"}), 400
    try:
        data = _cached_graph(date, time_str, tz)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(data)


# Mark these as heavy endpoints so the SPA uses the longer timeout.
for _p in HEAVY:
    pass  # referenced by static/app.js HEAVY_ENDPOINTS
