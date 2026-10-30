"""Golden-value tests for sbc.screener.indicators."""

import numpy as np
import pandas as pd

from sbc.screener.indicators import (
    atr,
    bollinger,
    ema,
    heikin_ashi,
    pivots,
    rsi,
    supertrend,
    true_range,
)


def _df(rows):
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"],
                        index=pd.RangeIndex(len(rows)))


def test_ema_constant_series():
    s = pd.Series([5.0] * 10)
    assert np.allclose(ema(s, 10), 5.0)


def test_ema_seeded_and_decays():
    # adjust=False: first value seeds the average.
    s = pd.Series([10.0, 10.0, 10.0, 20.0])
    out = ema(s, 3)
    assert out.iloc[0] == 10.0
    k = 2.0 / (3.0 + 1.0)
    assert np.isclose(out.iloc[3], (20.0 - out.iloc[2]) * k + out.iloc[2])


def test_rsi_all_up_is_100_all_down_zero_flat_fifty():
    up = pd.Series(np.linspace(1, 100, 30))
    down = pd.Series(np.linspace(100, 1, 30))
    flat = pd.Series([5.0] * 30)
    assert rsi(up, 14).dropna().iloc[-1] == 100.0
    assert rsi(down, 14).dropna().iloc[-1] == 0.0
    assert np.allclose(rsi(flat, 14).dropna(), 50.0)


def test_rsi_golden_wilder_14_on_known_sequence():
    # Classic Wilder example scaled: gains 1,1,1 ... simple monotone
    # steps with one pullback; verify against manual Wilder recursion.
    closes = [44.0, 44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10,
              45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
    s = pd.Series(closes)
    delta = s.diff()[1:]
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    ag = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    al = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    expected = 100 - 100 / (1 + ag / al)
    assert np.allclose(rsi(s, 14).dropna(), expected.dropna())


def test_bollinger_constant_collapses():
    s = pd.Series([7.0] * 25)
    bb = bollinger(s, 20, 2.0).dropna()
    assert np.allclose(bb["bb_mid"], 7.0)
    assert np.allclose(bb["bb_up"], 7.0)
    assert np.allclose(bb["bb_low"], 7.0)


def test_bollinger_golden_values():
    closes = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0]
    s = pd.Series(closes)
    bb = bollinger(s, 5, 2.0).iloc[-1]
    mid = np.mean(closes[-5:])
    sd = np.std(closes[-5:])
    assert np.isclose(bb["bb_mid"], mid)
    assert np.isclose(bb["bb_up"], mid + 2 * sd)
    assert np.isclose(bb["bb_low"], mid - 2 * sd)


def test_pivots_from_previous_candle():
    high = pd.Series([110.0, 120.0])
    low = pd.Series([100.0, 105.0])
    close = pd.Series([105.0, 112.0])
    piv = pivots(high, low, close, shift=1)
    assert np.isnan(piv["pivot_p"].iloc[0])
    p = (110.0 + 100.0 + 105.0) / 3.0
    row = piv.iloc[1]
    assert np.isclose(row["pivot_p"], p)
    assert np.isclose(row["pivot_r1"], 2 * p - 100.0)
    assert np.isclose(row["pivot_s1"], 2 * p - 110.0)


def test_true_range_and_atr():
    df = _df([[10, 12, 9, 11], [11, 15, 10, 14], [14, 14, 12, 13]])
    tr = true_range(df)
    assert np.isclose(tr.iloc[0], 3.0)          # high-low, no prev close
    assert np.isclose(tr.iloc[1], 5.0)          # max(4, 5, 4)
    assert np.isclose(tr.iloc[2], 2.0)          # max(2, 0, 2)
    a = atr(df, 2)
    assert np.isnan(a.iloc[0])                  # warm-up
    assert np.isclose(a.iloc[1], (3.0 + 5.0) / 2.0)   # SMA seed
    assert np.isclose(a.iloc[2], (4.0 * 1 + 2.0) / 2.0)  # Wilder step


def _trending_df(base=100.0, drift=0.5, n=40, noise=0.0, seed=1):
    rng = np.random.default_rng(seed)
    rows, price = [], base
    for _ in range(n):
        o = price
        c = price + drift + (rng.uniform(-noise, noise) if noise else 0)
        h = max(o, c) + 0.5
        low = min(o, c) - 0.5
        rows.append([o, h, low, c])
        price = c
    return _df(rows)


def test_supertrend_rides_below_in_uptrend():
    df = _trending_df(drift=0.5, n=60)
    st = supertrend(df, 10, 3.0).dropna()
    assert (st["st_dir"].iloc[-30:] == 1).all()
    assert (st["st"] < df["close"].iloc[-len(st):]).all()


def test_supertrend_flips_to_minus_in_downtrend():
    rows = _trending_df(drift=0.5, n=40).values.tolist()
    price = rows[-1][3]
    for _ in range(40):
        o = price
        c = price - 1.0
        rows.append([o, max(o, c) + 0.5, min(o, c) - 0.5, c])
        price = c
    df = _df(rows)
    st = supertrend(df, 10, 3.0).dropna()
    assert (st["st_dir"].iloc[-20:] == -1).all()
    assert (st["st"].iloc[-20:] > df["close"].iloc[-20:]).all()



def test_supertrend_flip_on_close_through_band():
    # Flat driftless market then a single violent gap up: direction
    # must be +1 on the last bar with the line below price.
    rng = np.random.default_rng(7)
    price = 100.0
    rows = []
    for _ in range(40):
        c = price + rng.uniform(-0.2, 0.2)
        rows.append([price, c + 0.4, c - 0.4, c])
        price = c
    rows.append([price, price + 12, price + 5, price + 10])
    df = _df(rows)
    st = supertrend(df, 10, 3.0).dropna()
    assert st["st_dir"].iloc[-1] == 1


def test_heikin_ashi_recursion_and_envelope():
    df = _df([[10, 12, 9, 11], [11, 15, 10, 14], [14, 16, 13, 15]])
    ha = heikin_ashi(df)
    assert np.isclose(ha["close"].iloc[0], (10 + 12 + 9 + 11) / 4)
    assert np.isclose(ha["open"].iloc[0], (10 + 11) / 2)
    assert np.isclose(ha["open"].iloc[1],
                      (ha["open"].iloc[0] + ha["close"].iloc[0]) / 2)
    assert (ha["high"] >= ha[["open", "close"]].max(axis=1) - 1e-9).all()
    assert (ha["low"] <= ha[["open", "close"]].min(axis=1) + 1e-9).all()
    assert np.isclose(ha["close"].iloc[2], (14 + 16 + 13 + 15) / 4)
