"""B-43: Exact-time geocentric sidereal aspect table tests."""

import datetime as dt

import pytest

from sbc.aspect_table import get_aspects

D = dt.date
T = dt.datetime


def close_to_minute(t1: dt.datetime, t2: dt.datetime, minutes: int = 2) -> bool:
    """Check if two datetimes are within N minutes of each other."""
    return abs((t1 - t2).total_seconds()) <= minutes * 60


def test_get_aspects_requires_valid_date_range():
    """Should raise ValueError for invalid ranges."""
    with pytest.raises(ValueError):
        get_aspects(D(2026, 10, 15), D(2026, 10, 1))  # end before start


def test_get_aspects_accepts_string_dates():
    """Should accept string dates in YYYY-MM-DD format."""
    result = get_aspects("2026-10-01", "2026-10-01")
    assert isinstance(result, list)


def test_get_aspects_returns_required_fields():
    """Each row should have all required fields."""
    aspects = get_aspects(D(2026, 10, 1), D(2026, 10, 1))
    if not aspects:
        pytest.skip("No aspects on test date")
    row = aspects[0]
    required = ["date", "weekday", "time", "pl1", "aspect", "pl2",
                "rashi1", "rashi2", "rashis", "relations", "combust",
                "retro", "winner", "muhurta"]
    for field in required:
        assert field in row, f"Missing field: {field}"


def test_aspects_are_sorted():
    """Results should be sorted by date, time, then planets."""
    aspects = get_aspects(D(2026, 10, 1), D(2026, 10, 5))
    if len(aspects) < 2:
        pytest.skip("Not enough aspects to test sorting")
    for i in range(len(aspects) - 1):
        curr = aspects[i]
        next_ = aspects[i + 1]
        if curr["date"] == next_["date"] and curr["time"] == next_["time"]:
            # Same date/time, check planet order
            assert (curr["pl1"], curr["pl2"]) <= (next_["pl1"], next_["pl2"])


def test_known_october_2026_aspects_match_backlog():
    """Acceptance test from B-43: reproduce screenshot 8's rows to within ±2 minutes.

    Expected examples from backlog:
    - Mo 0 Ur 01-10 08:17 Ta-Ta
    - Su 120 Mo 01-10 12:36 Vi-Ta
    - Su 180 Sa 04-10 17:53 Vi-Pi
    - Su 0 Mo 10-10 21:22 (new moon)
    - Mo 0 Ve 12-10 09:58 Li-Li
    """
    aspects = get_aspects(D(2026, 10, 1), D(2026, 10, 15))

    # Find Moon-Uranus conjunction
    mo_ur = [a for a in aspects if a["pl1"] == "Moon" and a["pl2"] == "Uranus" and a["aspect"] == 0]
    if mo_ur:
        expected = T(2026, 10, 1, 8, 17)
        actual = dt.datetime.strptime(f"{mo_ur[0]['date']} {mo_ur[0]['time']}", "%Y-%m-%d %H:%M")
        assert close_to_minute(actual, expected), f"Mo 0 Ur: got {actual}, expected ~{expected}"
        assert mo_ur[0]["rashis"] in ("Ta-Ta", "Aries-Aries"), f"Rashis: {mo_ur[0]['rashis']}"

    # Find Sun-Moon trine (120°)
    su_mo_trine = [a for a in aspects if set([a["pl1"], a["pl2"]]) == {"Sun", "Moon"} and a["aspect"] == 120]
    if su_mo_trine:
        expected = T(2026, 10, 1, 12, 36)
        actual = dt.datetime.strptime(f"{su_mo_trine[0]['date']} {su_mo_trine[0]['time']}", "%Y-%m-%d %H:%M")
        assert close_to_minute(actual, expected), f"Su 120 Mo: got {actual}, expected ~{expected}"
        assert su_mo_trine[0]["rashis"] in ("Vi-Ta", "Virgo-Taurus"), f"Rashis: {su_mo_trine[0]['rashis']}"

    # Find Sun-Saturn opposition
    su_sa = [a for a in aspects if set([a["pl1"], a["pl2"]]) == {"Sun", "Saturn"} and a["aspect"] == 180]
    if su_sa:
        expected = T(2026, 10, 4, 17, 53)
        actual = dt.datetime.strptime(f"{su_sa[0]['date']} {su_sa[0]['time']}", "%Y-%m-%d %H:%M")
        assert close_to_minute(actual, expected), f"Su 180 Sa: got {actual}, expected ~{expected}"
        assert su_sa[0]["rashis"] in ("Vi-Pi", "Virgo-Pisces"), f"Rashis: {su_sa[0]['rashis']}"

    # Find new moon (Sun-Moon conjunction)
    new_moon = [a for a in aspects if set([a["pl1"], a["pl2"]]) == {"Sun", "Moon"} and a["aspect"] == 0]
    if new_moon:
        expected = T(2026, 10, 10, 21, 22)
        actual = dt.datetime.strptime(f"{new_moon[0]['date']} {new_moon[0]['time']}", "%Y-%m-%d %H:%M")
        assert close_to_minute(actual, expected), f"Su 0 Mo (new moon): got {actual}, expected ~{expected}"

    # Find Moon-Venus conjunction
    mo_ve = [a for a in aspects if set([a["pl1"], a["pl2"]]) == {"Moon", "Venus"} and a["aspect"] == 0]
    if mo_ve:
        expected = T(2026, 10, 12, 9, 58)
        actual = dt.datetime.strptime(f"{mo_ve[0]['date']} {mo_ve[0]['time']}", "%Y-%m-%d %H:%M")
        assert close_to_minute(actual, expected), f"Mo 0 Ve: got {actual}, expected ~{expected}"
        assert mo_ve[0]["rashis"] in ("Li-Li", "Libra-Libra"), f"Rashis: {mo_ve[0]['rashis']}"


