#!/usr/bin/env python
"""
Backtest Alcohol sector bullish planetary syntax.
"""

import sys
sys.path.insert(0, r'D:\SBC_Tool')

import datetime
import pandas as pd
import numpy as np
import json

from sbc.planets import positions, all_planets_with_natures
from sbc.nakshatra import tithi_of, paksha_of, nakshatra_of
from sbc.cgsp_framework import angular_distance, get_planet
from sbc.prediction import sector_read, compute_vedhas, place_planets
from sbc.chakra import GRID

# =============================================================================
# ALCOHOL SECTOR PROXIES
# =============================================================================

ALCOHOL_TICKERS = {
    "UBL": "UBL.NS",              # United Breweries
    "RADICO": "RADICO.NS",        # Radico Khaitan
    "TILAKNAGAR": "TILAKNAGAR.NS", # Tilaknagar Industries
    "SOM": "SOMDIST.NS",          # Som Distilleries
    "ALLIED": "ALLIED.NS",        # Allied Blenders
}

# =============================================================================
# BACKTEST ENGINE
# =============================================================================

def get_julian_day(dt):
    base = datetime.datetime(2000, 1, 1, 12, 0, 0)
    diff = dt - base
    return 2451545.0 + diff.total_seconds() / 86400.0


def get_planets_for_date(date_str):
    import zoneinfo
    local = datetime.datetime.strptime(date_str + ' 09:15', '%Y-%m-%d %H:%M')
    tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    local = local.replace(tzinfo=tz)
    utc = local.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    jul = get_julian_day(utc)
    planets, _ = positions(jul)
    sun = next(p for p in planets if p["name"] == "Sun")
    moon = next(p for p in planets if p["name"] == "Moon")
    tithi = tithi_of(sun["longitude"], moon["longitude"])
    planets = all_planets_with_natures(planets, tithi, sun["longitude"])
    return planets, tithi, sun, moon


def fetch_price_data(ticker, start_date, end_date):
    import yfinance as yf
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=False)
        if data is not None and not data.empty:
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = [c[0] for c in data.columns]
            data = data.reset_index()
            data["Date"] = pd.to_datetime(data["Date"]).dt.tz_localize(None)
            data = data.set_index("Date")
            return data["Close"]
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
    return None


def run_backtest(start_date, end_date, price_data_dict):
    print(f"\nRunning Alcohol backtest from {start_date} to {end_date}...")
    
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    all_dates = pd.bdate_range(start=start, end=end)
    
    events = []
    
    from sbc.planets import positions, all_planets_with_natures
    from sbc.nakshatra import tithi_of
    from sbc.cgsp_framework import get_planet
    from sbc.alcohol_signals import check_alcohol_syntax, scan_alcohol_signals
    
    for i, date in enumerate(all_dates):
        date_str = date.strftime('%Y-%m-%d')
        if i % 500 == 0:
            print(f"  Progress: {i}/{len(all_dates)} days ({date_str})")
        
        planets, tithi, sun, moon = get_planets_for_date(date_str)
        syntax = check_alcohol_syntax(planets, tithi, sun, moon)
        
        if syntax["is_bullish"]:
            for ticker_name, prices in price_data_dict.items():
                if prices is None:
                    continue
                trigger_ts = pd.Timestamp(date_str)
                future_prices = prices[prices.index >= trigger_ts]
                if len(future_prices) == 0:
                    continue
                entry_price = future_prices.iloc[0]
                
                returns = {}
                for h in [1, 3, 5, 10, 20]:
                    if len(future_prices) > h:
                        exit_price = future_prices.iloc[h]
                        ret = (exit_price - entry_price) / entry_price * 100
                        returns[f"{h}d"] = round(ret, 2)
                
                if returns:
                    events.append({
                        "date": date_str,
                        "ticker": ticker_name,
                        "syntax": syntax,
                        "returns": returns
                    })
    
    return events


