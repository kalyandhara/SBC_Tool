"""Confluence analysis - combining multiple bullish/bearish signals to find alignment zones."""

from .prediction import sentiment_of


# The sector vocabulary lives in sbc.sector_keywords -- one canonical table for
# the whole tool. Re-exported here because callers (monthly_heatmap, the
# gap_analysis script) import these names from this module.
#
# The previous local table and its substring-containment fallback are gone:
# containment made "IT" swallow "Exit Zones", "Water & Liquidity" and
# "Commodities (grains, pulses)", and scattered bank signals across four
# separate canonical keys ("Nifty Bank", "Banking", "Financial Services",
# "Insurance") depending on dict iteration order.
from .sector_keywords import SECTOR_ALIASES, normalize_sectors  # noqa: F401


def score_to_signal(score):
    """Convert numeric score to signal: bullish/bearish/neutral."""
    if score > 0.5:
        return "BULLISH"
    if score < -0.5:
        return "BEARISH"
    return "NEUTRAL"


def signal_weight(signal, level):
    """Weight signal by alert level."""
    weights = {
        "CRITICAL": 3.0,
        "EXTREME": 2.5,
        "VERY HIGH": 2.0,
        "HIGH": 1.5,
        "MODERATE-HIGH": 1.25,
        "MODERATE": 1.0,
        "LOW": 0.5,
    }
    base = weights.get(level, 1.0)
    if signal == "BULLISH":
        return base
    if signal == "BEARISH":
        return -base
    return 0.0


def _point_to_sectors(point_name):
    """Map Pancha-Shakha sensitive points to market sectors."""
    mapping = {
        "Janma": ["Nifty 50", "Large Caps", "Banking", "Nifty Bank"],
        "Karma": ["Banking", "Nifty Bank", "Financial Services", "Finance & Banking"],
        "Sanghatika": ["Metals", "Energy", "Infrastructure", "PSU"],
        "Samudayika": ["FMCG", "Consumer", "IT", "Pharma"],
        "Adhana": ["Gold/MCX", "Real Estate", "PSU", "Large Caps"],
    }
    return mapping.get(point_name, ["All sectors"])


def analyze_vedha_confluence(analysis):
    """Extract confluence from vedha analysis on sensitive points."""
    per_point = analysis.get("per_point", {})
    point_scores = {}
    for point_name, hits in per_point.items():
        if not hits:
            continue
        net = sum(h["strength"] for h in hits)
        bullish = sum(h["strength"] for h in hits if h["nature"] == "benefic")
        bearish = sum(h["strength"] for h in hits if h["nature"] == "malefic")
        signal = score_to_signal(net)
        point_scores[point_name] = {
            "net": round(net, 3),
            "bullish": round(bullish, 3),
            "bearish": round(bearish, 3),
            "signal": signal,
            "hit_count": len(hits),
            "top_hits": sorted(hits, key=lambda x: abs(x["strength"]), reverse=True)[:3],
        }
    return point_scores


def analyze_sector_confluence(sector_read, planet_sector_read):
    """Combine rashi-sector and planet-sector reads."""
    sector_scores = {}

    for rashi_data in sector_read:
        for sector in rashi_data.get("sectors", []):
            canon = normalize_sectors([sector])[0]
            score = rashi_data.get("net", 0)
            sector_scores.setdefault(canon, {"rashi_hits": [], "planet_hits": [], "net": 0.0})
            sector_scores[canon]["rashi_hits"].append({
                "rashi": rashi_data["rashi"],
                "net": score,
                "verdict": rashi_data["verdict"],
                "strength": rashi_data["strength"],
            })

    for p_data in planet_sector_read:
        for sector in p_data.get("sectors", []):
            canon = normalize_sectors([sector])[0]
            strength = p_data.get("strength", 0)
            sector_scores.setdefault(canon, {"rashi_hits": [], "planet_hits": [], "net": 0.0})
            sector_scores[canon]["planet_hits"].append({
                "planet": p_data["planet"],
                "strength": strength,
                "read": p_data["read"],
                "nature": p_data["nature"],
            })

    for sector, data in sector_scores.items():
        rashi_net = sum(h["net"] for h in data["rashi_hits"])
        planet_net = sum(h["strength"] for h in data["planet_hits"])
        combined = round(rashi_net + planet_net, 3)
        data["net"] = combined
        data["signal"] = score_to_signal(combined)
        data["rashi_net"] = round(rashi_net, 3)
        data["planet_net"] = round(planet_net, 3)

    return sector_scores


