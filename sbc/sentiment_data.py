"""Sentiment data integration: Twitter/X, news sentiment, VIX correlation.

This module fetches and caches sentiment data to validate the psychological
mechanism premise: planetary cycles correlate with shifts in collective
human behavior.

API Keys Required (set as environment variables):
- TWITTER_BEARER_TOKEN: Twitter API v2 bearer token (for historical data)
- NEWS_API_KEY: News API key (https://newsapi.org/)
"""

import os
import sqlite3
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

TWITTER_BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")

# Positive/negative keyword lists for simple sentiment analysis
POSITIVE_KEYWORDS = [
    "bullish", "growth", "gain", "profit", "rally", "surge", "rise",
    "optimistic", "strong", "positive", "breakout", "recovery", "expansion",
    "win", "success", "boom", "boost", "momentum", "soar", "advance",
]

NEGATIVE_KEYWORDS = [
    "bearish", "decline", "loss", "drop", "fall", "crash", "plunge",
    "pessimistic", "weak", "negative", "correction", "recession", "contraction",
    "lose", "fail", "slump", "downturn", "collapse", "sell-off", "panic",
    "fear", "risk", "decline", "decrease", "slide", "dump",
]

DB_PATH = Path(__file__).parent.parent / "data" / "sentiment.db"


