#!/usr/bin/env python
"""
Backtest Chemical sector bullish planetary syntax.
"""

import sys

sys.path.insert(0, r'D:\SBC_Tool')

import datetime

import numpy as np
import pandas as pd

from sbc.cgsp_framework import angular_distance, get_planet
from sbc.nakshatra import tithi_of
from sbc.planets import all_planets_with_natures, positions

# =============================================================================
# CHEMICAL SECTOR PROXIES
# =============================================================================

CHEMICAL_TICKERS = {
    "PIIND": "PIIND.NS",          # PI Industries (agrochemicals)
    "UPL": "UPL.NS",              # UPL (agrochemicals)
    "SRF": "SRF.NS",              # SRF (chemicals)
    "TATACHEM": "TATACHEM.NS",    # Tata Chemicals
    "GNFC": "GNFC.NS",            # Gujarat Narmada Valley Fertilizers
    "COROMANDEL": "COROMANDEL.NS", # Coromandel International
    "DEEPAKNTR": "DEEPAKNTR.NS",  # Deepak Nitrite
    "NAVINFLUOR": "NAVINFLUOR.NS", # Navin Fluorine
    "ATUL": "ATUL.NS",            # Atul Ltd
    "PIDILITIND": "PIDILITIND.NS", # Pidilite (specialty chemicals)
}

# =============================================================================
# PLANETARY SYNTAX DEFINITIONS
# =============================================================================

