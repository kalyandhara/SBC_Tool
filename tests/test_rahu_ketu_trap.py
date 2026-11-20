"""Tests for the Rahu/Ketu trap score (audit B5, B6)."""

import sbc.rahu_ketu_trap as trap


def _fake_positions(lons):
    def fake(_jul):
        return [{"name": n, "longitude": v} for n, v in lons.items()], 24.0
    return fake


class TestKrishnaTithi:
    """B5: 'Krishna Paksha 8-14' means tithi 23-29 (tithi_of numbers Krishna 16-30)."""

    def test_waning_date_fires(self):
        s = trap.compute_daily_trap("2026-09-05", ["BANKING"])[0]  # tithi 24, Krishna 9
        assert s.tithi == 24
        assert "Krishna Paksha 8-14" in s.reasons

    def test_waxing_date_does_not_fire(self):
        s = trap.compute_daily_trap("2026-09-20", ["BANKING"])[0]  # tithi 9, Shukla 9
        assert s.tithi == 9
        assert "Krishna Paksha 8-14" not in s.reasons


class TestNodeContactOnce:
    """B6: one node contact scores once, as the strongest overlapping condition."""

    def test_single_contact_is_not_orange(self, monkeypatch):
        # Mercury conjunct Ketu (= opposite Rahu), same nakshatra as Ketu; Moon far, Shukla 1.
        monkeypatch.setattr(trap, "positions", _fake_positions(
            {"Sun": 0.0, "Moon": 5.0, "Rahu": 100.0, "Ketu": 280.0, "Mercury": 280.5}))
        s = trap.compute_daily_trap("2026-09-11", ["BANKING"])[0]
        assert s.score == trap.WEIGHTS["node_proximity"]
        assert s.level == "AMBER"

    def test_separate_facts_still_add(self, monkeypatch):
        # Same contact, plus Moon near Ketu and Krishna tithi 24.
        monkeypatch.setattr(trap, "positions", _fake_positions(
            {"Sun": 5.0, "Moon": 285.0, "Rahu": 100.0, "Ketu": 280.0, "Mercury": 280.5}))
        s = trap.compute_daily_trap("2026-09-11", ["BANKING"])[0]
        assert s.score == trap.WEIGHTS["node_proximity"] + trap.WEIGHTS["moon_conjunction"] + trap.WEIGHTS["tithi"]
        assert s.level == "ORANGE"

    def test_nakshatra_only_contact_scores_vedha(self, monkeypatch):
        # Mercury 8 deg from Rahu but in Rahu's nakshatra (93.33-106.67): vedha weight only.
        monkeypatch.setattr(trap, "positions", _fake_positions(
            {"Sun": 0.0, "Moon": 5.0, "Rahu": 94.0, "Ketu": 274.0, "Mercury": 102.0}))
        s = trap.compute_daily_trap("2026-09-11", ["BANKING"])[0]
        assert s.score == trap.WEIGHTS["vedha"]
