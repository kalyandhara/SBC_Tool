import datetime as dt
from sbc.yogas import vimshottari


def _d(s):
    return dt.datetime.fromisoformat(s)


def test_pratyantars_partition_each_antar():
    v = vimshottari(100.0, "1980-05-05", "2020-01-01")
    antar = v["mahadashas"][1]["antardashas"][2]
    p = antar["pratyantars"]
    assert len(p) == 9 and p[0]["lord"] == antar["lord"]
    assert abs((_d(p[-1]["end"]) - _d(antar["end"])).total_seconds()) < 2
    assert all(a["end"] == b["start"] for a, b in zip(p, p[1:]))


def test_at_names_pratyantar():
    assert vimshottari(100.0, "1980-05-05", "2020-01-01")["at"]["pratyantar"] is not None


ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter",
         "Saturn", "Mercury"]
YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
         "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}


def _days(a, b):
    return (_d(b) - _d(a)).total_seconds() / 86400.0


def test_pratyantar_lord_order_and_lengths():
    v = vimshottari(100.0, "1980-05-05", "2020-01-01")
    antar = v["mahadashas"][1]["antardashas"][2]
    p = antar["pratyantars"]
    start = ORDER.index(antar["lord"])
    expected = [ORDER[(start + i) % 9] for i in range(9)]
    assert [x["lord"] for x in p] == expected
    antar_days = _days(antar["start"], antar["end"])
    # first pratyantar = antar length * its years / 120
    assert _days(p[0]["start"], p[0]["end"]) == \
        __import__("pytest").approx(antar_days * YEARS[expected[0]] / 120.0,
                                    rel=1e-6)
    # unequal pair: second lord has different years, so different length
    d0 = _days(p[0]["start"], p[0]["end"])
    d1 = _days(p[1]["start"], p[1]["end"])
    assert d0 != d1
    assert d1 / d0 == __import__("pytest").approx(
        YEARS[expected[1]] / YEARS[expected[0]], rel=1e-6)


def test_at_pratyantar_concrete_value():
    # Derivation: Moon 100.0 deg / 13.333 = 7.5 -> nakshatra index 7
    # (Pushya) -> Saturn (19y) start lord, half elapsed, so 9.5y remain
    # at birth 1980-05-05. Saturn ends ~1989-11, Mercury (17y) ~2006-11,
    # Ketu (7y) ~2013-11-04, then Venus (20y). 2020-01-01 is ~6.15y into
    # Venus. Venus antars (20y*x/120): Venus 3.33, Sun 1.00, Moon 1.67,
    # Mars 1.17 -> cumulative 3.33/4.33/6.00/7.17, so 6.15y is in Mars,
    # ~0.15y (~55 days) in. Mars antar = 1.1667y = 426d; pratyantars
    # from Mars: Mars 7/120*426 = 24.9d, Rahu 18/120*426 = 63.9d
    # (cumulative 88.8d). 55 days falls in Rahu.
    at = vimshottari(100.0, "1980-05-05", "2020-01-01")["at"]
    assert (at["maha"], at["antar"], at["pratyantar"]) == \
        ("Venus", "Mars", "Rahu")
