"""Lunar Cycle Sector Forecast Module.

Combines lunar cycles (tithi, nakshatra, paksha), SBC vedha analysis,
and planetary nakshatra confluence to generate sector bullish/bearish forecasts.
"""

from .nakshatra import tithi_of, paksha_of, nakshatra_of, sign_of, moon_nature
from .planets import positions, all_planets_with_natures
from .cgsp_framework import angular_distance, get_planet
from .prediction import sector_read, compute_vedhas, place_planets, sentiment_of
from .chakra import GRID
from .sector_keywords import (
    NAKSHATRA_SECTOR_KEYWORDS,
    canonical_sector,
    canonical_sectors_for,
    classify,
    normalize_sectors,
)

# =============================================================================
# LUNAR CYCLE ANALYSIS
# =============================================================================

# Tithi groups and their market implications
TITHI_GROUPS = {
    # Nanda: 1, 6, 11, 16, 21, 26 - Growth, initiation
    # Bhadra: 2, 7, 12, 17, 22, 27 - Auspicious, prosperity
    # Jaya: 3, 8, 13, 18, 23, 28 - Victory, success
    # Rikta: 4, 9, 14, 19, 24, 29 - Empty, avoid new ventures
    # Purna: 5, 10, 15, 20, 25, 30 - Completion, fullness
}

# Nakshatra -> sector mapping used for scoring.
#
# Derived from the authoritative UI keywords in sbc.sector_keywords and
# collapsed onto the canonical scoring vocabulary, so a nakshatra's
# contribution lands on the same score key as a planet's. Deriving rather
# than duplicating is what stops the display and scoring layers drifting;
# to change what a nakshatra signifies, edit NAKSHATRA_SECTOR_KEYWORDS.
NAKSHATRA_SECTOR_MAP = {
    nak: canonical_sectors_for(nak) for nak in NAKSHATRA_SECTOR_KEYWORDS
}

# Paksha bias. "sectors" mixes canonical sectors with themes (Growth,
# Consolidation) -- both score the same way; callers classify them apart.
PAKSHA_BIAS = {
    "Shukla": {
        "bias": "BULLISH",
        "sectors": ["Growth", "Initiation", "New Ventures", "IT", "FMCG"],
        "strength": 1.2
    },
    "Krishna": {
        "bias": "BEARISH",
        "sectors": ["Consolidation", "Defensive", "Energy", "FMCG"],
        "strength": 1.1
    }
}

