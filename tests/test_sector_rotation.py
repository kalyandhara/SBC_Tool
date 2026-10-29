"""Sector rotation: event anchors, clusters, window returns, ranks, grading and labels."""

import numpy as np
import pytest

from sbc import sector_rotation as sr

SESSIONS = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-08"]  # 2024-01-06/07 weekend


def test_anchor_moves_weekend_to_next_session():
    assert sr.anchor_session(SESSIONS, "2024-01-06") == 3


def test_anchor_none_after_last_session():
    assert sr.anchor_session(SESSIONS, "2025-01-01") is None


def test_cluster_merges_within_gap():
    assert sr.cluster([0, 5, 30, 60], gap=20) == [[0, 5], [30], [60]]
    assert sr.cluster([0, 19], gap=20) == [[0, 19]]
    assert sr.cluster([0, 20], gap=20) == [[0], [20]]


def test_mercury_one_occurrence_per_retrograde_window():
    rows = [
        {"planet": "Mercury", "direction": "retrograde", "date": "2024-03-01"},
        {"planet": "Mercury", "direction": "direct", "date": "2024-03-25"},
        {"planet": "Venus", "direction": "retrograde", "date": "2024-04-01"},
    ]
    kept = sr.mercury_events(rows)
    assert [(e["event"], e["date"]) for e in kept] == [("MERCURY_RETROGRADE_START", "2024-03-01")]
    assert kept[0]["window_end"] == "2024-03-25"


def test_mercury_window_without_end_has_none():
    rows = [{"planet": "Mercury", "direction": "retrograde", "date": "2024-12-01"}]
    assert sr.mercury_events(rows)[0]["window_end"] is None


def test_core_events_2024_has_the_four_kinds():
    events = sr.core_events(2024, 2024)
    kinds = {e["event"] for e in events}
    assert {"MERCURY_RETROGRADE_START", "SOLAR_ECLIPSE", "LUNAR_ECLIPSE", "JUPITER_INGRESS"} <= kinds
    assert sum(e["event"] == "MERCURY_RETROGRADE_START" for e in events) == 3
    assert sum(e["event"] == "SOLAR_ECLIPSE" for e in events) == 2
    assert sum(e["event"] == "LUNAR_ECLIPSE" for e in events) == 2
    assert "NODES_INGRESS" not in kinds  # node ingresses are not a core event
