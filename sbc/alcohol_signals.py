#!/usr/bin/env python
"""
Backtest Alcohol sector bullish planetary syntax.
"""

import sys

sys.path.insert(0, r'D:\SBC_Tool')


from sbc.cgsp_framework import angular_distance, get_planet
from sbc.nakshatra import paksha_of

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
# PLANETARY SYNTAX DEFINITIONS
# =============================================================================

def check_alcohol_syntax(planets, tithi, sun, moon):
    """Check all alcohol sector bullish syntax configurations."""

    jupiter = get_planet(planets, "Jupiter")
    venus = get_planet(planets, "Venus")
    saturn = get_planet(planets, "Saturn")
    mercury = get_planet(planets, "Mercury")
    mars = get_planet(planets, "Mars")
    rahu = get_planet(planets, "Rahu")
    ketu = get_planet(planets, "Ketu")


    results = {}

    # ---- 1. VENUS (Primary for Alcohol) ----
    venus_strong = venus["sign"] in {"Libra", "Taurus", "Pisces"}
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

    # Venus Ideal for Alcohol
    results["venus_ideal_alcohol"] = venus_strong and (venus_jup_trine or venus_moon_trine) and venus_malefic_free

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

    # ---- 3. RAHU ----
    rahu_strong = rahu["sign"] in {"Taurus", "Pisces"}
    rahu_chemical_naks = rahu["nakshatra"] in {"Bharani", "Krittika", "Rohini", "Mrigashira"}
    rahu_ven_conj = angular_distance(rahu["longitude"], venus["longitude"]) < 8
    rahu_ven_trine = abs(angular_distance(rahu["longitude"], venus["longitude"]) - 120) < 8
    rahu_merc_trine = abs(angular_distance(rahu["longitude"], mercury["longitude"]) - 120) < 8

    results["rahu_strong"] = rahu_strong
    results["rahu_chemical_naks"] = rahu_chemical_naks
    results["rahu_ven_conj"] = rahu_ven_conj
    results["rahu_ven_trine"] = rahu_ven_trine
    results["rahu_merc_trine"] = rahu_merc_trine

    results["rahu_ideal_alcohol"] = (rahu_strong or rahu_chemical_naks) and (rahu_ven_conj or rahu_ven_trine or rahu_merc_trine)

    # ---- 4. MARS ----
    mars_strong = mars["sign"] in {"Scorpio", "Capricorn"}
    mars_sat_trine = abs(angular_distance(mars["longitude"], saturn["longitude"]) - 120) < 8
    mars_jup_trine = abs(angular_distance(mars["longitude"], jupiter["longitude"]) - 120) < 8

    results["mars_strong"] = mars_strong
    results["mars_sat_trine"] = mars_sat_trine
    results["mars_jup_trine"] = mars_jup_trine

    results["mars_ideal_alcohol"] = mars_strong and (mars_sat_trine or mars_jup_trine)

    # ---- 5. JUPITER ----
    jupiter_exalted = jupiter["sign"] == "Cancer"
    jupiter_pisces = jupiter["sign"] == "Pisces"
    jup_ven_trine = abs(angular_distance(jupiter["longitude"], venus["longitude"]) - 120) < 8
    jup_moon_trine = abs(angular_distance(jupiter["longitude"], moon["longitude"]) - 120) < 8

    results["jupiter_exalted"] = jupiter_exalted
    results["jupiter_pisces"] = jupiter_pisces
    results["jup_ven_trine"] = jup_ven_trine
    results["jup_moon_trine"] = jup_moon_trine

    results["jupiter_ideal_alcohol"] = (jupiter_exalted or jupiter_pisces) and (jup_ven_trine or jup_moon_trine)

    # ---- 6. SBC VEDHA CHECKS ----
    try:
        from sbc.prediction import compute_vedhas, sector_read

        vedha_map, _ = compute_vedhas(planets, school="allthree")

        sector_projections = sector_read(vedha_map, planets)

        alcohol_rashis = ["Taurus", "Libra", "Cancer", "Pisces", "Scorpio", "Sagittarius", "Leo"]

        positive_alcohol = 0
        negative_alcohol = 0
        for proj in sector_projections:
            if proj["rashi"] in alcohol_rashis:
                if proj["net"] > 0:
                    positive_alcohol += proj["net"]
                elif proj["net"] < 0:
                    negative_alcohol += abs(proj["net"])

        results["sbc_alcohol_net"] = positive_alcohol - negative_alcohol
        results["sbc_alcohol_positive"] = positive_alcohol > negative_alcohol
        results["sbc_alcohol_strong"] = positive_alcohol > negative_alcohol + 1

        # Specific cell vedha
        pleasure_vedha = False
        liquids_vedha = False
        luxury_vedha = False
        business_vedha = False

        for p in planets:
            if p["nature"] == "benefic":
                for hit in vedha_map.get(p["name"], []):
                    if hit["type"] == "rashi":
                        if hit["label"] in ["Taurus", "Libra", "Leo"]:
                            pleasure_vedha = True
                        if hit["label"] in ["Cancer", "Scorpio", "Pisces"]:
                            liquids_vedha = True
                        if hit["label"] in ["Taurus", "Libra", "Sagittarius"]:
                            luxury_vedha = True
                            business_vedha = True
                        if hit["label"] in ["Taurus", "Scorpio", "Gemini", "Sagittarius"]:
                            business_vedha = True

        results["sbc_pleasure_vedha"] = pleasure_vedha
        results["sbc_liquids_vedha"] = liquids_vedha
        results["sbc_luxury_vedha"] = luxury_vedha
        results["sbc_business_vedha"] = business_vedha
        results["sbc_alcohol_all_clear"] = pleasure_vedha and liquids_vedha and luxury_vedha and business_vedha

        # Malefic obstruction
        saturn_obstruction = False
        ketu_obstruction = False
        rahu_obstruction = False

        for p in planets:
            if p["nature"] == "malefic":
                for hit in vedha_map.get(p["name"], []):
                    if hit["type"] == "rashi" and \
                            hit["label"] in ["Taurus", "Libra", "Cancer", "Pisces"]:
                            if p["name"] == "Saturn":
                                saturn_obstruction = True
                            elif p["name"] == "Ketu":
                                ketu_obstruction = True
                            elif p["name"] == "Rahu":
                                rahu_obstruction = True

        results["saturn_obstruction"] = saturn_obstruction
        results["ketu_obstruction"] = ketu_obstruction
        results["rahu_obstruction"] = rahu_obstruction

    except Exception as e:
        results["sbc_error"] = str(e)

    # ---- 7. COMBINED SCORING ----
    score = 0
    active = []

    # Tier 1: Core planetary syntax
    if results.get("venus_ideal_alcohol", False):
        score += 4
        active.append("VENUS_IDEAL_ALCOHOL (Venus Libra/Taurus/Pisces + Jup/Moon trine + malefic-free)")
    if results.get("jupiter_ideal_alcohol", False):
        score += 3
        active.append("JUPITER_IDEAL_ALCOHOL (Jupiter Cancer/Pisces + trine Venus/Moon)")
    if results.get("rahu_ideal_alcohol", False):
        score += 3
        active.append("RAHU_IDEAL_ALCOHOL (Rahu Taurus/Pisces + Venus conj/trine + nakshatras)")

    # Tier 2: Core planetary
    if results.get("venus_strong", False):
        score += 2
        active.append("VENUS_STRONG (Libra/Taurus/Pisces)")
    if results.get("moon_strong", False):
        score += 2
        active.append("MOON_STRONG (Taurus/Cancer)")
    if results.get("mars_ideal_alcohol", False):
        score += 2
        active.append("MARS_IDEAL_ALCOHOL (Scorpio/Capricorn + Sat/Jup trine)")
    if results.get("rahu_ideal_alcohol", False):
        score += 2
        active.append("RAHU_IDEAL_ALCOHOL (Taurus/Pisces + Venus conj/trine + nakshatras)")

    # Tier 3: Supporting
    if results.get("venus_jup_trine", False):
        score += 1
        active.append("VENUS-JUPITER TRINE")
    if results.get("venus_moon_trine", False):
        score += 1
        active.append("VENUS-MOON TRINE")
    if results.get("moon_jupiter_combo", False):
        score += 1
        active.append("MOON-JUPITER TRINE")
    if results.get("moon_venus_combo", False):
        score += 1
        active.append("MOON-VENUS TRINE")
    if results.get("jupiter_ideal_alcohol", False):
        score += 2
        active.append("JUPITER_IDEAL_ALCOHOL")
    if results.get("jup_ven_trine", False):
        score += 1
        active.append("JUPITER-VENUS TRINE")
    if results.get("jup_moon_trine", False):
        score += 1
        active.append("JUPITER-MOON TRINE")
    if results.get("mars_ideal_alcohol", False):
        score += 1
        active.append("MARS_IDEAL_ALCOHOL")
    if results.get("rahu_ideal_alcohol", False):
        score += 1
        active.append("RAHU_IDEAL_ALCOHOL (support)")
    if results.get("rahu_strong", False) or results.get("rahu_chemical_naks", False):
        score += 1
        active.append("RAHU STRONG/INTOXICANT NAKS")
    if results.get("moon_waxing", False):
        score += 1
        active.append("MOON WAXING (Shukla Paksha)")
    if results.get("moon_waxing_benefic", False):
        score += 1
        active.append("MOON WAXING + BENEFIC TRINE")

    # SBC Vedha
    if results.get("sbc_alcohol_strong", False):
        score += 3
        active.append("SBC ALCOHOL STRONG (positive rashi net)")
    elif results.get("sbc_alcohol_positive", False):
        score += 1
        active.append("SBC ALCOHOL POSITIVE")

    if results.get("sbc_alcohol_all_clear", False):
        score += 3
        active.append("SBC ALL CLEAR (Pleasure+Liquids+Luxury+Business benefic)")
    elif results.get("sbc_pleasure_vedha", False) and results.get("sbc_liquids_vedha", False):
        score += 2
        active.append("SBC PLEASURE+LIQUIDS VEDHA BENEFIC")
    elif results.get("sbc_pleasure_vedha", False):
        score += 1
        active.append("SBC PLEASURE VEDHA BENEFIC")
    elif results.get("sbc_liquids_vedha", False):
        score += 1
        active.append("SBC LIQUIDS VEDHA BENEFIC")
    elif results.get("sbc_luxury_vedha", False):
        score += 1
        active.append("SBC LUXURY VEDHA BENEFIC")
    elif results.get("sbc_business_vedha", False):
        score += 1
        active.append("SBC BUSINESS VEDHA BENEFIC")

    # Malefic obstruction penalties
    if results.get("saturn_obstruction", False):
        score -= 2
        active.append("⚠ SATURN OBSTRUCTION ON PLEASURE/LIQUIDS")
    if results.get("ketu_obstruction", False):
        score -= 2
        active.append("⚠ KETU OBSTRUCTION ON CONSUMPTION")
    if results.get("rahu_obstruction", False):
        score -= 1
        active.append("⚠ RAHU OBSTRUCTION ON LIQUIDS")

    results["alcohol_score"] = score
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


