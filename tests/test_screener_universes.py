"""Tests for sbc.screener.universes (no network required)."""

import datetime as dt

import pytest

from sbc.screener import universes

LIST_CSV = ("Company Name,Industry,Symbol,Series,ISIN Code\r\n"
            "Reliance Industries,Energy,RELIANCE,EQ,INE002A01018\r\n"
            "Tata Consultancy Services,IT,TCS,EQ,INE467B01029\r\n"
            "Tata Consultancy Services,IT,TCS,EQ,INE467B01029\r\n")

FNO_CSV = ("UNDERLYING,ITEM,LOT SIZE\r\n"
           "RELIANCE,1,250\r\n"
           "BANKNIFTY,1,15\r\n"
           "TCS,1,175\r\n")


@pytest.fixture
def offline(monkeypatch, tmp_path):
    """Redirect the cache dir and stub the network fetch."""
    monkeypatch.setattr(universes, "CACHE_DIR", tmp_path)
    calls = []

    def fake_fetch(url):
        calls.append(url)
        if "fo_mktlots" in url:
            return FNO_CSV
        return LIST_CSV

    monkeypatch.setattr(universes, "_fetch_csv", fake_fetch)
    return calls


def test_watchlist_parses_and_dedupes():
    assert universes.watchlist("reliance, TCS.NS\nHDFCBANK; , tcs") == [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]


def test_watchlist_keeps_index_symbols():
    assert universes.watchlist("^NSEI") == ["^NSEI"]


def test_available_lists_sectors_and_basics():
    keys = universes.available()
    assert "NIFTY 50" in keys and "indices" in keys and "fno" in keys
    assert "sector:IT" in keys
    assert "IT" in universes.sector_names()


def test_load_fetches_and_maps_symbols(offline):
    symbols = universes.load("NIFTY 50")
    assert symbols == ["RELIANCE.NS", "TCS.NS"]


def test_load_serves_cached_copy_within_ttl(offline):
    universes.load("NIFTY 50")
    offline.clear()
    # refresh=False and fresh cache -> no network call
    assert universes.load("NIFTY 50") == ["RELIANCE.NS", "TCS.NS"]
    assert offline == []


def test_load_stale_cache_triggers_refetch(offline, tmp_path):
    universes.load("NIFTY 50")
    path = tmp_path / "nifty-50.csv"
    old = dt.datetime.now() - dt.timedelta(days=3)
    import os
    os.utime(path, (old.timestamp(), old.timestamp()))
    offline.clear()
    universes.load("NIFTY 50")
    assert len(offline) == 1


def test_load_falls_back_to_stale_cache_offline(offline, tmp_path):
    universes.load("sector:IT")
    path = tmp_path / "sector-it.csv"
    old = dt.datetime.now() - dt.timedelta(days=9)
    import os
    os.utime(path, (old.timestamp(), old.timestamp()))

    def boom(url):
        raise OSError("network down")

    offline.clear()
    import sbc.screener.universes as u
    monkey_original = u._fetch_csv
    u._fetch_csv = boom
    try:
        assert universes.load("sector:IT") == ["RELIANCE.NS", "TCS.NS"]
    finally:
        u._fetch_csv = monkey_original


def test_load_raises_without_any_cache(offline):
    import sbc.screener.universes as u
    original = u._fetch_csv
    u._fetch_csv = lambda url: (_ for _ in ()).throw(OSError("down"))
    try:
        with pytest.raises(RuntimeError, match="no cached copy"):
            universes.load("NIFTY 500")
    finally:
        u._fetch_csv = original


def test_unknown_universe_is_value_error():
    with pytest.raises(ValueError, match="unknown universe"):
        universes.load("nifty9999")


def test_fno_symbols_parsed():
    text = universes._symbols_from_fno_csv(FNO_CSV)
    assert text == ["BANKNIFTY", "RELIANCE", "TCS"]


def test_indices_universe_merges_static_map(offline):
    symbols = universes.load("indices")
    assert "^NSEI" in symbols and "^NSEBANK" in symbols
    assert "RELIANCE.NS" in symbols