def check_chemical_syntax(planets, tithi, sun, moon):
    """Check all chemical sector bullish syntax configurations."""

    jupiter = get_planet(planets, "Jupiter")
    venus = get_planet(planets, "Venus")
    saturn = get_planet(planets, "Saturn")
    mercury = get_planet(planets, "Mercury")
    mars = get_planet(planets, "Mars")
    rahu = get_planet(planets, "Rahu")
    ketu = get_planet(planets, "Ketu")

    results = {}

    # ---- 1. MARS (Primary for Chemicals) ----
    mars_strong = mars["sign"] in {"Aries", "Scorpio", "Capricorn"}
    mars_sat_trine = abs(angular_distance(mars["longitude"], saturn["longitude"]) - 120) < 8
    mars_jup_trine = abs(angular_distance(mars["longitude"], jupiter["longitude"]) - 120) < 8
    mars_rahu_free = angular_distance(mars["longitude"], rahu["longitude"]) > 15
    mars_ketu_free = angular_distance(mars["longitude"], ketu["longitude"]) > 15
    mars_malefic_free = mars_rahu_free and mars_ketu_free

    results["mars_strong"] = mars_strong
    results["mars_sat_trine"] = mars_sat_trine
    results["mars_jup_trine"] = mars_jup_trine
    results["mars_malefic_free"] = mars_malefic_free

    # Mars Ideal for Chemicals
    results["mars_ideal_chemical"] = mars_strong and (mars_sat_trine or mars_jup_trine) and mars_malefic_free

    # ---- 2. SATURN ----
    saturn_strong = saturn["sign"] in {"Capricorn", "Aquarius"}
    saturn_earthy = saturn["sign"] in {"Taurus", "Virgo"}
    sat_mars_trine = abs(angular_distance(saturn["longitude"], mars["longitude"]) - 120) < 8
    sat_merc_trine = abs(angular_distance(saturn["longitude"], mercury["longitude"]) - 120) < 8

    results["saturn_strong"] = saturn_strong
    results["saturn_earthy"] = saturn_earthy
    results["sat_mars_trine"] = sat_mars_trine
    results["sat_merc_trine"] = sat_merc_trine

    results["saturn_chemical_stable"] = (saturn_strong or saturn_earthy) and (sat_mars_trine or sat_merc_trine)

    # ---- 3. RAHU (Petrochemicals) ----
    rahu_strong = rahu["sign"] in {"Aries", "Taurus"}
    rahu_chemical_naks = rahu["nakshatra"] in {"Bharani", "Krittika", "Rohini", "Mrigashira"}
    rahu_mars_conj = angular_distance(rahu["longitude"], mars["longitude"]) < 8
    rahu_merc_trine = abs(angular_distance(rahu["longitude"], mercury["longitude"]) - 120) < 8
    rahu_chemical_support = rahu_mars_conj or rahu_merc_trine

    results["rahu_strong"] = rahu_strong
    results["rahu_chemical_naks"] = rahu_chemical_naks
    results["rahu_chemical_support"] = rahu_chemical_support

    results["rahu_ideal_chemical"] = (rahu_strong or rahu_chemical_naks) and rahu_chemical_support

    # ---- 4. MERCURY ----
    mercury_strong = mercury["sign"] in {"Virgo", "Gemini"}
    merc_sat_trine = abs(angular_distance(mercury["longitude"], saturn["longitude"]) - 120) < 8
    merc_mars_trine = abs(angular_distance(mercury["longitude"], mars["longitude"]) - 120) < 8
    merc_comb_free = True  # Simplified - would need combust check

    results["mercury_strong"] = mercury_strong
    results["merc_sat_trine"] = merc_sat_trine
    results["merc_mars_trine"] = merc_mars_trine
    results["merc_comb_free"] = merc_comb_free

    results["mercury_chemical_trade"] = mercury_strong and (merc_sat_trine or merc_mars_trine) and merc_comb_free

    # ---- 5. JUPITER (Secondary) ----
    jup_mars_trine = abs(angular_distance(jupiter["longitude"], mars["longitude"]) - 120) < 8
    jupiter_earthy = jupiter["sign"] in {"Taurus", "Virgo", "Capricorn"}
    jupiter_cancer = jupiter["sign"] == "Cancer"

    results["jup_mars_trine"] = jup_mars_trine
    results["jupiter_earthy"] = jupiter_earthy
    results["jupiter_cancer"] = jupiter_cancer
    results["jupiter_chemical_demand"] = jup_mars_trine or jupiter_earthy or jupiter_cancer

    # ---- 6. SBC VEDHA CHECKS ----
    try:
        from sbc.chakra import GRID
        from sbc.prediction import compute_vedhas, place_planets, sector_read

        grid = place_planets(GRID, planets)
        vedha_map, _ = compute_vedhas(planets, school="allthree")

        sector_projections = sector_read(vedha_map, planets)

        # Chemical sectors: Industry, Manufacturing, Materials, Fire, Engineering
        # Rashis: Aries/Scorpio (Mars), Capricorn/Aquarius (Saturn), Taurus/Scorpio (Materials)
        chemical_rashis = ["Aries", "Scorpio", "Capricorn", "Aquarius", "Taurus", "Virgo", "Leo"]

        positive_chemical = 0
        negative_chemical = 0
        for proj in sector_projections:
            if proj["rashi"] in chemical_rashis:
                if proj["net"] > 0:
                    positive_chemical += proj["net"]
                elif proj["net"] < 0:
                    negative_chemical += abs(proj["net"])

        results["sbc_chemical_net"] = positive_chemical - negative_chemical
        results["sbc_chemical_positive"] = positive_chemical > negative_chemical
        results["sbc_chemical_strong"] = positive_chemical > negative_chemical + 1

        # Specific cell vedha
        industry_vedha = False
        material_vedha = False
        business_vedha = False

        for p in planets:
            if p["nature"] == "benefic":
                for hit in vedha_map.get(p["name"], []):
                    if hit["type"] == "rashi":
                        if hit["label"] in ["Aries", "Scorpio", "Leo"]:  # Industry/Fire
                            industry_vedha = True
                        if hit["label"] in ["Taurus", "Scorpio", "Capricorn", "Virgo"]:  # Material
                            material_vedha = True
                        if hit["label"] in ["Taurus", "Scorpio", "Gemini", "Sagittarius"]:  # Business/Trade
                            business_vedha = True

        results["sbc_industry_vedha"] = industry_vedha
        results["sbc_material_vedha"] = material_vedha
        results["sbc_business_vedha"] = business_vedha
        results["sbc_chemical_all_clear"] = industry_vedha and material_vedha and business_vedha

        # Ketu obstruction check
        ketu_obstruction = False
        for hit in vedha_map.get("Ketu", []):
            if hit["type"] == "rashi" and hit["label"] in ["Aries", "Scorpio", "Taurus", "Virgo"]:
                ketu_obstruction = True
        results["ketu_obstruction"] = ketu_obstruction

    except Exception as e:
        results["sbc_error"] = str(e)

    # ---- 7. COMBINED SCORING ----
    score = 0
    active = []

    # Tier 1: Core planetary syntax
    if results.get("mars_ideal_chemical", False):
        score += 4
        active.append("MARS_IDEAL_CHEMICAL (Mars Aries/Scorpio/Cap + Sat/Jup trine + malefic-free)")
    if results.get("rahu_ideal_chemical", False):
        score += 3
        active.append("RAHU_IDEAL_CHEMICAL (Rahu Aries/Tau/Bharani-Krittika + Mars conj/Merc trine)")
    if results.get("saturn_chemical_stable", False):
        score += 3
        active.append("SATURN_CHEMICAL_STABLE (Sat Cap/Aqu/Tau/Vir + Mars/Merc trine)")

    # Tier 2: Core planetary
    if results.get("mars_strong", False):
        score += 2
        active.append("MARS STRONG (Aries/Scorpio/Capricorn)")
    if results.get("mars_sat_trine", False):
        score += 2
        active.append("MARS-SATURN TRINE (stable production)")
    if results.get("mars_jup_trine", False):
        score += 2
        active.append("MARS-JUPITER TRINE (industrial expansion)")
    if results.get("saturn_strong", False):
        score += 2
        active.append("SATURN STRONG (Capricorn/Aquarius)")
    if results.get("rahu_ideal_chemical", False):
        score += 2
        active.append("RAHU CHEMICAL (Aries/Tau + Bharani-Krittika + support)")
    if results.get("mercury_chemical_trade", False):
        score += 2
        active.append("MERCURY CHEMICAL TRADE (Virgo/Gemini + Sat/Mars trine)")

    # Tier 3: Supporting
    if results.get("saturn_earthy", False):
        score += 1
        active.append("SATURN EARTHY (Taurus/Virgo)")
    if results.get("rahu_strong", False) or results.get("rahu_chemical_naks", False):
        score += 1
        active.append("RAHU STRONG/CHEMICAL NAKS (Aries/Tau/Bharani-Krittika)")
    if results.get("mercury_strong", False):
        score += 1
        active.append("MERCURY STRONG (Virgo/Gemini)")
    if results.get("jupiter_chemical_demand", False):
        score += 1
        active.append("JUPITER CHEMICAL DEMAND (Mars trine/Earthy/Cancer)")

    # Tier 4: SBC Vedha
    if results.get("sbc_chemical_strong", False):
        score += 2
        active.append("SBC CHEMICAL STRONG (positive rashi net)")
    elif results.get("sbc_chemical_positive", False):
        score += 1
        active.append("SBC CHEMICAL POSITIVE")

    if results.get("sbc_chemical_all_clear", False):
        score += 2
        active.append("SBC CHEMICAL ALL CLEAR (Industry+Material+Business benefic)")
    elif results.get("sbc_industry_vedha", False) and results.get("sbc_material_vedha", False):
        score += 2
        active.append("SBC INDUSTRY+MATERIAL VEDHA BENEFIC")
    elif results.get("sbc_industry_vedha", False):
        score += 1
        active.append("SBC INDUSTRY VEDHA BENEFIC")
    elif results.get("sbc_material_vedha", False):
        score += 1
        active.append("SBC MATERIAL VEDHA BENEFIC")

    # Ketu obstruction penalty
    if results.get("ketu_obstruction", False):
        score -= 2
        active.append("KETU OBSTRUCTION ON INDUSTRY/MATERIAL")

    results["chemical_score"] = score
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


