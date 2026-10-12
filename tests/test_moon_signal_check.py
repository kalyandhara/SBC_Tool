"""Trading Signals panel: Moon-sign signal check (sbc.moon_signal_check)."""

import datetime as dt

import pytest

from sbc import moon_signal_check as msc


def bars_from(closes, opens=None, start=dt.date(2026, 1, 5)):
    out, d = [], start
    for i, c in enumerate(closes):
        while d.weekday() >= 5:
            d += dt.timedelta(days=1)
        o = opens[i] if opens else c
        out.append({"date": d.isoformat(), "open": o, "high": max(o, c), "low": min(o, c), "close": c})
        d += dt.timedelta(days=1)
    return out


ALWAYS_ARIES = lambda when: "Aries"  # noqa: E731  (RASHI_TREND: bullish)


def test_scores_next_close_against_todays_close():
    r = msc.check(bars_from([100, 101, 100, 102]), multi_tf=False, rashi_at=ALWAYS_ARIES)
    assert [x["actual"] for x in r["rows"]] == ["bullish", "bearish", "bullish"]
    assert r["summary"]["hits"] == 2 and r["summary"]["samples"] == 3


def test_base_rate_is_the_more_common_direction():
    r = msc.check(bars_from([100, 101, 102, 103, 102]), multi_tf=False, rashi_at=ALWAYS_ARIES)
    assert r["summary"]["up_share"] == pytest.approx(0.75)
    assert r["summary"]["base_rate"] == pytest.approx(0.75)
    # "always bullish" scores exactly the base rate: no edge
    assert r["summary"]["hit_rate"] == pytest.approx(0.75)
    assert "Not above the base rate" in r["summary"]["verdict"] or "within chance" in r["summary"]["verdict"]


def test_gap_filter_uses_next_open_and_is_flagged():
    closes = [100, 99, 101, 100, 102]
    opens = [100, 101, 100.5, 99, 101]  # next-session opens
    r = msc.check(bars_from(closes, opens), multi_tf=False, gap_filter=True, rashi_at=ALWAYS_ARIES)
    assert all(x["gap"] == "bullish" for x in r["rows"])
    assert "isn't known at signal time" in r["summary"]["verdict"]
    assert r["gap_control"]["hit_rate"] is not None


def test_empty_result_has_no_nan():
    r = msc.check(bars_from([100, 100, 100]), multi_tf=False, rashi_at=ALWAYS_ARIES)
    assert r["summary"]["samples"] == 0
    assert r["summary"]["hit_rate"] is None and r["summary"]["p_value"] is None


def test_endpoint_rejects_unknown_symbol(client):
    assert client.get("/api/signals/moon-check?symbol=XYZ").status_code == 400
    assert client.get("/api/signals/moon-check?years=abc").status_code == 400


def test_endpoint_runs_on_local_nifty(client):
    r = client.get("/api/signals/moon-check?symbol=NIFTY&years=2")
    if r.status_code == 404:
        pytest.skip("no NIFTY history in market.db")
    body = r.get_json()
    assert r.status_code == 200 and body["source"] == "market.db"
    s = body["summary"]
    assert s["samples"] > 50 and 0.4 < s["base_rate"] < 0.7 and s["p_value"] is not None
