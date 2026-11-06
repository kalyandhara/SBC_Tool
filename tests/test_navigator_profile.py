import math

import pytest
import swisseph as swe

from sbc.engine import _julday, _utc_from_local
from sbc.navigator import profile as P

GOOD = dict(label="x", birth_date="1985-03-14", birth_time="06:30",
            tz="Asia/Kolkata", lat=12.97, lon=77.59)


def _independent_sidereal_asc(date, time, tz, lat, lon):
    """Ascendant from the textbook formula, sharing no code path with houses_ex.

    tan(Asc) = cos(RAMC) / -(sin(RAMC)*cos(eps) + tan(lat)*sin(eps)), quadrant
    fixed with atan2, then Lahiri ayanamsa subtracted.
    """
    jd = _julday(_utc_from_local(date, time, tz))
    eps = math.radians(swe.calc_ut(jd, swe.ECL_NUT)[0][0])  # true obliquity
    ramc = math.radians((swe.sidtime(jd) * 15.0 + lon) % 360.0)
    la = math.radians(lat)
    asc = math.degrees(math.atan2(
        math.cos(ramc),
        -(math.sin(ramc) * math.cos(eps) + math.tan(la) * math.sin(eps)))) % 360.0
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return (asc - swe.get_ayanamsa_ut(jd)) % 360.0


@pytest.mark.parametrize("field,bad", [
    ("birth_time", ""), ("birth_time", "25:00"), ("tz", "Mars/Olympus"),
    ("tz", ""), ("lat", 91), ("lat", -90.5), ("lon", -181), ("lon", 180.5),
    ("lat", "north"), ("lat", None), ("birth_date", "1985-13-01"),
    ("birth_date", "")])
def test_invalid_rejected(field, bad):
    with pytest.raises(ValueError):
        P.validate({**GOOD, field: bad})


@pytest.mark.parametrize("field", ["birth_date", "birth_time", "tz", "lat", "lon"])
def test_missing_field_rejected_not_defaulted(field):
    d = dict(GOOD)
    del d[field]
    with pytest.raises(ValueError):
        P.validate(d)


def test_unknown_tz_is_not_silently_kolkata():
    # engine._utc_from_local falls back to Kolkata; validate must stop it first.
    with pytest.raises(ValueError):
        P.validate({**GOOD, "tz": "Not/AZone"})


def test_error_message_does_not_echo_birth_data():
    secret = dict(GOOD, birth_date="1971-07-23", birth_time="25:61",
                  tz="Secret/Place", lat=44.4321, lon=-99.8765)
    with pytest.raises(ValueError) as ei:
        P.validate(secret)
    text = repr(ei.value) + str(ei.value.__cause__) + str(ei.value.__context__)
    for frag in ("1971", "25:61", "Secret", "44.43", "99.87"):
        assert frag not in text
    assert ei.value.__cause__ is None
    assert ei.value.__suppress_context__


def test_boundary_coordinates_accepted():
    p = P.validate({**GOOD, "lat": 90, "lon": -180})
    assert (p.lat, p.lon) == (90.0, -180.0)


def test_validate_normalises_and_defaults_label_only():
    p = P.validate({k: v for k, v in GOOD.items() if k != "label"})
    assert p.label == "Unnamed" and p.is_sample is False
    assert (p.birth_date, p.birth_time) == ("1985-03-14", "06:30:00")
    with pytest.raises(Exception):
        p.lat = 1.0  # frozen


def test_lagna_uses_coordinates_not_city():
    a = P.lagna_at("1985-03-14", "06:30", "Asia/Kolkata", 12.97, 77.59)
    b = P.lagna_at("1985-03-14", "06:30", "Asia/Kolkata", 51.5, -0.12)
    assert abs(a - b) > 1
    jd = _julday(_utc_from_local("1985-03-14", "06:30", "Asia/Kolkata"))
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    assert a == pytest.approx(
        swe.houses_ex(jd, 12.97, 77.59, b"W", swe.FLG_SIDEREAL)[1][0] % 360, abs=1e-6)


def test_lagna_matches_independent_textbook_derivation():
    # No published chart could be sourced offline, so the reference is the
    # standard ascendant formula (Meeus, Astronomical Algorithms ch.14 /
    # Swiss Ephemeris docs "Ascendant") computed from sidtime + obliquity,
    # independent of swe.houses_ex, minus the Lahiri ayanamsa.
    for args in [("1985-03-14", "06:30", "Asia/Kolkata", 12.97, 77.59),
                 ("1980-01-15", "12:00", "Asia/Kolkata", 19.076, 72.878),
                 ("2000-06-21", "03:15", "America/New_York", 40.71, -74.0)]:
        assert P.lagna_at(*args) == pytest.approx(_independent_sidereal_asc(*args), abs=0.01)


def test_lagna_pinned_value_for_sample_chart():
    assert P.lagna_at("1980-01-15", "12:00", "Asia/Kolkata", 19.076, 72.878) == \
        pytest.approx(354.561, abs=0.01)


def test_lagna_respects_timezone_conversion():
    a = P.lagna_at("1985-03-14", "06:30", "Asia/Kolkata", 12.97, 77.59)
    b = P.lagna_at("1985-03-14", "06:30", "America/New_York", 12.97, 77.59)
    assert abs(a - b) > 1


def test_natal_points_include_lagna_and_ketu_opposite_rahu():
    n = P.natal_points(P.validate(GOOD))
    assert set(n) == {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                      "Saturn", "Rahu", "Ketu", "Lagna"}
    assert abs((n["Rahu"] + 180) % 360 - n["Ketu"]) < 1e-3
    assert all(0 <= v < 360 for v in n.values())
    assert n["Lagna"] == pytest.approx(
        P.lagna_at("1985-03-14", "06:30", "Asia/Kolkata", 12.97, 77.59))


def test_natal_points_sun_pinned_sidereal():
    # 14 Mar 1985 sidereal (Lahiri) Sun is in Pisces (330-360), tropical ~353 minus ~23.7.
    sun = P.natal_points(P.validate(GOOD))["Sun"]
    assert sun == pytest.approx(329.3, abs=1.0)


def test_hash_changes_with_input():
    assert P.chart_hash(P.validate(GOOD)) != P.chart_hash(P.validate({**GOOD, "lat": 13.0}))


def test_hash_stable_and_ignores_label():
    a = P.chart_hash(P.validate(GOOD))
    assert a == P.chart_hash(P.validate({**GOOD, "label": "other"}))
    assert len(a) == 16


def test_sample_is_marked():
    assert P.SAMPLE_PROFILE.is_sample and P.SAMPLE_PROFILE.label.startswith("SAMPLE")
    assert P.validate({**GOOD, "is_sample": True}).is_sample
