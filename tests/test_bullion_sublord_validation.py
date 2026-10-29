"""B-57 plumbing on synthetic bars only (no market data here)."""

import datetime as dt
import lzma
import struct

import numpy as np
import pytest

from sbc import bullion_sublord_validation as bv


def test_us_daylight_and_session_window():
    assert bv.us_daylight(dt.date(2026, 7, 1)) and not bv.us_daylight(dt.date(2026, 12, 1))
    assert bv.session_hours(dt.date(2026, 7, 1))[-1] == 23
    assert bv.session_hours(dt.date(2026, 12, 1))[-1] == 24


def test_bar_takes_lord_at_end_of_hour():
    # 18 Sep 2026: Mars until 10:52, Rahu from 10:52 (sheet: 10:51). Bar 10:00-11:00 -> Rahu.
    lords = bv.lords_at_hours(dt.date(2026, 9, 18), [9, 10, 11], {})
    assert lords == ["Mars", "Rahu", "Rahu"]


def test_segments_are_runs_within_sessions():
    labels = np.array([1, 1, 2, 2, 2, 1])
    values = np.array([1.0, 1.0, 0.5, 0.5, 0.5, 3.0])
    sess = np.array([0, 0, 0, 1, 1, 1])
    lab, sums, cnt, sid = bv._segments(labels, values, sess)
    assert lab.tolist() == [1, 2, 2, 1] and cnt.tolist() == [2, 1, 2, 1] and sums.tolist() == [2.0, 0.5, 1.0, 3.0]


def _session(date, lords, rets):
    return {"date": date, "hours": list(range(9, 9 + len(rets))), "ret": list(rets), "lords": list(lords)}


def test_planted_effect_is_found_and_null_is_not():
    rng = np.random.default_rng(1)
    cycle = ["Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Ketu", "Mercury"]
    planted, null = [], []
    for i in range(300):
        lords = [cycle[(i + k // 2) % 9] for k in range(15)]
        noise = rng.normal(0, 0.001, 15)
        boost = np.array([0.002 if l in ("Venus", "Jupiter") else 0.0 for l in lords])
        d = (dt.date(2015, 1, 1) + dt.timedelta(days=i)).isoformat()
        planted.append(_session(d, lords, noise + boost))
        null.append(_session(d, lords, noise))
    hit = bv.permutation_test(planted, n_perm=200)
    assert hit["p"]["raw"]["up"] < 0.01 and hit["halves"]["first"]["up"] > 0
    miss = bv.permutation_test(null, n_perm=200)
    assert miss["p"]["raw"]["up"] > 0.01


def test_fetch_decoder_reads_dukascopy_records():
    import importlib.util
    spec = importlib.util.spec_from_file_location("fd", "scripts/fetch_dukascopy.py")
    fd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fd)
    raw = lzma.compress(struct.pack(">IIIIIf", 3600, 1900500, 1901250, 1899000, 1902000, 12.5))
    rows = fd._decode(raw, dt.datetime(2014, 3, 1), "XAUUSD")
    assert rows == [(dt.datetime(2014, 3, 1, 1), 1900.5, 1902.0, 1899.0, 1901.25, 12.5)]
    with pytest.raises(ValueError):
        fd._decode(lzma.compress(struct.pack(">IIIIIf", 0, 5, 5, 5, 5, 1.0)), dt.datetime(2014, 3, 1), "XAUUSD")
