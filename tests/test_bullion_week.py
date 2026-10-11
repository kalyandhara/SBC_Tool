"""Weekly bullion brief (sbc.bullion_week, B-56) against a published daily sheet."""

import datetime as dt

import pytest

from sbc import bullion_week as bw

D = dt.date


def minutes(hm):
    h, m = map(int, hm.split(":"))
    return h * 60 + m


def near(a, b, tol=2):
    return abs(minutes(a) - minutes(b)) <= tol


@pytest.fixture(scope="module")
def sep18():
    return bw.day_block(D(2026, 9, 18))


# Source: "Bullion Trading Strategy" sheet for Friday 18 Sep 2026 (IST).
def test_rahu_kaal_matches_sheet(sep18):
    assert near(sep18["rahu_kaal"]["from"], "11:02")
    assert near(sep18["rahu_kaal"]["to"], "12:33")


@pytest.mark.parametrize("lord,start", [("Jupiter", "10:30"), ("Jupiter", "17:37"),
                                        ("Mercury", "14:34"), ("Mercury", "21:35")])
def test_horas_match_sheet(sep18, lord, start):
    assert any(h["lord"] == lord and near(h["from"], start) for h in sep18["horas"])


def test_moon_transit_matches_sheet(sep18):
    got = {(p["nakshatra"], p["pada"]): p["time"] for p in sep18["padas"]}
    assert near(got[("Jyeshtha", 3)], "09:17")
    assert near(got[("Jyeshtha", 4)], "16:00")
    assert near(got[("Mula", 1)], "22:44")


@pytest.mark.parametrize("start,lord", [("05:42", "Sun"), ("07:02", "Moon"), ("09:17", "Mars"),
                                        ("10:51", "Rahu"), ("14:52", "Jupiter"), ("18:28", "Saturn"),
                                        ("22:44", "Ketu")])
def test_sub_lord_timeline_matches_sheet(sep18, start, lord):
    assert any(s["lord"] == lord and near(s["from"], start, 3) for s in sep18["subs"])


def test_lahiri_survives_kp_global_mode():
    """kp_ephemeris sets the Krishnamurti mode globally; our timings must not move."""
    from sbc import kp_ephemeris
    first = bw.day_block(D(2026, 9, 18))["subs"]
    kp_ephemeris.chart_at(dt.datetime(2026, 9, 18, 9, 15))
    assert bw.day_block(D(2026, 9, 18))["subs"] == first


def test_sub_lords_follow_vimshottari_order():
    # First sub of every nakshatra is its own lord; Mula (Ketu star) starts with Ketu.
    assert bw.sub_lord(18 * 360 / 27 + 0.01) == "Ketu"
    assert bw.sub_lord(0.01) == "Ketu" and bw.sub_lord(360 / 27 + 0.01) == "Venus"


def test_no_duplicate_pada_rows():
    padas = bw.day_block(D(2026, 10, 15))["padas"]
    keys = [(p["nakshatra"], p["pada"]) for p in padas]
    assert len(keys) == len(set(keys))


def test_build_week_shape(tmp_path, monkeypatch):
    econ = tmp_path / "econ.json"
    econ.write_text('[{"date":"2026-10-14","time":"18:00","name":"US CPI (Sep)"},'
                    '{"date":"2026-10-21","time":"18:00","name":"next week"}]')
    real = bw.econ_events
    monkeypatch.setattr(bw, "econ_events", lambda monday: real(monday, econ))
    w = bw.build(D(2026, 10, 14))  # a Wednesday: snaps back to Monday
    assert w["week_of"] == "2026-10-12" and len(w["days"]) == 5
    assert [e["name"] for e in w["econ"]] == ["US CPI (Sep)"]
    assert any(e["text"] == "Sun enters Libra" for e in w["events"])



def test_binomial_p_value():
    assert bw._binom_two_sided(25, 50, 0.5) == pytest.approx(1.0)
    assert bw._binom_two_sided(40, 50, 0.5) < 0.001


def test_track_record_counts_only_earlier_sessions(tmp_path, monkeypatch):
    csv = tmp_path / "gold_ohlc.csv"
    csv.write_text("Date,Open,High,Low,Close,Volume\n2026-09-01,1,1,1,100,0\n2026-09-02,1,1,1,101,0\n"
                   "2026-09-03,1,1,1,100,0\n2026-09-04,1,1,1,102,0\n")
    monkeypatch.setattr(bw, "DATA_DIR", tmp_path)
    bw._closes.cache_clear()
    bw._session_naks.cache_clear()
    try:
        t = bw.track_record(["Ashwini"], D(2026, 9, 4))
        assert t["gold"]["as_of"] == "2026-09-03"
        assert t["gold"]["sessions_in_base"] == 2
        assert t["silver"] == {"available": False}
    finally:
        bw._closes.cache_clear()
        bw._session_naks.cache_clear()


def test_endpoint(client):
    r = client.get("/api/engine/bullion-week?start=2026-10-12")
    assert r.status_code == 200
    body = r.get_json()
    assert body["week_of"] == "2026-10-12" and body["days"][0]["weekday"] == "Monday"
    assert client.get("/api/engine/bullion-week?start=nope").status_code == 400