# Tithi specific effects
TITHI_EFFECTS = {
    # Shukla Paksha
    1: {"name": "Pratipada", "bias": "NEUTRAL", "note": "New beginnings"},
    2: {"name": "Dwitiya", "bias": "MILD_BULLISH", "note": "Growth"},
    3: {"name": "Tritiya", "bias": "BULLISH", "note": "Expansion"},
    4: {"name": "Chaturthi", "bias": "MILD_BEARISH", "note": "Obstacles"},
    5: {"name": "Panchami", "bias": "BULLISH", "note": "Knowledge, gains"},
    6: {"name": "Shashthi", "bias": "BULLISH", "note": "Victory"},
    7: {"name": "Saptami", "bias": "MILD_BULLISH", "note": "Power"},
    8: {"name": "Ashtami", "bias": "VOLATILE", "note": "Transformation"},
    9: {"name": "Navami", "bias": "MILD_BEARISH", "note": "Completion"},
    10: {"name": "Dashami", "bias": "BULLISH", "note": "Success"},
    11: {"name": "Ekadashi", "bias": "NEUTRAL", "note": "Spiritual"},
    12: {"name": "Dwadashi", "bias": "MILD_BULLISH", "note": "Wealth"},
    13: {"name": "Trayodashi", "bias": "BULLISH", "note": "Gains"},
    14: {"name": "Chaturdashi", "bias": "VOLATILE", "note": "Intensity"},
    15: {"name": "Purnima", "bias": "PEAK_BULLISH", "note": "Fullness, culmination"},
    
    # Krishna Paksha (16-30)
    16: {"name": "Pratipada", "bias": "MILD_BEARISH", "note": "Decline begins"},
    17: {"name": "Dwitiya", "bias": "BEARISH", "note": "Decline"},
    18: {"name": "Tritiya", "bias": "MILD_BEARISH", "note": "Decline"},
    19: {"name": "Chaturthi", "bias": "BEARISH", "note": "Obstacles"},
    20: {"name": "Panchami", "bias": "NEUTRAL", "note": "Stabilization"},
    21: {"name": "Shashthi", "bias": "MILD_BULLISH", "note": "Support"},
    22: {"name": "Saptami", "bias": "NEUTRAL", "note": "Consolidation"},
    23: {"name": "Ashtami", "bias": "BEARISH", "note": "Pressure"},
    24: {"name": "Navami", "bias": "BEARISH", "note": "Decline"},
    25: {"name": "Dashami", "bias": "MILD_BEARISH", "note": "Completion"},
    26: {"name": "Ekadashi", "bias": "NEUTRAL", "note": "Spiritual"},
    27: {"name": "Dwadashi", "bias": "MILD_BULLISH", "note": "Wealth"},
    28: {"name": "Trayodashi", "bias": "MILD_BULLISH", "note": "Gains"},
    29: {"name": "Chaturdashi", "bias": "VOLATILE", "note": "Intensity"},
    30: {"name": "Amavasya", "bias": "PEAK_BEARISH", "note": "Void, reset"},
}

# =============================================================================
# PLANETARY NAKSHATRA CONFLUENCE
# =============================================================================

# Planet significations, in the canonical vocabulary (themes included).
#
# Facets that named the same sector twice have been collapsed to one entry --
# Mercury's "Technology" and "Communication" are both IT, and listing both
# would hand IT double weight now that they share a score key.
PLANET_NAKSHATRA_SECTOR_WEIGHT = {
    "Sun": {"weight": 1.0, "sectors": ["PSU", "Energy", "Gold"]},
    "Moon": {"weight": 1.2, "sectors": ["Liquids", "FMCG", "Hospitality", "Public Sentiment"]},
    "Mars": {"weight": 1.0, "sectors": ["Metals", "Infra", "Defence", "Energy"]},
    "Mercury": {"weight": 1.1, "sectors": ["IT", "Banks", "Retail"]},
    "Jupiter": {"weight": 1.3, "sectors": ["Banks", "Education", "Expansion"]},
    "Venus": {"weight": 1.2, "sectors": ["Luxury", "FMCG", "Auto", "Media", "Alcohol"]},
    "Saturn": {"weight": 1.0, "sectors": ["Infra", "Metals", "Energy", "Realty"]},
    "Rahu": {"weight": 1.1, "sectors": ["IT", "Pharma", "Aviation", "Speculative"]},
    "Ketu": {"weight": 0.8, "sectors": ["Spiritual", "Research", "Pharma", "Isolation"]},
}

# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def get_lunar_cycle_analysis(sun_lon, moon_lon, planets):
    """Complete lunar cycle analysis for a date."""
    tithi = tithi_of(sun_lon, moon_lon)
    paksha = paksha_of(tithi)
    moon_nak = nakshatra_of(moon_lon)[0]
    sun_nak = nakshatra_of(sun_lon)[0]
    
    # Tithi effect
    tithi_effect = TITHI_EFFECTS.get(tithi, {"bias": "NEUTRAL", "note": ""})
    
    # Paksha bias
    paksha_info = PAKSHA_BIAS.get(paksha, {"bias": "NEUTRAL", "sectors": [], "strength": 1.0})
    
    # Moon nakshatra sector influence
    moon_nak_sectors = NAKSHATRA_SECTOR_MAP.get(moon_nak, [])
    
    # Sun nakshatra sector influence
    sun_nak_sectors = NAKSHATRA_SECTOR_MAP.get(sun_nak, [])
    
    # Moon nature (shubha/ashubha)
    moon_nat = moon_nature(tithi)
    
    return {
        "tithi": tithi,
        "tithi_name": tithi_effect.get("name", ""),
        "paksha": paksha,
        "moon_nakshatra": moon_nak,
        "sun_nakshatra": sun_nak,
        "tithi_bias": tithi_effect.get("bias", "NEUTRAL"),
        "tithi_note": tithi_effect.get("note", ""),
        "paksha_bias": paksha_info["bias"],
        "paksha_sectors": paksha_info["sectors"],
        "paksha_strength": paksha_info["strength"],
        "moon_nature": moon_nat,
        "moon_nak_sectors": moon_nak_sectors,
        "sun_nak_sectors": sun_nak_sectors,
        "is_purnima": tithi == 15,
        "is_amavasya": tithi == 30,
        "is_ekadashi": tithi in (11, 26),
        "is_ashtami": tithi in (8, 23),
        "is_chaturthi": tithi in (4, 19),
        "is_chaturdashi": tithi in (14, 29),
    }


def get_planetary_nakshatra_confluence(planets):
    """Calculate planetary nakshatra confluence for sectors."""
    sector_scores = {}
    details = []
    
    for p in planets:
        p_name = p["name"]
        p_nak = p["nakshatra"]
        p_sign = p["sign"]
        p_weight = PLANET_NAKSHATRA_SECTOR_WEIGHT.get(p_name, {"weight": 1.0, "sectors": []})
        
        # Nakshatra-based sectors
        nak_sectors = NAKSHATRA_SECTOR_MAP.get(p_nak, [])
        
        # Planet's natural sectors
        planet_sectors = p_weight["sectors"]
        
        # Combined weight
        base_weight = p_weight["weight"]
        
        # Dignity multiplier (simplified)
        dignity_mult = 1.0
        if p["sign"] in {"Aries", "Leo", "Sagittarius"} and p_name == "Sun":
            dignity_mult = 1.5
        elif p["sign"] == "Taurus" and p_name == "Moon":
            dignity_mult = 1.5
        elif p["sign"] == "Capricorn" and p_name == "Mars":
            dignity_mult = 1.5
        elif p["sign"] == "Virgo" and p_name == "Mercury":
            dignity_mult = 1.5
        elif p["sign"] == "Cancer" and p_name == "Jupiter":
            dignity_mult = 1.5
        elif p["sign"] == "Pisces" and p_name == "Venus":
            dignity_mult = 1.5
        elif p["sign"] == "Libra" and p_name == "Saturn":
            dignity_mult = 1.5
        
        # Retrograde bonus
        if p.get("retrograde", False):
            dignity_mult *= 1.5
        
        # Combustion penalty
        sun_lon = next((p2["longitude"] for p2 in planets if p2["name"] == "Sun"), 0)
        if p_name != "Sun":
            dist = abs((p["longitude"] - sun_lon + 180) % 360 - 180)
            if dist < 15:
                dignity_mult *= 0.5
        
        total_weight = base_weight * dignity_mult
        
        # Apply to nakshatra sectors
        for sector in nak_sectors:
            sector_scores[sector] = sector_scores.get(sector, 0) + total_weight
            details.append(f"{p_name} in {p_nak} -> {sector} (+{total_weight:.2f})")
        
        # Apply to planet natural sectors
        for sector in planet_sectors:
            sector_scores[sector] = sector_scores.get(sector, 0) + total_weight * 0.8
            details.append(f"{p_name} natural -> {sector} (+{total_weight * 0.8:.2f})")
    
    return {
        "sector_scores": sector_scores,
        "details": details,
        "top_bullish": sorted(sector_scores.items(), key=lambda x: -x[1])[:5],
        "top_bearish": sorted(sector_scores.items(), key=lambda x: x[1])[:3],
    }