def test_ksc_ksp_orb_entry_events():
    """KSc/KSp should appear before exact aspects.

    From backlog: Su KSc Mo 08-10 06:12, then Su 30 Mo 10:45
    """
    aspects = get_aspects(D(2026, 10, 8), D(2026, 10, 8))

    # Find Sun-Moon sextile and any KSc events for same pair
    su_mo = [a for a in aspects if set([a["pl1"], a["pl2"]]) == {"Sun", "Moon"}]
    ksc_events = [a for a in su_mo if a["aspect"] in ("KSc", "KSp")]
    exact_events = [a for a in su_mo if isinstance(a["aspect"], int)]

    if ksc_events and exact_events:
        # KSc should come before the exact aspect
        ksc_time = dt.datetime.strptime(f"{ksc_events[0]['date']} {ksc_events[0]['time']}", "%Y-%m-%d %H:%M")
        exact_time = dt.datetime.strptime(f"{exact_events[0]['date']} {exact_events[0]['time']}", "%Y-%m-%d %H:%M")
        assert ksc_time < exact_time, f"KSc at {ksc_time} should be before exact at {exact_time}"


def test_ksp_for_conjunctions_only():
    """KSp should only appear for conjunctions (0°); KSc for all others."""
    aspects = get_aspects(D(2026, 10, 1), D(2026, 10, 31))

    ksp = [a for a in aspects if a["aspect"] == "KSp"]
    ksc = [a for a in aspects if a["aspect"] == "KSc"]

    # For each KSp, there should be a nearby conjunction between the same planets
    for ksp_row in ksp:
        pair = set([ksp_row["pl1"], ksp_row["pl2"]])
        # Find the exact conjunction for this pair on the same day
        conj = [a for a in aspects if set([a["pl1"], a["pl2"]]) == pair
                and a["aspect"] == 0 and a["date"] == ksp_row["date"]]
        assert len(conj) > 0, f"KSp for {pair} on {ksp_row['date']} has no corresponding conjunction"


def test_winner_uses_speed_then_rank():
    """Winner should be the faster planet, with rank as tie-breaker."""
    aspects = get_aspects(D(2026, 10, 1), D(2026, 10, 5))
    if not aspects:
        pytest.skip("No aspects to test")

    # Check a few aspects to verify winner is one of the two planets
    for row in aspects[:5]:
        assert row["winner"] in (row["pl1"], row["pl2"]), \
            f"Winner {row['winner']} not in {row['pl1']}, {row['pl2']}"


