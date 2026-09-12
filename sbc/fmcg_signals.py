"""FMCG/Food Sector Bullish Planetary Syntax Engine.

Implements the validated planetary syntax from backtesting:
1. Venus Ideal (Venus Libra/Taurus + trine Jupiter + free from malefics) - STRONGEST
2. Moon + Jupiter combo (trine/conjunction)
3. Moon + Venus combo (trine)
4. Jupiter in Cancer + trine Moon/Venus
5. Jupiter in water/earth signs
"""

from .cgsp_framework import angular_distance, get_planet


# =============================================================================
# FMCG SYNTAX CHECKS
# =============================================================================

def check_fmcg_syntax(planets, tithi, sun, moon):
    """Check all FMCG bullish syntax configurations."""
    
    jupiter = get_planet(planets, "Jupiter")
    venus = get_planet(planets, "Venus")
    saturn = get_planet(planets, "Saturn")
    mercury = get_planet(planets, "Mercury")
    rahu = get_planet(planets, "Rahu")
    ketu = get_planet(planets, "Ketu")
    mars = get_planet(planets, "Mars")
    
    from .nakshatra import paksha_of
    
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
    
    # Key combinations
    results["moon_jupiter_combo"] = moon_jup_trine or moon_jup_conj
    results["moon_venus_combo"] = moon_ven_trine
    results["moon_waxing_benefic"] = moon_waxing and (moon_jup_trine or moon_ven_trine or moon_jup_conj or moon_ven_conj)
    
    # ---- 2. VENUS SYNTAX (STRONGEST PER BACKTEST) ----
    venus_strong_sign = venus["sign"] in {"Libra", "Taurus"}
    venus_jup_trine = abs(angular_distance(venus["longitude"], jupiter["longitude"]) - 120) < 8
    venus_sat_free = angular_distance(venus["longitude"], saturn["longitude"]) > 15
    venus_rahu_free = angular_distance(venus["longitude"], rahu["longitude"]) > 15
    venus_malefic_free = venus_sat_free and venus_rahu_free
    
    results["venus_strong_sign"] = venus_strong_sign
    results["venus_jup_trine"] = venus_jup_trine
    results["venus_malefic_free"] = venus_malefic_free
    
    # VENUS IDEAL - strongest per backtest (Sharpe 5.52 at 1d, 4.10 at 5d)
    results["venus_ideal"] = venus_strong_sign and venus_jup_trine and venus_malefic_free
    
    # ---- 3. JUPITER SYNTAX ----
    jupiter_exalted = jupiter["sign"] == "Cancer"
    jupiter_water_earth = jupiter["sign"] in {"Cancer", "Scorpio", "Pisces", "Taurus", "Virgo", "Capricorn"}
    jup_moon_trine = abs(angular_distance(jupiter["longitude"], moon["longitude"]) - 120) < 8
    jup_ven_trine = abs(angular_distance(jupiter["longitude"], venus["longitude"]) - 120) < 8
    
    results["jupiter_exalted_cancer"] = jupiter_exalted
    results["jupiter_water_earth"] = jupiter_water_earth
    results["jup_moon_trine"] = jup_moon_trine
    results["jup_ven_trine"] = jup_ven_trine
    
    # Jupiter Cancer + trine Moon/Venus
    results["jupiter_cancer_moon_venus"] = jupiter_exalted and (jup_moon_trine or jup_ven_trine)
    results["jupiter_water_earth_bullish"] = jupiter_water_earth
    
    # ---- 4. SATURN STABILIZING ----
    sat_jup_trine = abs(angular_distance(saturn["longitude"], jupiter["longitude"]) - 120) < 8
    sat_moon_trine = abs(angular_distance(saturn["longitude"], moon["longitude"]) - 120) < 8
    sat_taurus_virgo = saturn["sign"] in {"Taurus", "Virgo"}
    
    results["sat_jup_trine"] = sat_jup_trine
    results["sat_moon_trine"] = sat_moon_trine
    results["sat_taurus_virgo"] = sat_taurus_virgo
    results["saturn_stabilizing"] = (sat_jup_trine or sat_moon_trine) and sat_taurus_virgo
    
    # ---- 5. ADDITIONAL FOOD-SECTOR SPECIFIC ----
    # Mercury in Virgo (food processing, logistics) + Jupiter support
    merc_virgo = mercury["sign"] == "Virgo"
    merc_jup_trine = abs(angular_distance(mercury["longitude"], jupiter["longitude"]) - 120) < 8
    results["mercury_virgo_jupiter"] = merc_virgo and merc_jup_trine
    
    # Rahu in food signs (Taurus, Cancer) - speculative food demand
    rahu_food_sign = rahu["sign"] in {"Taurus", "Cancer"}
    results["rahu_food_sign"] = rahu_food_sign
    
    # Ketu in Virgo/Pisces - food supply chain transformation
    ketu_supply_chain = ketu["sign"] in {"Virgo", "Pisces"}
    results["ketu_supply_chain"] = ketu_supply_chain
    
    # Mars in Taurus/Cancer - aggressive food commodity buying
    mars_food_sign = mars["sign"] in {"Taurus", "Cancer"}
    results["mars_food_commodity"] = mars_food_sign
    
    # ---- OVERALL SCORING ----
    # Weighted scoring based on backtest performance
    score = 0
    active_signals = []
    
    # Tier 1: Strongest signals (backtested high Sharpe)
    if results["venus_ideal"]:
        score += 4
        active_signals.append("VENUS_IDEAL (Venus Libra/Taurus + Jup trine + malefic-free)")
    if results["venus_strong_sign"] and results["venus_jup_trine"]:
        score += 3
        active_signals.append("Venus Libra/Taurus + Jup trine")
    
    # Tier 2: Strong combinations
    if results["moon_jupiter_combo"]:
        score += 2
        active_signals.append("Moon-Jupiter trine/conj")
    if results["moon_venus_combo"]:
        score += 2
        active_signals.append("Moon-Venus trine")
    if results["jupiter_cancer_moon_venus"]:
        score += 3
        active_signals.append("Jupiter Cancer + trine Moon/Venus")
    
    # Tier 3: Supporting
    if results["jupiter_water_earth_bullish"]:
        score += 1
        active_signals.append("Jupiter in water/earth")
    if results["venus_strong_sign"]:
        score += 1
        active_signals.append("Venus in Libra/Taurus")
    if results["saturn_stabilizing"]:
        score += 1
        active_signals.append("Saturn stabilizing (trine Jup/Moon in Tau/Vir)")
    
    # Tier 4: Food-sector specific
    if results["mercury_virgo_jupiter"]:
        score += 2
        active_signals.append("Mercury Virgo + Jup trine (food processing)")
    if results["rahu_food_sign"]:
        score += 1
        active_signals.append("Rahu in food sign (Tau/Can)")
    if results["ketu_supply_chain"]:
        score += 1
        active_signals.append("Ketu in supply chain sign (Vir/Pis)")
    if results["mars_food_commodity"]:
        score += 1
        active_signals.append("Mars in food commodity sign (Tau/Can)")
    
    # Moon phase modifier
    if results["moon_waxing"]:
        score += 1
        active_signals.append("Moon waxing (Shukla Paksha)")
    
    results["fmcg_score"] = score
    results["active_signals"] = active_signals
    results["is_bullish"] = score >= 5  # Threshold for bullish
    results["is_strong_bullish"] = score >= 8
    
    # Conviction level
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


