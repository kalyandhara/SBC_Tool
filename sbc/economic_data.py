"""Economic data integration: FRED API for US, RBI for India.

This module fetches and caches economic indicators that correlate with
planetary cycles (e.g., Saturn signals with interest rates, Jupiter signals
with earnings data).

API Keys Required (set as environment variables):
- FRED_API_KEY: Federal Reserve Economic Data API key (https://fred.stlouisfed.org/docs/api/api_key.html)
"""

import os
import sqlite3
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

FRED_API_KEY = os.environ.get("FRED_API_KEY")
FRED_BASE_URL = "https://api.stlouisfed.org/fred"

# Economic indicators to track
FRED_SERIES = {
    "FEDFUNDS": "Federal Funds Rate",
    "DGS10": "10-Year Treasury Yield",
    "UNRATE": "Unemployment Rate",
    "CPIAUCSL": "Consumer Price Index",
    "GDP": "Gross Domestic Product",
    "M2SL": "M2 Money Stock",
}

# RBI policy rates (manual data source - no public API)
RBI_SERIES = {
    "repo_rate": "RBI Repo Rate",
    "reverse_repo_rate": "RBI Reverse Repo Rate",
}

DB_PATH = Path(__file__).parent.parent / "data" / "economic.db"


def _get_conn():
    """Get SQLite connection for economic data."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _bootstrap_db():
    """Create economic data tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS economic_indicators (
            series TEXT NOT NULL,
            date TEXT NOT NULL,
            value REAL NOT NULL,
            source TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (series, date)
        );
        CREATE INDEX IF NOT EXISTS idx_economic_series ON economic_indicators(series);
        CREATE INDEX IF NOT EXISTS idx_economic_date ON economic_indicators(date);
    """)
    conn.commit()
    conn.close()


def fetch_fred_series(series_id: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Fetch time series from FRED API.
    
    Args:
        series_id: FRED series identifier (e.g., "FEDFUNDS")
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        List of dicts with date, value, and metadata
    """
    if not FRED_API_KEY:
        raise ValueError("FRED_API_KEY environment variable not set")
    
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "observation_start": start_date,
        "observation_end": end_date,
        "file_type": "json",
    }
    
    try:
        response = requests.get(f"{FRED_BASE_URL}/series/observations", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if "observations" not in data:
            return []
        
        observations = []
        for obs in data["observations"]:
            observations.append({
                "date": obs["date"],
                "value": float(obs["value"]) if obs["value"] else None,
                "series": series_id,
                "source": "FRED",
            })
        
        return observations
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch FRED data for {series_id}: {e}")


def cache_economic_data(observations: List[Dict[str, Any]]) -> int:
    """Store economic data in SQLite.
    
    Args:
        observations: List of dicts with date, value, series, source
    
    Returns:
        Number of rows inserted
    """
    _bootstrap_db()
    conn = _get_conn()
    
    inserted = 0
    for obs in observations:
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO economic_indicators 
                (series, date, value, source, fetched_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    obs["series"],
                    obs["date"],
                    obs["value"],
                    obs["source"],
                    datetime.now().isoformat(),
                ),
            )
            inserted += 1
        except sqlite3.Error as e:
            print(f"Error inserting economic data: {e}")
    
    conn.commit()
    conn.close()
    return inserted


def get_economic_data(series: Optional[str] = None, start: Optional[str] = None, 
                     end: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve economic data from cache.
    
    Args:
        series: Filter by series ID (None = all series)
        start: Start date in YYYY-MM-DD format (None = all dates)
        end: End date in YYYY-MM-DD format (None = all dates)
    
    Returns:
        Dict with series data and metadata
    """
    _bootstrap_db()
    conn = _get_conn()
    
    query = "SELECT * FROM economic_indicators WHERE 1=1"
    params = []
    
    if series:
        query += " AND series = ?"
        params.append(series)
    
    if start:
        query += " AND date >= ?"
        params.append(start)
    
    if end:
        query += " AND date <= ?"
        params.append(end)
    
    query += " ORDER BY date ASC"
    
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    # Group by series
    by_series: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        s = row["series"]
        if s not in by_series:
            by_series[s] = []
        by_series[s].append({
            "date": row["date"],
            "value": row["value"],
            "fetched_at": row["fetched_at"],
        })
    
    return {
        "series": by_series,
        "total_observations": len(rows),
        "query_params": {"series": series, "start": start, "end": end},
    }


def refresh_fred_data(years: int = 10) -> Dict[str, Any]:
    """Refresh economic data from FRED API.
    
    Args:
        years: Number of years of historical data to fetch
    
    Returns:
        Dict with refresh results
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365 * years)).strftime("%Y-%m-%d")
    
    results = {
        "start_date": start_date,
        "end_date": end_date,
        "series_fetched": [],
        "total_observations": 0,
        "errors": [],
    }
    
    for series_id, name in FRED_SERIES.items():
        try:
            observations = fetch_fred_series(series_id, start_date, end_date)
            inserted = cache_economic_data(observations)
            results["series_fetched"].append(series_id)
            results["total_observations"] += inserted
            print(f"Fetched {name}: {inserted} observations")
        except Exception as e:
            error_msg = f"Failed to fetch {series_id}: {e}"
            results["errors"].append(error_msg)
            print(error_msg)
    
    return results


def add_rbi_manual_data(date: str, repo_rate: Optional[float] = None, 
                       reverse_repo_rate: Optional[float] = None) -> int:
    """Manually add RBI policy rate data (no public API available).
    
    Args:
        date: Date in YYYY-MM-DD format
        repo_rate: RBI repo rate (optional)
        reverse_repo_rate: RBI reverse repo rate (optional)
    
    Returns:
        Number of rows inserted
    """
    _bootstrap_db()
    conn = _get_conn()
    
    inserted = 0
    if repo_rate is not None:
        conn.execute(
            """
            INSERT OR REPLACE INTO economic_indicators 
            (series, date, value, source, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("repo_rate", date, repo_rate, "RBI (manual)", datetime.now().isoformat()),
        )
        inserted += 1
    
    if reverse_repo_rate is not None:
        conn.execute(
            """
            INSERT OR REPLACE INTO economic_indicators 
            (series, date, value, source, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("reverse_repo_rate", date, reverse_repo_rate, "RBI (manual)", datetime.now().isoformat()),
        )
        inserted += 1
    
    conn.commit()
    conn.close()
    return inserted


def get_rate_at_date(date: str, series: str) -> Optional[float]:
    """Get the economic indicator value closest to a given date.
    
    Args:
        date: Target date in YYYY-MM-DD format
        series: Series identifier (e.g., "FEDFUNDS", "repo_rate")
    
    Returns:
        Value at or closest to the date, or None if no data
    """
    data = get_economic_data(series=series, start=date, end=date)
    
    if not data["series"] or series not in data["series"]:
        return None
    
    series_data = data["series"][series]
    if not series_data:
        return None
    
    # Return the first (closest) observation
    return series_data[0]["value"]


__all__ = [
    "fetch_fred_series",
    "cache_economic_data",
    "get_economic_data",
    "refresh_fred_data",
    "add_rbi_manual_data",
    "get_rate_at_date",
]
