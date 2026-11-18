"""Confluence items and intraday windows."""
import pytest

from sbc.navigator import context as C
from sbc.navigator.profile import SAMPLE_PROFILE, natal_points

SPAN = 360 / 27


@pytest.mark.parametrize("offset,name,direction", [
    (0, "Janma", "neutral"), (1, "Sampat", "up"), (2, "Vipat", "down"), (3, "Kshema", "up"),
    (4, "Pratyak", "down"), (5, "Sadhana", "up"), (6, "Naidhana", "down"), (7, "Mitra", "up"),
    (8, "Parama Mitra", "up"), (9, "Janma", "neutral"), (26, "Parama Mitra", "up")])
def test_tarabala(offset, name, direction):
    natal = 5 * SPAN + 1.0
    item = C.tarabala(natal, (natal + offset * SPAN) % 360)
    assert name in item["detail"] and item["direction"] == direction


@pytest.mark.parametrize("count,direction", [(1, "up"), (2, "down"), (3, "up"), (6, "up"),
                                             (7, "up"), (8, "down"), (10, "up"), (11, "up"), (12, "down")])
def test_chandrabala(count, direction):
    assert C.chandrabala(10.0, (10.0 + (count - 1) * 30) % 360)["direction"] == direction


def test_chart_sav_total_and_item():
    sav = C.chart_sav(natal_points(SAMPLE_PROFILE))
    assert len(sav) == 12 and sum(sav) == 337
    hi = max(range(12), key=lambda s: sav[s])
    item = C.sav_item(sav, hi * 30 + 1.0)
    assert item["direction"] == ("up" if sav[hi] >= 28 else "neutral")


def test_item_badges():
    natal = natal_points(SAMPLE_PROFILE)
    ctx = C.context_items(natal, "2026-11-18", {"maha": "Mercury", "antar": "Jupiter", "pratyantar": "Saturn"})
    assert {i["key"] for i in ctx} == {"tarabala", "chandrabala", "sav", "contacts", "panchang", "dasha"}
    assert all(not i["in_rule"] and i["badge"] == "experimental" for i in ctx)
    rule = C.rule_items("Normal", "Up", "High")
    assert [i["key"] for i in rule] == ["band", "trend", "vix"]
    assert all(i["in_rule"] and i["badge"] == "unvalidated" for i in rule)


def test_time_windows_blocks_and_ties():
    times = [f"{9 + (15 + 5 * k) // 60:02d}:{(15 + 5 * k) % 60:02d}" for k in range(75)]
    scores = [0.0] * 75
    scores[6] = 5.0    # 09:45 block
    scores[13] = 4.0   # 10:20 is in the 10:15 block
    scores[74] = -9.0  # 15:25 tail
    out = C.time_windows({"buckets": [{"time": t, "score": s} for t, s in zip(times, scores)],
                          "status": "experimental", "experimental_notice": "No validated edge."})
    assert [w["start"] for w in out["best"]] == ["09:45", "10:15"]
    assert out["worst"][0]["start"] == "15:15" and out["worst"][0]["end"] == "15:30"
    assert out["notice"] == "No validated edge." and out["available"] is True


def test_sav_item_down_branch():
    assert C.sav_item([20] * 12, 15.0)["direction"] == "down"


def test_time_windows_without_session_buckets_is_unavailable():
    out = C.time_windows({"buckets": [{"time": "07:00", "score": 1.0}]})
    assert out["available"] is False and out["best"] == []
