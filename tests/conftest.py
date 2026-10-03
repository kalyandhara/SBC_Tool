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
