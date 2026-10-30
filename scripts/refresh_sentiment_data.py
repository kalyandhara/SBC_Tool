"""Refresh sentiment data from Twitter, news, and VIX.

Usage:
    python scripts/refresh_sentiment_data.py               # Refresh last 90 days
    python scripts/refresh_sentiment_data.py --days 30   # Refresh last 30 days
    python scripts/refresh_sentiment_data.py --ticker "NIFTY 50"
"""

import argparse
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc.sentiment_data import refresh_sentiment_data


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=90,
                       help="Number of days of historical data to fetch (default: 90)")
    parser.add_argument("--ticker", type=str, default="NIFTY 50",
                       help="Ticker to search for in news (default: 'NIFTY 50')")
    args = parser.parse_args()
    
    print(f"Refreshing sentiment data for the last {args.days} days...")
    
    # Check for API keys
    has_news_api = bool(os.environ.get("NEWS_API_KEY"))
    has_twitter_api = bool(os.environ.get("TWITTER_BEARER_TOKEN"))
    
    if not has_news_api:
        print("WARNING: NEWS_API_KEY environment variable not set")
        print("News sentiment will not be fetched. Set it with:")
        print("  export NEWS_API_KEY=your_api_key_here")
        print("  Get API key from: https://newsapi.org/")
    
    if not has_twitter_api:
        print("INFO: TWITTER_BEARER_TOKEN not set")
        print("Twitter sentiment requires paid API for historical data")
        print("Current implementation uses VIX and news sentiment only")
    
    # Refresh sentiment data
    try:
        results = refresh_sentiment_data(days=args.days, ticker=args.ticker)
        print(f"\nRefresh complete:")
        print(f"  Sources fetched: {len(results['sources_fetched'])}")
        print(f"  Total observations: {results['total_observations']}")
        if results['errors']:
            print(f"  Errors: {len(results['errors'])}")
            for error in results['errors']:
                print(f"    - {error}")
    except Exception as e:
        print(f"Error refreshing sentiment data: {e}")


if __name__ == "__main__":
    main()
