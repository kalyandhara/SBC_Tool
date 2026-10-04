"""Market prediction logic on the Sarvatobhadra Chakra.

The method (as used in modern mundane/timing practice, documented in
Phaladeepika XXVI and Horaratna/Rajavijaya):

1. Place the transiting planets on the 28-nakshatra ring of the chakra.
2. Each graha casts vedha (piercing) rays: front (straight across),
   left (diagonal in the zodiacal direction) and right (the other
   diagonal).  The classical school selects ONE operative ray by the
   planet's motion; the 'all-three' school uses all three.
3. From the market's anchor nakshatra, count out the sensitive points
   on the 28-star ring - the five Pancha-Shakha points (Janma, Karma,
   Sanghatika, Samudayika, Adhana) form the market core.
4. A malefic vedha on a sensitive point is bearish; a benefic vedha is
   bullish.  Strength is scaled by dignity (retrograde x2, exalted x3,
   debilitated x0.5, combust x0.5).
"""

from .chakra import GRID, NAKSHATRA_CELL, vedha_cells
from .nakshatra import PS_POINT_NAMES, sensitive_stars


def place_planets(grid, planets):
    """Attach planet markers to their nakshatra cells on a grid copy."""
    out = [[dict(cell) for cell in row] for row in grid]
    for p in planets:
        key = p["nakshatra"]
        cell = NAKSHATRA_CELL.get(key)
        if cell is None:
            continue
        r, c = cell
        cell_out = out[r - 1][c - 1]
        cell_out.setdefault("planets", []).append(p)
    return out


def compute_vedhas(planets, school="classical"):
    """Return a dict mapping planet name -> list of hit cells with rays,
    plus the full ray paths for drawing."""
    vedha_map: dict = {}
    ray_paths: dict = {}
    for p in planets:
        key = p["nakshatra"]
        cell = NAKSHATRA_CELL.get(key)
        if cell is None:
            vedha_map[p["name"]] = []
            ray_paths[p["name"]] = []
            continue
        grid_cell = GRID[cell[0] - 1][cell[1] - 1]
        hits = vedha_cells(grid_cell, p, school=school)
        vedha_map[p["name"]] = [
            {"row": c["row"], "col": c["col"], "type": c["type"],
             "label": c["label"], "ray": ray} for c, ray in hits
        ]
        # group into contiguous rays, preserving order
        paths = []
        current = None
        for c, ray in hits:
            if current is None or current["ray"] != ray:
                current = {"ray": ray, "cells": [[c["row"], c["col"]]]}
                paths.append(current)
            else:
                current["cells"].append([c["row"], c["col"]])
        ray_paths[p["name"]] = paths
    return vedha_map, ray_paths


def _contribution(p):
    sign = 1.0 if p["nature"] == "benefic" else -1.0
    return round(sign * p["dignity_multiplier"], 3)


def analyze(planets, vedha_map, birth_nakshatra, school):
    points = sensitive_stars(birth_nakshatra)
    point_cells = {}
    for pt in points:
        key = pt["nakshatra"]
        point_cells[pt["name"]] = NAKSHATRA_CELL.get(key)

    point_hits = []
    for p in planets:
        for hit in vedha_map.get(p["name"], []):
            for pt in points:
                key = pt["nakshatra"]
                if NAKSHATRA_CELL.get(key) == (hit["row"], hit["col"]):
                    point_hits.append({
                        "planet": p["name"],
                        "symbol": p["symbol"],
                        "nature": p["nature"],
                        "point": pt["name"],
                        "nakshatra": pt["nakshatra"],
                        "ray": hit["ray"],
                        "strength": _contribution(p),
                        "dignity_multiplier": p["dignity_multiplier"],
                        "dignity_reasons": p["dignity_reasons"],
                    })

    # Score on the five Pancha-Shakha points.
    score = {"benefic": 0.0, "malefic": 0.0}
    per_point: dict[str, list] = {name: [] for name in PS_POINT_NAMES}
    for hit in point_hits:
        if hit["point"] in PS_POINT_NAMES:
            score[hit["nature"]] += abs(hit["strength"])
            per_point[hit["point"]].append(hit)

    net = round(score["benefic"] - score["malefic"], 3)
    return {
        "points": points,
        "point_cells": point_cells,
        "point_hits": point_hits,
        "score": score,
        "net": net,
        "per_point": per_point,
        "school": school,
    }


