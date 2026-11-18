"""Stance rule and its T-1 inputs. Pure."""
import datetime as dt

import numpy as np
import pytest

from sbc.navigator import decision as D
from sbc.navigator import scoring as S


@pytest.mark.parametrize("band,trend,vix,stance,mult", [
    ("No Trading", "Up", "Normal", D.ASIDE, 0.0), ("Very Defensive", "Down", "Normal", D.ASIDE, 0.0),
    ("Normal", "Up", "Normal", D.LONG, 0.5), ("High Probability", "Down", "Normal", D.SHORT, 0.75),
    ("Exceptional Setup", "Up", "High", D.LONG, 0.5), ("Exceptional Setup", "Up", "Unknown", D.LONG, 1.0),
    ("High Probability", "Mixed", "Normal", D.ASIDE, 0.0)])
def test_stance_rule(band, trend, vix, stance, mult):
    out = D.stance(band, trend, vix)
    assert out["stance"] == stance and out["multiplier"] == mult and out["rule_version"] == D.RULE_VERSION


@pytest.mark.parametrize("trend,vix,stance,mult", [
    ("Up", "Normal", D.LONG, 0.5), ("Down", "High", D.SHORT, 0.25), ("Mixed", "Normal", D.ASIDE, 0.0)])
def test_control(trend, vix, stance, mult):
    assert D.control(trend, vix) == {"stance": stance, "multiplier": mult}


@pytest.mark.parametrize("now,expected", [
    (dt.datetime(2026, 11, 17, 15, 29), dt.date(2026, 11, 17)),
    (dt.datetime(2026, 11, 17, 15, 30), dt.date(2026, 11, 18)),
    (dt.datetime(2026, 11, 21, 10, 0), dt.date(2026, 11, 23)),     # Saturday
    (dt.datetime(2026, 11, 24, 10, 0), dt.date(2026, 11, 25))])    # Guru Nanak Jayanti
def test_session_for(now, expected):
    assert D.session_for(now) == expected


def test_trend_needs_fifty_closes():
    assert D.trend_of(np.arange(1, 50, dtype=float)) == "Mixed"
    assert D.trend_of(np.arange(1, 61, dtype=float)) == "Up"
    assert D.trend_of(np.arange(60, 0, -1, dtype=float)) == "Down"


def _fixture(n=700):
    days = [str(d)[:10] for d in np.busday_offset("2023-01-02", np.arange(n), roll="forward")]
    closes = 100 + 10 * np.sin(np.arange(n) / 25.0) + np.arange(n) * .01
    vix = {d: 12 + 6 * np.sin(i / 40.0) for i, d in enumerate(days)}
    return days, closes, vix


def test_inputs_ignore_rows_from_t_onward_and_vary():
    days, closes, vix = _fixture()
    seen_trend, seen_vix = set(), set()
    for k in range(320, 690, 7):
        t = days[k]
        base = D.inputs_before(days, closes, vix, t)
        shocked = closes.copy()
        shocked[k:] *= 3.0
        vix2 = {d: (v * 5 if d >= t else v) for d, v in vix.items()}
        assert D.inputs_before(days, shocked, vix2, t) == base
        seen_trend.add(base["trend"])
        seen_vix.add(base["vix"])
    assert len(seen_trend) >= 2 and len(seen_vix) >= 2


def test_missing_t_minus_1_is_stale():
    days, closes, vix = _fixture()
    t = days[400]
    cut = days[:399] + days[400:]
    keep = np.delete(closes, 399)
    assert D.inputs_before(cut, keep, vix, t)["stale"] is True
    assert D.inputs_before(days, closes, vix, t)["stale"] is False


def test_vix_unknown_when_t_minus_1_missing():
    days, _, vix = _fixture()
    assert D.vix_regime(days[:500], days[500], {d: v for d, v in vix.items() if d != days[499]}) == "Unknown"


def _gappy_fixture():
    days, closes, vix = _fixture()
    vix = dict(vix)
    missing = {days[i] for i in (300, 333, 410, 411, 520)}
    for d in missing:
        del vix[d]
    only = [d for d in ("2023-03-04", "2023-09-09", "2024-01-06", "2024-05-11") if d not in days]
    for i, d in enumerate(only):
        vix[d] = 40.0 + i                      # VIX-only dates (weekends)
    assert only and missing
    return days, vix, missing, only


def test_vix_regime_matches_vol_term_percentile():
    days, vix, missing, only = _gappy_fixture()
    checked_missing = checked_only = 0
    for k in range(260, 690):
        t = days[k]
        vlt = {d: v for d, v in vix.items() if d < t}
        pct = S.vol_percentiles_with_lead_in(days[:k + 1], vlt)[-1]
        vol, lead = S._vol_with_lead_in(days[:k + 1], vlt)
        v = vol.values[lead:][-1]
        if np.isnan(pct):
            assert v == 50.0 and D.vix_regime(days[:k], t, vix) == "Unknown"
        else:
            assert v == pytest.approx(100.0 - pct)
            assert D.vix_regime(days[:k], t, vix) == ("High" if pct >= 80 else "Normal")
        checked_missing += days[k - 1] in missing
        checked_only += 1
    assert checked_missing >= 1 and checked_only > 0


def test_vix_regime_window_differs_from_own_calendar_when_vix_only_dates():
    # a VIX-only date inside the window must not enter the percentile (session list rules)
    days, vix, missing, only = _gappy_fixture()
    k = days.index("2023-03-06") + 300
    t = days[k]
    vlt = {d: v for d, v in vix.items() if d < t}
    pct = S.vol_percentiles_with_lead_in(days[:k + 1], vlt)[-1]
    assert D.vix_regime(days[:k], t, vix) == ("Unknown" if np.isnan(pct) else ("High" if pct >= 80 else "Normal"))


def test_special_session_row_before_t_is_not_stale():
    # 2024-11-01 is a Muhurat/special session row; T = 2024-11-04, previous trading day 2024-10-31
    days = ["2024-10-30", "2024-10-31", "2024-11-01"]
    out = D.inputs_before(days, np.array([1.0, 2.0, 3.0]), {}, "2024-11-04")
    assert out["t_minus_1"] == "2024-11-01" and out["stale"] is False


def test_stale_inputs_have_unknown_vix_regime():
    # T-1 missing: the score's Vol term is neutral, so the regime must agree
    days, closes, vix = _fixture()
    k = 500

    cut = days[:k]
    t = days[k + 3]
    out = D.inputs_before(cut, closes[:k], vix, t)
    assert out["stale"] is True and out["vix"] == "Unknown"
