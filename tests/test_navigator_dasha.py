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