def summarize_vedhas(vedha_map, planets, points):
    """Build a human-readable list of every vedha ray from the chakra.

    Each planet entry lists its active rays with the cells they pierce,
    marking which pierced cells are sensitive stars of the anchor.
    """
    star_to_point = {}
    for pt in points:
        star_to_point[pt["nakshatra"]] = pt["name"]

    out = []
    for p in planets:
        hits = vedha_map.get(p["name"], [])
        rays: list = []
        for h in hits:
            point = star_to_point.get(h["label"])
            last = rays[-1] if rays else None
            if last is not None and last["ray"] == h["ray"]:
                last["cells"].append({"label": h["label"], "point": point})
                if point:
                    last["hit_points"].append(point)
            else:
                hit_points = [point] if point else []
                rays.append({"ray": h["ray"],
                             "cells": [{"label": h["label"], "point": point}],
                             "hit_points": hit_points})
        out.append({
            "planet": p["name"],
            "symbol": p["symbol"],
            "nature": p["nature"],
            "nature_note": p.get("nature_note", ""),
            "dignity_reasons": p.get("dignity_reasons", []),
            "nakshatra": p["nakshatra"],
            "strength": p["signed_strength"],
            "rays": rays,
        })
    return out


def sentiment_of(net):
    """Return (verdict, strength_label) for a net score."""
    if net >= 2.0:
        return "BULLISH", "strong"
    if net >= 0.75:
        return "BULLISH", "moderate"
    if net > 0.0:
        return "BULLISH", "mild"
    if net <= -2.0:
        return "BEARISH", "strong"
    if net <= -0.75:
        return "BEARISH", "moderate"
    if net < 0.0:
        return "BEARISH", "mild"
    return "NEUTRAL", "flat"


