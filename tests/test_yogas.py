"""Tests for sbc.yogas: Gaja Kesari evaluation + Vimshottari dasha."""

import datetime as dt

from sbc.yogas import (
    SIGN_LORDS,
    drishti_targets,
    evaluate_gaja_kesari,
    vimshottari,
)


def _chart(moon=45.0, jupiter=135.0, sun=310.0, mars=20.0, saturn=200.0,
           rahu=275.0, mercury=300.0, venus=330.0):
    return {"Sun": sun, "Moon": moon, "Jupiter": jupiter, "Mars": mars,
            "Saturn": saturn, "Rahu": rahu, "Ketu": (rahu + 180) % 360,
            "Mercury": mercury, "Venus": venus}


ACTIVE_MOON_DASHA = {"at": {"maha": "Moon", "antar": "Jupiter"}}
DORMANT_DASHA = {"at": {"maha": "Saturn", "antar": "Mercury"}}


def test_primary_kendra_conjunction_form():
    # Jupiter conjunct the Moon (same sign = 1st from Moon).
    out = evaluate_gaja_kesari(_chart(jupiter=50.0))
    assert out["present"] and out["checks"]["kendra_from_moon"] == 1
    assert any("conjunction form" in r for r in out["reasons"])


def test_primary_kendra_opposition_form():
    out = evaluate_gaja_kesari(_chart(jupiter=225.0))  # Scorpio, 7th
    assert out["present"] and out["checks"]["kendra_from_moon"] == 7


def test_primary_failure_is_absent():
    out = evaluate_gaja_kesari(_chart(jupiter=75.0))  # 2nd from Moon
    assert not out["present"] and out["tier"] == "absent"
    assert "not a Kendra" in out["reasons"][0]


def test_strong_case_with_exaltation_and_active_dasha():
    # Moon exalted (Taurus), Jupiter 4th from Moon, no malefics, dasha on.
    out = evaluate_gaja_kesari(_chart(), lagna_sign=0,
                               dasha=ACTIVE_MOON_DASHA)
    assert out["present"] and out["tier"] in ("strong", "moderate")
    assert any("Moon is exalted" in r for r in out["reasons"])
    assert any("activates the yoga" in r for r in out["reasons"])
    assert not out["checks"]["combust"]
    assert out["checks"]["afflictions"] == []


def test_combust_reduces_score():
    clean = evaluate_gaja_kesari(_chart(sun=310.0))
    burnt = evaluate_gaja_kesari(_chart(sun=130.0))  # 5 deg from Jupiter
    assert burnt["checks"]["combust"]
    assert not clean["checks"]["combust"]
    assert burnt["score"] < clean["score"]
    assert any("combust" in r for r in burnt["reasons"])


def test_debilitation_without_bhanga_is_weaker():
    # Moon in Libra (195), Jupiter debilitated in Capricorn (285) = 4th
    # from Moon; Saturn (Capricorn's dispositor) in Scorpio - NOT in a
    # Kendra from the Moon or the Lagna -> no cancellation.
    out = evaluate_gaja_kesari(_chart(moon=195.0, jupiter=285.0,
                                      mars=120.0, saturn=230.0),
                               lagna_sign=0)
    assert out["present"]
    assert out["checks"]["debilitated"]
    assert not out["checks"]["neecha_bhanga"]
    assert any("no neecha bhanga" in r for r in out["reasons"])
    assert out["tier"] in ("weak", "moderate")


def test_neecha_bhanga_via_dispositor_in_kendra():
    # Same debilitated Jupiter, but Saturn (Capricorn's dispositor)
    # conjunct the Moon (1st from Moon = Kendra) -> Neecha Bhanga
    # restores part of the score.
    out = evaluate_gaja_kesari(_chart(moon=195.0, jupiter=285.0,
                                      mars=120.0, saturn=195.0),
                               lagna_sign=0)
    assert out["checks"]["neecha_bhanga"]
    assert any("neecha bhanga" in r for r in out["reasons"])
    base = evaluate_gaja_kesari(_chart(moon=195.0, jupiter=285.0,
                                       mars=120.0, saturn=230.0),
                                lagna_sign=0)
    assert out["score"] > base["score"]


