import pytest

from sbc.navigator import profile as P
from sbc.navigator import visuals as V


@pytest.mark.parametrize("score,group", [(61, "green"), (100, "green"), (60, "yellow"), (41, "yellow"),
                                         (40, "red"), (0, "red")])
def test_colour_group_boundaries(score, group):
    assert V.colour_group(score) == group


def test_natal_strength_is_shadbala_based():
    s = V.natal_strength(P.SAMPLE_PROFILE)
    assert set(s) == set(V.STRENGTH_PLANETS)
    assert s["Moon"]["reasons"][0].startswith("Shadbala 0.84x") and s["Moon"]["reasons"][1] == "Bala"
    assert all(0 <= v["strength"] <= 100 for v in s.values())


def test_model_frames_and_edges_have_real_effects():
    m = V.model(P.SAMPLE_PROFILE, "2026-11-12", days=5)
    assert len(m["frames"]) == 5 and m["frames"][0]["date"] == "2026-11-12"
    assert {n["name"] for n in m["nodes"]} >= {"Sun", "Moon", "Lagna", "Rahu", "Ketu"}
    for f in m["frames"]:
        assert len(f["transits"]) == 9
        assert all(e["effect"] != 0 for e in f["edges"])
    assert any(f["edges"] for f in m["frames"])
