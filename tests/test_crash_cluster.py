"""Tests for the Crash Cluster Index (pre-registered 2026-11-19)."""

import datetime as dt

import numpy as np

from sbc import crash_cluster as cc
from sbc.planetary_event_timeline import episode_starts, max_drawdown, realized_volatility


def _weekdays(start, end):
    d, out = dt.date.fromisoformat(start), []
    while d <= dt.date.fromisoformat(end):
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += dt.timedelta(1)
    return out


class TestSkyFamilies:
    def test_backdrop_applying_saturn_uranus_square(self):
        assert cc.sky_flags("2021-02-10")["B"]  # Saturn-Uranus 90.68 deg, applying

    def test_backdrop_needs_applying(self):
        assert not cc.sky_flags("2021-02-20")["B"]  # 89.8 deg but separating

    def test_backdrop_saturn_neptune_conjunction(self):
        assert cc.sky_flags("2026-01-20")["B"]  # 2.29 deg, applying

    def test_trigger_mars_saturn_applying(self):
        f = cc.sky_flags("2000-04-14")  # Mars-Saturn conjunction 1.01 deg, applying
        assert f["T_mars_saturn"]

    def test_trigger_mars_uranus_without_applying(self):
        f = cc.sky_flags("2000-04-20")  # Mars-Saturn 2.54 separating; Mars-Uranus square 0.02
        assert not f["T_mars_saturn"]
        assert f["T_mars_uranus"]

    def test_quiet_day(self):
        f = cc.sky_flags("2019-01-01")
        assert not (f["B"] or f["T_mars_saturn"] or f["T_mars_uranus"] or f["T_mars_pluto"])


class TestWindows:
    def test_mars_station_within_three_sessions(self):
        s = _weekdays("2020-08-31", "2020-09-25")  # Mars stations retrograde 2020-09-10
        out = cc.compute(s)
        i = s.index("2020-09-10")
        assert all(out["T_mars_station"][i - 3:i + 4])
        assert not out["T_mars_station"][i - 4] and not out["T_mars_station"][i + 4]

    def test_eclipse_within_ten_days(self):
        s = _weekdays("2021-05-10", "2021-05-31")  # lunar eclipse 2021-05-26
        out = cc.compute(s)
        assert out["W_eclipse"][s.index("2021-05-17")]   # 9 days before
        assert not out["W_eclipse"][s.index("2021-05-14")]  # 12 days before, 27 before 06-10

    def test_outer_station_within_five_sessions(self):
        s = _weekdays("2020-05-01", "2020-05-29")  # Saturn stations retrograde 2020-05-11
        out = cc.compute(s)
        i = s.index("2020-05-11")
        assert out["W_station"][i + 5] and not out["W_station"][i + 6]


class TestIndex:
    def test_one_vote_per_family(self):
        # Sept 2020: Mars station (09-10) overlaps a Mars-Saturn square on 09-14/15.
        out = cc.compute(_weekdays("2020-08-31", "2020-10-09"))
        fam = out["B"].astype(int) + out["T"].astype(int) + out["W"].astype(int)
        assert np.array_equal(out["cci"], fam)
        assert out["cci"].max() <= 3
        multi_t = (out["T_mars_saturn"].astype(int) + out["T_mars_uranus"] + out["T_mars_pluto"]
                   + out["T_mars_station"]) >= 2
        assert multi_t.any()
        assert np.all(out["T"][multi_t])

    def test_fire_and_episodes(self):
        out = cc.compute(_weekdays("2000-03-20", "2000-05-10"))
        assert np.array_equal(out["fire"], out["cci"] == 3)
        assert np.array_equal(out["episode_start"], episode_starts(out["fire"]))

    def test_deterministic(self):
        s = _weekdays("2020-01-01", "2020-03-31")
        a, b = cc.compute(s), cc.compute(s)
        for k in a:
            assert np.array_equal(a[k], b[k])

    def test_sky_offset_shifts_the_sky(self):
        s = _weekdays("2021-01-04", "2021-01-29")
        out = cc.compute(s, sky_offset_days=37)
        for i, d in enumerate(s):
            shifted = (dt.date.fromisoformat(d) + dt.timedelta(37)).isoformat()
            assert out["B"][i] == cc.sky_flags(shifted)["B"]


class TestHarnessOutcomes:
    def test_max_drawdown(self):
        dd = max_drawdown([100.0, 110.0, 90.0, 95.0, 120.0], 2)
        assert np.isclose(dd[0], -0.10)
        assert np.isclose(dd[1], 90 / 110 - 1)
        assert np.isclose(dd[2], 95 / 90 - 1)
        assert np.isnan(dd[3]) and np.isnan(dd[4])

    def test_realized_volatility(self):
        vol = realized_volatility([100.0 * 1.01 ** k for k in range(6)], 3)
        assert np.allclose(vol[:3], 0.0)
        assert np.isnan(vol[3])
