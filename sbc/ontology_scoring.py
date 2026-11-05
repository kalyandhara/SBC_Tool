"""SBC market ontology scoring layer.

Builds on `sbc.ontology` (RDFS reasoner + certificate) and `sbc.planets`
(ephemeris) to produce the SBC Market Ontology Framework scoring:

    Planet Score + Nakshatra Score + Vedha Score + Sensitive Star Multiplier
    = Final Sector Score

Every score is explainable: each sector score carries a per-planet breakdown
and the rule chain that produced it, so the UI can render
"explainable reasoning paths" per the framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sbc import ontology as ont
from sbc.planets import positioned_planets

# ── framework constants (SBC_Market_Ontology_Framework.md) ──────────────────

# Planet -> sectors (Level 2: Planet-to-Sector Ontology)
PLANET_SECTORS = {
    "Mars": ["Energy", "Metals", "Defense", "Chemicals"],
    "Saturn": ["Infrastructure", "PSU", "Coal", "Oil"],
    "Jupiter": ["Banking", "NBFC", "Wealth", "Education"],
    "Mercury": ["IT", "Telecom", "Media", "Trading"],
    "Venus": ["FMCG", "Luxury", "Retail", "Auto"],
    "Moon": ["Consumer Sentiment", "Dairy", "Hospitality"],
    "Sun": ["Government", "Leadership", "PSU Banks"],
    "Rahu": ["Speculation", "EV", "AI", "New-age Technology"],
    "Ketu": ["Defence R&D", "Cyber Security", "Deep Tech"],
}

SECTOR_LIST = [
    "Banking", "IT", "Pharma", "Energy", "Capital Goods", "Auto", "PSU",
    "Infrastructure", "Insurance", "Metals", "Chemicals", "Defence",
    "Railways", "Real Estate", "Telecom", "Media", "FMCG",
    "Consumer Durables",
]

# Natural nature (mirrors sbc.planets.NATURAL_NATURE)
PLANET_NATURE = {
    "Sun": "malefic", "Moon": "benefic", "Mars": "malefic",
    "Mercury": "benefic", "Jupiter": "benefic", "Venus": "benefic",
    "Saturn": "malefic", "Rahu": "malefic", "Ketu": "malefic",
}

# Sensitive stars from the framework (Level 1 example lists Mula, Ashlesha,
# Jyeshta). The market's Janma nakshatra can extend this; we keep the
# canonical three plus whatever the anchored chart's Janma star is.
SENSITIVE_STARS = {"Mula", "Ashlesha", "Jyeshta"}

# Nakshatra -> lord (KP order, from data/ontologies/sbc_core.ttl)
NAKSHATRA_LORDS = {
    "Ashwini": "Ketu", "Bharani": "Venus", "Krittika": "Sun",
    "Rohini": "Moon", "Mrigashira": "Mars", "Ardra": "Rahu",
    "Punarvasu": "Jupiter", "Pushya": "Saturn", "Ashlesha": "Mercury",
    "Magha": "Ketu", "P.Phalguni": "Venus", "U.Phalguni": "Sun",
    "Hasta": "Moon", "Chitra": "Mars", "Swati": "Rahu",
    "Vishakha": "Jupiter", "Anuradha": "Saturn", "Jyeshtha": "Mercury",
    "Mula": "Ketu", "P.Ashadha": "Venus", "U.Ashadha": "Sun",
    "Shravana": "Moon", "Dhanishta": "Mars", "Shatabhisha": "Rahu",
    "P.Bhadrapada": "Jupiter", "U.Bhadrapada": "Saturn",
    "Revati": "Mercury",
}

# Sector -> sector group (for the Liquidity Flow Map)
SECTOR_GROUPS = {
    "Banking": "Financials", "NBFC": "Financials", "Wealth": "Financials",
    "Insurance": "Financials", "PSU": "Financials", "PSU Banks": "Financials",
    "Energy": "Energy", "Oil": "Energy", "Coal": "Energy",
    "IT": "Technology", "Telecom": "Technology", "Media": "Technology",
    "Trading": "Technology", "AI": "Technology", "New-age Technology": "Technology",
    "Metals": "Materials", "Chemicals": "Materials",
    "Defence": "Industrials", "Defence R&D": "Industrials",
    "Capital Goods": "Industrials", "Infrastructure": "Industrials",
    "Railways": "Industrials", "Real Estate": "Industrials",
    "Auto": "Consumer", "FMCG": "Consumer", "Luxury": "Consumer",
    "Retail": "Consumer", "Consumer Durables": "Consumer",
    "Consumer Sentiment": "Consumer", "Dairy": "Consumer",
    "Hospitality": "Consumer", "Cyber Security": "Technology",
    "Speculation": "Financials", "Education": "Consumer",
    "Government": "Industrials", "Leadership": "Industrials",
}

TRADING_ACTIONS = [
    "Bullish", "Bearish", "Neutral", "Strong Bullish", "Strong Bearish",
    "Accumulation", "Distribution", "Momentum Continuation", "Reversal Risk",
]


@dataclass
class PlanetReading:
    name: str
    nakshatra: str
    sign: str
    nature: str
    signed_strength: float
    dignity_multiplier: float
    retrograde: bool
    lord: str  # nakshatra lord
    lord_nature: str
    lord_strength: float
    is_sensitive: bool
    sectors: list[str]


@dataclass
class SectorScore:
    sector: str
    score: float = 0.0
    breakdown: list[dict] = field(default_factory=list)
    planets: list[str] = field(default_factory=list)


@dataclass
class OntologyReport:
    date: str
    time: str
    tz: str
    planets: list[PlanetReading]
    sector_scores: list[SectorScore]
    regime: str
    confidence: float
    liquidity_flow: dict[str, str]  # group -> "↑"/"↓"/"→"
    trading_actions: list[str]
    reasoning_paths: list[dict]
    sensitive_stars: list[str]
    certificate: dict


def _nature_score(nature: str) -> float:
    return 1.0 if nature == "benefic" else -1.0


def _planet_reading(p: dict) -> PlanetReading:
    name = p["name"]
    nak = p["nakshatra"]
    lord = NAKSHATRA_LORDS.get(nak, "Unknown")
    lord_nature = PLANET_NATURE.get(lord, "benefic")
    # Lord strength: use dignity_multiplier as a proxy if available; the
    # ephemeris only computes it for the 9 grahas, so fall back to nature.
    lord_strength = 1.0 if lord_nature == "benefic" else -1.0
    return PlanetReading(
        name=name,
        nakshatra=nak,
        sign=p["sign"],
        nature=p["nature"],
        signed_strength=p.get("signed_strength", _nature_score(p["nature"])),
        dignity_multiplier=p.get("dignity_multiplier", 1.0),
        retrograde=p.get("retrograde", False),
        lord=lord,
        lord_nature=lord_nature,
        lord_strength=lord_strength,
        is_sensitive=nak in SENSITIVE_STARS,
        sectors=PLANET_SECTORS.get(name, []),
    )


def _vedha_score(reading: PlanetReading, all_readings: list[PlanetReading]) -> float:
    """Vedha score: +2 benefic / -2 malefic, amplified near sensitive stars."""
    base = 2.0 if reading.nature == "benefic" else -2.0
    if reading.is_sensitive:
        base *= 1.5  # Sensitive Star Multiplier applies to vedha too
    return base


def compute_readings(date_str: str, time_str: str = "09:15",
                     tz_name: str = "Asia/Kolkata") -> list[PlanetReading]:
    """Extract planetary state for a date/time (Level 1: Event Extraction)."""
    planets, _ayanamsa, _sun, _moon, _tithi = positioned_planets(
        date_str, time_str, tz_name)
    return [_planet_reading(p) for p in planets if p["name"] in PLANET_SECTORS]


def compute_sector_scores(readings: list[PlanetReading]) -> list[SectorScore]:
    """Score every sector using the framework formula.

    Sector Score = Planet Score + Nakshatra Score + Vedha Score
                   (+ Sensitive Star Multiplier where applicable)
    """
    scores: dict[str, SectorScore] = {s: SectorScore(sector=s)
                                      for s in SECTOR_LIST}
    for r in readings:
        planet_score = r.signed_strength
        nak_score = r.lord_strength
        vedha = _vedha_score(r, readings)
        sensitive_mult = 1.5 if r.is_sensitive else 1.0
        total = (planet_score + nak_score + vedha) * sensitive_mult
        for sector in r.sectors:
            if sector not in scores:
                scores[sector] = SectorScore(sector=sector)
            sc = scores[sector]
            sc.score += total
            sc.planets.append(r.name)
            sc.breakdown.append({
                "planet": r.name,
                "nakshatra": r.nakshatra,
                "lord": r.lord,
                "planet_score": round(planet_score, 2),
                "nakshatra_score": round(nak_score, 2),
                "vedha_score": round(vedha, 2),
                "sensitive_multiplier": sensitive_mult,
                "contribution": round(total, 2),
                "nature": r.nature,
                "retrograde": r.retrograde,
            })
    out = list(scores.values())
    out.sort(key=lambda s: s.score, reverse=True)
    return out


def classify_regime(sector_scores: list[SectorScore]) -> tuple[str, float]:
    """Risk-On / Risk-Off classification with confidence.

    Aggregates sector scores: net bullish strength and breadth determine
    the regime; confidence = fraction of sectors aligned with the regime.
    """
    if not sector_scores:
        return "Neutral", 0.0
    pos = [s for s in sector_scores if s.score > 0.5]
    neg = [s for s in sector_scores if s.score < -0.5]
    neu = [s for s in sector_scores if -0.5 <= s.score <= 0.5]
    total = len(sector_scores)
    if len(pos) >= len(neg) and len(pos) > total / 2:
        regime = "Risk ON"
        confidence = len(pos) / total
    elif len(neg) > len(pos) and len(neg) > total / 2:
        regime = "Risk OFF"
        confidence = len(neg) / total
    else:
        regime = "Neutral"
        confidence = len(neu) / total
    # Strength modifier: strong regime when extremes exceed thresholds
    max_abs = max(abs(s.score) for s in sector_scores)
    if max_abs > 6:
        confidence = min(0.95, confidence + 0.15)
    elif max_abs > 3:
        confidence = min(0.90, confidence + 0.05)
    return regime, round(confidence, 2)


def compute_liquidity_flow(sector_scores: list[SectorScore]) -> dict[str, str]:
    """Liquidity Flow Map: sector group -> up/down/flat arrow."""
    group_scores: dict[str, list[float]] = {}
    for s in sector_scores:
        grp = SECTOR_GROUPS.get(sector_scores and s.sector, "Other")
        group_scores.setdefault(grp, []).append(s.score)
    flow: dict[str, str] = {}
    for grp, vals in group_scores.items():
        avg = sum(vals) / len(vals)
        if avg > 1.0:
            flow[grp] = "↑"
        elif avg < -1.0:
            flow[grp] = "↓"
        else:
            flow[grp] = "→"
    return flow


def trading_actions_for(regime: str, confidence: float) -> list[str]:
    """Map regime + confidence to the framework's trading actions."""
    if regime == "Risk ON" and confidence >= 0.7:
        return ["Strong Bullish", "Momentum Continuation", "Accumulation"]
    if regime == "Risk ON":
        return ["Bullish", "Accumulation"]
    if regime == "Risk OFF" and confidence >= 0.7:
        return ["Strong Bearish", "Distribution", "Reversal Risk"]
    if regime == "Risk OFF":
        return ["Bearish", "Distribution"]
    return ["Neutral", "Momentum Continuation"]


