#!/usr/bin/env python
"""
Backtest FMCG/Food sector bullish planetary syntax.

Tests the planetary configurations from the user's takeaway against
historical FMCG sector performance.
"""

import sys
sys.path.insert(0, r'D:\SBC_Tool')

import datetime
import pandas as pd
import numpy as np
import json

from sbc.planets import positions, all_planets_with_natures
from sbc.nakshatra import tithi_of, paksha_of
from sbc.cgsp_framework import angular_distance, get_planet

# =============================================================================
# PLANETARY SYNTAX DEFINITIONS (from user's takeaway)
# =============================================================================

def check_fmcg_syntax(planets, tithi, sun, moon):
    """Check all FMCG bullish syntax configurations."""
    
    jupiter = get_planet(planets, "Jupiter")
    venus = get_planet(planets, "Venus")
    saturn = get_planet(planets, "Saturn")
    mercury = get_planet(planets, "Mercury")
    rahu = get_planet(planets, "Rahu")
    ketu = get_planet(planets, "Ketu")
    
    results = {}
    
    # ---- 1. MOON SYNTAX ----
    moon_strong_sign = moon["sign"] in {"Taurus", "Cancer"}
    moon_waxing = paksha_of(tithi) == "Shukla"
    moon_jup_trine = abs(angular_distance(moon["longitude"], jupiter["longitude"]) - 120) < 8
    moon_ven_trine = abs(angular_distance(moon["longitude"], venus["longitude"]) - 120) < 8
    moon_jup_conj = angular_distance(moon["longitude"], jupiter["longitude"]) < 8
    moon_ven_conj = angular_distance(moon["longitude"], venus["longitude"]) < 8
    
    results["moon_strong_sign"] = moon_strong_sign
    results["moon_waxing"] = moon_waxing
    results["moon_jup_trine"] = moon_jup_trine
    results["moon_ven_trine"] = moon_ven_trine
    results["moon_jup_conj"] = moon_jup_conj
    results["moon_ven_conj"] = moon_ven_conj
    
    # Moon + Jupiter combination (trine or conjunction)
    results["moon_jupiter_combo"] = moon_jup_trine or moon_jup_conj
    # Moon + Venus combination (trine)
    results["moon_venus_combo"] = moon_ven_trine
    # Moon waxing + benefic aspects
    results["moon_waxing_benefic"] = moon_waxing and (moon_jup_trine or moon_ven_trine or moon_jup_conj or moon_ven_conj)
    
    # ---- 2. VENUS SYNTAX ----
    venus_strong_sign = venus["sign"] in {"Libra", "Taurus"}
    venus_jup_trine = abs(angular_distance(venus["longitude"], jupiter["longitude"]) - 120) < 8
    venus_sat_free = angular_distance(venus["longitude"], saturn["longitude"]) > 15
    venus_rahu_free = angular_distance(venus["longitude"], rahu["longitude"]) > 15
    venus_malefic_free = venus_sat_free and venus_rahu_free
    
    results["venus_strong_sign"] = venus_strong_sign
    results["venus_jup_trine"] = venus_jup_trine
    results["venus_malefic_free"] = venus_malefic_free
    
    # Venus in Libra/Taurus + trine Jupiter + free from malefics
    results["venus_ideal"] = venus_strong_sign and venus_jup_trine and venus_malefic_free
    
    # ---- 3. JUPITER SYNTAX ----
    jupiter_exalted = jupiter["sign"] == "Cancer"
    jupiter_water_earth = jupiter["sign"] in {"Cancer", "Scorpio", "Pisces", "Taurus", "Virgo", "Capricorn"}
    jup_moon_trine = abs(angular_distance(jupiter["longitude"], moon["longitude"]) - 120) < 8
    jup_ven_trine = abs(angular_distance(jupiter["longitude"], venus["longitude"]) - 120) < 8
    jupiter_new_sign = False  # Would need ingress tracking
    
    results["jupiter_exalted_cancer"] = jupiter_exalted
    results["jupiter_water_earth"] = jupiter_water_earth
    results["jup_moon_trine"] = jup_moon_trine
    results["jup_ven_trine"] = jup_ven_trine
    
    # Jupiter in Cancer + trine Moon/Venus
    results["jupiter_cancer_moon_venus"] = jupiter_exalted and (jup_moon_trine or jup_ven_trine)
    # Jupiter in water/earth signs
    results["jupiter_water_earth_bullish"] = jupiter_water_earth
    
    # ---- 4. SATURN SYNTAX (stabilizing) ----
    sat_jup_trine = abs(angular_distance(saturn["longitude"], jupiter["longitude"]) - 120) < 8
    sat_moon_trine = abs(angular_distance(saturn["longitude"], moon["longitude"]) - 120) < 8
    sat_taurus_virgo = saturn["sign"] in {"Taurus", "Virgo"}
    
    results["sat_jup_trine"] = sat_jup_trine
    results["sat_moon_trine"] = sat_moon_trine
    results["sat_taurus_virgo"] = sat_taurus_virgo
    
    # Saturn stabilizing
    results["saturn_stabilizing"] = (sat_jup_trine or sat_moon_trine) and sat_taurus_virgo
    
    # ---- COMBINED SCORES ----
    # Most reliable combinations per user
    combo_1 = results["moon_jupiter_combo"]  # Moon + Jupiter trine/conj
    combo_2 = results["moon_venus_combo"]    # Moon + Venus trine
    combo_3 = results["jupiter_exalted_cancer"]  # Jupiter in Cancer
    combo_4 = results["venus_strong_sign"] and results["venus_jup_trine"]  # Venus Libra/Taurus + Jup trine
    combo_5 = results["moon_waxing_benefic"]  # Moon waxing + benefic aspects
    
    results["combo_moon_jupiter"] = combo_1
    results["combo_moon_venus"] = combo_2
    results["combo_jupiter_cancer"] = combo_3
    results["combo_venus_jupiter"] = combo_4
    results["combo_moon_waxing_benefic"] = combo_5
    
    # Overall bullish count
    bullish_count = sum([
        combo_1, combo_2, combo_3, combo_4, combo_5,
        results["venus_ideal"],
        results["jupiter_water_earth_bullish"],
        results["saturn_stabilizing"]
    ])
    results["bullish_score"] = bullish_count
    results["is_bullish"] = bullish_count >= 3  # At least 3 configurations
    
    return results


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


