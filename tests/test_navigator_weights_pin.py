"""nav-1 is signed off. Any change to a table must come with a WEIGHTS_VERSION bump
and a new entry in PINNED, so results are never silently produced by other weights."""
import hashlib
import json
import pytest
from sbc.navigator import weights as W

PINNED = {"nav-1": "d6fe9cd8f98c9b2a269ab7a3ad4efc9ccdfdbbe5a38c2424d1ce587accf20b54"}
POINTS = W.TRANSIT_BODIES + ["Asc"]


def canon(value):
    if isinstance(value, dict):
        return {"dict": sorted(([repr(k), canon(v)] for k, v in value.items()), key=lambda kv: kv[0])}
    if isinstance(value, (set, frozenset)):
        return {"set": sorted(repr(v) for v in value)}
    if isinstance(value, (list, tuple)):
        return {"seq": [canon(v) for v in value]}
    return repr(value)


def tables():
    """Every data constant in the module, private ones included, found by scan so
    a new table is pinned without editing this test."""
    return {k: v for k, v in vars(W).items()
            if not k.startswith("__") and k != "WEIGHTS_VERSION" and not callable(v)}


def resolved_aspects():
    """ASPECT_WEIGHT's output, so a change to the function body is caught too."""
    return {f"{b}|{p}|{a}": W.ASPECT_WEIGHT(b, p, a)
            for b in W.TRANSIT_BODIES for p in POINTS for a in W.ASPECTS}


def digest():
    blob = json.dumps({"tables": canon(tables()), "aspects": canon(resolved_aspects())}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def test_tables_match_the_pin_for_this_version():
    assert W.WEIGHTS_VERSION in PINNED, "new WEIGHTS_VERSION needs a PINNED entry"
    assert digest() == PINNED[W.WEIGHTS_VERSION], "tables changed without a WEIGHTS_VERSION bump"


def test_scan_finds_every_table():
    assert {"TERM_WEIGHTS", "ASPECTS", "ORB", "TRANSIT_BODIES", "BENEFIC", "NODE_FACTOR", "ASPECT_SIGN",
            "_EXPLICIT", "MOON_PHASE", "MOON_TITHI_RIKTA", "MOON_TITHI_NANDA", "MOON_SIGN",
            "MOON_NAKSHATRA_DRUVA", "MOON_NAKSHATRA_UGRA", "DRUVA", "UGRA", "DASHA_LORD", "DASHA_LEVELS",
            "STRENGTH_EXALTED", "STRENGTH_DEBILITATED", "STRENGTH_COMBUST", "STRENGTH_RETRO",
            "HIST_MIN_YEARS", "HIST_HORIZON"} <= set(tables())


def edits():
    for name, value in sorted(tables().items()):
        if isinstance(value, dict):
            for key in value:
                yield name, {**value, key: "changed"}, key
        elif isinstance(value, (set, list)):
            yield name, type(value)([*value, "changed"]), "added"
        else:
            yield name, value + 1, "scalar"


@pytest.mark.parametrize("name,edited,_where", list(edits()), ids=lambda v: str(v)[:24])
def test_every_single_value_change_moves_the_digest(monkeypatch, name, edited, _where):
    # patch ASPECT_WEIGHT out so edits to its inputs test the table scan alone
    monkeypatch.setattr(W, "ASPECT_WEIGHT", lambda *a: 0.0)
    before = digest()
    monkeypatch.setattr(W, name, edited)
    assert digest() != before


def test_change_to_the_aspect_function_moves_the_digest(monkeypatch):
    before = digest()
    original = W.ASPECT_WEIGHT
    monkeypatch.setattr(W, "ASPECT_WEIGHT", lambda b, p, a: original(b, p, a) + (b == "Sun" and p == "Asc"))
    assert digest() != before