def get_sbc_sector_vedha(planets):
    """Get SBC vedha analysis for sectors."""
    try:
        grid = place_planets(GRID, planets)
        vedha_map, _ = compute_vedhas(planets, school="allthree")
        sector_projections = sector_read(vedha_map, planets)
        
        # sector_read() scores each *rashi*; the forecast below looks sectors up
        # by *sector name*. Until this mapping existed the lookup never matched
        # and the SBC term of every lunar score was silently zero. Each rashi's
        # net is credited to every canonical sector that rashi signifies.
        rashi_vedha = {}
        sector_vedha = {}
        for proj in sector_projections:
            rashi = proj["rashi"]
            net = proj["net"]
            hits = proj["hits"]
            benefic = sum(1 for h in hits if h["nature"] == "benefic")
            malefic = sum(1 for h in hits if h["nature"] == "malefic")
            rashi_vedha[rashi] = {
                "net": net,
                "verdict": proj["verdict"],
                "benefic_hits": benefic,
                "malefic_hits": malefic,
            }
            for sector in normalize_sectors(proj.get("sectors", [])):
                agg = sector_vedha.setdefault(
                    sector, {"net": 0.0, "benefic_hits": 0, "malefic_hits": 0, "rashis": []})
                agg["net"] += net
                agg["benefic_hits"] += benefic
                agg["malefic_hits"] += malefic
                agg["rashis"].append(rashi)
        for agg in sector_vedha.values():
            agg["net"] = round(agg["net"], 3)
            agg["verdict"] = sentiment_of(agg["net"])[0]
        
        # Overall SBC bias
        total_net = sum(p["net"] for p in sector_projections)
        bullish_rashis = sum(1 for p in sector_projections if p["verdict"] in ["BULLISH", "STRONG_BULLISH"])
        bearish_rashis = sum(1 for p in sector_projections if p["verdict"] in ["BEARISH", "STRONG_BEARISH"])
        
        return {
            "sector_vedha": sector_vedha,
            "rashi_vedha": rashi_vedha,
            "total_net": round(total_net, 2),
            "bullish_rashis": bullish_rashis,
            "bearish_rashis": bearish_rashis,
            "overall_bias": "BULLISH" if total_net > 1 else "BEARISH" if total_net < -1 else "NEUTRAL",
        }
    except Exception as e:
        return {"error": str(e)}


