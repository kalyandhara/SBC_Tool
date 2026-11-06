"""3D Impact Lineage Ontology Graph builder.

Builds a {nodes, edges} graph across 7 layers:
  Planet → Rasi → Nakshatra → Aspect → Theme → Sector → Stock (representative)

Research-grade only; no backtested edge.
Dasha layer deferred to Phase 2 (BSE birth time unconfirmed).
"""
from __future__ import annotations

import datetime as dt
import math
from typing import Any

from sbc.aspect_sets import CLASSICAL_ASPECTS, evaluate_aspect
from sbc.ontology_scoring import (
    PLANET_NATURE,
    PLANET_SECTORS,
    SECTOR_GROUPS,
    SENSITIVE_STARS,
    classify_regime,
    compute_liquidity_flow,
    compute_readings,
    compute_sector_scores,
)
from sbc.planets import positioned_planets

# ── rasi metadata ────────────────────────────────────────────────────────────

RASI_ELEMENT: dict[str, str] = {
    "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
    "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
    "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
    "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
}

RASI_MODALITY: dict[str, str] = {
    "Aries": "Cardinal", "Cancer": "Cardinal",
    "Libra": "Cardinal", "Capricorn": "Cardinal",
    "Taurus": "Fixed", "Leo": "Fixed",
    "Scorpio": "Fixed", "Aquarius": "Fixed",
    "Gemini": "Mutable", "Virgo": "Mutable",
    "Sagittarius": "Mutable", "Pisces": "Mutable",
}

# ── planet daily motion (degrees/day) for theme fallback ────────────────────

PLANET_MEAN_MOTION: dict[str, float] = {
    "Moon": 13.17, "Mercury": 1.38, "Venus": 1.20, "Sun": 0.99,
    "Mars": 0.52, "Jupiter": 0.083, "Saturn": 0.034,
    "Rahu": 0.053, "Ketu": 0.053,  # abs value; always retrograde
}

# ── theme mapping ────────────────────────────────────────────────────────────

# Key: frozenset({planet_a, planet_b}), aspect subset.
# "any" means matches regardless of aspect type.
_THEME_TABLE: list[tuple[frozenset[str], set[str], str]] = [
    (frozenset({"Jupiter", "Saturn"}), {"any"}, "Long Cycle / Structural Shift"),
    (frozenset({"Jupiter", "Venus"}), {"Trine", "Sextile"}, "Risk Appetite / Capital Flow"),
    (frozenset({"Jupiter", "Venus"}), {"Square", "Opposition"}, "Excess / Bubble Risk"),
    (frozenset({"Jupiter", "Mars"}), {"Trine", "Sextile"}, "Expansion / Capex"),
    (frozenset({"Saturn", "Mars"}), {"Conjunction", "Square"}, "Restriction / Contraction"),
    (frozenset({"Saturn", "Rahu"}), {"any"}, "Systemic Pressure"),
    (frozenset({"Rahu", "Ketu"}), {"Opposition"}, "Axis Disruption / Volatility"),
    (frozenset({"Mercury", "Sun"}), {"any"}, "Communication / Commerce"),
    (frozenset({"Moon", "Saturn"}), {"any"}, "Sentiment Compression"),
    (frozenset({"Venus", "Mars"}), {"Trine", "Sextile"}, "Consumer Momentum"),
]


def _lookup_theme(p_a: str, p_b: str, aspect_name: str) -> str:
    pair = frozenset({p_a, p_b})
    for entry_pair, aspects, label in _THEME_TABLE:
        if entry_pair == pair:
            if "any" in aspects or aspect_name in aspects:
                return label
    # Fallback: slower planet archetype via aspect
    slower = p_a if PLANET_MEAN_MOTION.get(p_a, 1.0) <= PLANET_MEAN_MOTION.get(p_b, 1.0) else p_b
    return f"{slower} / {aspect_name}"


# ── stock universe ────────────────────────────────────────────────────────────

STOCK_UNIVERSE: dict[str, list[str]] = {
    "Pharma":   ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "AUROPHARMA"],
    "Auto":     ["MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "EICHERMOT"],
    "Energy":   ["RELIANCE", "ONGC", "IOC", "BPCL", "HINDPETRO"],
    "Metal":    ["TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "COALINDIA"],
    "FMCG":     ["HINDUNILVR", "ITC", "NESTLE", "BRITANNIA", "DABUR"],
    "Infra":    ["LT", "ULTRACEMCO", "SHREECEM", "ACC", "GRASIM"],
    "Realty":   ["OBEROIRTY", "GODREJPROP", "DLF", "PHOENIXLTD", "BRIGADE"],
    "Bank":     ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "INDUSINDBK"],
    "Consumer": ["TITAN", "PAGEIND", "BERGEPAINT", "ASIANPAINT", "TRIDENT"],
    "Fin":      ["BAJFINANCE", "SHRIRAMFIN", "CHOLAFIN", "MUTHOOTFIN", "L&TFH"],
    "PSUBANK":  ["SBIN", "PNB", "BANKBARODA", "CANARBANK", "UNIONBANK"],
    "IT":       ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM"],
}

