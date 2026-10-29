"""Sector rotation report: build on a frozen series, JSON contents, and the CLI guard."""

import datetime as dt

import numpy as np
import pytest

from scripts import sector_rotation_report as rep
from sbc import sector_rotation as sr


def _series(seed=0):
    """Frozen synthetic daily closes for NIFTY and every sector; weekdays 2019-2020."""
    rng = np.random.default_rng(seed)
    days = [d.isoformat() for d in (dt.date(2019, 1, 1) + dt.timedelta(i) for i in range(730))
            if d.weekday() < 5]
    out = {}
    for key in ["NIFTY"] + list(rep.SECTOR_KEYS):
        level = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(days))))
        out[key] = [{"date": d, "close": float(c)} for d, c in zip(days, level, strict=True)]
    return out


def test_build_is_reproducible_on_frozen_series():
    a = rep.build(series=_series())
    b = rep.build(series=_series())
    assert a == b


def test_build_refuses_without_preregistration(monkeypatch, tmp_path):
    monkeypatch.setattr(rep, "PREREG", tmp_path / "missing.md")
    with pytest.raises(FileNotFoundError):
        rep.build(series=_series())


def test_json_has_counts_coverage_and_input_record():
    out = rep.build(series=_series())
    assert out["events"]["SOLAR_ECLIPSE"]["raw"] >= out["events"]["SOLAR_ECLIPSE"]["clusters"] >= 1
    assert set(out["coverage"]) == set(rep.SECTOR_KEYS)
    assert out["input"]["price_sha256"]
    assert out["input"]["last_session"]["NIFTY"] == _series()["NIFTY"][-1]["date"]
    assert out["confirmatory"] == []
    assert out["breadth"] == "not computed"


def test_forecast_is_no_call_everywhere_without_confirmatory_pass():
    out = rep.build(series=_series())
    assert {v for ev in out["forecast"].values() for v in ev.values()} == {"No call"}


def test_markdown_states_outcome_and_limits():
    md = rep.render(rep.build(series=_series()))
    assert "No pre-registered edge" in md
    assert "not trading advice" in md
    assert "Breadth" in md and "not computed" in md
    assert "descriptive, not graded" in md


def test_cli_refuses_until_sector_set_is_decided():
    assert rep.sector_set_decided("## Addendum 1: ticker check\nno decision") is False
    assert rep.sector_set_decided("Sector set decision: 12 sectors, see Addendum 2") is True
