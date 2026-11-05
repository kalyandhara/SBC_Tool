"""The confluence study: permutation control and filter wiring (no ephemeris, stub bias)."""

import numpy as np
import pandas as pd
import pytest

from scripts import study_astro_ma_confluence as study


@pytest.fixture
def wave_csv(tmp_path):
    """~400 bars of a sine wave: enough EMA 9/21 crosses of both signs."""
    n = 400
    close = 100 + 10 * np.sin(np.arange(n) / 6.0)
    df = pd.DataFrame({
        "Date": pd.bdate_range("2020-01-01", periods=n).strftime("%Y-%m-%d"),
        "Open": close - 0.2, "High": close + 0.5, "Low": close - 0.5,
        "Close": close, "Volume": 1000,
    })
    path = tmp_path / "wave.csv"
    df.to_csv(path, index=False)
    return str(path)


def test_permutation_p_extremes():
    rets = np.linspace(-0.01, 0.01, 50)
    assert study.permutation_p(rets, 10, observed_mean=1.0, iters=500) == 0.0
    assert study.permutation_p(rets, 10, observed_mean=-1.0, iters=500) == 1.0


def test_permutation_p_is_deterministic_and_nan_when_empty():
    rets = np.linspace(-0.01, 0.01, 50)
    a = study.permutation_p(rets, 10, 0.0, iters=300)
    assert a == study.permutation_p(rets, 10, 0.0, iters=300)
    assert np.isnan(study.permutation_p(rets, 0, 0.0))


def test_neutral_bias_confirms_nothing(wave_csv):
    out = study.run_confluence_study(wave_csv, bias_fn=lambda d: 0)
    assert out["bull"]["n_all"] > 3 and out["bear"]["n_all"] > 3
    assert out["bull"]["n_confirmed"] == 0 and out["bear"]["n_confirmed"] == 0


def test_bullish_bias_confirms_only_bull_crosses(wave_csv):
    out = study.run_confluence_study(wave_csv, bias_fn=lambda d: 1)
    assert out["bull"]["n_confirmed"] == out["bull"]["n_all"]
    assert out["bear"]["n_confirmed"] == 0


def test_bearish_bias_confirms_only_bear_crosses(wave_csv):
    out = study.run_confluence_study(wave_csv, bias_fn=lambda d: -1)
    assert out["bear"]["n_confirmed"] == out["bear"]["n_all"]
    assert out["bull"]["n_confirmed"] == 0


def test_bias_is_read_for_the_traded_session(wave_csv):
    seen = []
    study.run_confluence_study(wave_csv, bias_fn=lambda d: seen.append(d) or 0)
    df = pd.read_csv(wave_csv)
    # never the first bar's date: bias is asked for bar i+1, so a cross needs a following bar
    assert seen and df["Date"].iloc[0] not in seen