def get_fmcg_summary(results):
    """Generate human-readable summary."""
    if not results["active_signals"]:
        return "No FMCG bullish planetary syntax active."
    
    conviction = results["conviction"]
    score = results["fmcg_score"]
    signals = "; ".join(results["active_signals"])
    
    return f"FMCG Score: {score} ({conviction}). Active: {signals}"


def get_fmcg_price_levels(current_price, results):
    """Generate FMCG-specific price levels based on syntax strength."""
    if current_price is None:
        current_price = 2500  # HUL approximate
    
    score = results["fmcg_score"]
    
    if results["is_strong_bullish"]:
        # Strong bullish: target 5-8% up, support 2-3% down
        target_high = round(current_price * 1.06, -1)
        support = round(target_high * 0.97, -1)
        stop = round(support * 0.98, -1)
    elif results["is_bullish"]:
        # Moderate bullish: target 3-5% up, support 1-2% down
        target_high = round(current_price * 1.04, -1)
        support = round(target_high * 0.98, -1)
        stop = round(support * 0.99, -1)
    else:
        # Neutral/bearish
        target_high = round(current_price * 1.02, -1)
        support = round(current_price * 0.98, -1)
        stop = round(support * 0.99, -1)
    
    return {
        "current_price": current_price,
        "target_high": target_high,
        "support_zone": support,
        "stop_loss": stop,
        "method": f"FMCG syntax score {score}: " + 
                 ("Strong bullish 6% target, 3% support" if results["is_strong_bullish"] else
                  "Moderate bullish 4% target, 2% support" if results["is_bullish"] else
                  "Neutral 2% target, 2% support")
    }


def scan_fmcg_signals(date_str, planets, tithi, sun, moon, current_price=None):
    """Complete FMCG signal scan for a date."""
    results = check_fmcg_syntax(planets, tithi, sun, moon)
    summary = get_fmcg_summary(results)
    price_levels = get_fmcg_price_levels(current_price, results)
    
    return {
        "date": date_str,
        "fmcg_score": results["fmcg_score"],
        "conviction": results["conviction"],
        "is_bullish": results["is_bullish"],
        "is_strong_bullish": results["is_strong_bullish"],
        "active_signals": results["active_signals"],
        "summary": summary,
        "price_levels": price_levels,
        "details": results
    }