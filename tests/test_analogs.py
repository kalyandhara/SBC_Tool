"""Analog engine (sbc.analogs) and its walk-forward test (sbc.analog_validation)."""

import datetime as dt

import numpy as np
import pytest

from sbc import analog_validation as av
from sbc import analogs as an
from sbc import fingerprint as fpm


@pytest.fixture(scope="module")
def history():
    """~3 years of daily 'sessions' (weekdays) with a random-walk index."""
    days = [dt.date(2018, 1, 1) + dt.timedelta(days=i) for i in range(1100)]
    days = [d for d in days if d.weekday() < 5]
    fps = [fpm.fingerprint(d) for d in days]
    closes = 1000 * np.exp(np.cumsum(np.random.default_rng(0).normal(0, 0.01, len(days))))
    return an.History.build([d.isoformat() for d in days], closes, fps)


def test_a_date_is_fully_similar_to_itself(history):
    target = an._slice_rows(history.sky, 100, 101)
    sims = an.similarity(target, history.sky)
    for key in (*fpm.TIERS, "overall"):
        assert sims[key][100] == pytest.approx(1.0)
        assert ((sims[key] >= 0) & (sims[key] <= 1 + 1e-9)).all()


def test_neighbouring_days_are_similar_on_the_slow_tier_only(history):
    sims = an.similarity(an._slice_rows(history.sky, 300, 301), history.sky)
    assert sims["slow"][301] > 0.9
    assert sims["fast"][301] < 0.6  # the Moon has moved a sign


def test_no_lookahead(history):
    target_fp = fpm.fingerprint(history.dates[600])
    for h in an.HORIZONS:
        res = an.find_analogs(history, target_fp, horizon=h)
        entry = 599  # previous close
        for a in res["analogs"]:
            i = history.dates.index(a["date"])
            assert i + h - 1 <= entry, (h, a["date"])  # forward window closed by the entry close
            assert abs((dt.date.fromisoformat(a["date"]) - dt.date.fromisoformat(target_fp["date"])).days) > an.EXCLUDE_DAYS


def test_analogs_are_spaced_and_ranked(history):
    res = an.find_analogs(history, fpm.fingerprint(history.dates[-1]), horizon=5, min_similarity=None)
    idx = sorted(history.dates.index(a["date"]) for a in res["analogs"])
    assert len(idx) == an.TOP_K and res["mode"] == "top_k"
    assert min(np.diff(idx)) >= an.MIN_SPACING
    sims = [a["similarity"] for a in res["analogs"]]
    assert sims == sorted(sims, reverse=True)
    assert res["best_similarity"] == pytest.approx(sims[0])


def test_threshold_mode_when_enough_matches(history):
    res = an.find_analogs(history, fpm.fingerprint(history.dates[-1]), horizon=1,
                          min_similarity=0.0, weights={"slow": 1, "medium": 0, "fast": 0})
    assert res["mode"] == "threshold" and len(res["analogs"]) > an.TOP_K


def test_future_target_uses_all_history(history):
    future = fpm.fingerprint("2031-05-01")
    res = an.find_analogs(history, future, horizon=20)
    assert res["pool"] > 0 and res["summary"]["n"] == an.TOP_K
    assert all(a["forward"]["20"] is not None for a in res["analogs"])


def test_walk_forward_signals_cover_every_variant(history):
    signals, best = av.walk_forward(history, start=history.dates[500])
    assert set(signals) == {*av.VARIANTS, av.CONTROL}
    for name, by_h in signals.items():
        for h, sig in by_h.items():
            assert set(np.unique(sig)) <= {-1, 0, 1}
            assert not sig[:500].any()  # nothing before the start
            assert np.count_nonzero(sig[520:]) > 0.9 * len(sig[520:]), (name, h)


def test_analogs_endpoint(client, monkeypatch, history):
    monkeypatch.setattr(an, "load_nifty_history", lambda: history)
    body = client.get("/api/engine/analogs?date=2021-01-05&horizon=5&variant=fast&k=10").get_json()
    assert body["variant"] == "fast" and len(body["analogs"]) == 10
    assert body["status"] == "experimental" and "not investment advice" in body["caveat"]
    assert {"same_sign", "same_nakshatra", "age_years", "tiers"} <= set(body["analogs"][0])
    for bad in ("horizon=3", "variant=x", "k=1", "min_similarity=2", "date=nope"):
        assert client.get(f"/api/engine/analogs?{bad}").status_code == 400


def test_analogs_endpoint_without_market_data(client, monkeypatch):
    from sbc.market_store import MarketDataMissing

    def missing():
        raise MarketDataMissing("empty")
    monkeypatch.setattr(an, "load_nifty_history", missing)
    resp = client.get("/api/engine/analogs?date=2026-10-05")
    assert resp.status_code == 404 and "refresh_market_data" in resp.get_json()["error"]