# Maps ontology sector names → STOCK_UNIVERSE keys
SECTOR_STOCK_MAP: dict[str, str] = {
    "Banking": "Bank", "NBFC": "Fin", "Wealth": "Fin",
    "Energy": "Energy", "Oil": "Energy", "Coal": "Energy",
    "IT": "IT", "Telecom": "IT", "Media": "IT", "Trading": "IT",
    "FMCG": "FMCG", "Luxury": "Consumer", "Retail": "Consumer", "Auto": "Auto",
    "Metals": "Metal", "Chemicals": "Metal",
    "Defence": "Infra", "Defence R&D": "Infra",
    "Infrastructure": "Infra", "Real Estate": "Realty",
    "PSU Banks": "PSUBANK", "PSU": "PSUBANK", "Government": "PSUBANK",
}

# ── sentiment helpers ─────────────────────────────────────────────────────────

SENTIMENT_COLOR: dict[str, str] = {
    "bullish": "#22c55e",
    "bearish": "#f87171",
    "volatile": "#fbbf24",
    "neutral": "#94a3b8",
}

ASPECT_SYMBOLS: dict[str, str] = {
    "Conjunction": "☌", "Sextile": "⚹", "Square": "□",
    "Trine": "△", "Opposition": "☍",
}


def _sentiment(planet_nature: str, aspect_polarity: int) -> str:
    if aspect_polarity > 0 and planet_nature == "benefic":
        return "bullish"
    if aspect_polarity == 0:
        return "volatile"
    return "bearish"


def _edge_color(sentiment: str) -> str:
    return SENTIMENT_COLOR.get(sentiment, SENTIMENT_COLOR["neutral"])


# ── 3D coordinate layout ──────────────────────────────────────────────────────

_LAYER_Z: dict[str, float] = {
    "planet": 0.0, "rasi": 1.5, "nakshatra": 3.0,
    "aspect": 4.5, "theme": 6.0, "sector": 7.5, "stock": 9.0,
}
_LAYER_RADIUS: dict[str, float] = {
    "planet": 2.0, "rasi": 2.5, "nakshatra": 3.0,
    "aspect": 2.5, "theme": 2.0, "sector": 2.5, "stock": 3.5,
}


def _xyz(node_type: str, index: int, total: int) -> tuple[float, float, float]:
    z = _LAYER_Z[node_type]
    r = _LAYER_RADIUS[node_type]
    if total == 0:
        return 0.0, 0.0, z
    angle = 2 * math.pi * index / total
    return round(r * math.cos(angle), 4), round(r * math.sin(angle), 4), z


# ── radial overview (Root → Planet → Sector group → Stock) ───────────────────

# Representative basket per sector group. "Other" has no basket of its own.
GROUP_STOCK_MAP: dict[str, str] = {
    "Financials": "Bank", "Energy": "Energy", "Technology": "IT",
    "Materials": "Metal", "Industrials": "Infra", "Consumer": "Consumer",
}


def _score_sentiment(score: float) -> str:
    return "bullish" if score > 0.5 else ("bearish" if score < -0.5 else "volatile")