def _get_conn():
    """Get SQLite connection for sentiment data."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _bootstrap_db():
    """Create sentiment data tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sentiment (
            source TEXT NOT NULL,
            ticker TEXT NOT NULL DEFAULT '',
            date TEXT NOT NULL,
            sentiment_score REAL NOT NULL,
            article_count INTEGER DEFAULT 0,
            tweet_count INTEGER DEFAULT 0,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (source, ticker, date)
        );
        CREATE INDEX IF NOT EXISTS idx_sentiment_source ON sentiment(source);
        CREATE INDEX IF NOT EXISTS idx_sentiment_date ON sentiment(date);
    """)
    conn.commit()
    conn.close()


def analyze_sentiment(text: str) -> float:
    """Simple keyword-based sentiment analysis.
    
    Args:
        text: Text to analyze
    
    Returns:
        Sentiment score from -1.0 (very negative) to +1.0 (very positive)
    """
    text_lower = text.lower()
    
    positive_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)
    negative_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
    
    total = positive_count + negative_count
    if total == 0:
        return 0.0
    
    # Normalize to -1 to +1 range
    return (positive_count - negative_count) / total


def fetch_news_sentiment(ticker: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Fetch news sentiment using News API.
    
    Args:
        ticker: Stock ticker or market identifier (e.g., "NIFTY", "NIFTY 50")
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        List of daily sentiment scores
    """
    if not NEWS_API_KEY:
        raise ValueError("NEWS_API_KEY environment variable not set")
    
    # Group sentiment by date
    url = "https://newsapi.org/v2/everything"
    daily_sentiment: Dict[str, Dict[str, Any]] = {}
    
    # Fetch in 10-day chunks (News API limitation)
    current_start = datetime.strptime(start_date, "%Y-%m-%d")
    current_end = datetime.strptime(end_date, "%Y-%m-%d")
    
    while current_start <= current_end:
        chunk_end = min(current_start + timedelta(days=10), current_end)
        
        params = {
            "q": ticker,
            "apiKey": NEWS_API_KEY,
            "from": current_start.strftime("%Y-%m-%d"),
            "to": chunk_end.strftime("%Y-%m-%d"),
            "language": "en",
            "sortBy": "publishedAt",
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if "articles" in data:
                for article in data["articles"]:
                    pub_date = article.get("publishedAt", "")
                    if pub_date:
                        date_str = pub_date.split("T")[0]
                        title = article.get("title", "") or ""
                        description = article.get("description", "") or ""
                        text = f"{title} {description}"
                        score = analyze_sentiment(text)
                        
                        if date_str not in daily_sentiment:
                            daily_sentiment[date_str] = {"scores": [], "count": 0}
                        daily_sentiment[date_str]["scores"].append(score)
                        daily_sentiment[date_str]["count"] += 1
        
        except requests.RequestException as e:
            print(f"Failed to fetch news for {current_start}: {e}")
        
        current_start = chunk_end + timedelta(days=1)
    
    # Average sentiment per day
    observations = []
    for date_str, data in daily_sentiment.items():
        if data["scores"]:
            avg_score = sum(data["scores"]) / len(data["scores"])
            observations.append({
                "date": date_str,
                "value": avg_score,
                "source": "news",
                "ticker": ticker,
            })
    
    return observations


def fetch_vix_sentiment(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Fetch VIX data as fear gauge using yfinance.
    
    VIX is normalized to sentiment score: high VIX = fear = negative sentiment.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        List of daily sentiment scores
    """
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError("yfinance not installed. Run: pip install yfinance")

    vix = yf.download("^VIX", start=start_date, end=end_date,
                      progress=False, auto_adjust=False)

    if vix is None or vix.empty:
        return []

    # Newer yfinance returns MultiIndex columns; row["Close"] must be a
    # scalar, not a Series (same handling as sbc.market_store).
    if isinstance(vix.columns, pd.MultiIndex):
        vix.columns = vix.columns.get_level_values(0)
    vix = vix.dropna(subset=["Close"])
    
    # Normalize VIX to sentiment score (-1 to +1)
    # VIX range historically: ~10 (low fear) to ~80 (high fear)
    # Use 30 as midpoint, normalize to -1 to +1
    observations = []
    for date, row in vix.iterrows():
        vix_value = row["Close"]
        # Normalize: VIX < 30 = positive sentiment, VIX > 30 = negative sentiment
        normalized = (30 - vix_value) / 50  # Range roughly -1 to +1
        normalized = max(-1.0, min(1.0, normalized))  # Clamp to -1 to +1
        
        observations.append({
            "date": date.strftime("%Y-%m-%d"),
            "value": normalized,
            "source": "vix",
            "ticker": None,
        })
    
    return observations


def cache_sentiment_data(observations: List[Dict[str, Any]]) -> int:
    """Store sentiment data in SQLite.
    
    Args:
        observations: List of dicts with date, value, source, ticker
    
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
                INSERT OR REPLACE INTO sentiment 
                (source, ticker, date, sentiment_score, fetched_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    obs["source"],
                    obs.get("ticker") or "",
                    obs["date"],
                    obs["value"],
                    datetime.now().isoformat(),
                ),
            )
            inserted += 1
        except sqlite3.Error as e:
            print(f"Error inserting sentiment data: {e}")
    
    conn.commit()
    conn.close()
    return inserted


def get_sentiment_data(source: Optional[str] = None, ticker: Optional[str] = None,
                       start: Optional[str] = None, end: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve sentiment data from cache.
    
    Args:
        source: Filter by source (vix, news, twitter) (None = all sources)
        ticker: Filter by ticker (None = all tickers)
        start: Start date in YYYY-MM-DD format (None = all dates)
        end: End date in YYYY-MM-DD format (None = all dates)
    
    Returns:
        Dict with sentiment data and metadata
    """
    _bootstrap_db()
    conn = _get_conn()
    
    query = "SELECT * FROM sentiment WHERE 1=1"
    params = []
    
    if source:
        query += " AND source = ?"
        params.append(source)
    
    if ticker:
        query += " AND ticker = ?"
        params.append(ticker)
    
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
    
    # Group by source and ticker
    by_source: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for row in rows:
        s = row["source"]
        t = row["ticker"] or "none"
        if s not in by_source:
            by_source[s] = {}
        if t not in by_source[s]:
            by_source[s][t] = []
        by_source[s][t].append({
            "date": row["date"],
            "sentiment_score": row["sentiment_score"],
            "fetched_at": row["fetched_at"],
        })
    
    return {
        "by_source": by_source,
        "total_observations": len(rows),
        "query_params": {"source": source, "ticker": ticker, "start": start, "end": end},
    }


def refresh_sentiment_data(days: int = 90, ticker: str = "NIFTY 50") -> Dict[str, Any]:
    """Refresh sentiment data from all sources.
    
    Args:
        days: Number of days of historical data to fetch
        ticker: Ticker to search for in news (e.g., "NIFTY 50")
    
    Returns:
        Dict with refresh results
    """
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    results = {
        "start_date": start_date,
        "end_date": end_date,
        "sources_fetched": [],
        "total_observations": 0,
        "errors": [],
    }
    
    # Fetch VIX sentiment
    try:
        vix_observations = fetch_vix_sentiment(start_date, end_date)
        inserted = cache_sentiment_data(vix_observations)
        results["sources_fetched"].append("vix")
        results["total_observations"] += inserted
        print(f"Fetched VIX sentiment: {inserted} observations")
    except Exception as e:
        error_msg = f"Failed to fetch VIX sentiment: {e}"
        results["errors"].append(error_msg)
        print(error_msg)
    
    # Fetch news sentiment
    try:
        news_observations = fetch_news_sentiment(ticker, start_date, end_date)
        inserted = cache_sentiment_data(news_observations)
        results["sources_fetched"].append("news")
        results["total_observations"] += inserted
        print(f"Fetched news sentiment: {inserted} observations")
    except Exception as e:
        error_msg = f"Failed to fetch news sentiment: {e}"
        results["errors"].append(error_msg)
        print(error_msg)
    
    # Twitter sentiment requires paid API for historical data
    # Placeholder for future implementation
    print("Twitter sentiment: Not implemented (requires paid API)")
    
    return results


def get_sentiment_at_date(date: str, source: str = "vix") -> Optional[float]:
    """Get the sentiment score closest to a given date.
    
    Args:
        date: Target date in YYYY-MM-DD format
        source: Sentiment source (vix, news, twitter)
    
    Returns:
        Sentiment score at or closest to the date, or None if no data
    """
    data = get_sentiment_data(source=source, start=date, end=date)
    
    if not data["by_source"] or source not in data["by_source"]:
        return None
    
    # Get first ticker's data
    for ticker_data in data["by_source"][source].values():
        if ticker_data:
            return ticker_data[0]["sentiment_score"]
    
    return None


__all__ = [
    "analyze_sentiment",
    "fetch_news_sentiment",
    "fetch_vix_sentiment",
    "cache_sentiment_data",
    "get_sentiment_data",
    "refresh_sentiment_data",
    "get_sentiment_at_date",
]
