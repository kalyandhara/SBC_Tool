"""B-58 plumbing on synthetic data (no market results here)."""

import numpy as np

from sbc import transit_event_validation as tv

DATES = ["2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08", "2026-01-09", "2026-01-12"]


def test_event_moves_to_next_session():
    assert tv.session_index(DATES, "2026-01-03") == 1  # Saturday -> Monday
    assert tv.session_index(DATES, "2026-01-13") is None


def test_window_counts_sessions_not_days():
    flag = tv.window_flags(DATES, ["2026-01-03"], 1)
    assert flag.tolist() == [True, True, True, False, False, False, False]
    assert not tv.window_flags(DATES, ["2025-12-01"], 3).any()  # before the sample


def test_signals_follow_the_registration():
    closes = np.linspace(100, 110, len(DATES))
    events = [
        {"date": "2026-01-06", "type": "station", "body": "Mercury", "kind": "Retrograde"},
        {"date": "2026-01-08", "type": "aspect", "aspect": "trine", "body": "Mars", "other": "Jupiter"},
        {"date": "2026-01-08", "type": "aspect", "aspect": "square", "body": "Venus", "other": "Saturn"},
        {"date": "2026-01-12", "type": "eclipse", "kind": "Solar"},
        {"date": "2026-01-02", "type": "ingress", "body": "Jupiter", "sign": "Leo"},
        {"date": "2026-01-02", "type": "ingress", "body": "Mars", "sign": "Leo"},
    ]
    entries, _any, counts, _shares = tv.signals(DATES, closes, events)
    names = [e["name"] for e in entries]
    assert names == ["h1_mercury_station_volatility", "h2_mercury_retrograde_down",
                     "h3_tense_mars_saturn_pluto_volatility", "h4_eclipse_volatility",
                     "h5_jupiter_saturn_ingress_reversal"]
    assert counts == {"mercury_stations": 1, "tense_aspects": 1, "eclipses": 1, "jupiter_saturn_ingresses": 1}
    h3 = entries[2]["signal"]
    assert h3.tolist() == [False, False, True, True, True, True, True]  # +-2 around 01-08
    assert set(np.unique(entries[1]["signal"])) <= {-1.0, 0.0}
