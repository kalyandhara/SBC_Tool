"""Swiss Ephemeris KP data generator (sbc.kp_ephemeris)."""

import csv
import datetime as dt

import pytest

from sbc import kp_ephemeris as k
from sbc.kp_intraday import assess_kp_data, generate_kp_intraday_report


def _dms(d, m, s=0):
    return d + m / 60 + s / 3600


# Standard KP sub table for Ashwini (0deg-13deg20' Aries): sub ends.
ASHWINI_SUBS = [
    (_dms(0, 46, 40), "Ketu"), (_dms(3, 0), "Venus"), (_dms(3, 40), "Sun"),
    (_dms(4, 46, 40), "Moon"), (_dms(5, 33, 20), "Mars"), (_dms(7, 33, 20), "Rahu"),
    (_dms(9, 20), "Jupiter"), (_dms(11, 26, 40), "Saturn"), (_dms(13, 20), "Mercury"),
]


@pytest.mark.parametrize("end,lord", ASHWINI_SUBS)
def test_sub_lords_match_kp_table(end, lord):
    assert k.kp_point(end - 0.01)["sublord"] == lord


def test_star_and_sub_start_with_star_lord():
    p = k.kp_point(_dms(13, 21))  # just inside Bharani
    assert p["star"] == "Bharani" and p["star_lord"] == "Venus"
    assert p["sublord"] == "Venus" and p["sub_sublord"] == "Venus"


def test_sky_on_2026_10_01_matches_lahiri_engine():
    """KP and Lahiri differ by ~6 arcmin, so stars agree away from edges."""
    from sbc.planets import positions
    import swisseph as swe
    when = dt.datetime(2026, 10, 1, 9, 15)
    chart = k.chart_at(when)
    utc = when - k.IST
    lahiri, _ = positions(swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute / 60))
    by_name = {p["name"]: p for p in lahiri}
    for name in ("Sun", "Moon", "Mars", "Jupiter", "Saturn"):
        diff = (chart["lons"][name] - by_name[name]["longitude"]) % 360
        # Lahiri's ayanamsa is ~5.8' larger, so KP longitudes run ~0.097 deg ahead.
        assert 0.05 < diff < 0.15, (name, diff)
    assert k.kp_point(chart["lons"]["Moon"])["star"] == "Rohini"
    assert k.kp_point(chart["asc"])["sign"] == "Libra"


def test_horas_follow_weekday_lord_and_chaldean_order():
    sched = k.hora_schedule(dt.date(2026, 10, 1))  # Thursday
    assert sched[0][1] == "Jupiter"
    assert [lord for _, lord in sched[:4]] == ["Jupiter", "Mars", "Sun", "Venus"]
    assert dt.time(6, 0) < sched[0][0].time() < dt.time(7, 0)


def test_house_sets_are_valid_and_strength_matches_convention():
    chart = k.chart_at(dt.datetime(2026, 10, 1, 11, 0))
    for p in k.PLANETS:
        hs = k.house_set_for(k.kp_point(chart["lons"][p])["sublord"], chart)
        assert hs and all(1 <= h <= 12 for h in hs) and hs == sorted(set(hs))
    assert k.house_set_strength([2, 11]) == 2.5
    assert k.house_set_strength([8, 12]) == -2.5


def test_generated_month_passes_sanity_check_and_feeds_report(tmp_path):
    path = tmp_path / "KP_Data_Oct2026.csv"
    days = {dt.date(2026, 10, 1), dt.date(2026, 10, 2)}
    info = k.generate_kp_month(2026, 10, path, step_minutes=15,
                               holidays={d for d in k.trading_days(2026, 10)} - days)
    assert info["days"] == 2
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows and list(rows[0].keys()) == k.COLUMNS
    assert assess_kp_data(rows)["synthetic"] is False
    report = generate_kp_intraday_report(path, dt.date(2026, 10, 1))
    ds = report.day_signature
    assert ds.day_lord == "Jupiter" and ds.moon_star == "Rohini"
    # Thursday (Jupiter, benefic) + Moon star lord Moon (benefic) => +2
    assert ds.day_bias_score == 2.0
    lords = [h.lord for h in ds.hora_slots]
    assert len(lords) == len(set(zip(lords, [h.start for h in ds.hora_slots])))
    assert all(a.lord != b.lord for a, b in zip(ds.hora_slots, ds.hora_slots[1:]))
    assert report.data_quality["synthetic"] is False


def test_generate_endpoint_refuses_to_overwrite_real_data(client):
    """data/kp/KP_Data_Oct2026.csv is ephemeris data now: no overwrite without force."""
    resp = client.post("/api/kp_intraday_sample", json={"date": "2026-10-01"})
    assert resp.status_code == 409
    assert "ephemeris" in resp.get_json()["error"]
