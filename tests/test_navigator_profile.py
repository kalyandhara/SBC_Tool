import dataclasses
import math

import pytest
import swisseph as swe

from sbc.engine import _julday, _utc_from_local
from sbc.navigator import profile as P

GOOD = {"label": "x", "birth_date": "1985-03-14", "birth_time": "06:30",
            "tz": "Asia/Kolkata", "lat": 12.97, "lon": 77.59}


def _independent_sidereal_asc(date, time, tz, lat, lon):
    """Ascendant from the textbook formula. Shares the time helpers
    (_julday/_utc_from_local) with the code under test but not houses_ex.

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


@pytest.mark.parametrize("field,bad", [
    ("birth_time", "SECRETTIME"), ("birth_date", "SECRETDATE"),
    ("tz", "Secret/Place"), ("lat", "SECRETLAT"), ("lon", "SECRETLON")])
def test_error_does_not_leak_birth_data(field, bad):
    with pytest.raises(ValueError) as ei:
        P.validate({**GOOD, field: bad})
    e = ei.value
    assert str(e) == "invalid birth data"
    assert e.__context__ is None and e.__cause__ is None
    assert "SECRET" not in repr(e) and "Secret" not in repr(e)


@pytest.mark.parametrize("bad", ["06", "06:30Z", "06:30+09:00", "06:30:15.75",
                                 "6:30", "06:30:15:00", " 06:30"])
def test_strict_time_format(bad):
    with pytest.raises(ValueError):
        P.validate({**GOOD, "birth_time": bad})


def test_time_with_seconds_accepted():
    assert P.validate({**GOOD, "birth_time": "06:30:15"}).birth_time == "06:30:15"


@pytest.mark.parametrize("date", ["1799-12-31", "2101-01-01"])
def test_date_outside_supported_range_rejected(date):
    with pytest.raises(ValueError):
        P.validate({**GOOD, "birth_date": date})


@pytest.mark.parametrize("date", ["1800-01-01", "2100-12-31"])
def test_date_range_bounds_inclusive(date):
    assert P.validate({**GOOD, "birth_date": date}).birth_date == date


@pytest.mark.parametrize("date,time", [
    ("2021-03-14", "02:30"),   # DST gap: clocks jump 02:00 -> 03:00
    ("2021-11-07", "01:30")])  # ambiguous: 01:30 occurs twice
def test_dst_gap_and_fold_rejected_never_defaulted(date, time):
    with pytest.raises(ValueError):
        P.validate({**GOOD, "tz": "America/New_York", "birth_date": date,
                    "birth_time": time})


def test_dst_neighbours_accepted():
    P.validate({**GOOD, "tz": "America/New_York", "birth_date": "2021-03-14",
                "birth_time": "03:30"})
    P.validate({**GOOD, "tz": "America/New_York", "birth_date": "2021-11-07",
                "birth_time": "02:30"})


@pytest.mark.parametrize("field,bad", [
    ("birth_date", 19850314), ("birth_time", 630), ("tz", 5), ("tz", None),
    ("lat", True), ("lon", False), ("lat", "12.97"), ("lon", [77.5]),
    ("lat", float("nan")), ("lon", float("inf")),
    ("is_sample", "yes"), ("is_sample", 1), ("is_sample", None)])
def test_wrong_types_rejected(field, bad):
    with pytest.raises(ValueError):
        P.validate({**GOOD, field: bad})


def test_int_coordinates_accepted():
    p = P.validate({**GOOD, "lat": 13, "lon": 77})
    assert (p.lat, p.lon) == (13.0, 77.0)


def test_repr_hides_birth_data():
    r = repr(P.validate({**GOOD, "label": "lbl"}))
    for frag in ("1985", "06:30", "Kolkata", "12.97", "77.59"):
        assert frag not in r


def test_boundary_coordinates_accepted():
    p = P.validate({**GOOD, "lat": 90, "lon": -180})
    assert (p.lat, p.lon) == (90.0, -180.0)


def test_validate_normalises_and_defaults_label_only():
    p = P.validate({k: v for k, v in GOOD.items() if k != "label"})
    assert p.label == "Unnamed" and p.is_sample is False
    assert (p.birth_date, p.birth_time) == ("1985-03-14", "06:30:00")
    with pytest.raises(dataclasses.FrozenInstanceError):
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
    # The published-chart lagna reference is still outstanding (tracked by the
    # controller in a separate bead); this independent check stands in. The reference is the
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
    # 14 Mar 1985 sidereal (Lahiri) Sun is in Aquarius (300-330), tropical ~353 minus ~23.7.
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


def test_sample_chart_points_pinned():
    n = P.natal_points(P.SAMPLE_PROFILE)
    for name, val in {"Sun": 270.681, "Moon": 236.4827,
                      "Rahu": 127.5644, "Ketu": 307.5644}.items():
        assert n[name] == pytest.approx(val, abs=0.01), name


def test_label_default_only_when_absent():
    assert P.validate({k: v for k, v in GOOD.items() if k != "label"}).label == "Unnamed"
    assert P.validate({**GOOD, "label": "a" * 80}).label == "a" * 80


@pytest.mark.parametrize("bad", [None, 5, ["x"], "a" * 81, "a<b", "a>b",
                                 "line\nbreak", "tab\there", "nul\x00", "bell\x07",
                                 "del\x7f", "c1\x85"])
def test_bad_label_rejected(bad):
    with pytest.raises(ValueError) as ei:
        P.validate({**GOOD, "label": bad})
    assert str(ei.value) == "invalid birth data"
    assert ei.value.__context__ is None


def _direct(tz):
    return P.Profile("x", False, "1985-03-14", "06:30:00", tz, 12.97, 77.59)


@pytest.mark.parametrize("tz", ["Not/AZone", "", None, 5])
def test_lagna_and_natal_reject_unknown_tz_without_validate(tz):
    with pytest.raises(ValueError):
        P.lagna_at("1985-03-14", "06:30", tz, 12.97, 77.59)
    with pytest.raises(ValueError):
        P.natal_points(_direct(tz))
