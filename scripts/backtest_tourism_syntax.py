#!/usr/bin/env python
"""
Backtest Tourism/Leisure/Hospitality sector bullish planetary syntax.

Tests the planetary configurations from user's takeaway against
historical tourism/leisure sector proxies.
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
from sbc.prediction import sector_read, compute_vedhas, place_planets
from sbc.chakra import GRID

# =============================================================================
# SECTOR PROXIES
# =============================================================================

TOURISM_TICKERS = {
    "HOTELAVI": "HAVELLS.NS",    # Hotel proxy (Havells has hospitality exposure)
    "IRCTC": "IRCTC.NS",         # Railways/tourism
    "THOMASCOOK": "TCI.NS",      # Travel logistics
    "WONDERLA": "WONDERLA.NS",   # Amusement park (if listed)
    "LEMONTREE": "LEMONTREE.NS", # Hotels
    "CHOLET": "CHOLET.NS",       # Hotels
    "TAJGVK": "TAJGVK.NS",       # Taj hotels
    "EIHOTEL": "EIHOTEL.NS",     # Oberoi hotels
    "FOOD": "HINDUNILVR.NS",     # Food brands
    "JUBLFOOD": "JUBLFOOD.NS",   # QSR
}

# =============================================================================
# PLANETARY SYNTAX DEFINITIONS
# =============================================================================

def check_tourism_syntax(planets, tithi, sun, moon):
    """Check all tourism/leisure bullish syntax configurations."""
    
    jupiter = get_planet(planets, "Jupiter")
    venus = get_planet(planets, "Venus")
    saturn = get_planet(planets, "Saturn")
    mercury = get_planet(planets, "Mercury")
    mars = get_planet(planets, "Mars")
    rahu = get_planet(planets, "Rahu")
    ketu = get_planet(planets, "Ketu")
    
    results = {}
    
    # ---- 1. VENUS (Primary) ----
    venus_strong = venus["sign"] in {"Libra", "Taurus"}
    venus_jup_trine = abs(angular_distance(venus["longitude"], jupiter["longitude"]) - 120) < 8
    venus_moon_trine = abs(angular_distance(venus["longitude"], moon["longitude"]) - 120) < 8
    venus_sat_free = angular_distance(venus["longitude"], saturn["longitude"]) > 15
    venus_rahu_free = angular_distance(venus["longitude"], rahu["longitude"]) > 15
    venus_ketu_free = angular_distance(venus["longitude"], ketu["longitude"]) > 15
    venus_malefic_free = venus_sat_free and venus_rahu_free and venus_ketu_free
    
    results["venus_strong"] = venus_strong
    results["venus_jup_trine"] = venus_jup_trine
    results["venus_moon_trine"] = venus_moon_trine
    results["venus_malefic_free"] = venus_malefic_free
    
    # Venus Ideal for Tourism
    results["venus_ideal_tourism"] = venus_strong and (venus_jup_trine or venus_moon_trine) and venus_malefic_free
    
    # ---- 2. MOON ----
    moon_strong = moon["sign"] in {"Taurus", "Cancer"}
    moon_waxing = paksha_of(tithi) == "Shukla"
    moon_jup_trine = abs(angular_distance(moon["longitude"], jupiter["longitude"]) - 120) < 8
    moon_ven_trine = abs(angular_distance(moon["longitude"], venus["longitude"]) - 120) < 8
    
    results["moon_strong"] = moon_strong
    results["moon_waxing"] = moon_waxing
    results["moon_jup_trine"] = moon_jup_trine
    results["moon_ven_trine"] = moon_ven_trine
    
    results["moon_jupiter_combo"] = moon_jup_trine
    results["moon_venus_combo"] = moon_ven_trine
    results["moon_waxing_benefic"] = moon_waxing and (moon_jup_trine or moon_ven_trine)
    
    # ---- 3. JUPITER ----
    jupiter_exalted = jupiter["sign"] == "Cancer"
    jupiter_travel = jupiter["sign"] in {"Cancer", "Sagittarius", "Pisces"}
    jup_ven_trine = abs(angular_distance(jupiter["longitude"], venus["longitude"]) - 120) < 8
    jup_moon_trine = abs(angular_distance(jupiter["longitude"], moon["longitude"]) - 120) < 8
    
    results["jupiter_exalted"] = jupiter_exalted
    results["jupiter_travel_signs"] = jupiter_travel
    results["jup_ven_trine"] = jup_ven_trine
    results["jup_moon_trine"] = jup_moon_trine
    
    results["jupiter_venus_combo"] = jup_ven_trine
    results["jupiter_moon_combo"] = jup_moon_trine
    results["jupiter_tourism_ideal"] = (jupiter_exalted or jupiter_travel) and (jup_ven_trine or jup_moon_trine)
    
    # ---- 4. MERCURY ----
    mercury_strong = mercury["sign"] in {"Virgo", "Gemini"}
    merc_jup_trine = abs(angular_distance(mercury["longitude"], jupiter["longitude"]) - 120) < 8
    merc_ven_trine = abs(angular_distance(mercury["longitude"], venus["longitude"]) - 120) < 8
    
    results["mercury_strong"] = mercury_strong
    results["merc_jup_trine"] = merc_jup_trine
    results["merc_ven_trine"] = merc_ven_trine
    results["mercury_tourism_support"] = mercury_strong and (merc_jup_trine or merc_ven_trine)
    
    # ---- 5. MARS (Secondary) ----
    mars_sat_trine = abs(angular_distance(mars["longitude"], saturn["longitude"]) - 120) < 8
    mars_jup_trine = abs(angular_distance(mars["longitude"], jupiter["longitude"]) - 120) < 8
    
    results["mars_sat_trine"] = mars_sat_trine
    results["mars_jup_trine"] = mars_jup_trine
    results["mars_adventure_support"] = mars_sat_trine or mars_jup_trine
    
    # ---- 6. SBC VEDHA CHECKS ----
    # Check vedha on key life-area cells
    # We need to place planets on grid and check vedha
    try:
        grid = place_planets(GRID, planets)
        vedha_map, _ = compute_vedhas(planets, school="allthree")
        
        # Get sector projections - look for positive net on travel/hospitality sectors
        sector_projections = sector_read(vedha_map, planets)
        
        # Tourism sectors map to: Travel, Arts & Sports, Business, Finance, Property
        # In SBC, these are sectors from rashi projections
        tourism_rashis = ["Gemini", "Sagittarius", "Libra", "Taurus", "Cancer", "Leo"]
        
        positive_tourism = 0
        negative_tourism = 0
        for proj in sector_projections:
            if proj["rashi"] in tourism_rashis:
                if proj["net"] > 0:
                    positive_tourism += proj["net"]
                elif proj["net"] < 0:
                    negative_tourism += abs(proj["net"])
        
        results["sbc_tourism_net"] = positive_tourism - negative_tourism
        results["sbc_tourism_positive"] = positive_tourism > negative_tourism
        results["sbc_tourism_strong"] = positive_tourism > negative_tourism + 1
        
        # Check specific cell vedha
        # Travel cell: Gemini/Sagittarius axis
        # Arts & Sports: Leo/Aquarius
        # Business: Taurus/Scorpio
        # Finance: Taurus/Scorpio
        # Property: Cancer/Capricorn
        
        travel_vedha_benefic = False
        arts_vedha_benefic = False
        business_vedha_benefic = False
        
        for p in planets:
            if p["nature"] == "benefic":
                for hit in vedha_map.get(p["name"], []):
                    if hit["type"] == "rashi":
                        if hit["label"] in ["Gemini", "Sagittarius"]:  # Travel
                            travel_vedha_benefic = True
                        if hit["label"] in ["Leo", "Aquarius"]:  # Arts & Sports
                            arts_vedha_benefic = True
                        if hit["label"] in ["Taurus", "Scorpio"]:  # Business/Finance
                            business_vedha_benefic = True
        
        results["sbc_travel_vedha_benefic"] = travel_vedha_benefic
        results["sbc_arts_vedha_benefic"] = arts_vedha_benefic
        results["sbc_business_vedha_benefic"] = business_vedha_benefic
        results["sbc_all_clear"] = travel_vedha_benefic and arts_vedha_benefic and business_vedha_benefic
        
    except Exception as e:
        results["sbc_error"] = str(e)
    
    # ---- 7. COMBINED SCORING ----
    score = 0
    active = []
    
    # Tier 1: Core planetary syntax (backtested)
    if results.get("venus_ideal_tourism", False):
        score += 4
        active.append("VENUS_IDEAL_TOURISM (Venus Libra/Taurus + Jup/Moon trine + malefic-free)")
    if results.get("jupiter_tourism_ideal", False):
        score += 3
        active.append("JUPITER_TOURISM (Jupiter Cancer/Sag/Pisces + trine Venus/Moon)")
    if results.get("moon_jupiter_combo", False):
        score += 2
        active.append("MOON-JUPITER TRINE (comfort + expansion)")
    if results.get("moon_venus_combo", False):
        score += 2
        active.append("MOON-VENUS TRINE (comfort + pleasure)")
    if results.get("jupiter_venus_combo", False):
        score += 2
        active.append("JUPITER-VENUS TRINE (luxury expansion)")
    
    # Tier 2: Supporting planetary
    if results.get("venus_strong", False):
        score += 1
        active.append("VENUS STRONG (Libra/Taurus)")
    if results.get("moon_strong", False):
        score += 1
        active.append("MOON STRONG (Taurus/Cancer)")
    if results.get("mercury_tourism_support", False):
        score += 2
        active.append("MERCURY SUPPORT (Virgo/Gemini + Jup/Ven trine)")
    if results.get("mars_adventure_support", False):
        score += 1
        active.append("MARS ADVENTURE (Sat/Jup trine)")
    
    # Tier 3: Moon phase
    if results.get("moon_waxing", False):
        score += 1
        active.append("MOON WAXING (Shukla Paksha)")
    
    # Tier 4: SBC Vedha (structural)
    if results.get("sbc_tourism_strong", False):
        score += 3
        active.append("SBC TOURISM STRONG (positive rashi net)")
    elif results.get("sbc_tourism_positive", False):
        score += 1
        active.append("SBC TOURISM POSITIVE")
    
    if results.get("sbc_travel_vedha_benefic", False):
        score += 1
        active.append("SBC TRAVEL VEDHA BENEFIC")
    if results.get("sbc_arts_vedha_benefic", False):
        score += 1
        active.append("SBC ARTS&SPORTS VEDHA BENEFIC")
    if results.get("sbc_business_vedha_benefic", False):
        score += 1
        active.append("SBC BUSINESS VEDHA BENEFIC")
    if results.get("sbc_all_clear", False):
        score += 2
        active.append("SBC ALL CLEAR (Travel+Arts+Business benefic)")
    
    results["tourism_score"] = score
    results["active_signals"] = active
    results["is_bullish"] = score >= 5
    results["is_strong_bullish"] = score >= 8
    
    if score >= 10:
        results["conviction"] = "VERY_HIGH"
    elif score >= 7:
        results["conviction"] = "HIGH"
    elif score >= 5:
        results["conviction"] = "MEDIUM"
    elif score >= 3:
        results["conviction"] = "LOW"
    else:
        results["conviction"] = "NONE"
    
    return results


def get_tourism_summary(results):
    if not results["active_signals"]:
        return "No tourism/leisure bullish syntax active."
    return f"Tourism Score: {results['tourism_score']} ({results['conviction']}). Active: {'; '.join(results['active_signals'])}"


def get_tourism_price_levels(current_price, results):
    if current_price is None:
        current_price = 500
    score = results["tourism_score"]
    if results["is_strong_bullish"]:
        target = round(current_price * 1.08, -1)
        support = round(target * 0.96, -1)
        stop = round(support * 0.97, -1)
    elif results["is_bullish"]:
        target = round(current_price * 1.05, -1)
        support = round(target * 0.97, -1)
        stop = round(support * 0.98, -1)
    else:
        target = round(current_price * 1.02, -1)
        support = round(current_price * 0.98, -1)
        stop = round(support * 0.99, -1)
    return {
        "current_price": current_price,
        "target_high": target,
        "support_zone": support,
        "stop_loss": stop,
        "method": f"Tourism score {score}: " + 
                 ("Strong 8% target" if results["is_strong_bullish"] else 
                  "Moderate 5% target" if results["is_bullish"] else "Neutral")
    }


def scan_tourism_signals(date_str, planets, tithi, sun, moon, current_price=None):
    results = check_tourism_syntax(planets, tithi, sun, moon)
    summary = get_tourism_summary(results)
    price_levels = get_tourism_price_levels(current_price, results)
    return {
        "date": date_str,
        "tourism_score": results["tourism_score"],
        "conviction": results["conviction"],
        "is_bullish": results["is_bullish"],
        "is_strong_bullish": results["is_strong_bullish"],
        "active_signals": results["active_signals"],
        "summary": summary,
        "price_levels": price_levels,
        "details": results
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
    print(f"\nRunning Tourism backtest from {start_date} to {end_date}...")
    
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    all_dates = pd.bdate_range(start=start, end=end)
    
    events = []
    
    for i, date in enumerate(all_dates):
        date_str = date.strftime('%Y-%m-%d')
        if i % 500 == 0:
            print(f"  Progress: {i}/{len(all_dates)} days ({date_str})")
        
        planets, tithi, sun, moon = get_planets_for_date(date_str)
        syntax = check_tourism_syntax(planets, tithi, sun, moon)
        
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
    print("TOURISM/LEISURE/HOSPITALITY SECTOR BACKTEST RESULTS")
    print("="*70)
    
    if not events:
        print("No bullish events!")
        return
    
    # Analyze by syntax component
    syntax_keys = [
        "venus_ideal_tourism", "jupiter_tourism_ideal", "moon_jupiter_combo",
        "moon_venus_combo", "jupiter_venus_combo", "venus_strong",
        "moon_strong", "mercury_tourism_support", "jupiter_travel_signs",
        "sbc_tourism_strong", "sbc_all_clear", "sbc_travel_vedha_benefic"
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
    
    # Overall
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

def main():
    end_date = datetime.date.today().strftime('%Y-%m-%d')
    start_date = (datetime.date.today() - datetime.timedelta(days=10*365)).strftime('%Y-%m-%d')
    
    if len(sys.argv) > 1:
        start_date = sys.argv[1]
    if len(sys.argv) > 2:
        end_date = sys.argv[2]
    
    print(f"Tourism/Leisure/Hospitality Backtest")
    print(f"Period: {start_date} to {end_date}")
    
    # Fetch price data for multiple tourism proxies
    extended_end = (datetime.date.fromisoformat(end_date) + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    price_data = {}
    
    for name, ticker in TOURISM_TICKERS.items():
        print(f"  Fetching {name} ({ticker})...")
        prices = fetch_price_data(ticker, start_date, extended_end)
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