def recommendation(analysis, anchor, date_str, weekday, tithi_info):
    net = analysis["net"]
    verdict, strength = sentiment_of(net)
    hits = analysis["point_hits"]
    malefics = [h for h in hits if h["nature"] == "malefic"]
    benefics = [h for h in hits if h["nature"] == "benefic"]

    if not hits:
        summary = (
            "No transiting graha pierces any of %s's sensitive stars; the day reads "
            "neutral on the chakra."
            % anchor["name"])
        lines = [
            "No vedha pressure lands on the market core, pointing to a low-signal, "
            "range-bound session. Treat the day as neutral and watch external drivers.",
        ]
    else:
        b_lines = []
        for h in sorted(benefics, key=lambda x: -x["strength"])[:4]:
            b_lines.append("%s (%s) to %s via %s ray" % (
                h["symbol"], h["planet"], h["point"], h["ray"]))
        m_lines = []
        for h in sorted(malefics, key=lambda x: -x["strength"])[:4]:
            m_lines.append("%s (%s) to %s via %s ray" % (
                h["symbol"], h["planet"], h["point"], h["ray"]))
        lines = []
        if b_lines:
            lines.append("Support: " + "; ".join(b_lines) + ".")
        if m_lines:
            lines.append("Pressure: " + "; ".join(m_lines) + ".")
        summary = {
            "BULLISH": "Benefic vedha outweighs malefic vedha on the market core, "
                       "favouring buying dips and momentum on strength.",
            "BEARISH": "Malefic vedha outweighs benefic vedha on the market core, "
                       "calling for caution, tighter risk and profit-booking on "
                       "strength.",
            "NEUTRAL": "Benefic and malefic vedha are finely balanced; expect "
                       "two-way movement and avoid large directional bets.",
        }[verdict]

    if strength == "strong":
        lines.append("The net read is strong; size positions accordingly.")
    elif strength == "moderate":
        lines.append("The net read is moderate; trade with defined risk.")
    elif strength == "mild":
        lines.append("The edge is mild; prefer small size and clear levels.")

    lines.append(
        "Context: Moon in %s paksha, tithi %d (%s) - %s. Weekday %s pairs with the "
        "%s tithi group."
        % (tithi_info["paksha"], tithi_info["tithi"], tithi_info["group"],
           tithi_info["moon_note"], weekday, tithi_info["group"]))

    # Build actionable investment directive
    if verdict == "BEARISH":
        bias = "Defensive / Bearish"
        sizing = "Reduce net directional exposure to 20-40% of normal. Cash preferred. Trim longs into strength. No fresh long initiation."
        risk = "Tighter stops 0.5-1.0R max per trade. Avoid leverage and intraday momentum amplification."
        action = "Prefer profit booking / selective short bias on rallies. Avoid fresh long initiation, especially after Bhadra onset if applicable."
    elif verdict == "BULLISH":
        bias = "Constructive / Bullish"
        sizing = "Increase exposure to 60-80% of normal with defined risk. Add on dips in favoured sectors."
        risk = "Use trailing stops, protect profits. Manage intraday pullbacks."
        action = "Prefer buying dips and momentum on strength. Initiate fresh longs in favoured sectors."
    else:
        bias = "Neutral / Range"
        sizing = "Keep exposure 40-60% of normal. Avoid large directional bets."
        risk = "Tight risk, scalp only."
        action = "Range trade, wait for breakout confirmation."

    # Tithi/weekday nuance
    tithi_group = tithi_info["group"]
    moon_note = tithi_info["moon_note"]
    tithi_note = "No initiation bias" if tithi_group.lower() in ("rikta",) else "Initiation allowed with caution"

    actionable = {
        "bias": bias,
        "sizing": sizing,
        "risk": risk,
        "action": action,
        "tithi_note": f"Weekday {weekday} with {tithi_group} tithi {tithi_info['tithi']}. Moon {moon_note}. {tithi_note}.",
        "strength": strength,
    }

    return {
        "verdict": verdict,
        "strength": strength,
        "net": net,
        "summary": summary,
        "text": lines,
        "actionable": actionable,
    }


# Interpretive mapping of the 12 rashis (which sit on the chakra's inner ring)
# to market sectors, derived from classical rashi significations. This mapping
# is a study heuristic and is configurable at the API level.
RASHI_SECTORS = {
    "Aries": ["Defense & Infra", "Steel & Energy"],
    "Taurus": ["Banks & Finance", "Food & Agri", "Jewelry"],
    "Gemini": ["IT & Media", "Telecom", "Auto & Mobility"],
    "Cancer": ["Realty & Housing", "Healthcare", "Consumer Staples"],
    "Leo": ["Gold & Metals", "PSU & Sovereign", "Entertainment"],
    "Virgo": ["Pharma", "Healthcare IT", "Consulting"],
    "Libra": ["Retail & E-com", "Trade & Exports", "Airlines"],
    "Scorpio": ["Oil & Gas", "Mining", "Insurance"],
    "Sagittarius": ["Travel & Aviation", "Education", "Shipping"],
    "Capricorn": ["Manufacturing", "Cement & Infra", "Coal & Railways"],
    "Aquarius": ["Technology", "Renewables", "Semiconductors"],
    "Pisces": ["Petroleum", "Pharma & Alcohol", "Logistics"],
}

