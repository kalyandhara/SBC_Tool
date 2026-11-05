"""Tests for the SBC ontology reasoner and its certificates."""

import os

import pytest

from sbc import ontology as ont

CORE_TTL = ont.CORE_TTL
USER_RULES = ont.USER_RULES

# Open Ontologies' own README example, as a restricted-Turtle string.
COFFEE_TTL = """
@prefix ex:   <http://example.org/> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:Espresso rdfs:subClassOf ex:Coffee .
ex:Coffee   rdfs:subClassOf ex:Drink .
ex:myCup    a               ex:Espresso .
"""


@pytest.fixture(scope="module")
def user_rules():
    return ont.load_user_rules(USER_RULES)


@pytest.fixture(scope="module")
def core_triples():
    return ont.load_turtle(CORE_TTL)


def _write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


class TestLoader:
    def test_core_loads_and_covers_domain(self, core_triples):
        assert len(core_triples) > 120
        lord = ont.iri("http://sbc.tool/ont#lord")
        ketu = ont.iri("http://sbc.tool/ont#Ketu")
        lords = [t for t in core_triples if t.p == lord and t.o == ketu]
        assert {t.s for t in lords} == {
            ont.iri(f"http://sbc.tool/ont#{n}")
            for n in ("Ashwini", "Magha", "Mula")}

    def test_rejects_unknown_prefix(self, tmp_path):
        path = _write(tmp_path / "bad.ttl", "foo:Bar a foo:Baz .\n")
        with pytest.raises(ValueError, match="unknown prefix"):
            ont.load_turtle(str(path))

    def test_rejects_unterminated_statement(self, tmp_path):
        path = _write(tmp_path / "bad.ttl",
                      "@prefix ex: <http://e/> .\nex:A ex:p ex:B\n")
        with pytest.raises(ValueError, match="cannot parse"):
            ont.load_turtle(str(path))


class TestCoffeeExample:
    """The Open Ontologies README run: 3 asserted, 3 derived."""

    @pytest.fixture(scope="class")
    def result(self, tmp_path_factory):
        path = _write(tmp_path_factory.mktemp("coffee") / "coffee.ttl",
                      COFFEE_TTL)
        reasoner = ont.Reasoner(ont.load_turtle(str(path)))
        reasoner.run()
        out = str(tmp_path_factory.mktemp("cert"))
        written = reasoner.write_certificate(out)
        checked = ont.check_certificate(out, [])
        return reasoner, written, checked

    def test_exactly_three_derivation_lines(self, result):
        reasoner, written, _ = result
        assert written["asserted"] == 3
        assert written["derivations"] == 3
        rules = [d.rule for d in reasoner.derivations]
        assert sorted(rules) == ["rdfs11", "rdfs9", "rdfs9"]

    def test_transitive_conclusions_present(self, result):
        reasoner, _w, _c = result
        facts = reasoner.facts
        cup, coffee, drink = (ont.iri(f"http://example.org/{n}")
                              for n in ("myCup", "Coffee", "Drink"))
        assert ont.Triple(cup, ont.TYPE, coffee) in facts
        assert ont.Triple(cup, ont.TYPE, drink) in facts
        assert ont.Triple(coffee, ont.SUBCLASS, drink) in facts

    def test_certificate_checks_clean(self, result):
        _r, _w, checked = result
        assert checked["ok"] is True
        assert checked["asserted"] == 3
        assert checked["derivations"] == 3


class TestUserRules:
    def test_ketu_lord_derivation_is_under_supplied_rules(
            self, core_triples, user_rules):
        reasoner = ont.Reasoner(list(core_triples), user_rules)
        reasoner.run()
        magha = ont.iri("http://sbc.tool/ont#Magha")
        ketu_class = ont.iri("http://sbc.tool/ont#KetuRuledNakshatra")
        der = reasoner.derived[(magha, ont.TYPE, ketu_class)]
        assert der.rule == "astro_ketu_ruled"
        assert der.verdict == "entailed_under_supplied_rules"

    def test_transit_becomes_crash_risk_under_supplied_rules(
            self, core_triples, user_rules):
        sbc = "http://sbc.tool/ont#"
        triples = list(core_triples) + [
            ont.Triple(ont.iri(sbc + "T1"), ont.iri(sbc + "transitOf"),
                       ont.iri(sbc + "Jupiter")),
            ont.Triple(ont.iri(sbc + "T1"), ont.iri(sbc + "inNakshatra"),
                       ont.iri(sbc + "Magha")),
            ont.Triple(ont.iri(sbc + "T1"), ont.iri(sbc + "afflictedBy"),
                       ont.iri(sbc + "Rahu")),
        ]
        reasoner = ont.Reasoner(triples, user_rules)
        reasoner.run()
        crash = ont.iri(sbc + "CrashRiskSetup")
        assert (ont.iri(sbc + "T1"), ont.TYPE, crash) in reasoner.facts
        der = reasoner.derived[(ont.iri(sbc + "T1"), ont.TYPE, crash)]
        assert der.rule == "astro_crash_risk"
        assert der.verdict == "entailed_under_supplied_rules"

    def test_unafflicted_ketu_transit_is_not_a_crash_setup(
            self, core_triples, user_rules):
        sbc = "http://sbc.tool/ont#"
        triples = list(core_triples) + [
            ont.Triple(ont.iri(sbc + "T2"), ont.iri(sbc + "transitOf"),
                       ont.iri(sbc + "Jupiter")),
            ont.Triple(ont.iri(sbc + "T2"), ont.iri(sbc + "inNakshatra"),
                       ont.iri(sbc + "Magha")),
        ]
        reasoner = ont.Reasoner(triples, user_rules)
        reasoner.run()
        assert (ont.iri(sbc + "T2"), ont.TYPE,
                ont.iri(sbc + "KetuNakshatraTransit")) in reasoner.facts
        assert (ont.iri(sbc + "T2"), ont.TYPE,
                ont.iri(sbc + "CrashRiskSetup")) not in reasoner.facts


class TestCertificateSecurity:
    def test_forged_conclusion_is_refused(self, tmp_path, user_rules):
        reasoner = ont.Reasoner(ont.load_turtle(CORE_TTL), user_rules)
        reasoner.run()
        out = str(tmp_path / "cert")
        reasoner.write_certificate(out)
        deriv = os.path.join(out, "derivations.tsv")
        with open(deriv, encoding="utf-8") as fh:
            lines = fh.readlines()
        fields = lines[0].rstrip("\n").split("\t")
        fields[3] = "<http://sbc.tool/ont#Forged>"  # forge the object
        with open(deriv, "w", encoding="utf-8") as fh:
            fh.write("\t".join(fields) + "\n")
            fh.writelines(lines[1:])
        checked = ont.check_certificate(out, user_rules)
        assert checked["ok"] is False
        assert checked["line"] == 1
        assert checked["reason"] == "conclusion does not follow"

    def test_digest_catches_asserted_edits(self, tmp_path, user_rules):
        reasoner = ont.Reasoner(ont.load_turtle(CORE_TTL), user_rules)
        reasoner.run()
        out = str(tmp_path / "cert")
        reasoner.write_certificate(out)
        asserted = os.path.join(out, "asserted.tsv")
        with open(asserted, "a", encoding="utf-8") as fh:
            fh.write('<http://sbc.tool/ont#X>\t<http://sbc.tool/ont#p>\t'
                     '<http://sbc.tool/ont#Y>\n')
        checked = ont.check_certificate(out, user_rules)
        assert checked["ok"] is False
        assert checked["reason"] == "digest mismatch"
