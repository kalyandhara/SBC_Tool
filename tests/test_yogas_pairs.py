"""Tests for the two-planet conjunction yogas (pairs + detect_all)."""


from sbc.yogas import (
    YOGAS,
    detect_all,
    evaluate_budha_aditya,
    evaluate_chandra_aditya,
    evaluate_chandra_mangal,
    evaluate_guru_chandal,
    evaluate_punarphoo,
    evaluate_shrapit,
)


def _chart(moon=45.0, jupiter=135.0, sun=310.0, mars=20.0, saturn=200.0,
           rahu=275.0, mercury=300.0, venus=330.0):
    return {"Sun": sun, "Moon": moon, "Jupiter": jupiter, "Mars": mars,
            "Saturn": saturn, "Rahu": rahu, "Ketu": (rahu + 180) % 360,
            "Mercury": mercury, "Venus": venus}


# --- Budha-Aditya (Sun + Mercury) -----------------------------------

def test_budha_aditya_present_absent():
    out = evaluate_budha_aditya(_chart(sun=120.0, mercury=125.0),
                                lagna_sign=0)
    assert out["present"] and out["tier"] != "absent"
    assert any("conjunct" in r for r in out["reasons"])
    away = evaluate_budha_aditya(_chart(sun=120.0, mercury=300.0))
    assert not away["present"] and away["tier"] == "absent"


def test_budha_aditya_dignity_vs_debilitation():
    dignified = evaluate_budha_aditya(_chart(sun=150.0, mercury=155.0))
    debil = evaluate_budha_aditya(_chart(sun=335.0, mercury=330.0))
    assert any("exalted" in r for r in dignified["reasons"])
    assert any("debilitated" in r for r in debil["reasons"])
    assert dignified["score"] > debil["score"]


def test_budha_aditya_deep_combust_penalty():
    near = evaluate_budha_aditya(_chart(sun=120.0, mercury=125.0))
    deep = evaluate_budha_aditya(_chart(sun=120.0, mercury=122.0))
    assert any("deeply combust" in r for r in deep["reasons"])
    assert deep["score"] < near["score"]


# --- Guru-Chandal (Jupiter + Rahu/Ketu) ------------------------------

def test_guru_chandal_present_with_rahu_and_ketu_variants():
    out = evaluate_guru_chandal(_chart(jupiter=135.0, rahu=140.0))
    assert out["present"]
    assert any("unorthodox" in r for r in out["reasons"])
    ketu = evaluate_guru_chandal(_chart(jupiter=135.0, rahu=315.0))
    assert ketu["present"]
    assert any("Ketu variant" in r for r in ketu["reasons"])


def test_guru_chandal_absent_when_separated():
    out = evaluate_guru_chandal(_chart(jupiter=135.0, rahu=275.0))
    assert not out["present"]


def test_guru_chandal_dignity_and_drishti_soften():
    raw = evaluate_guru_chandal(_chart(jupiter=135.0, rahu=140.0))
    dignified = evaluate_guru_chandal(_chart(jupiter=255.0, rahu=260.0))
    softened = evaluate_guru_chandal(_chart(jupiter=255.0, rahu=260.0,
                                            venus=75.0))
    assert dignified["score"] < raw["score"]
    assert softened["score"] < dignified["score"]


# --- Chandra-Mangal (Moon + Mars) ------------------------------------

def test_chandra_mangal_waxing_beats_waning():
    waxing = evaluate_chandra_mangal(_chart(sun=310.0, mars=50.0))
    waning = evaluate_chandra_mangal(_chart(sun=110.0, mars=50.0))
    assert waxing["present"] and waning["present"]
    assert any("Shukla" in r for r in waxing["reasons"])
    assert waxing["score"] > waning["score"]


def test_chandra_mangal_absent():
    out = evaluate_chandra_mangal(_chart(mars=200.0))
    assert not out["present"]


# --- Shrapit (Saturn + Rahu) -----------------------------------------

def test_shrapit_present_and_dignity_softens():
    raw = evaluate_shrapit(_chart(saturn=230.0, rahu=235.0))
    dignified = evaluate_shrapit(_chart(saturn=285.0, rahu=280.0))
    assert raw["present"] and dignified["present"]
    assert raw["yoga"] == "shrapit"
    assert any("softened" in r for r in dignified["reasons"])
    assert dignified["score"] < raw["score"]


def test_shrapit_absent():
    out = evaluate_shrapit(_chart(rahu=135.0))
    assert not out["present"]


# --- Punarphoo (Moon + Saturn) ---------------------------------------

def test_punarphoo_present_absent_and_softening():
    out = evaluate_punarphoo(_chart(saturn=50.0))
    assert out["present"]
    assert any("delays" in r for r in out["reasons"])
    softened = evaluate_punarphoo(_chart(saturn=50.0, venus=215.0))
    assert softened["score"] < out["score"]
    away = evaluate_punarphoo(_chart(saturn=200.0))
    assert not away["present"]


# --- Chandra-Aditya (Sun + Moon) --------------------------------------

def test_chandra_aditya_separation_matters():
    separated = evaluate_chandra_aditya(_chart(sun=120.0, moon=135.0))
    deep = evaluate_chandra_aditya(_chart(sun=120.0, moon=126.0))
    assert separated["present"] and deep["present"]
    assert any("near-Amavasya" in r for r in deep["reasons"])
    assert deep["score"] < separated["score"]


def test_chandra_aditya_absent():
    out = evaluate_chandra_aditya(_chart(moon=45.0))
    assert not out["present"]


# --- registry + detect_all -------------------------------------------

def test_registry_has_all_seven():
    expected = {"gaja_kesari", "budha_aditya", "guru_chandal",
                "chandra_mangal", "shrapit", "punarphoo", "chandra_aditya"}
    assert set(YOGAS) == expected


def test_detect_all_runs_every_yoga_on_a_chart():
    out = detect_all("nifty")
    names = {k for k in out if k not in ("summary",)}
    assert names == set(YOGAS)
    for name in names:
        assert {"yoga", "present", "tier", "score",
                "reasons"} <= set(out[name])
    assert out["summary"]["present"]  # gaja_kesari is present on this chart