def _build_radial(planets_raw: list[dict], sector_scores: list) -> dict[str, Any]:
    """Readable hub-and-spoke tree: about 50 nodes rather than the full lineage."""
    groups: dict[str, list] = {}
    for sc in sector_scores:
        groups.setdefault(SECTOR_GROUPS.get(sc.sector, "Other"), []).append(sc)

    nodes: list[dict] = [{
        "id": "root", "type": "root", "label": "Ontology Root",
        "x": 0.0, "y": 0.0, "z": 0.0, "sentiment": "neutral", "score": 0.0,
        "detail": {},
    }]
    edges: list[dict] = []

    def link(src: str, dst: str, sent: str) -> None:
        edges.append({"from": src, "to": dst, "label": "", "strength": 1.0,
                      "color": "#cbd5e1", "sentiment": sent})

    for i, p in enumerate(planets_raw):
        theta = 2 * math.pi * i / max(len(planets_raw), 1)
        score = p.get("signed_strength", 0.0)
        pid = f"planet_{p['name']}"
        sent = "bullish" if score > 0 else "bearish"
        nodes.append({
            "id": pid, "type": "planet",
            "label": f"{p['name']} ({p['nakshatra']})",
            "x": round(2.4 * math.cos(theta), 4),
            "y": round(2.4 * math.sin(theta), 4),
            "z": round(0.4 * math.sin(3 * theta), 4),
            "sentiment": sent, "score": score,
            "detail": {"rasi": p["sign"], "nature": p.get("nature", "")},
        })
        link("root", pid, sent)

    known = {p["name"] for p in planets_raw}
    names = sorted(groups)
    flow = compute_liquidity_flow(sector_scores)
    for i, group in enumerate(names):
        members = groups[group]
        avg = sum(m.score for m in members) / len(members)
        sent = _score_sentiment(avg)
        theta = 2 * math.pi * (i + 0.5) / len(names)
        gx, gy, gz = 7.0 * math.cos(theta), 7.0 * math.sin(theta), math.cos(2 * theta)
        gid = f"group_{group}"
        stocks = STOCK_UNIVERSE.get(GROUP_STOCK_MAP.get(group, ""), [])
        detail: dict[str, Any] = {
            "sectors": len(members),
            "strongest": max(members, key=lambda m: abs(m.score)).sector,
        }
        if not stocks:
            detail["unconfigured"] = True
        nodes.append({
            "id": gid, "type": "group",
            "label": f"{group} {flow.get(group, '')}".strip(),
            "x": round(gx, 4), "y": round(gy, 4), "z": round(gz, 4),
            "sentiment": sent, "score": round(avg, 2), "detail": detail,
        })
        # Attach to the planet carrying the most absolute weight in this group.
        weight: dict[str, float] = {}
        for m in members:
            for name in m.planets:
                if name in known:
                    weight[name] = weight.get(name, 0.0) + abs(m.score)
        parent = f"planet_{max(sorted(weight), key=weight.get)}" if weight else "root"
        link(parent, gid, sent)

        for j, sym in enumerate(stocks):
            spread = (j - (len(stocks) - 1) / 2) * 0.42
            sid = f"stock_{group}_{sym}"
            nodes.append({
                "id": sid, "type": "stock", "label": sym,
                "x": round(gx + 2.6 * math.cos(theta + spread), 4),
                "y": round(gy + 2.6 * math.sin(theta + spread), 4),
                "z": round(gz, 4),
                "sentiment": sent, "score": 0.0,
                "detail": {"group": group, "symbol": sym},
            })
            link(gid, sid, sent)

    regime, confidence = classify_regime(sector_scores)
    return {"regime": regime, "confidence": confidence, "nodes": nodes, "edges": edges}


# ── main builder ──────────────────────────────────────────────────────────────

