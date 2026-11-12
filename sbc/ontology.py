"""Ontological analysis for the SBC_Tool, in the Open Ontologies style.

Ingests the pattern of github.com/fabio-rovai/open-ontologies (MIT):
domain claims live in an RDF ontology, an RDFS forward chainer
materialises the consequences, and every derived line is written to a
derivation certificate (`asserted.tsv` + `derivations.tsv` +
`asserted.sha256`) that an independent checker can re-verify line by
line - no trust in the engine required.

Scope, stated plainly:
- The loader reads a restricted Turtle subset (prefix declarations,
  `a`, comments, one statement per line, plain string literals). The
  vendored `data/ontologies/sbc_core.ttl` stays inside it.
- The chainer implements the RDFS core rules rdfs2/3/5/7/9/11 with
  per-step premise tracking, plus user Horn rules loaded from a TSV
  table (`data/ontologies/astro_rules.tsv`).
- Derivations from built-in RDFS rules carry the verdict "entailed";
  derivations that needed a user rule carry
  "entailed_under_supplied_rules" - the user's rule is an assumption
  the certificate carries, not a fact it establishes.
- The certificate format mirrors Open Ontologies (tab separated,
  angle-bracket IRIs, one derivation per line). The checker here is a
  second implementation, not the Lean `oo-cert` binary; where that
  binary is installed it should be run on the same files.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import os
import re
from collections.abc import Iterable

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"

TYPE = f"<{RDF}type>"
SUBCLASS = f"<{RDFS}subClassOf>"
SUBPROP = f"<{RDFS}subPropertyOf>"
DOMAIN = f"<{RDFS}domain>"
RANGE = f"<{RDFS}range>"

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        "data", "ontologies")
CORE_TTL = os.path.join(DATA_DIR, "sbc_core.ttl")
USER_RULES = os.path.join(DATA_DIR, "astro_rules.tsv")

BUILTIN_RULES = ("rdfs2", "rdfs3", "rdfs5", "rdfs7", "rdfs9", "rdfs11")


# ── terms and triples ──────────────────────────────────────────────────────

def iri(term: str) -> str:
    """Certificate token for an IRI: <http://...>."""
    return term if term.startswith("<") else f"<{term}>"


class Triple:
    """One (s, p, o) with certificate-ready tokens."""

    __slots__ = ("s", "p", "o")

    def __init__(self, s: str, p: str, o: str):
        self.s, self.p, self.o = s, p, o

    def as_tuple(self) -> tuple[str, str, str]:
        return (self.s, self.p, self.o)

    def text(self) -> str:
        return f"{self.s}\t{self.p}\t{self.o}"

    def __eq__(self, other):
        if isinstance(other, Triple):
            return self.as_tuple() == other.as_tuple()
        if isinstance(other, tuple) and len(other) == 3:
            return self.as_tuple() == other
        return NotImplemented

    def __hash__(self):
        return hash(self.as_tuple())

    def __repr__(self):
        return f"Triple({self.s!r}, {self.p!r}, {self.o!r})"


# ── restricted Turtle loader ───────────────────────────────────────────────

_PREFIX_RE = re.compile(r"@prefix\s+([A-Za-z0-9_-]*):\s*<([^>]*)>\s*\.")
_STMT_RE = re.compile(
    r"^(?P<s><[^>]*>|[A-Za-z0-9_-]*:[A-Za-z0-9_-]*|[A-Za-z0-9_-]+)\s+"
    r"(?P<p><[^>]*>|[A-Za-z0-9_-]*:[A-Za-z0-9_-]*|a)\s+"
    r"(?P<o><[^>]*>|[A-Za-z0-9_-]*:[A-Za-z0-9_-]*|a|\"[^\"]*\")\s*\.$")


def _expand(term: str, prefixes: dict[str, str]) -> str:
    """Expand a Turtle term to its certificate token."""
    if term.startswith("<") or term == "a" or term.startswith('"'):
        return TYPE if term == "a" else term
    prefix, _, local = term.partition(":")
    if prefix not in prefixes:
        raise ValueError(f"unknown prefix in {term!r}")
    return iri(prefixes[prefix] + local)


def _parse_turtle_lines(lines: Iterable[str], source_label: str) -> list[Triple]:
    """Core restricted-Turtle parser over an iterable of raw lines.

    One statement per line, ending with a dot.  Inline comments are only
    recognised on lines without a quoted literal.
    """
    triples: list[Triple] = []
    prefixes: dict[str, str] = {}
    for lineno, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pm = _PREFIX_RE.match(line)
        if pm:
            prefixes[pm.group(1)] = pm.group(2)
            continue
        body = line if ' "' in line else line.split("#", 1)[0].strip()
        if not body:
            continue
        sm = _STMT_RE.match(body)
        if not sm:
            raise ValueError(f"{source_label}:{lineno}: cannot parse {line!r}")
        triples.append(Triple(_expand(sm.group("s"), prefixes),
                              _expand(sm.group("p"), prefixes),
                              _expand(sm.group("o"), prefixes)))
    return triples


