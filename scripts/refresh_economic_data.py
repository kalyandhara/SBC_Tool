"""Refresh economic data from FRED and RBI sources.

Usage:
    python scripts/refresh_economic_data.py              # Refresh last 10 years
    python scripts/refresh_economic_data.py --years 5   # Refresh last 5 years
"""

import argparse
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbc.economic_data import refresh_fred_data, add_rbi_manual_data


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--years", type=int, default=10, 
                       help="Number of years of historical data to fetch (default: 10)")
    args = parser.parse_args()
    
    print(f"Refreshing economic data for the last {args.years} years...")
    
    # Check for FRED API key
    if not os.environ.get("FRED_API_KEY"):
        print("WARNING: FRED_API_KEY environment variable not set")
        print("FRED data will not be fetched. Set it with:")
        print("  export FRED_API_KEY=your_api_key_here")
        print("  or set it in your shell profile")
    
    # Refresh FRED data
    try:
        results = refresh_fred_data(years=args.years)
        print(f"\nRefresh complete:")
        print(f"  Series fetched: {len(results['series_fetched'])}")
        print(f"  Total observations: {results['total_observations']}")
        if results['errors']:
            print(f"  Errors: {len(results['errors'])}")
            for error in results['errors']:
                print(f"    - {error}")
    except Exception as e:
        print(f"Error refreshing FRED data: {e}")
    
    # RBI data must be added manually (no public API)
    print("\nRBI data:")
    print("  RBI does not have a public API for policy rates")
    print("  Add manual data using:")
    print("    from sbc.economic_data import add_rbi_manual_data")
    print("    add_rbi_manual_data('2024-01-01', repo_rate=6.5, reverse_repo_rate=6.25)")


if __name__ == "__main__":
    main()
