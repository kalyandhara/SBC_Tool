import datetime as dt

import pytest

from sbc import market_holidays as MH
from sbc.navigator import forecast as F


def test_rank_top_and_low_with_ties_to_earlier_date():
    days = ["d0", "d1", "d2", "d3", "d4"]
    scores = [50, 60, 60, 40, 40]
    top, low = F.rank(days, scores, n=3)
    assert top == [1, 2, 0]
    assert low == [3, 4, 0]


def test_rank_caps_at_n():
    top, low = F.rank(list("abcdef"), [1, 2, 3, 4, 5, 6], n=2)
    assert top == [5, 4] and low == [0, 1]


def test_sessions_stay_within_window_and_are_trading_days():
    out = F.sessions_for(30, "2026-11-06")
    assert out[0] > "2026-11-06"
    assert all(d <= "2026-12-06" for d in out)
    assert all(MH.is_trading_day(dt.date.fromisoformat(d)) for d in out)
    assert 15 <= len(out) <= 23


def test_bad_window_rejected():
    with pytest.raises(ValueError):
        F.build(None, None, 45)  # type: ignore[arg-type]