def generate_lunar_sector_forecast(date_str, planets, tithi, sun, moon, current_prices=None):
    """Generate complete lunar cycle sector forecast."""
    
    # 1. Lunar cycle analysis
    lunar = get_lunar_cycle_analysis(sun["longitude"], moon["longitude"], planets)
    
    # 2. Planetary nakshatra confluence
    confluence = get_planetary_nakshatra_confluence(planets)
    
    # 3. SBC sector vedha
    sbc = get_sbc_sector_vedha(planets)
    
    # 3.5. Aspect analysis
    from .cgsp_framework import get_planet, angular_distance
    
    ASPECTS = {
        'conjunction': {'angle': 0, 'orb': 8, 'bias': 0, 'weight': 1.0, 'planet_dependent': True},
        'semisextile': {'angle': 30, 'orb': 3, 'bias': 0.3, 'weight': 0.5},
        'semisquare': {'angle': 45, 'orb': 3, 'bias': -0.7, 'weight': 0.7},
        'sextile': {'angle': 60, 'orb': 6, 'bias': 0.8, 'weight': 0.8},
        'square': {'angle': 90, 'orb': 8, 'bias': -1.0, 'weight': 1.2},
        'trine': {'angle': 120, 'orb': 8, 'bias': 0.8, 'weight': 1.0},
        'opposition': {'angle': 180, 'orb': 8, 'bias': -0.8, 'weight': 1.3},
    }
    
    PLANET_PAIRS = [
        ('Sun', 'Moon'), ('Sun', 'Mars'), ('Sun', 'Jupiter'), ('Sun', 'Saturn'),
        ('Moon', 'Mars'), ('Moon', 'Jupiter'), ('Moon', 'Saturn'),
        ('Mars', 'Jupiter'), ('Mars', 'Saturn'), ('Jupiter', 'Saturn'),
        ('Mercury', 'Jupiter'), ('Mercury', 'Saturn'), ('Venus', 'Mars'), ('Venus', 'Jupiter'),
    ]
    
    def get_planet_by_name(planets, name):
        return next((p for p in planets if p['name'] == name), None)
    
    def angular_distance(lon1, lon2):
        return abs((lon1 - lon2 + 180) % 360 - 180)
    
    aspects = []
    for p1_name, p2_name in [('Sun', 'Moon'), ('Sun', 'Mars'), ('Sun', 'Jupiter'), ('Sun', 'Saturn'),
                              ('Moon', 'Mars'), ('Moon', 'Jupiter'), ('Moon', 'Saturn'),
                              ('Mars', 'Jupiter'), ('Mars', 'Saturn'), ('Jupiter', 'Saturn'),
                              ('Mercury', 'Jupiter'), ('Mercury', 'Saturn'), ('Venus', 'Mars'), ('Venus', 'Jupiter')]:
        p1 = get_planet_by_name(planets, p1_name)
        p2 = get_planet_by_name(planets, p2_name)
        if not p1 or not p2: continue
        dist = angular_distance(p1['longitude'], p2['longitude'])
        for aspect_name, aspect_data in ASPECTS.items():
            target = aspect_data['angle']; orb = aspect_data['orb']
            if abs(dist - target) <= orb:
                exactness = 1.0 - (abs(dist - target) / orb)
                aspects.append({
                    'aspect': aspect_name, 'planet1': p1_name, 'planet2': p2_name,
                    'bias': aspect_data['bias'], 'weight': aspect_data['weight'],
                    'exactness': 1.0 - (abs(dist - target) / orb)
                })
    
    # Sector synthesis
    all_sectors = set()
    for data in [confluence, lunar]:
        if isinstance(data, dict):
            if "moon_nak_sectors" in data:
                all_sectors.update(data["moon_nak_sectors"])
            if "sun_nak_sectors" in data:
                all_sectors.update(data["sun_nak_sectors"])
            if "paksha_sectors" in data:
                all_sectors.update(data["paksha_sectors"])
            if "sector_scores" in data:
                all_sectors.update(data["sector_scores"].keys())
    
    # Add confluence top sectors
    for sector, score in confluence.get("top_bullish", []):
        all_sectors.add(sector)
    
    # Sector forecasts
    sector_forecasts = {}
    
    for sector in all_sectors:
        score = 0
        signals = []
        risks = []
        
        # Lunar influence
        if sector in lunar.get("moon_nak_sectors", []):
            score += 2
            signals.append(f"Moon in {lunar['moon_nakshatra']} supports {sector}")
        if sector in lunar.get("sun_nak_sectors", []):
            score += 1
            signals.append(f"Sun in {lunar['sun_nakshatra']} supports {sector}")
        if sector in lunar.get("paksha_sectors", []):
            score += 1.5
            signals.append(f"{lunar['paksha']} Paksha favors {sector}")
        
        # Tithi bias
        tithi_bias = lunar.get("tithi_bias", "NEUTRAL")
        if tithi_bias in ["BULLISH", "PEAK_BULLISH"]:
            score += 1
            signals.append(f"Tithi {lunar['tithi']} ({lunar['tithi_name']}) is {tithi_bias}")
        elif tithi_bias in ["BEARISH", "PEAK_BEARISH"]:
            score -= 1
            risks.append(f"Tithi {lunar['tithi']} ({lunar['tithi_name']}) is {tithi_bias}")
        
        # Paksha bias
        if lunar["paksha_bias"] == "BULLISH":
            score += lunar["paksha_strength"]
        elif lunar["paksha_bias"] == "BEARISH":
            score -= lunar["paksha_strength"]
        
        # Moon nature
        if lunar["moon_nature"] == "benefic":
            score += 0.5
        elif lunar["moon_nature"] == "malefic":
            score -= 0.5
        
        # Confluence
        conf_score = confluence.get("sector_scores", {}).get(sector, 0)
        if conf_score > 0:
            score += min(conf_score, 3)
            signals.append(f"Planetary confluence: +{conf_score:.1f}")
        
        # SBC Vedha
        sbc_data = sbc.get("sector_vedha", {}).get(sector, {})
        if sbc_data.get("net", 0) > 0:
            score += min(sbc_data["net"], 2)
            signals.append(f"SBC Vedha bullish: net {sbc_data['net']:.1f}")
        elif sbc_data.get("net", 0) < 0:
            score -= min(abs(sbc_data["net"]), 2)
            risks.append(f"SBC Vedha bearish: net {sbc_data['net']:.1f}")
        
        # Aspect influence
        aspect_score = 0
        for a in aspects:
            if a["bias"] > 0:
                aspect_score += a["bias"] * a["weight"] * a["exactness"]
            elif a["bias"] < 0:
                aspect_score += a["bias"] * a["weight"] * a["exactness"]
        
        score += aspect_score * 0.5
        
        # Determine bias
        if score >= 3:
            bias = "STRONG_BULLISH"
        elif score >= 1.5:
            bias = "BULLISH"
        elif score >= 0.5:
            bias = "MILD_BULLISH"
        elif score <= -3:
            bias = "STRONG_BEARISH"
        elif score <= -1.5:
            bias = "BEARISH"
        elif score <= -0.5:
            bias = "MILD_BEARISH"
        else:
            bias = "NEUTRAL"
        
        kind, _ = classify(sector)
        sector_forecasts[sector] = {
            "sector": sector,
            "kind": kind,
            "score": round(score, 2),
            "bias": bias,
            "signals": signals,
            "risks": risks,
            "confluence_score": round(conf_score, 2),
            "sbc_net": round(sbc_data.get("net", 0), 2) if sbc_data else 0,
            "aspect_score": round(aspect_score, 2),
        }
    
    # Sort by score
    sorted_sectors = sorted(sector_forecasts.items(), key=lambda x: -x[1]["score"])
    
    # Overall market bias
    total_score = sum(s["score"] for s in sector_forecasts.values())
    avg_score = total_score / len(sector_forecasts) if sector_forecasts else 0
    
    if avg_score >= 1.5:
        overall_bias = "BULLISH"
    elif avg_score >= 0.5:
        overall_bias = "MILD_BULLISH"
    elif avg_score <= -1.5:
        overall_bias = "BEARISH"
    elif avg_score <= -0.5:
        overall_bias = "MILD_BEARISH"
    else:
        overall_bias = "NEUTRAL"
    
    # Key dates
    key_dates = []
    if lunar["is_purnima"]:
        key_dates.append({"date": "Today", "event": "Purnima (Full Moon)", "impact": "HIGH", "note": "Peak liquidity, culmination"})
    if lunar["is_amavasya"]:
        key_dates.append({"date": "Today", "event": "Amavasya (New Moon)", "impact": "HIGH", "note": "Reset, new beginnings"})
    if lunar["is_ekadashi"]:
        key_dates.append({"date": "Today", "event": "Ekadashi", "impact": "MEDIUM", "note": "Spiritual, low volume"})
    if lunar["is_ashtami"]:
        key_dates.append({"date": "Today", "event": "Ashtami", "impact": "MEDIUM", "note": "Volatility"})
    if lunar["is_chaturthi"]:
        key_dates.append({"date": "Today", "event": "Chaturthi", "impact": "MEDIUM", "note": "Obstacles"})
    if lunar["is_chaturdashi"]:
        key_dates.append({"date": "Today", "event": "Chaturdashi", "impact": "HIGH", "note": "Intensity, volatility"})
    
    # Tradeable sectors vs market themes. "sector_forecasts" still carries both
    # so existing consumers are unaffected; the split views are additive.
    tradeable = {k: v for k, v in sector_forecasts.items() if v["kind"] == "sector"}
    themes = {k: v for k, v in sector_forecasts.items() if v["kind"] == "theme"}

    return {
        "date": date_str,
        "lunar": lunar,
        "confluence": confluence,
        "sbc": sbc,
        "sector_forecasts": sector_forecasts,
        "tradeable_forecasts": tradeable,
        "theme_forecasts": themes,
        "sorted_sectors": sorted_sectors,
        "overall_bias": overall_bias,
        "avg_score": round(avg_score, 2),
        "key_dates": key_dates,
        "total_sectors_analyzed": len(sector_forecasts),
        "tradeable_sectors_analyzed": len(tradeable),
        "themes_analyzed": len(themes),
        "bullish_sectors": len([s for s in sector_forecasts.values() if s["bias"] in ["BULLISH", "STRONG_BULLISH", "MILD_BULLISH"]]),
        "bearish_sectors": len([s for s in sector_forecasts.values() if s["bias"] in ["BEARISH", "STRONG_BEARISH", "MILD_BEARISH"]]),
        "neutral_sectors": len([s for s in sector_forecasts.values() if s["bias"] == "NEUTRAL"]),
    }