def load_turtle(path: str) -> list[Triple]:
    """Load the restricted Turtle subset used by data/ontologies/*.ttl.

    One statement per line, ending with a dot.  Inline comments are only
    recognised on lines without a quoted literal.
    """
    with open(path, encoding="utf-8") as fh:
        return _parse_turtle_lines(fh, path)


def load_turtle_from_string(text: str, source_label: str = "<upload>") -> list[Triple]:
    """Parse restricted Turtle from an in-memory string (e.g. a file upload)."""
    return _parse_turtle_lines(text.splitlines(), source_label)


# ── user Horn rules (TSV) ──────────────────────────────────────────────────

class UserRule:
    """A Horn rule: premises then conclusion, each 3 terms, ?vars bound."""

    __slots__ = ("name", "premises", "conclusion")

    def __init__(self, name: str, premises: list[tuple[str, str, str]],
                 conclusion: tuple[str, str, str]):
        self.name = name
        self.premises = premises
        self.conclusion = conclusion


def load_user_rules(path: str) -> list[UserRule]:
    """Load the Horn rule table; terms expand over sbc:/rdf:/rdfs:."""
    prefixes = {"sbc": "http://sbc.tool/ont#", "rdf": RDF, "rdfs": RDFS}

    def expand(term: str) -> str:
        if term.startswith("?") or term.startswith("<"):
            return term
        prefix, _, local = term.partition(":")
        if prefix not in prefixes:
            raise ValueError(f"{path}: unknown prefix in {term!r}")
        return iri(prefixes[prefix] + local)

    rules: list[UserRule] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) < 7 or (len(fields) - 1) % 3 != 0:
                raise ValueError(f"{path}:{lineno}: bad field count")
            name = fields[0]
            terms = [expand(t) for t in fields[1:]]
            n_prem = (len(terms) - 3) // 3
            premises = [(terms[i * 3], terms[i * 3 + 1], terms[i * 3 + 2])
                        for i in range(n_prem)]
            conclusion = (terms[-3], terms[-2], terms[-1])
            rules.append(UserRule(name, premises, conclusion))
    return rules


def _bind(pattern: tuple[str, str, str], triple: Triple,
          env: dict[str, str]) -> dict[str, str] | None:
    """Extend env by matching pattern against triple; None on mismatch."""
    local = dict(env)
    for pat_term, fact_term in zip(pattern, triple.as_tuple()):
        if pat_term.startswith("?"):
            if local.get(pat_term, fact_term) != fact_term:
                return None
            local[pat_term] = fact_term
        elif pat_term != fact_term:
            return None
    return local


def _apply(pattern: tuple[str, str, str],
           env: dict[str, str]) -> tuple[str, str, str]:
    return (env.get(pattern[0], pattern[0]),
            env.get(pattern[1], pattern[1]),
            env.get(pattern[2], pattern[2]))


# ── the reasoner ───────────────────────────────────────────────────────────

class Derivation:
    """One materialised line: rule, conclusion, premises, verdict."""

    __slots__ = ("rule", "conclusion", "premises", "verdict")

    def __init__(self, rule: str, conclusion: Triple,
                 premises: list[Triple]):
        self.rule = rule
        self.conclusion = conclusion
        self.premises = premises
        self.verdict = ("entailed" if rule in BUILTIN_RULES
                        else "entailed_under_supplied_rules")

    def text(self) -> str:
        parts = [self.rule, self.conclusion.text()]
        parts += [p.text() for p in self.premises]
        return "\t".join(parts)