def analyze_reversal_window_confluence(windows, active_only=True):
    """Score reversal windows by bias and level."""
    target = [w for w in windows if (w.get("active", True) if active_only else True)]
    sector_scores = {}
    total_bullish = 0.0
    total_bearish = 0.0

    for w in target:
        bias = w.get("bias", "").upper()
        level = w.get("level", "MODERATE")
        sectors = normalize_sectors(w.get("sectors", []))

        if "BULLISH" in bias and "BEARISH" not in bias:
            signal = "BULLISH"
        elif "BEARISH" in bias and "BULLISH" not in bias:
            signal = "BEARISH"
        elif "VOLATILE" in bias or "UNCLEAR" in bias:
            signal = "NEUTRAL"
        else:
            signal = "NEUTRAL"

        weight = signal_weight(signal, level)
        for sector in sectors:
            sector_scores.setdefault(sector, {"windows": [], "net": 0.0})
            sector_scores[sector]["windows"].append({
                "title": w.get("title", ""),
                "level": level,
                "bias": w.get("bias", ""),
                "weight": weight,
            })
            sector_scores[sector]["net"] += weight

        if signal == "BULLISH":
            total_bullish += abs(weight)
        elif signal == "BEARISH":
            total_bearish += abs(weight)

    for sector, data in sector_scores.items():
        data["signal"] = score_to_signal(data["net"])

    overall_signal = "BULLISH" if total_bullish > total_bearish else ("BEARISH" if total_bearish > total_bullish else "NEUTRAL")
    return {
        "sectors": sector_scores,
        "overall": {
            "bullish_weight": round(total_bullish, 2),
            "bearish_weight": round(total_bearish, 2),
            "signal": overall_signal,
        },
    }


def analyze_transit_confluence(transits):
    """Score major transits."""
    sector_scores = {}
    total_bullish = 0.0
    total_bearish = 0.0

    for t in transits:
        bias = t.get("bias", "").upper()
        sectors = normalize_sectors(t.get("sectors", []))
        retrograde = t.get("retrograde", False)

        if "BULLISH" in bias and "BEARISH" not in bias:
            signal = "BULLISH"
            weight = 1.5 if not retrograde else 1.0
        elif "BEARISH" in bias and "BULLISH" not in bias:
            signal = "BEARISH"
            weight = -1.5 if not retrograde else -1.0
        else:
            signal = "NEUTRAL"
            weight = 0.0

        for sector in sectors:
            sector_scores.setdefault(sector, {"transits": [], "net": 0.0})
            sector_scores[sector]["transits"].append({
                "planet": t.get("planet", ""),
                "sign": t.get("sign", ""),
                "bias": bias,
                "retrograde": retrograde,
                "weight": weight,
            })
            sector_scores[sector]["net"] += weight

        if signal == "BULLISH":
            total_bullish += abs(weight)
        elif signal == "BEARISH":
            total_bearish += abs(weight)

    for sector, data in sector_scores.items():
        data["signal"] = score_to_signal(data["net"])

    overall_signal = "BULLISH" if total_bullish > total_bearish else ("BEARISH" if total_bearish > total_bullish else "NEUTRAL")
    return {
        "sectors": sector_scores,
        "overall": {
            "bullish_weight": round(total_bullish, 2),
            "bearish_weight": round(total_bearish, 2),
            "signal": overall_signal,
        },
    }


def analyze_jupiter_confluence(jupiter_analysis):
    """Score Jupiter market heuristic."""
    if not jupiter_analysis or not jupiter_analysis.get("active"):
        return {"sectors": {}, "overall": {"bullish_weight": 0, "bearish_weight": 0, "signal": "NEUTRAL"}}

    bias = jupiter_analysis.get("bias", "").upper()
    level = jupiter_analysis.get("level", "MODERATE")
    sectors = normalize_sectors(jupiter_analysis.get("sectors", []))

    if "BEARISH" in bias:
        signal = "BEARISH"
        weight = -signal_weight("BEARISH", level)
    elif "BULLISH" in bias:
        signal = "BULLISH"
        weight = signal_weight("BULLISH", level)
    else:
        signal = "NEUTRAL"
        weight = 0.0

    sector_scores = {}
    for sector in sectors:
        sector_scores[sector] = {"jupiter": [jupiter_analysis], "net": weight, "signal": signal}

    return {
        "sectors": sector_scores,
        "overall": {
            "bullish_weight": max(0, weight),
            "bearish_weight": max(0, -weight),
            "signal": signal,
        },
    }