def fetch_fmcg_price_data(ticker, start_date, end_date):
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


def run_backtest(start_date, end_date, fmcg_prices):
    print(f"\nRunning FMCG backtest from {start_date} to {end_date}...")
    
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    all_dates = pd.bdate_range(start=start, end=end)
    
    events = []
    
    for i, date in enumerate(all_dates):
        date_str = date.strftime('%Y-%m-%d')
        if i % 500 == 0:
            print(f"  Progress: {i}/{len(all_dates)} days ({date_str})")
        
        planets, tithi, sun, moon = get_planets_for_date(date_str)
        syntax = check_fmcg_syntax(planets, tithi, sun, moon)
        
        if syntax["is_bullish"]:
            # Compute forward returns
            trigger_ts = pd.Timestamp(date_str)
            future_prices = fmcg_prices[fmcg_prices.index >= trigger_ts]
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
                    "syntax": syntax,
                    "returns": returns
                })
    
    return events


def analyze_fmcg_results(events):
    print("\n" + "="*70)
    print("FMCG/FOOD SECTOR BULLISH SYNTAX BACKTEST RESULTS")
    print("="*70)
    
    if not events:
        print("No bullish events found!")
        return
    
    # Analyze by individual syntax components
    syntax_keys = [
        "moon_jupiter_combo", "moon_venus_combo", "jupiter_cancer_moon_venus",
        "venus_ideal", "moon_waxing_benefic", "jupiter_water_earth_bullish",
        "saturn_stabilizing"
    ]
    
    for key in syntax_keys:
        active_events = [e for e in events if e["syntax"].get(key, False)]
        if not active_events:
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
    
    # Overall bullish events
    print(f"\n{'='*50}")
    print(f"ALL BULLISH EVENTS (score >= 3): {len(events)}")
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

def main():
    end_date = datetime.date.today().strftime('%Y-%m-%d')
    start_date = (datetime.date.today() - datetime.timedelta(days=10*365)).strftime('%Y-%m-%d')
    
    if len(sys.argv) > 1:
        start_date = sys.argv[1]
    if len(sys.argv) > 2:
        end_date = sys.argv[2]
    
    print(f"FMCG/FOOD Sector Planetary Syntax Backtest")
    print(f"Period: {start_date} to {end_date}")
    
    # Fetch FMCG proxy data (HUL)
    extended_end = (datetime.date.fromisoformat(end_date) + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    fmcg_prices = fetch_fmcg_price_data("HINDUNILVR.NS", start_date, extended_end)
    
    if fmcg_prices is None or len(fmcg_prices) < 100:
        print("ERROR: Could not fetch FMCG price data!")
        return
    
    print(f"Fetched {len(fmcg_prices)} trading days of HINDUNILVR.NS data")
    
    events = run_backtest(start_date, end_date, fmcg_prices)
    analyze_fmcg_results(events)


if __name__ == "__main__":
    main()