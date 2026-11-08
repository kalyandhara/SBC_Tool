"""Pytest configuration and fixtures for SBC Tool tests."""

import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import tempfile

# Keep test runs out of the real on-disk series cache.
os.environ.setdefault("SBC_SERIES_CACHE_DB",
                      os.path.join(tempfile.gettempdir(), "sbc_test_series_cache.db"))
# ...and out of the real birth-data profiles (fresh file per session).
_PROFILES_DB = os.path.join(tempfile.gettempdir(), f"sbc_test_profiles_{os.getpid()}.db")
os.environ["SBC_PROFILES_DB"] = _PROFILES_DB
os.environ["SBC_FINGERPRINT_DB"] = os.path.join(tempfile.gettempdir(), f"sbc_test_fingerprints_{os.getpid()}.db")
os.environ["SBC_DAILY_LEDGER_DB"] = os.path.join(tempfile.gettempdir(), f"sbc_test_daily_ledger_{os.getpid()}.db")
os.environ["SBC_MARKET_DB"] = os.path.join(tempfile.gettempdir(), f"sbc_test_market_{os.getpid()}.db")
os.environ["SBC_FORECAST_DB"] = os.path.join(tempfile.gettempdir(), f"sbc_test_forecast_{os.getpid()}.db")

from app import app as flask_app


@pytest.fixture
def app():
    """Create Flask app for testing."""
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
    })
    yield flask_app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def sample_date():
    """Sample date for testing."""
    return "2026-09-11"


@pytest.fixture
def sample_datetime():
    """Sample datetime for testing."""
    return "2026-09-11 09:15"


@pytest.fixture(scope="module")
def synthetic():
    """60 real NSE sessions to 2026-11-06 with synthetic prices and real skies."""
    import datetime as dt
    from functools import lru_cache

    import numpy as np
    from sbc import market_holidays as MH
    from sbc.analogs import SkyArrays
    from sbc.fingerprint import fingerprint
    from sbc.navigator import analogs as A
    d, dates = dt.date(2026, 11, 6), []
    while len(dates) < 60:
        if MH.is_trading_day(d):
            dates.append(d.isoformat())
        d -= dt.timedelta(days=1)
    dates.reverse()
    fp = lru_cache(maxsize=None)(fingerprint)
    sky = SkyArrays.from_fingerprints([fp(x) for x in dates])
    rng = np.random.default_rng(7)
    o = 20000 * np.cumprod(1 + rng.normal(0, 0.01, 60))
    c = o * (1 + rng.normal(0, 0.005, 60))
    p = {"open": o, "close": c, "low": np.minimum(o, c) * 0.995,
         "bank_open": o * 2, "bank_close": c * 2, "vix_close": np.full(60, 14.0),
         "sector_open": {s: o for s in A.SECTORS}, "sector_close": {s: c for s in A.SECTORS}}
    vix = {x: 14.0 for x in dates}
    return A.Market(dates, p, vix), sky, fp