def test_malefic_afflictions():
    # Saturn in Aquarius casts its 3rd-house drishti onto Taurus (Moon).
    drishti = evaluate_gaja_kesari(_chart(saturn=335.0))
    assert any("Saturn aspects Moon" in r for r in drishti["reasons"])
    conj = evaluate_gaja_kesari(_chart(saturn=50.0))  # Saturn on Moon
    assert any("Saturn conjunct Moon" in r for r in conj["reasons"])
    assert conj["score"] < evaluate_gaja_kesari(_chart())["score"]


def test_guru_chandal_warning_on_node_conjunct_jupiter():
    out = evaluate_gaja_kesari(_chart(rahu=135.0))  # Rahu on Jupiter
    assert any("Guru-Chandal" in r for r in out["reasons"])
    assert any("Rahu conjunct Jupiter" in r
               for r in out["checks"]["afflictions"])


def test_dusthana_from_lagna_weakens():
    # Jupiter 4th from Moon but 12th from a Virgo Lagna.
    out = evaluate_gaja_kesari(_chart(), lagna_sign=5)
    assert out["checks"]["dusthana"] == "Jupiter"
    assert any("dusthana" in r for r in out["reasons"])
    clean = evaluate_gaja_kesari(_chart(), lagna_sign=0)
    assert out["score"] < clean["score"]


def test_dasha_activation_state():
    active = evaluate_gaja_kesari(_chart(), dasha=ACTIVE_MOON_DASHA)
    dormant = evaluate_gaja_kesari(_chart(), dasha=DORMANT_DASHA)
    assert active["checks"]["dasha"] == "active"
    assert dormant["checks"]["dasha"] == "dormant"
    assert active["score"] == dormant["score"] + 1.0


def test_vimshottari_balance_and_sequence():
    # Moon at 6d40' Aries = exactly halfway through Ashwini (Ketu, 7y)
    # -> born in Ketu Mahadasha with 3.5 years balance.
    dasha = vimshottari(360.0 / 27.0 * 0.5, "1990-01-01")
    assert dasha["birth_maha"] == "Ketu"
    assert abs(dasha["balance_years"] - 3.5) < 0.01
    lords = [m["lord"] for m in dasha["mahadashas"]]
    assert lords[:5] == ["Ketu", "Venus", "Sun", "Moon", "Mars"]
    # durations follow the classical years: the FIRST Mahadasha runs
    # its full span (elapsed before birth + balance after).
    m0 = dasha["mahadashas"][0]
    span = ((dt.datetime.fromisoformat(m0["end"])
             - dt.datetime.fromisoformat(m0["start"])).total_seconds()
            / 86400.0 / 365.25)
    assert abs(span - 7.0) < 0.01


def test_vimshottari_antardasha_proportions():
    dasha = vimshottari(45.0, "1990-01-01")  # Rohini -> Moon maha first
    maha = dasha["mahadashas"][0]
    assert maha["lord"] == "Moon"
    antars = maha["antardashas"]
    assert antars[0]["lord"] == "Moon" and antars[1]["lord"] == "Mars"
    total = sum((dt.datetime.fromisoformat(a["end"])
                 - dt.datetime.fromisoformat(a["start"])).total_seconds()
                for a in antars)
    maha_seconds = (dt.datetime.fromisoformat(maha["end"])
                    - dt.datetime.fromisoformat(maha["start"])).total_seconds()
    assert abs(total - maha_seconds) <= 3 * 86400.0  # per-antar day rounding


def test_drishti_targets():
    # Saturn casts 3/7/10; Jupiter 5/7/9; Mars 4/7/8.
    assert drishti_targets("Saturn", 10) == {(10 + 2) % 12, (10 + 6) % 12,
                                             (10 + 9) % 12}
    assert (3 + 6) % 12 in drishti_targets("Jupiter", 3)
    assert (3 + 3) % 12 in drishti_targets("Mars", 3)


def test_sign_lords_map():
    assert SIGN_LORDS[9] == "Saturn" and SIGN_LORDS[0] == "Mars"
