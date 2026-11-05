"""Ontological analysis CLI: load the SBC ontology, reason, certify.

Loads `data/ontologies/sbc_core.ttl` (+ the user Horn rule table), adds
the day's transit facts straight from the engine's ephemeris
(`sbc.planets`), forward chains with per-step derivations, writes a
certificate in the Open Ontologies format, re-checks it with the
independent checker, and prints a summary.

Example:
    python scripts/ontology_report.py --date 2026-10-31
"""

import argparse
import datetime as dt
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from sbc import ontology as ont  # noqa: E402
from sbc.planets import positioned_planets  # noqa: E402

SBC_NS = "http://sbc.tool/ont#"


def s(local: str) -> str:
    """Certificate token for an sbc: local name."""
    return ont.iri(SBC_NS + local)


def _sep(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _nak_token(name: str) -> str:
    return ont.iri(SBC_NS + name.replace(".", ""))


def transit_triples(date_str: str) -> list[ont.Triple]:
    """Assert the day's transit facts from the engine's ephemeris.

    Only the structural facts are asserted (transitOf, inSign,
    inNakshatra, afflictedBy); the rdf:type lines follow by rdfs2, and
    the video-rule conclusions follow under the supplied astro rules.
    """
    planets, _ay, sun, _moon, _tithi = positioned_planets(date_str)
    p = {x["name"]: x for x in planets}
    sun_lon = sun["longitude"]
    out: list[ont.Triple] = []
    for name in ("Jupiter", "Saturn", "Mars", "Rahu"):
        pl = p[name]
        ev = s(f"Transit_{name}_{date_str}")
        out.append(ont.Triple(ev, s("transitOf"), s(name)))
        out.append(ont.Triple(ev, s("inSign"), _nak_token(pl["sign"])))
        out.append(ont.Triple(ev, s("inNakshatra"),
                              _nak_token(pl["nakshatra"])))
    # afflictions of the Jupiter event (the videos' focus)
    ju = p["Jupiter"]
    ev = s(f"Transit_Jupiter_{date_str}")
    sat_68 = (ju["sign_index"] - p["Saturn"]["sign_index"]) % 12
    if sat_68 in (5, 7):
        out.append(ont.Triple(ev, s("afflictedBy"), s("Saturn")))
    for other, orb in (("Rahu", 10.0), ("Ketu", 10.0), ("Mars", 10.0)):
        if _sep(ju["longitude"], p[other]["longitude"]) <= orb:
            out.append(ont.Triple(ev, s("afflictedBy"), s(other)))
    if _sep(ju["longitude"], sun_lon) <= 11.0:
        out.append(ont.Triple(ev, s("afflictedBy"), s("Sun")))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--date", default=None,
                        help="transit date, YYYY-MM-DD (default: today)")
    parser.add_argument("--no-transit", action="store_true",
                        help="core ontology only, no day facts")
    parser.add_argument("--save", default=None)
    args = parser.parse_args()
    date_str = args.date or dt.date.today().isoformat()
    out_dir = os.path.join(_ROOT, "reports", "ontology",
                           f"certificate_{date_str}")

    triples = ont.load_turtle(ont.CORE_TTL)
    if not args.no_transit:
        triples += transit_triples(date_str)
    user_rules = ont.load_user_rules(ont.USER_RULES)

    reasoner = ont.Reasoner(triples, user_rules)
    reasoner.run()
    written = reasoner.write_certificate(out_dir)
    checked = ont.check_certificate(out_dir, user_rules)

    summ = ont.summary(len(reasoner.asserted), reasoner.derivations)
    crash_token = s("CrashRiskSetup")
    crash = [d for d in reasoner.derivations
             if d.conclusion.o == crash_token]
    lines = ["# SBC ontological analysis (Open Ontologies pattern)",
             "",
             f"Date: {date_str} | asserted {summ['asserted']} | derived "
             f"{summ['derivations']} | by verdict {summ['by_verdict']}",
             f"Certificate: {written['directory']} "
             f"(sha256 {written['digest'][:16]}...)",
             f"Checker: {'OK' if checked.get('ok') else checked}",
             "",
             "## Crash-risk derivations (verdict: under supplied rules)"]
    lines += [f"- {d.conclusion.s} via {d.rule} ({d.verdict})"
              for d in crash] or ["- none on this date"]
    lines += ["",
              "Every derivation line is re-verifiable with "
              "`sbc.ontology.check_certificate` and, where the Lean "
              "tooling is installed, with Open Ontologies' `oo-cert`."]
    report = "\n".join(lines) + "\n"
    print(report)
    save = args.save or os.path.join(
        _ROOT, "reports", "ontology", f"ontology_report_{date_str}.md")
    os.makedirs(os.path.dirname(save), exist_ok=True)
    with open(save, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(f"saved: {save}")


if __name__ == "__main__":
    main()
