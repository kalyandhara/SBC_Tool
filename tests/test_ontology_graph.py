# tests/test_ontology_graph.py
"""Unit tests for sbc/ontology_graph.py — build_graph_data()."""
import pytest
from unittest.mock import patch

MOCK_PLANETS = [
    {"name": "Jupiter", "longitude": 45.0, "sign": "Taurus", "sign_index": 1,
     "nakshatra": "Rohini", "nature": "benefic", "retrograde": False,
     "signed_strength": 1.2, "dignity_multiplier": 1.0, "speed": 0.08},
    {"name": "Mars", "longitude": 110.0, "sign": "Cancer", "sign_index": 3,
     "nakshatra": "Ashlesha", "nature": "malefic", "retrograde": False,
     "signed_strength": -1.0, "dignity_multiplier": 0.8, "speed": 0.5},
    {"name": "Venus", "longitude": 86.0, "sign": "Gemini", "sign_index": 2,
     "nakshatra": "Punarvasu", "nature": "benefic", "retrograde": False,
     "signed_strength": 1.0, "dignity_multiplier": 1.0, "speed": 1.2},
    {"name": "Saturn", "longitude": 300.0, "sign": "Aquarius", "sign_index": 10,
     "nakshatra": "Shatabhisha", "nature": "malefic", "retrograde": True,
     "signed_strength": -1.5, "dignity_multiplier": 1.0, "speed": -0.03},
    {"name": "Mercury", "longitude": 50.0, "sign": "Taurus", "sign_index": 1,
     "nakshatra": "Rohini", "nature": "benefic", "retrograde": False,
     "signed_strength": 1.0, "dignity_multiplier": 1.0, "speed": 1.4},
    {"name": "Sun", "longitude": 200.0, "sign": "Libra", "sign_index": 6,
     "nakshatra": "Swati", "nature": "malefic", "retrograde": False,
     "signed_strength": -0.5, "dignity_multiplier": 0.9, "speed": 0.99},
    {"name": "Moon", "longitude": 150.0, "sign": "Virgo", "sign_index": 5,
     "nakshatra": "U.Phalguni", "nature": "benefic", "retrograde": False,
     "signed_strength": 0.5, "dignity_multiplier": 1.0, "speed": 13.0},
    {"name": "Rahu", "longitude": 15.0, "sign": "Aries", "sign_index": 0,
     "nakshatra": "Ashwini", "nature": "malefic", "retrograde": True,
     "signed_strength": -1.0, "dignity_multiplier": 1.0, "speed": -0.05},
    {"name": "Ketu", "longitude": 195.0, "sign": "Libra", "sign_index": 6,
     "nakshatra": "Swati", "nature": "malefic", "retrograde": True,
     "signed_strength": -1.0, "dignity_multiplier": 1.0, "speed": -0.05},
]

MOCK_TITHI = "Shukla Panchami"


def _mock_positioned_planets(date_str, time_str="09:15", tz_name="Asia/Kolkata"):
    sun = next(p for p in MOCK_PLANETS if p["name"] == "Sun")
    moon = next(p for p in MOCK_PLANETS if p["name"] == "Moon")
    return MOCK_PLANETS, 23.1, sun, moon, MOCK_TITHI


@pytest.fixture
def graph():
    with patch("sbc.ontology_graph.positioned_planets", side_effect=_mock_positioned_planets):
        from sbc.ontology_graph import build_graph_data
        return build_graph_data("2026-11-06")


def test_graph_has_all_layers(graph):
    types = {n["type"] for n in graph["nodes"]}
    for layer in ["planet", "rasi", "nakshatra", "aspect", "theme", "sector", "stock"]:
        assert layer in types, f"Layer '{layer}' missing from nodes"


def test_sensitive_nakshatra_flag(graph):
    # Mars is in Ashlesha — its nakshatra node should be sensitive
    ashlesha_nodes = [n for n in graph["nodes"] if n["id"] == "nak_Ashlesha"]
    assert ashlesha_nodes, "Ashlesha nakshatra node missing"
    assert ashlesha_nodes[0]["detail"]["is_sensitive"] is True