def generate_infographic_card(forecast):
    """Generate infographic card data for clipboard/social media."""

    # The card is a shareable sector call, so it reads tradeable sectors only --
    # a themed row ("Growth: BULLISH") is not something anyone can act on.
    tradeable = forecast.get("tradeable_forecasts") or forecast["sector_forecasts"]

    # Top 3 bullish sectors
    bullish = [(s, d) for s, d in tradeable.items()
               if d["bias"] in ["BULLISH", "STRONG_BULLISH", "MILD_BULLISH"]]
    bullish = sorted(bullish, key=lambda x: -x[1]["score"])[:3]

    # Top 3 bearish sectors
    bearish = [(s, d) for s, d in tradeable.items()
               if d["bias"] in ["BEARISH", "STRONG_BEARISH", "MILD_BEARISH"]]
    bearish = sorted(bearish, key=lambda x: x[1]["score"])[:3]
    
    # Lunar info
    lunar = forecast["lunar"]
    
    # Key aspects
    key_aspects = []
    from .cgsp_framework import get_planet, angular_distance
    from .cgsp_framework import get_planet
    
    # Build card data
    card = {
        "title": "🌙 LUNAR CYCLE SECTOR FORECAST",
        "date": forecast["date"],
        "overall_bias": forecast["overall_bias"],
        "lunar_phase": f"{forecast['lunar']['tithi_name']} ({forecast['lunar']['paksha']} Paksha)",
        "moon_nakshatra": forecast["lunar"]["moon_nakshatra"],
        "sun_nakshatra": forecast["lunar"]["sun_nakshatra"],
        "tithi": f"{forecast['lunar']['tithi']} - {forecast['lunar']['tithi_name']}",
        "paksha": forecast["lunar"]["paksha"],
        "overall_bias": forecast["overall_bias"],
        "avg_score": forecast["avg_score"],
        "top_bullish": [{"sector": s, "score": round(d["score"], 1), "bias": d["bias"]}
                        for s, d in sorted(tradeable.items(), key=lambda x: -x[1]["score"])[:5]],
        "top_bearish": [{"sector": s, "score": round(d["score"], 1), "bias": d["bias"]}
                        for s, d in sorted(tradeable.items(), key=lambda x: x[1]["score"])[:3]],
        "key_dates": forecast["key_dates"],
        "lunar_info": {
            "tithi": f"{lunar['tithi']} - {lunar['tithi_name']}",
            "paksha": lunar["paksha"],
            "moon_nakshatra": lunar["moon_nakshatra"],
            "moon_nature": lunar["moon_nature"],
            "tithi_bias": lunar["tithi_bias"],
        },
        "sbc_summary": {
            "overall_bias": forecast["sbc"].get("overall_bias", "NEUTRAL"),
            "total_net": forecast["sbc"].get("total_net", 0),
            "bullish_rashis": forecast["sbc"].get("bullish_rashis", 0),
            "bearish_rashis": forecast["sbc"].get("bearish_rashis", 0),
        },
        "confluence_top": forecast["confluence"].get("top_bullish", [])[:3],
        "key_dates": forecast["key_dates"],
        "stats": {
            "bullish_sectors": forecast["bullish_sectors"],
            "bearish_sectors": forecast["bearish_sectors"],
            "neutral_sectors": forecast["neutral_sectors"],
        },
        "disclaimer": "For research only. Not financial advice. Vedic astrology is probabilistic.",
    }
    
    return card