def get_alcohol_summary(results):
    if not results["active_signals"]:
        return "No alcohol sector bullish syntax active."
    return f"Alcohol Score: {results['alcohol_score']} ({results['conviction']}). Active: {'; '.join(results['active_signals'])}"


def get_alcohol_price_levels(current_price, results):
    if current_price is None:
        current_price = 1000
    score = results["alcohol_score"]
    if results["is_strong_bullish"]:
        target = round(current_price * 1.12, -1)
        support = round(target * 0.94, -1)
        stop = round(support * 0.97, -1)
    elif results["is_bullish"]:
        target = round(current_price * 1.07, -1)
        support = round(target * 0.96, -1)
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
        "method": f"Alcohol score {score}: " +
                 ("Strong 12% target" if results["is_strong_bullish"] else
                  "Moderate 7% target" if results["is_bullish"] else "Neutral")
    }


def scan_alcohol_signals(date_str, planets, tithi, sun, moon, current_price=None):
    results = check_alcohol_syntax(planets, tithi, sun, moon)
    summary = get_alcohol_summary(results)
    price_levels = get_alcohol_price_levels(current_price, results)
    return {
        "date": date_str,
        "alcohol_score": results["alcohol_score"],
        "conviction": results["conviction"],
        "is_bullish": results["is_bullish"],
        "is_strong_bullish": results["is_strong_bullish"],
        "active_signals": results["active_signals"],
        "summary": summary,
        "price_levels": price_levels,
        "details": results
    }
