"""Tourism/Leisure/Hospitality Sector Bullish Planetary Syntax Engine.

Validated planetary syntax from 10-year backtest (2015-2024):
1. Moon in Taurus/Cancer (STRONGEST) - 63.5% win at 10d, Sharpe 1.83
2. Venus in Libra/Taurus - 59.7% win at 10d, Sharpe 1.65
3. Jupiter-Venus trine - 60.2% win at 10d, Sharpe 1.83
4. Moon-Venus trine - 60.8% win at 10d, Sharpe 1.65
5. Moon-Jupiter trine - 56.8% win at 10d, Sharpe 1.44
6. Mercury Tourism Support (Vir/Gem + Jup/Ven trine) - 55.8% win at 10d, Sharpe 1.49
"""

from .cgsp_framework import angular_distance, get_planet

# =============================================================================
# TOURISM/LEISURE SYNTAX CHECKS
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

    from .nakshatra import paksha_of

    results = {}

    # ---- 1. MOON (STRONGEST PER BACKTEST) ----
    moon_strong = moon["sign"] in {"Taurus", "Cancer"}
    moon_waxing = paksha_of(tithi) == "Shukla"
    moon_jup_trine = abs(angular_distance(moon["longitude"], jupiter["longitude"]) - 120) < 8
    moon_ven_trine = abs(angular_distance(moon["longitude"], venus["longitude"]) - 120) < 8
    moon_jup_conj = angular_distance(moon["longitude"], jupiter["longitude"]) < 8
    moon_ven_conj = angular_distance(moon["longitude"], venus["longitude"]) < 8

    results["moon_strong"] = moon_strong
    results["moon_waxing"] = moon_waxing
    results["moon_jup_trine"] = moon_jup_trine
    results["moon_ven_trine"] = moon_ven_trine
    results["moon_jup_conj"] = moon_jup_conj
    results["moon_ven_conj"] = moon_ven_conj

    # Key combinations
    results["moon_jupiter_combo"] = moon_jup_trine or moon_jup_conj
    results["moon_venus_combo"] = moon_ven_trine
    results["moon_waxing_benefic"] = moon_waxing and (moon_jup_trine or moon_ven_trine or moon_jup_conj or moon_ven_conj)

    # ---- 2. VENUS ----
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

    # ---- 3. JUPITER ----
    jupiter_exalted = jupiter["sign"] == "Cancer"
    jupiter_travel = jupiter["sign"] in {"Cancer", "Sagittarius", "Pisces"}
    jup_ven_trine = abs(angular_distance(jupiter["longitude"], venus["longitude"]) - 120) < 8
    jup_moon_trine = abs(angular_distance(jupiter["longitude"], moon["longitude"]) - 120) < 8

    results["jupiter_exalted"] = jupiter_exalted
    results["jupiter_travel_signs"] = jupiter_travel
    results["jup_ven_trine"] = jup_ven_trine
    results["jup_moon_trine"] = jup_moon_trine

    # Jupiter Tourism Ideal
    results["jupiter_tourism_ideal"] = (jupiter_exalted or jupiter_travel) and (jup_ven_trine or jup_moon_trine)
    results["jupiter_venus_combo"] = jup_ven_trine
    results["jupiter_moon_combo"] = jup_moon_trine

    # ---- 4. MERCURY ----
    mercury_strong = mercury["sign"] in {"Virgo", "Gemini"}
    merc_jup_trine = abs(angular_distance(mercury["longitude"], jupiter["longitude"]) - 120) < 8
    merc_ven_trine = abs(angular_distance(mercury["longitude"], venus["longitude"]) - 120) < 8

    results["mercury_strong"] = mercury_strong
    results["merc_jup_trine"] = merc_jup_trine
    results["merc_ven_trine"] = merc_ven_trine

    # Mercury Tourism Support (backtested strong)
    results["mercury_tourism_support"] = mercury_strong and (merc_jup_trine or merc_ven_trine)

    # ---- 5. MARS (Secondary) ----
    mars_sat_trine = abs(angular_distance(mars["longitude"], saturn["longitude"]) - 120) < 8
    mars_jup_trine = abs(angular_distance(mars["longitude"], jupiter["longitude"]) - 120) < 8

    results["mars_sat_trine"] = mars_sat_trine
    results["mars_jup_trine"] = mars_jup_trine
    results["mars_adventure_support"] = mars_sat_trine or mars_jup_trine

    # ---- 6. SBC VEDHA CHECKS ----
    try:
        from .chakra import GRID
        from .prediction import compute_vedhas, place_planets, sector_read

        grid = place_planets(GRID, planets)
        vedha_map, _ = compute_vedhas(planets, school="allthree")

        sector_projections = sector_read(vedha_map, planets)

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
        travel_vedha_benefic = False
        arts_vedha_benefic = False
        business_vedha_benefic = False

        for p in planets:
            if p["nature"] == "benefic":
                for hit in vedha_map.get(p["name"], []):
                    if hit["type"] == "rashi":
                        if hit["label"] in ["Gemini", "Sagittarius"]:
                            travel_vedha_benefic = True
                        if hit["label"] in ["Leo", "Aquarius"]:
                            arts_vedha_benefic = True
                        if hit["label"] in ["Taurus", "Scorpio"]:
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

    # Tier 1: Core planetary syntax (backtested highest Sharpe)
    if results.get("moon_strong", False):
        score += 4
        active.append("MOON_STRONG (Taurus/Cancer) - 63.5% win 10d, Sharpe 1.83")
    if results.get("venus_strong", False):
        score += 3
        active.append("VENUS_STRONG (Libra/Taurus) - 59.7% win 10d, Sharpe 1.65")
    if results.get("jupiter_venus_combo", False):
        score += 3
        active.append("JUPITER-VENUS TRINE - 60.2% win 10d, Sharpe 1.83")
    if results.get("moon_venus_combo", False):
        score += 3
        active.append("MOON-VENUS TRINE - 60.8% win 10d, Sharpe 1.65")
    if results.get("moon_jupiter_combo", False):
        score += 2
        active.append("MOON-JUPITER TRINE - 56.8% win 10d, Sharpe 1.44")

    # Tier 2: Strong supporting
    if results.get("mercury_tourism_support", False):
        score += 2
        active.append("MERCURY TOURISM SUPPORT (Virgo/Gemini + Jup/Ven trine) - Sharpe 1.49")
    if results.get("venus_ideal_tourism", False):
        score += 2
        active.append("VENUS_IDEAL_TOURISM (Venus Libra/Taurus + Jup/Moon trine + malefic-free)")
    if results.get("jupiter_tourism_ideal", False):
        score += 2
        active.append("JUPITER_TOURISM_IDEAL (Jupiter Cancer/Sag/Pisces + trine Venus/Moon)")

    # Tier 3: Supporting planetary
    if results.get("venus_strong", False) and not results.get("venus_ideal_tourism", False):
        score += 1
        active.append("VENUS STRONG (Libra/Taurus)")
    if results.get("jupiter_travel_signs", False):
        score += 1
        active.append("JUPITER IN TRAVEL SIGNS (Cancer/Sag/Pisces)")
    if results.get("mars_adventure_support", False):
        score += 1
        active.append("MARS ADVENTURE (Sat/Jup trine)")

    # Tier 4: Moon phase
    if results.get("moon_waxing", False):
        score += 1
        active.append("MOON WAXING (Shukla Paksha)")

    # Tier 5: SBC Vedha (structural)
    if results.get("sbc_tourism_strong", False):
        score += 2
        active.append("SBC TOURISM STRONG (positive rashi net)")
    elif results.get("sbc_tourism_positive", False):
        score += 1
        active.append("SBC TOURISM POSITIVE")

    if results.get("sbc_all_clear", False):
        score += 2
        active.append("SBC ALL CLEAR (Travel+Arts+Business benefic vedha)")
    elif results.get("sbc_travel_vedha_benefic", False):
        score += 1
        active.append("SBC TRAVEL VEDHA BENEFIC")
    if results.get("sbc_arts_vedha_benefic", False):
        score += 1
        active.append("SBC ARTS&SPORTS VEDHA BENEFIC")
    if results.get("sbc_business_vedha_benefic", False):
        score += 1
        active.append("SBC BUSINESS VEDHA BENEFIC")

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
    """Complete tourism signal scan for a date."""
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
