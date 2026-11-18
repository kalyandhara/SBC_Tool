"""Rule backtest: rule-1 against the trend-only control."""
import numpy as np
import pandas as pd

from sbc.navigator import decision as D
from sbc.navigator import rule_backtest as R
from sbc.navigator.profile import SAMPLE_PROFILE


def _planted(n=800, seed=3, planted=True):
    rng = np.random.default_rng(seed)
    trend = np.ones(n)                       # every day on the long side
    gate = np.where(rng.random(n) < .5, 0.5, 0.0)
    r = rng.normal(0, .01, n)
    if planted:
        r = np.where(gate > 0, np.abs(r), -np.abs(r))   # the gate skips only losing days
    return gate, trend, np.ones(n), r


def test_side_excess_formula_size_neutral_and_sized():
    gate = np.array([0.75, 0.0]); trend = np.array([1.0, 1.0]); vixfac = np.ones(2)
    r = np.array([.01, -.02]); side = np.array([True, True])
    # Size-neutral (the verdict's statistic): an open gate trades 1 unit, as the control does.
    # Day 1: rule .009 and control .009, so 0. Day 2: rule 0 and control -.021, so +.021. Mean .0105.
    assert np.isclose(R.side_excess(gate, trend, vixfac, r, 10, side), .0105)
    # Sized (descriptive): rule .75*.009 against control .5*.009; day 2 as before at half size.
    assert np.isclose(R.side_excess(gate, trend, vixfac, r, 10, side, sized=True),
                      ((.75 - .5) * .009 + .5 * .021) / 2)


def test_planted_signal_detected_and_noise_not():
    gate, trend, vixfac, r = _planted()
    hit = R.side_stats(gate, trend, vixfac, r, 10, trend > 0, n_perm=400, seed=7)
    assert hit["excess"] > 0 and hit["p"] < .05
    gate, trend, vixfac, r = _planted(planted=False)
    miss = R.side_stats(gate, trend, vixfac, r, 10, trend > 0, n_perm=400, seed=7)
    assert miss["p"] > .1


def _ohlc(n=1100):
    days = [str(d)[:10] for d in np.busday_offset("2019-01-01", np.arange(n), roll="forward")]
    x = 100 + np.cumsum(np.sin(np.arange(n) / 9.0))
    df = pd.DataFrame({"date": days, "open": x, "close": x + .2 * np.cos(np.arange(n))})
    vix = {str(d)[:10]: 14 + 4 * np.sin(i / 30.0)
           for i, d in enumerate(np.busday_offset("2017-11-01", np.arange(n + 300), roll="forward"))}
    return df, vix


def test_market_codes_agree_with_today_card_inputs():
    df, vix = _ohlc(700)
    for d in list(vix)[::37]:               # gaps in the VIX history
        vix.pop(d)
    days, closes = list(df["date"]), df["close"].to_numpy(float)
    trend, vixfac = R.market_codes(days, closes, vix)
    codes = {"Up": 1.0, "Down": -1.0}
    seen = set()
    for t in range(1, len(days), 7):
        want = D.inputs_before(days, closes, vix, days[t])
        assert trend[t] == codes.get(want["trend"], 0.0)
        assert vixfac[t] == (0.5 if want["vix"] == "High" else 1.0)
        seen.add(want["trend"])
    assert {"Up", "Down"} <= seen


def test_run_is_deterministic_and_sample_never_edge():
    df, vix = _ohlc()
    params = {"n_placebo": 2, "n_perm": 50, "min_sessions": 300}
    a = R.run(SAMPLE_PROFILE, df, vix, params=params)
    b = R.run(SAMPLE_PROFILE, df, vix, params=params)
    assert a == b
    assert set(a["sides"]) == {"long", "short"}
    assert all(a["sides"][s]["verdict"] == "no demonstrated edge" for s in R.SIDES)
    assert a["kind"] == "rule" and a["rule_version"] == "rule-1"