class Reasoner:
    """RDFS core + user Horn rules, forward chained to a fixpoint."""

    def __init__(self, triples: list[Triple],
                 user_rules: list[UserRule] | None = None):
        self.facts: set[Triple] = set(triples)
        self.asserted: list[Triple] = list(triples)
        self.user_rules = user_rules or []
        self.derivations: list[Derivation] = []
        self.derived: dict[tuple[str, str, str], Derivation] = {}

    def _emit(self, der: Derivation) -> bool:
        key = der.conclusion.as_tuple()
        if der.conclusion in self.facts or key in self.derived:
            return False
        self.facts.add(der.conclusion)
        self.derived[key] = der
        self.derivations.append(der)
        return True

    def _apply_builtins(self, fact: Triple) -> list[Derivation]:
        out: list[Derivation] = []
        s, p, o = fact.as_tuple()
        if p == SUBCLASS and o != s:  # rdfs11: subClassOf transitivity
            for t in self.facts:
                if t.p == SUBCLASS and t.s == o:
                    out.append(Derivation(
                        "rdfs11", Triple(s, SUBCLASS, t.o), [fact, t]))
            for t in self.facts:  # rdfs9 on the type reading
                if t.p == TYPE and t.o == s:
                    out.append(Derivation(
                        "rdfs9", Triple(t.s, TYPE, o), [t, fact]))
        if p == SUBPROP and o != s:  # rdfs5 + rdfs7
            for t in self.facts:
                if t.p == SUBPROP and t.s == o:
                    out.append(Derivation(
                        "rdfs5", Triple(s, SUBPROP, t.o), [fact, t]))
                if t.p == s:
                    out.append(Derivation(
                        "rdfs7", Triple(t.s, o, t.o), [t, fact]))
        if p == DOMAIN:  # rdfs2: domain conclusion
            for t in self.facts:
                if t.p == s and t.s != o:
                    out.append(Derivation(
                        "rdfs2", Triple(t.s, TYPE, o), [fact, t]))
        if p == RANGE:  # rdfs3: range conclusion
            for t in self.facts:
                if t.p == s and t.o != o:
                    out.append(Derivation(
                        "rdfs3", Triple(t.o, TYPE, o), [fact, t]))
        if p == TYPE:  # rdfs9: type via subClassOf
            for t in self.facts:
                if t.p == SUBCLASS and t.s == o:
                    out.append(Derivation(
                        "rdfs9", Triple(s, TYPE, t.o), [fact, t]))
        return out

    def _apply_user_rules(self, fact: Triple) -> list[Derivation]:
        out: list[Derivation] = []
        for rule in self.user_rules:
            anchored: int | None = None
            env0: dict[str, str] | None = None
            for idx, prem in enumerate(rule.premises):
                env0 = _bind(prem, fact, {})
                if env0 is not None:
                    anchored = idx
                    break
            if anchored is None or env0 is None:
                continue
            rest = [p for i, p in enumerate(rule.premises) if i != anchored]
            matches: list[dict[str, str]] = [env0]
            for prem in rest:
                nxt = []
                for e in matches:
                    for t in self.facts:
                        e2 = _bind(prem, t, e)
                        if e2 is not None:
                            nxt.append(e2)
                matches = nxt
                if not matches:
                    break
            for env in matches:
                conc = _apply(rule.conclusion, env)
                if conc == fact.as_tuple():
                    continue  # the fact itself is not a new derivation
                premises = [fact if i == anchored
                            else Triple(*_apply(prem, env))
                            for i, prem in enumerate(rule.premises)]
                out.append(Derivation(rule.name, Triple(*conc), premises))
        return out

    def run(self) -> list[Derivation]:
        """Forward chain to a fixpoint; returns all derivations."""
        pending = list(self.asserted)
        while pending:
            fact = pending.pop()
            fresh = self._apply_builtins(fact) + self._apply_user_rules(fact)
            for der in fresh:
                if self._emit(der):
                    pending.append(der.conclusion)
        return self.derivations

    # ── certificate I/O ──

    def write_certificate(self, directory: str) -> dict:
        """Write asserted.tsv, derivations.tsv, asserted.sha256."""
        os.makedirs(directory, exist_ok=True)
        asserted_path = os.path.join(directory, "asserted.tsv")
        deriv_path = os.path.join(directory, "derivations.tsv")
        with open(asserted_path, "w", encoding="utf-8", newline="") as fh:
            for t in self.asserted:
                fh.write(t.text() + "\n")
        with open(deriv_path, "w", encoding="utf-8", newline="") as fh:
            for der in self.derivations:
                fh.write(der.text() + "\n")
        with open(asserted_path, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        with open(os.path.join(directory, "asserted.sha256"), "w",
                  encoding="utf-8") as fh:
            fh.write(digest + "\n")
        return {"asserted": len(self.asserted),
                "derivations": len(self.derivations),
                "digest": digest, "directory": directory}


# ── the independent checker ────────────────────────────────────────────────

def check_certificate(directory: str,
                      user_rules: list[UserRule]) -> dict:
    """Re-verify a certificate line by line (independent of the chainer).

    Mirrors the Open Ontologies `oo-cert` contract: every derivation
    line must follow from its premises under the named rule, and every
    premise must be asserted or concluded by an earlier line.  Also
    re-computes the sha256 of asserted.tsv against asserted.sha256.
    """
    asserted_path = os.path.join(directory, "asserted.tsv")
    deriv_path = os.path.join(directory, "derivations.tsv")
    with open(asserted_path, encoding="utf-8") as fh:
        asserted_lines = [ln.rstrip("\n") for ln in fh if ln.strip()]
    with open(asserted_path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    with open(os.path.join(directory, "asserted.sha256"),
              encoding="utf-8") as fh:
        recorded = fh.read().strip()
    if digest != recorded:
        return {"ok": False, "reason": "digest mismatch",
                "expected": recorded, "computed": digest}
    known: set[tuple[str, str, str]] = set()
    for ln in asserted_lines:
        parts = ln.split("\t")
        if len(parts) == 3:
            known.add((parts[0], parts[1], parts[2]))
    with open(deriv_path, encoding="utf-8") as fh:
        deriv_lines = [ln.rstrip("\n") for ln in fh if ln.strip()]
    user_by_name = {r.name: r for r in user_rules}
    for lineno, line in enumerate(deriv_lines, 1):
        fields = line.split("\t")
        if len(fields) < 4 or (len(fields) - 4) % 3 != 0:
            return {"ok": False, "line": lineno, "reason": "malformed line"}
        rule = fields[0]
        conclusion = (fields[1], fields[2], fields[3])
        premises = [(fields[4 + i * 3], fields[5 + i * 3], fields[6 + i * 3])
                    for i in range((len(fields) - 4) // 3)]
        for prem in premises:
            if prem not in known:
                return {"ok": False, "line": lineno, "rule": rule,
                        "reason": "premise not known",
                        "premise": list(prem)}
        if rule in BUILTIN_RULES:
            ok = _check_builtin(rule, premises, conclusion)
        elif rule in user_by_name:
            ok = _check_user(user_by_name[rule], premises, conclusion)
        else:
            return {"ok": False, "line": lineno,
                    "reason": "unknown rule", "rule": rule}
        if not ok:
            return {"ok": False, "line": lineno, "rule": rule,
                    "conclusion": list(conclusion),
                    "premises": [list(p) for p in premises],
                    "reason": "conclusion does not follow"}
        known.add(conclusion)
    return {"ok": True, "asserted": len(asserted_lines),
            "derivations": len(deriv_lines),
            "rules": sorted({ln.split("\t")[0] for ln in deriv_lines})}


def _check_builtin(rule: str, premises: list[tuple[str, str, str]],
                   conclusion: tuple[str, str, str]) -> bool:
    s, p, o = conclusion
    if len(premises) != 2:
        return False
    a, b = premises
    if rule == "rdfs9":
        return (a[1] == TYPE and a[2] == b[0] and b[1] == SUBCLASS
                and (s, p, o) == (a[0], TYPE, b[2]))
    if rule == "rdfs11":
        return (a[1] == SUBCLASS and b[1] == SUBCLASS and a[2] == b[0]
                and (s, p, o) == (a[0], SUBCLASS, b[2]))
    if rule == "rdfs5":
        return (a[1] == SUBPROP and b[1] == SUBPROP and a[2] == b[0]
                and (s, p, o) == (a[0], SUBPROP, b[2]))
    if rule == "rdfs2":
        return (a[1] == DOMAIN and b[1] == a[0]
                and (s, p, o) == (b[0], TYPE, a[2]))
    if rule == "rdfs3":
        return (a[1] == RANGE and b[1] == a[0]
                and (s, p, o) == (b[2], TYPE, a[2]))
    if rule == "rdfs7":
        return (a[1] == SUBPROP and b[1] == a[0]
                and (s, p, o) == (b[0], a[2], b[2]))
    return False


def _check_user(rule: UserRule, premises: list[tuple[str, str, str]],
                conclusion: tuple[str, str, str]) -> bool:
    if len(premises) != len(rule.premises):
        return False
    env: dict[str, str] = {}
    for prem, pat in zip(premises, rule.premises):
        new_env = _bind(pat, Triple(*prem), env)
        if new_env is None:
            return False
        env = new_env
    return _apply(rule.conclusion, env) == conclusion


def summary(asserted: int, derivations: list[Derivation]) -> dict:
    by_verdict: dict[str, int] = {}
    for der in derivations:
        by_verdict[der.verdict] = by_verdict.get(der.verdict, 0) + 1
    return {"asserted": asserted, "derivations": len(derivations),
            "by_verdict": by_verdict,
            "generated_at": dt.datetime.now(dt.UTC).isoformat(
                timespec="seconds")}