def analyze_results(events):
    print("\n" + "="*70)
    print("ALCOHOL SECTOR BACKTEST RESULTS")
    print("="*70)
    
    if not events:
        print("No bullish events!")
        return
    
    syntax_keys = [
        "venus_ideal_alcohol", "jupiter_ideal_alcohol", "rahu_ideal_alcohol",
        "venus_strong", "moon_strong", "mars_ideal_alcohol",
        "venus_jup_trine", "venus_moon_trine", "moon_jupiter_combo",
        "moon_venus_combo", "jupiter_ideal_alcohol", "jup_ven_trine",
        "mars_ideal_alcohol", "rahu_ideal_alcohol", "moon_waxing",
        "sbc_alcohol_strong", "sbc_alcohol_all_clear", "saturn_obstruction"
    ]
    
    for key in syntax_keys:
        active_events = [e for e in events if e["syntax"].get(key, False)]
        if not active_events or len(active_events) < 5:
            continue
        
        print(f"\n{'='*50}")
        print(f"SYNTAX: {key} ({len(active_events)} events)")
        print(f"{'='*50}")
        
        for h in ["1d", "3d", "5d", "10d", "20d"]:
            rets = [e["returns"][h] for e in active_events if e["returns"].get(h) is not None]
            if not rets:
                continue
            rets = np.array(rets)
            wins = rets[rets > 0]
            print(f"  {h:>4}: Count={len(rets):3d}  Win%={len(wins)/len(rets)*100:5.1f}%  "
                  f"Avg={np.mean(rets):6.2f}%  Med={np.median(rets):6.2f}%  "
                  f"Sharpe={np.mean(rets)/np.std(rets)*np.sqrt(252/int(h[:-1])) if np.std(rets)>0 else 0:5.2f}")
    
    print(f"\n{'='*50}")
    print(f"ALL BULLISH EVENTS: {len(events)}")
    print(f"{'='*50}")
    for h in ["1d", "3d", "5d", "10d", "20d"]:
        rets = [e["returns"][h] for e in events if e["returns"].get(h) is not None]
        if not rets:
            continue
        rets = np.array(rets)
        wins = rets[rets > 0]
        print(f"  {h:>4}: Count={len(rets):3d}  Win%={len(wins)/len(rets)*100:5.1f}%  "
              f"Avg={np.mean(rets):6.2f}%  Med={np.median(rets):6.2f}%  "
              f"Sharpe={np.mean(rets)/np.std(rets)*np.sqrt(252/int(h[:-1])) if np.std(rets)>0 else 0:5.2f}")


# =============================================================================
# MAIN
# =============================================================================

def get_planets_for_date(date_str):
    import zoneinfo
    local = datetime.datetime.strptime(date_str + ' 09:15', '%Y-%m-%d %H:%M')
    tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    local = local.replace(tzinfo=tz)
    utc = local.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    base = datetime.datetime(2000, 1, 1, 12, 0, 0)
    diff = utc - base
    jul = 2451545.0 + diff.total_seconds() / 86400.0
    planets, _ = positions(jul)
    sun = next(p for p in planets if p["name"] == "Sun")
    moon = next(p for p in planets if p["name"] == "Moon")
    tithi = tithi_of(sun["longitude"], moon["longitude"])
    planets = all_planets_with_natures(planets, tithi, sun["longitude"])
    return planets, tithi, sun, moon


def fetch_price_data(ticker, start_date, end_date):
    import yfinance as yf
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=False)
        if data is not None and not data.empty:
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = [c[0] for c in data.columns]
            data = data.reset_index()
            data["Date"] = pd.to_datetime(data["Date"]).dt.tz_localize(None)
            data = data.set_index("Date")
            return data["Close"]
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
    return None


def main():
    end_date = datetime.date.today().strftime('%Y-%m-%d')
    start_date = (datetime.date.today() - datetime.timedelta(days=10*365)).strftime('%Y-%m-%d')
    
    if len(sys.argv) > 1:
        start_date = sys.argv[1]
    if len(sys.argv) > 2:
        end_date = sys.argv[2]
    
    print(f"Alcohol Sector Backtest")
    print(f"Period: {start_date} to {end_date}")
    
    extended_end = (datetime.date.fromisoformat(end_date) + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    price_data = {}
    
    for name, ticker in ALCOHOL_TICKERS.items():
        print(f"  Fetching {name} ({ticker})...")
        prices = fetch_price_data(ticker, start_date, end_date)
        if prices is not None and len(prices) > 50:
            price_data[name] = prices
            print(f"    OK: {len(prices)} rows")
        else:
            print(f"    FAILED")
    
    if not price_data:
        print("ERROR: No price data!")
        return
    
    events = run_backtest(start_date, end_date, price_data)
    analyze_results(events)


if __name__ == "__main__":
    main()