def format_card_for_clipboard(card):
    """Format card as text for clipboard copying."""
    lines = []
    lines.append("=" * 50)
    lines.append(f"🌙 LUNAR CYCLE SECTOR FORECAST - {card['date']}")
    lines.append("=" * 50)
    lines.append(f"📅 {card['lunar_phase']} | Tithi: {card['tithi']}")
    lines.append(f"🌙 Moon: {card['moon_nakshatra']} | ☀️ Sun: {card['sun_nakshatra']}")
    lines.append(f"📊 Overall Bias: {card['overall_bias']} (Score: {card['avg_score']})")
    lines.append("")
    lines.append("🟢 TOP BULLISH SECTORS:")
    for i, s in enumerate(card["top_bullish"], 1):
        lines.append(f"  {i}. {s['sector']} ({s['bias']}) Score: {s['score']}")
    lines.append("")
    lines.append("🔴 TOP BEARISH SECTORS:")
    for i, s in enumerate(card["top_bearish"], 1):
        lines.append(f"  {i}. {s['sector']} ({s['bias']}) Score: {s['score']}")
    lines.append("")
    lines.append("🌙 LUNAR INFO:")
    for k, v in card["lunar_info"].items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append("📅 KEY DATES:")
    for kd in card["key_dates"]:
        lines.append(f"  {kd['event']}: {kd['impact']} - {kd['note']}")
    lines.append("")
    lines.append("🧿 SBC SUMMARY:")
    for k, v in card["sbc_summary"].items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append("⚠️ DISCLAIMER: For research only. Not financial advice.")
    lines.append("=" * 50)
    return "\n".join(lines)