def build_graph_data(
    date_str: str,
    time_str: str = "09:15",
    tz_name: str = "Asia/Kolkata",
) -> dict[str, Any]:
    """Build the full 7-layer ontology graph for a given date.

    Returns::

        {
            "date": str,
            "generated_at": str,
            "nodes": list[dict],
            "edges": list[dict],
            "layers": list[str],
            "meta": dict,
        }

    Research-grade only. No validated edge. Dasha layer deferred to Phase 2.
    """
    planets_raw, _ayanamsa, _sun, _moon, _tithi = positioned_planets(
        date_str, time_str, tz_name
    )
    # Keep only the 9 Vedic grahas that have sector mappings
    planets_raw = [p for p in planets_raw if p["name"] in PLANET_SECTORS]

    readings = compute_readings(date_str, time_str, tz_name)
    sector_scores = compute_sector_scores(readings)

    nodes: list[dict] = []
    edges: list[dict] = []
    node_ids: set[str] = set()

    def _add_node(node: dict) -> None:
        if node["id"] not in node_ids:
            node_ids.add(node["id"])
            nodes.append(node)

    # ── Layer 0: Planets ──────────────────────────────────────────────────
    for idx, p in enumerate(planets_raw):
        name = p["name"]
        sentiment = "bullish" if p.get("nature", "") == "benefic" else "bearish"
        x, y, z = _xyz("planet", idx, len(planets_raw))
        _add_node({
            "id": f"planet_{name}",
            "type": "planet",
            "label": name,
            "x": x, "y": y, "z": z,
            "sentiment": sentiment,
            "score": p.get("signed_strength", 0.0),
            "detail": {
                "longitude": p["longitude"],
                "rasi": p["sign"],
                "nakshatra": p["nakshatra"],
                "nature": p.get("nature", ""),
                "retrograde": p.get("retrograde", False),
            },
        })

    # ── Layer 1: Rasi ─────────────────────────────────────────────────────
    unique_rasis = list({p["sign"] for p in planets_raw})
    for idx, rasi in enumerate(unique_rasis):
        x, y, z = _xyz("rasi", idx, len(unique_rasis))
        _add_node({
            "id": f"rasi_{rasi.replace(' ', '_')}",
            "type": "rasi",
            "label": rasi,
            "x": x, "y": y, "z": z,
            "sentiment": "neutral",
            "score": 0.0,
            "detail": {
                "element": RASI_ELEMENT.get(rasi, "Unknown"),
                "modality": RASI_MODALITY.get(rasi, "Unknown"),
            },
        })
        # Edge: planet → rasi
        for p in planets_raw:
            if p["sign"] == rasi:
                nature = p.get("nature", "")
                sent = "bullish" if nature == "benefic" else "bearish"
                edges.append({
                    "from": f"planet_{p['name']}",
                    "to": f"rasi_{rasi.replace(' ', '_')}",
                    "label": "occupies",
                    "strength": 1.0,
                    "color": _edge_color(sent),
                    "sentiment": sent,
                })

    # ── Layer 2: Nakshatra ────────────────────────────────────────────────
    unique_naks = list({p["nakshatra"] for p in planets_raw})
    for idx, nak in enumerate(unique_naks):
        is_sensitive = nak in SENSITIVE_STARS
        x, y, z = _xyz("nakshatra", idx, len(unique_naks))
        _add_node({
            "id": f"nak_{nak.replace('.', '').replace(' ', '_')}",
            "type": "nakshatra",
            "label": nak,
            "x": x, "y": y, "z": z,
            "sentiment": "bearish" if is_sensitive else "neutral",
            "score": 2.0 if is_sensitive else 0.0,
            "detail": {"is_sensitive": is_sensitive},
        })
        for p in planets_raw:
            if p["nakshatra"] == nak:
                sent = "bearish" if is_sensitive else (
                    "bullish" if p.get("nature", "") == "benefic" else "bearish"
                )
                edges.append({
                    "from": f"planet_{p['name']}",
                    "to": f"nak_{nak.replace('.', '').replace(' ', '_')}",
                    "label": "in",
                    "strength": 2.0 if is_sensitive else 1.0,
                    "color": _edge_color(sent),
                    "sentiment": sent,
                })

    # ── Layer 3: Aspects ──────────────────────────────────────────────────
    seen_pairs: set[frozenset[str]] = set()
    aspect_nodes: list[dict] = []
    for i, pa in enumerate(planets_raw):
        for pb in planets_raw[i + 1:]:
            pair = frozenset({pa["name"], pb["name"]})
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            result = evaluate_aspect(pa["longitude"], pb["longitude"])
            if result is None:
                continue
            asp_id = f"asp_{pa['name']}_{pb['name']}"
            sym = ASPECT_SYMBOLS.get(result["aspect"], "~")
            polarity = result["polarity"]
            # Combined sentiment: use the more negative planet nature
            natures = {pa.get("nature", ""), pb.get("nature", "")}
            combined_nature = "malefic" if "malefic" in natures else "benefic"
            sent = _sentiment(combined_nature, polarity)
            aspect_nodes.append({
                "id": asp_id,
                "type": "aspect",
                "label": f"{pa['name']} {sym} {pb['name']}",
                "sentiment": sent,
                "score": result["energy"],
                "detail": {
                    "aspect_name": result["aspect"],
                    "orb_diff": round(result["orb_diff"], 3),
                    "energy": result["energy"],
                    "polarity": polarity,
                    "planet_a": pa["name"],
                    "planet_b": pb["name"],
                },
            })
            edges.append({
                "from": f"planet_{pa['name']}",
                "to": asp_id,
                "label": result["aspect"],
                "strength": round(result["energy"], 2),
                "color": _edge_color(sent),
                "sentiment": sent,
            })
            edges.append({
                "from": asp_id,
                "to": f"planet_{pb['name']}",
                "label": result["aspect"],
                "strength": round(result["energy"], 2),
                "color": _edge_color(sent),
                "sentiment": sent,
            })
    for idx, anode in enumerate(aspect_nodes):
        x, y, z = _xyz("aspect", idx, len(aspect_nodes))
        _add_node({**anode, "x": x, "y": y, "z": z})

    # ── Layer 4: Themes ───────────────────────────────────────────────────
    theme_nodes: list[dict] = []
    seen_themes: set[str] = set()
    for anode in aspect_nodes:
        pa = anode["detail"]["planet_a"]
        pb = anode["detail"]["planet_b"]
        asp_name = anode["detail"]["aspect_name"]
        theme_label = _lookup_theme(pa, pb, asp_name)
        theme_id = f"theme_{theme_label.replace('/', '').replace(' ', '_')[:30]}"
        if theme_id not in seen_themes:
            seen_themes.add(theme_id)
            theme_nodes.append({
                "id": theme_id,
                "type": "theme",
                "label": theme_label,
                "sentiment": anode["sentiment"],
                "score": anode["score"],
                "detail": {"source_aspect": anode["id"]},
            })
        edges.append({
            "from": anode["id"],
            "to": theme_id,
            "label": "implies",
            "strength": round(anode["score"], 2),
            "color": _edge_color(anode["sentiment"]),
            "sentiment": anode["sentiment"],
        })
    for idx, tnode in enumerate(theme_nodes):
        x, y, z = _xyz("theme", idx, len(theme_nodes))
        _add_node({**tnode, "x": x, "y": y, "z": z})

    # ── Layer 5: Sectors ──────────────────────────────────────────────────
    for idx, sc in enumerate(sector_scores):
        sector = sc.sector
        x, y, z = _xyz("sector", idx, len(sector_scores))
        abs_score = abs(sc.score)
        sent = "bullish" if sc.score > 0.5 else ("bearish" if sc.score < -0.5 else "volatile")
        _add_node({
            "id": f"sector_{sector.replace(' ', '_')}",
            "type": "sector",
            "label": sector,
            "x": x, "y": y, "z": z,
            "sentiment": sent,
            "score": round(sc.score, 2),
            "detail": {"planets": sc.planets, "breakdown": sc.breakdown},
        })
        # Edge: theme → sector (via PLANET_SECTORS mapping)
        for anode in aspect_nodes:
            pa, pb = anode["detail"]["planet_a"], anode["detail"]["planet_b"]
            pa_sectors = PLANET_SECTORS.get(pa, [])
            if sector in pa_sectors:
                theme_label = _lookup_theme(pa, pb, anode["detail"]["aspect_name"])
                theme_id = f"theme_{theme_label.replace('/', '').replace(' ', '_')[:30]}"
                strength = min(1.0, abs_score / 20.0)
                edges.append({
                    "from": theme_id,
                    "to": f"sector_{sector.replace(' ', '_')}",
                    "label": "drives",
                    "strength": round(strength, 2),
                    "color": _edge_color(sent),
                    "sentiment": sent,
                })
                break  # one theme → sector edge is sufficient

    # ── Layer 6: Stocks ───────────────────────────────────────────────────
    all_stocks: list[dict] = []
    for sc in sector_scores:
        sector = sc.sector
        stock_key = SECTOR_STOCK_MAP.get(sector)
        stocks = STOCK_UNIVERSE.get(stock_key, []) if stock_key else []
        # Mark unconfigured sectors
        if stock_key and stock_key not in STOCK_UNIVERSE:
            for n in nodes:
                if n["id"] == f"sector_{sector.replace(' ', '_')}":
                    n["detail"]["unconfigured"] = True
        if not stocks:
            # mark sector node as unconfigured (no stock list available)
            for n in nodes:
                if n["id"] == f"sector_{sector.replace(' ', '_')}":
                    n["detail"]["unconfigured"] = True
            continue
        sent = "bullish" if sc.score > 0.5 else ("bearish" if sc.score < -0.5 else "volatile")
        for sym in stocks:
            stock_id = f"stock_{sector.replace(' ', '_')}_{sym}"
            all_stocks.append({
                "id": stock_id,
                "type": "stock",
                "label": sym,
                "sentiment": sent,
                "score": 0.0,
                "detail": {"sector": sector, "symbol": sym},
            })
            edges.append({
                "from": f"sector_{sector.replace(' ', '_')}",
                "to": stock_id,
                "label": "contains",
                "strength": 1.0,
                "color": _edge_color(sent),
                "sentiment": sent,
            })
    for idx, snode in enumerate(all_stocks):
        x, y, z = _xyz("stock", idx, len(all_stocks))
        _add_node({**snode, "x": x, "y": y, "z": z})

    return {
        "date": date_str,
        "generated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "nodes": nodes,
        "edges": edges,
        "layers": ["planet", "rasi", "nakshatra", "aspect", "theme", "sector", "stock"],
        "radial": _build_radial(planets_raw, sector_scores),
        "meta": {
            "planet_count": sum(1 for n in nodes if n["type"] == "planet"),
            "aspect_count": sum(1 for n in nodes if n["type"] == "aspect"),
            "sector_count": sum(1 for n in nodes if n["type"] == "sector"),
            "stock_count": sum(1 for n in nodes if n["type"] == "stock"),
        },
    }