def get_chemical_summary(results):
    if not results["active_signals"]:
        return "No chemical sector bullish syntax active."
    return f"Chemical Score: {results['chemical_score']} ({results['conviction']}). Active: {'; '.join(results['active_signals'])}"


def get_chemical_price_levels(current_price, results):
    if current_price is None:
        current_price = 2000
    score = results["chemical_score"]
    if results["is_strong_bullish"]:
        target = round(current_price * 1.10, -1)
        support = round(target * 0.95, -1)
        stop = round(support * 0.97, -1)
    elif results["is_bullish"]:
        target = round(current_price * 1.06, -1)
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
        "method": f"Chemical score {score}: " +
                 ("Strong 10% target" if results["is_strong_bullish"] else
                  "Moderate 6% target" if results["is_bullish"] else "Neutral")
    }


def scan_chemical_signals(date_str, planets, tithi, sun, moon, current_price=None):
    results = check_chemical_syntax(planets, tithi, sun, moon)
    summary = get_chemical_summary(results)
    price_levels = get_chemical_price_levels(current_price, results)
    return {
        "date": date_str,
        "chemical_score": results["chemical_score"],
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
    utc = local.astimezone(datetime.UTC).replace(tzinfo=None)
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
    print(f"\nRunning Chemical backtest from {start_date} to {end_date}...")

    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    all_dates = pd.bdate_range(start=start, end=end)

    events = []

    for i, date in enumerate(all_dates):
        date_str = date.strftime('%Y-%m-%d')
        if i % 500 == 0:
            print(f"  Progress: {i}/{len(all_dates)} days ({date_str})")

        planets, tithi, sun, moon = get_planets_for_date(date_str)
        syntax = check_chemical_syntax(planets, tithi, sun, moon)

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
    print("CHEMICAL SECTOR BACKTEST RESULTS")
    print("="*70)

    if not events:
        print("No bullish events!")
        return

    syntax_keys = [
        "mars_ideal_chemical", "rahu_ideal_chemical", "saturn_chemical_stable",
        "mars_strong", "mars_sat_trine", "mars_jup_trine", "saturn_strong",
        "rahu_ideal_chemical", "mercury_chemical_trade", "saturn_chemical_stable",
        "jupiter_chemical_demand", "sbc_chemical_strong", "sbc_chemical_all_clear"
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

def main():
    end_date = datetime.date.today().strftime('%Y-%m-%d')
    start_date = (datetime.date.today() - datetime.timedelta(days=10*365)).strftime('%Y-%m-%d')

    if len(sys.argv) > 1:
        start_date = sys.argv[1]
    if len(sys.argv) > 2:
        end_date = sys.argv[2]

    print("Chemical Sector Backtest")
    print(f"Period: {start_date} to {end_date}")

    extended_end = (datetime.date.fromisoformat(end_date) + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    price_data = {}

    for name, ticker in CHEMICAL_TICKERS.items():
        print(f"  Fetching {name} ({ticker})...")
        prices = fetch_price_data(ticker, start_date, extended_end)
        if prices is not None and len(prices) > 50:
            price_data[name] = prices
            print(f"    OK: {len(prices)} rows")
        else:
            print("    FAILED")

    if not price_data:
        print("ERROR: No price data!")
        return

    events = run_backtest(start_date, end_date, price_data)
    analyze_results(events)


if __name__ == "__main__":
    main()