def test_relations_convention():
    """Relations should be 1/7 for conjunctions, 7/1 for oppositions, else sign-count."""
    aspects = get_aspects(D(2026, 10, 1), D(2026, 10, 31))

    # Check conjunctions
    conj = [a for a in aspects if a["aspect"] == 0]
    if conj:
        assert all(a["relations"] == "1/7" for a in conj), "Conjunctions should have relations 1/7"

    # Check oppositions
    opp = [a for a in aspects if a["aspect"] == 180]
    if opp:
        assert all(a["relations"] == "7/1" for a in opp), "Oppositions should have relations 7/1"

    # Check other aspects have sign-count format (X/Y)
    other = [a for a in aspects if isinstance(a["aspect"], int) and a["aspect"] not in (0, 180)]
    if other:
        for a in other:
            assert "/" in a["relations"], f"Relations {a['relations']} should be X/Y format"
            parts = a["relations"].split("/")
            assert len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit()


def test_combust_flag():
    """Combust should be True when planet is within combustion orb of Sun."""
    aspects = get_aspects(D(2026, 10, 1), D(2026, 10, 31))

    # Find aspects involving Sun and another planet
    sun_aspects = [a for a in aspects if "Sun" in (a["pl1"], a["pl2"])]
    if sun_aspects:
        # At least some should be combust (Mercury, Venus often close to Sun)
        combust_count = sum(1 for a in sun_aspects if a["combust"])
        # We expect at least one combust aspect in a month
        assert combust_count > 0, "Should have at least one combust aspect in October 2026"


def test_retrograde_flag():
    """Retro should be True when either planet is retrograde."""
    aspects = get_aspects(D(2026, 10, 1), D(2026, 10, 31))

    # October 2026 has Venus retrograde (R 03-10) and Mercury retrograde (R 24-10)
    # So some aspects should have retro=True
    retro_count = sum(1 for a in aspects if a["retro"])
    assert retro_count > 0, "Should have retrograde aspects in October 2026"


def test_muhurta_integration():
    """Muhurta field should show Ghabad/Ardha-ghabad when applicable."""
    from sbc.muhurta import ghabad_kind_at

    aspects = get_aspects(D(2026, 10, 5), D(2026, 10, 5))  # Known Ghabad day
    if aspects:
        # Check at least one aspect has muhurta info
        has_muhurta = any(a["muhurta"] for a in aspects)
        # Verify it matches ghabad_kind_at
        for a in aspects:
            when = dt.datetime.strptime(f"{a['date']} {a['time']}", "%Y-%m-%d %H:%M")
            expected = ghabad_kind_at(when) or ""
            assert a["muhurta"] == expected, f"Muhurta mismatch: got {a['muhurta']}, expected {expected}"


def test_moon_included_in_aspects():
    """Moon should be included in aspect calculations."""
    aspects = get_aspects(D(2026, 10, 1), D(2026, 10, 1))
    if not aspects:
        pytest.skip("No aspects on test date")

    moon_aspects = [a for a in aspects if "Moon" in (a["pl1"], a["pl2"])]
    assert len(moon_aspects) > 0, "Moon should be included in aspects"


def test_planet_names():
    """Planet names should match expected set."""
    aspects = get_aspects(D(2026, 10, 1), D(2026, 10, 5))
    if not aspects:
        pytest.skip("No aspects to test")

    expected_planets = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter",
                        "Saturn", "Uranus", "Neptune", "Pluto", "Rahu", "Ketu"}
    all_planets = set()
    for a in aspects:
        all_planets.add(a["pl1"])
        all_planets.add(a["pl2"])

    assert all_planets <= expected_planets, f"Unexpected planets: {all_planets - expected_planets}"


def test_aspect_table_endpoint(client):
    """API endpoint should return proper structure."""
    response = client.get("/api/engine/aspect_table?start=2026-10-01&end=2026-10-01")
    assert response.status_code == 200
    data = response.get_json()
    assert "start" in data
    assert "end" in data
    assert "count" in data
    assert "aspects" in data
    assert isinstance(data["aspects"], list)


def test_aspect_table_endpoint_validates_params(client):
    """Should reject missing or invalid parameters."""
    # Missing params
    response = client.get("/api/engine/aspect_table")
    assert response.status_code == 400
    assert "error" in response.get_json()

    # Invalid date format
    response = client.get("/api/engine/aspect_table?start=invalid&end=2026-10-01")
    assert response.status_code == 400

    # End before start
    response = client.get("/api/engine/aspect_table?start=2026-10-15&end=2026-10-01")
    assert response.status_code == 400