def format_card_for_social_media(card):
    """Format card for social media (Twitter/LinkedIn)."""
    bias_emoji = {"BULLISH": "🟢", "MILD_BULLISH": "🟢", "STRONG_BULLISH": "🚀",
                  "BEARISH": "🔴", "MILD_BEARISH": "🔴", "STRONG_BEARISH": "📉",
                  "NEUTRAL": "⚪"}[card["overall_bias"]]
    
    text = f"{bias_emoji} LUNAR SECTOR FORECAST - {card['date']}\n\n"
    text += f"🌙 {card['lunar_phase']} | Tithi: {card['tithi']}\n"
    text += f"🌙 Moon: {card['moon_nakshatra']} | ☀️ Sun: {card['sun_nakshatra']}\n\n"
    text += f"📊 Overall: {card['overall_bias']} (Score: {card['avg_score']})\n\n"
    text += "🟢 TOP BULLISH:\n"
    for i, s in enumerate(card["top_bullish"][:3], 1):
        text += f"  {i}. {s['sector']} ({s['bias']}) Score: {s['score']}\n"
    text += "\n🔴 TOP BEARISH:\n"
    for i, s in enumerate(card["top_bearish"][:2], 1):
        text += f"  {i}. {s['sector']} ({s['bias']}) Score: {s['score']}\n"
    text += f"\n🌙 {card['lunar_phase']} | Moon: {card['moon_nakshatra']}\n"
    text += f"\n#VedicAstrology #MarketForecast #LunarCycle #Trading"
    return text