def build_report(date_str: str, time_str: str = "09:15",
                 tz_name: str = "Asia/Kolkata") -> OntologyReport:
    """Full ontology report: readings, scores, regime, flows, actions."""
    readings = compute_readings(date_str, time_str, tz_name)
    sector_scores = compute_sector_scores(readings)
    regime, confidence = classify_regime(sector_scores)
    liquidity_flow = compute_liquidity_flow(sector_scores)
    actions = trading_actions_for(regime, confidence)

    # Reasoning paths: planet -> nakshatra -> lord -> behaviour -> sector
    reasoning_paths = []
    for r in readings:
        for sector in r.sectors:
            reasoning_paths.append({
                "planet": r.name,
                "nakshatra": r.nakshatra,
                "lord": r.lord,
                "sector": sector,
                "chain": f"{r.name} → {r.nakshatra} → {r.lord} "
                         f"({r.lord_nature}) → {sector}",
                "contribution": round(
                    (r.signed_strength + r.lord_strength
                     + _vedha_score(r, readings))
                    * (1.5 if r.is_sensitive else 1.0), 2),
            })
    reasoning_paths.sort(key=lambda p: p["contribution"], reverse=True)

    sensitive = sorted({r.nakshatra for r in readings if r.is_sensitive})

    # Build a certificate from the ontology reasoner for auditability.
    # Assert each planet->nakshatra fact as an asserted triple, then reason.
    triples = []
    for r in readings:
        planet_iri = ont.iri(f"http://sbc.tool/ont/{r.name}")
        nak_iri = ont.iri(f"http://sbc.tool/ont{r.nakshatra.replace('.', '')}")
        triples.append(ont.Triple(planet_iri, ont.iri(
            "http://sbc.tool/ont#inNakshatra"), nak_iri))
    user_rules = ont.load_user_rules(ont.USER_RULES)
    reasoner = ont.Reasoner(triples, user_rules)
    reasoner.run()
    certificate = {
        "asserted": len(reasoner.asserted),
        "derivations": len(reasoner.derivations),
        "by_verdict": {},
        "paths": [d.text() for d in reasoner.derivations[:20]],
    }
    for d in reasoner.derivations:
        certificate["by_verdict"][d.verdict] = (
            certificate["by_verdict"].get(d.verdict, 0) + 1)

    return OntologyReport(
        date=date_str, time=time_str, tz=tz_name,
        planets=readings, sector_scores=sector_scores,
        regime=regime, confidence=confidence,
        liquidity_flow=liquidity_flow,
        trading_actions=actions,
        reasoning_paths=reasoning_paths,
        sensitive_stars=sensitive,
        certificate=certificate,
    )


def report_to_dict(report: OntologyReport) -> dict:
    return {
        "date": report.date,
        "time": report.time,
        "tz": report.tz,
        "planetary_summary": [
            {
                "planet": p.name,
                "nakshatra": p.nakshatra,
                "sign": p.sign,
                "nature": p.nature,
                "strength": round(p.signed_strength, 2),
                "retrograde": p.retrograde,
                "sectors": p.sectors,
                "sensitive": p.is_sensitive,
            }
            for p in report.planets
        ],
        "sector_scorecard": [
            {
                "sector": s.sector,
                "score": round(s.score, 2),
                "group": SECTOR_GROUPS.get(s.sector, "Other"),
                "planets": s.planets,
                "breakdown": s.breakdown,
            }
            for s in report.sector_scores
        ],
        "liquidity_flow": report.liquidity_flow,
        "regime": report.regime,
        "confidence": report.confidence,
        "trading_actions": report.trading_actions,
        "reasoning_paths": report.reasoning_paths,
        "sensitive_stars": report.sensitive_stars,
        "certificate": report.certificate,
    }