def analyze_venus_vedha_confluence(venus_vedha):
    """Score the SBC Venus-vedha event (Venus ray on Chitra/Libra).

    This is an SBC-layer signal, kept parallel to the planetary-transit layer.
    Venus is a soft benefic: supportive/stabilising, mild bullish weight that
    favours premium/luxury/FMCG sectors.  The "deceptive breakouts" caveat is
    noted but does not flip the sign.
    """
    if not venus_vedha or not venus_vedha.get("active"):
        return {"sectors": {}, "overall": {"bullish_weight": 0, "bearish_weight": 0, "signal": "NEUTRAL", "active": False}}

    # Mild supportive weight (soft benefic, but lower confidence than a
    # hard malefic/benefic transit because of the "beautiful/deceptive" risk).
    weight = 1.0
    sectors = normalize_sectors(
        venus_vedha.get("chitra_sectors", []) + venus_vedha.get("libra_sectors", []))

    sector_scores = {}
    for sector in sectors:
        sector_scores[sector] = {
            "venus_vedha": [venus_vedha],
            "net": weight,
            "signal": "BULLISH",
        }

    return {
        "sectors": sector_scores,
        "overall": {
            "bullish_weight": weight,
            "bearish_weight": 0.0,
            "signal": "BULLISH",
            "active": True,
        },
        "detail": venus_vedha_summary(venus_vedha),
    }


def venus_vedha_summary(venus_vedha):
    """Compact summary for reporting the Venus-vedha confluence component."""
    hits = []
    if venus_vedha.get("hits_chitra"):
        hits.append("Chitra")
    if venus_vedha.get("hits_libra"):
        hits.append("Libra")
    return {
        "targets": hits,
        "position": venus_vedha.get("venus_position", ""),
        "dignity": venus_vedha.get("dignity", ""),
        "combined": venus_vedha.get("combined", False),
    }


def analyze_lunar_confluence(lunar_phase):
    """Score lunar phase."""
    if not lunar_phase or not lunar_phase.get("active"):
        return {"sectors": {}, "overall": {"bullish_weight": 0, "bearish_weight": 0, "signal": "NEUTRAL"}}

    bias = lunar_phase.get("bias", "").upper()
    level = lunar_phase.get("level", "MODERATE")
    sectors = normalize_sectors(lunar_phase.get("sectors", []))

    if "BULLISH" in bias:
        signal = "BULLISH"
    elif "BEARISH" in bias or "REVERSAL" in bias or "EXTREME" in bias or "LOW VISIBILITY" in bias:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"

    weight = signal_weight(signal, level)
    sector_scores = {}
    for sector in sectors:
        sector_scores[sector] = {"lunar": [lunar_phase], "net": weight, "signal": signal}

    return {
        "sectors": sector_scores,
        "overall": {
            "bullish_weight": max(0, weight),
            "bearish_weight": max(0, -weight),
            "signal": signal,
        },
    }


def combine_confluence(*analyses):
    """Combine multiple confluence analyses into unified sector scores."""
    all_sectors = set()
    for name, analysis in analyses:
        all_sectors.update(analysis.get("sectors", {}).keys())

    combined = {}
    for sector in all_sectors:
        sector_data = {"sector": sector, "components": {}, "net": 0.0, "signals": []}
        for name, analysis in analyses:
            if sector in analysis.get("sectors", {}):
                sdata = analysis["sectors"][sector]
                sector_data["components"][name] = sdata
                sector_data["net"] += sdata.get("net", 0)
                sector_data["signals"].append(sdata.get("signal", "NEUTRAL"))
        sector_data["net"] = round(sector_data["net"], 3)
        sector_data["signal"] = score_to_signal(sector_data["net"])
        sector_data["agreement"] = _agreement_score(sector_data["signals"])
        combined[sector] = sector_data

    sorted_sectors = dict(sorted(combined.items(), key=lambda x: -abs(x[1]["net"])))
    return sorted_sectors