# Three-letter abbreviations for compact card headers.
RASHI_SHORT = {
    "Aries": "ARI", "Taurus": "TAU", "Gemini": "GEM", "Cancer": "CAN",
    "Leo": "LEO", "Virgo": "VIR", "Libra": "LIB", "Scorpio": "SCO",
    "Sagittarius": "SAG", "Capricorn": "CAP", "Aquarius": "AQU",
    "Pisces": "PIS",
}

# Planet-ruled sectors, per the classical cheatsheet. A benefic graha
# favours its sectors; a malefic graha pressures them. Strength is scaled
# by the dignity multiplier (retrograde x2, exalted x3, debilitated x0.5,
# combust x0.5).
PLANET_SECTORS = {
    "Jupiter": ["Finance & Banking", "Large Caps", "Gold (store of wealth)"],
    "Venus": ["Consumer-FMCG", "Cosmetics & Media", "Luxury & Silver"],
    "Mercury": ["IT & Software", "Banking & Management", "Commodities (grains, pulses)",
                "Telecom", "Cable & Media", "Communication Infrastructure"],
    "Mars": ["Defense & Aerospace", "Copper & Red Metals", "Gold (strong Mars)"],
    "Saturn": ["Metals & Mining", "Petroleum & Crude", "Industrial / Base-Metal Index"],
    "Sun": ["PSU", "PSU & Utilities", "PSU & Sovereign", "Government-linked", "Energy & Power", "Agriculture (state-run)"],
    "Moon": ["Shipping & Fisheries", "Water & Liquidity", "Intraday Momentum"],
    "Rahu": ["Speculative Spikes", "Gap Plays", "Momentum Amplifiers",
             "Telecom", "Cable & Media", "Digital Infrastructure"],
    "Ketu": ["Crash Risk / Corrections", "Exit Zones", "Reversal Risk"],
}


def sector_read(vedha_map, planets):
    """Derive sector-wise bullish/bearish projections from the vedha rays.

    Each active vedha ray pierces rashi cells on the chakra's inner ring as it
    travels; every graha that strikes a rashi adds its signed strength (benefic
    positive, malefic negative, scaled by dignity) to that rashi.  The net per
    rashi is classified into BULLISH / BEARISH / NEUTRAL and mapped onto the
    market sectors associated with that rashi.
    """
    rashi_hits: dict = {}
    for p in planets:
        for hit in vedha_map.get(p["name"], []):
            if hit["type"] != "rashi":
                continue
            rashi_hits.setdefault(hit["label"], []).append({
                "planet": p["name"],
                "symbol": p["symbol"],
                "nature": p["nature"],
                "ray": hit["ray"],
                "strength": p["signed_strength"],
            })

    out = []
    for rashi, sectors in RASHI_SECTORS.items():
        hits = rashi_hits.get(rashi, [])
        net = round(sum(h["strength"] for h in hits), 3)
        verdict, strength = sentiment_of(net)
        out.append({
            "rashi": rashi,
            "abbr": RASHI_SHORT[rashi],
            "sectors": sectors,
            "net": net,
            "verdict": verdict,
            "strength": strength,
            "hits": hits,
        })
    out.sort(key=lambda x: -x["net"])
    return out


def planet_sector_read(planets):
    """Derive a per-planet sector read from the rulership cheatsheet.

    Each graha rules a fixed set of sectors; a benefic graha is read as
    favouring them, a malefic graha as pressuring them. The read is scaled
    by the planet's signed strength (nature x dignity multiplier).
    """
    out = []
    for p in planets:
        if p["name"] not in PLANET_SECTORS:
            continue
        strength = p.get("signed_strength", 0.0)
        read = "FAVOR" if strength > 0 else ("AVOID" if strength < 0 else "NEUTRAL")
        out.append({
            "planet": p["name"],
            "symbol": p["symbol"],
            "nature": p["nature"],
            "sectors": PLANET_SECTORS[p["name"]],
            "strength": strength,
            "read": read,
            "dignity_reasons": p.get("dignity_reasons", []),
        })
    out.sort(key=lambda x: -x["strength"])
    return out