def test_aspect_orb_filter(graph):
    # All aspect nodes must have orb_diff <= their aspect's configured orb
    from sbc.aspect_sets import CLASSICAL_ASPECTS
    for node in graph["nodes"]:
        if node["type"] == "aspect":
            orb_diff = node["detail"]["orb_diff"]
            aspect_name = node["detail"]["aspect_name"]
            profile = next(
                (v for v in CLASSICAL_ASPECTS.values() if v["name"] == aspect_name),
                None,
            )
            assert profile is not None, f"Unknown aspect: {aspect_name}"
            assert orb_diff <= profile["orb"], (
                f"Aspect {node['id']} has orb_diff {orb_diff} > max {profile['orb']}"
            )


def test_edge_colors_match_sentiment(graph):
    color_to_sentiment = {"#22c55e": "bullish", "#f87171": "bearish", "#fbbf24": "volatile"}
    for edge in graph["edges"]:
        if edge.get("color") in color_to_sentiment:
            assert edge["sentiment"] == color_to_sentiment[edge["color"]], (
                f"Edge {edge['from']}->{edge['to']}: color {edge['color']} "
                f"doesn't match sentiment {edge['sentiment']}"
            )


def test_representative_stocks_per_sector(graph):
    from sbc.ontology_graph import SECTOR_STOCK_MAP, STOCK_UNIVERSE
    for node in graph["nodes"]:
        if node["type"] == "sector":
            sector = node["label"]
            stock_key = SECTOR_STOCK_MAP.get(sector)
            if stock_key and stock_key in STOCK_UNIVERSE:
                # Count stock children for this sector
                stock_children = [
                    e for e in graph["edges"]
                    if e["from"] == node["id"] and
                    any(n["id"] == e["to"] and n["type"] == "stock"
                        for n in graph["nodes"])
                ]
                assert len(stock_children) == 5, (
                    f"Sector {sector!r} should have 5 stock children, got {len(stock_children)}"
                )


def test_unconfigured_sector_graceful(graph):
    # Sectors with no STOCK_UNIVERSE entry must still produce a sector node
    from sbc.ontology_graph import SECTOR_STOCK_MAP, STOCK_UNIVERSE
    unconfigured = [
        n for n in graph["nodes"]
        if n["type"] == "sector"
        and SECTOR_STOCK_MAP.get(n["label"]) not in STOCK_UNIVERSE
        and SECTOR_STOCK_MAP.get(n["label"]) is not None
    ]
    # Each unconfigured sector node should have detail.unconfigured = True
    for node in unconfigured:
        assert node["detail"].get("unconfigured") is True, (
            f"Sector {node['label']!r} missing unconfigured flag"
        )


def test_no_duplicate_aspect_nodes(graph):
    aspect_ids = [n["id"] for n in graph["nodes"] if n["type"] == "aspect"]
    assert len(aspect_ids) == len(set(aspect_ids)), "Duplicate aspect node IDs found"


# ── Task 2: Flask endpoint tests ──────────────────────────────────────────────

def test_graph_endpoint_requires_date(client):
    """GET /api/ontology/graph without date returns 400."""
    resp = client.get("/api/ontology/graph")
    assert resp.status_code == 400
    assert "date" in resp.get_json()["error"]


def test_graph_endpoint_invalid_tz(client):
    """GET /api/ontology/graph with unknown tz returns 400."""
    resp = client.get("/api/ontology/graph?date=2026-11-06&tz=Mars/Olympus")
    assert resp.status_code == 400
    assert "time zone" in resp.get_json()["error"]


def test_graph_endpoint_valid(client, monkeypatch):
    """GET /api/ontology/graph with valid params returns 200 with nodes+edges."""
    from sbc import ontology_graph
    _sun = next(p for p in MOCK_PLANETS if p["name"] == "Sun")
    _moon = next(p for p in MOCK_PLANETS if p["name"] == "Moon")
    monkeypatch.setattr(
        ontology_graph, "positioned_planets",
        lambda *a, **kw: (MOCK_PLANETS, 23.1, _sun, _moon, MOCK_TITHI)
    )
    resp = client.get("/api/ontology/graph?date=2026-11-06")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "nodes" in data and "edges" in data


def test_radial_overview_is_a_small_rooted_tree(graph):
    radial = graph["radial"]
    ids = [n["id"] for n in radial["nodes"]]
    assert len(ids) == len(set(ids))
    assert len(ids) <= 60
    assert {"root", "planet", "group", "stock"} == {n["type"] for n in radial["nodes"]}
    children = [e["to"] for e in radial["edges"]]
    assert len(children) == len(set(children)), "every node has exactly one parent"
    assert set(children) == set(ids) - {"root"}