def _agreement_score(signals):
    """Calculate agreement among signals (1.0 = full agreement, 0 = split)."""
    if not signals:
        return 0.0
    bullish = signals.count("BULLISH")
    bearish = signals.count("BEARISH")
    neutral = signals.count("NEUTRAL")
    total = len(signals)
    if bullish == total or bearish == total:
        return 1.0
    if bullish > 0 and bearish > 0:
        return 0.0
    return 0.5


def build_confluence_report(
    analysis,
    sector_read,
    planet_sector_read,
    reversal_data,
    transits,
    jupiter_analysis,
    lunar_phase,
    venus_vedha=None,
):
    """Build complete confluence report for a date.

    SBC-layer signals (vedha, sector_read, planet_sector_read, venus_vedha)
    and transit-layer signals (reversal_windows, transits, jupiter, lunar)
    are each scored independently and only combined at the end.
    """
    vedha_confluence = analyze_vedha_confluence(analysis)
    sector_confluence = analyze_sector_confluence(sector_read, planet_sector_read)
    window_confluence = analyze_reversal_window_confluence(
        reversal_data.get("windows", []) + reversal_data.get("upcoming_windows", [])
    )
    transit_confluence = analyze_transit_confluence(transits)
    jupiter_confluence = analyze_jupiter_confluence(jupiter_analysis)
    lunar_confluence = analyze_lunar_confluence(lunar_phase)
    venus_vedha_confluence = analyze_venus_vedha_confluence(venus_vedha)

    # Convert vedha confluence (point-based) to sector-based for combination
    vedha_sector_map = {}
    for point, data in vedha_confluence.items():
        # Map points to sectors they influence
        point_sectors = _point_to_sectors(point)
        for sector in point_sectors:
            vedha_sector_map.setdefault(sector, {"net": 0.0, "signal": "NEUTRAL", "points": []})
            vedha_sector_map[sector]["net"] += data["net"]
            vedha_sector_map[sector]["points"].append(point)
    for sector, data in vedha_sector_map.items():
        data["signal"] = score_to_signal(data["net"])

    combined = combine_confluence(
        ("vedha", {"sectors": vedha_sector_map}),
        ("sector_read", {"sectors": sector_confluence}),
        ("reversal_windows", window_confluence),
        ("transits", transit_confluence),
        ("jupiter", jupiter_confluence),
        ("lunar", lunar_confluence),
        ("venus_vedha", venus_vedha_confluence),
    )

    overall_bullish = sum(a["overall"]["bullish_weight"] for a in [
        window_confluence, transit_confluence, jupiter_confluence, lunar_confluence,
        venus_vedha_confluence,
    ])
    overall_bearish = sum(a["overall"]["bearish_weight"] for a in [
        window_confluence, transit_confluence, jupiter_confluence, lunar_confluence,
        venus_vedha_confluence,
    ])

    vedha_net = analysis.get("net", 0)
    if vedha_net > 0:
        overall_bullish += abs(vedha_net)
    elif vedha_net < 0:
        overall_bearish += abs(vedha_net)

    overall_signal = "BULLISH" if overall_bullish > overall_bearish else ("BEARISH" if overall_bearish > overall_bullish else "NEUTRAL")

    top_bullish = [s for s, d in combined.items() if d["signal"] == "BULLISH" and d["agreement"] > 0.5]
    top_bearish = [s for s, d in combined.items() if d["signal"] == "BEARISH" and d["agreement"] > 0.5]
    conflicted = [s for s, d in combined.items() if d["agreement"] < 0.5 and d["signal"] != "NEUTRAL"]

    return {
        "vedha_points": vedha_confluence,
        "sector_confluence": combined,
        "overall": {
            "bullish_weight": round(overall_bullish, 2),
            "bearish_weight": round(overall_bearish, 2),
            "net": round(overall_bullish - overall_bearish, 2),
            "signal": overall_signal,
            "vedha_net": vedha_net,
        },
        "highlights": {
            "bullish_confluence_sectors": top_bullish[:5],
            "bearish_confluence_sectors": top_bearish[:5],
            "conflicted_sectors": conflicted[:5],
        },
        "components": {
            "reversal_windows": window_confluence,
            "transits": transit_confluence,
            "jupiter": jupiter_confluence,
            "lunar": lunar_confluence,
            "venus_vedha": venus_vedha_confluence,
        },
    }