"""
Bullion Vedha Matrix - SBC Vedha Types for Gold/Silver Markets
Based on classical Sarvatobhadra Chakra principles for precious metals.
"""

import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

import swisseph as swe

from sbc.nakshatra import tithi_of
from sbc.planets import all_planets_with_natures, positions
from sbc.prediction import compute_vedhas


class VedhaType(Enum):
    """Bullion-specific Vedha classifications."""
    KRITTIKA_PRIMARY = "krittika_primary"           # 1. Primary Gold Trigger
    ROHINI_LIQUIDITY = "rohini_liquidity"           # 2. Liquidity & Metals
    ADITYA_GURU = "aditya_guru"                     # 3. Sun-Jupiter Conjunction/Vedha
    SHUKI_CHANDRA = "shuki_chandra"                 # 4. Venus-Moon Silver Multiplier
    RETROGRADE_MALEFIC = "retrograde_malefic"       # 5. Vakra Kroora Vedha
    VIPREET_OBSTRUCTIVE = "vipreet_obstructive"     # 6. Mandi/Price Dump Trigger
    MERCURY_KETU_SUN_TRIANGLE = "mercury_ketu_sun_triangle"  # 7. Volatility Cluster


# Bullion-significant nakshatras
BULLION_NAKSHATRAS = {
    "Krittika": {"metal": "Gold", "element": "Fire", "rulership": "Agni", "primary": True},
    "Rohini": {"metal": "Silver", "element": "Earth/Water", "rulership": "Moon/Brahma", "primary": True},
    "Mrigashira": {"metal": "Silver", "element": "Earth", "rulership": "Mars"},
    "Ardra": {"metal": "Gold", "element": "Air", "rulership": "Rahu"},
    "Punarvasu": {"metal": "Gold", "element": "Water", "rulership": "Jupiter"},
    "Pushya": {"metal": "Both", "element": "Water", "rulership": "Saturn"},
    "Ashlesha": {"metal": "Gold", "element": "Water", "rulership": "Mercury"},
    "Magha": {"metal": "Gold", "element": "Fire", "rulership": "Ketu"},
    "P.Phalguni": {"metal": "Silver", "element": "Fire", "rulership": "Venus"},
    "U.Phalguni": {"metal": "Silver", "element": "Fire", "rulership": "Sun"},
    "Hasta": {"metal": "Silver", "element": "Fire", "rulership": "Moon"},
    "Chitra": {"metal": "Gold", "element": "Fire", "rulership": "Mars"},
    "Swati": {"metal": "Silver", "element": "Air", "rulership": "Rahu"},
    "Vishakha": {"metal": "Gold", "element": "Fire", "rulership": "Jupiter"},
    "Anuradha": {"metal": "Silver", "element": "Water", "rulership": "Saturn"},
    "Jyeshtha": {"metal": "Gold", "element": "Air", "rulership": "Mercury"},
    "Mula": {"metal": "Gold", "element": "Fire", "rulership": "Ketu"},
    "P.Ashadha": {"metal": "Gold", "element": "Fire", "rulership": "Venus"},
    "U.Ashadha": {"metal": "Gold", "element": "Fire", "rulership": "Sun"},
    "Shravana": {"metal": "Silver", "element": "Earth", "rulership": "Moon"},
    "Dhanishta": {"metal": "Both", "element": "Earth", "rulership": "Mars"},
    "Shatabhisha": {"metal": "Silver", "element": "Air", "rulership": "Rahu"},
    "P.Bhadrapada": {"metal": "Gold", "element": "Fire", "rulership": "Jupiter"},
    "U.Bhadrapada": {"metal": "Silver", "element": "Water", "rulership": "Saturn"},
    "Revati": {"metal": "Silver", "element": "Water", "rulership": "Mercury"},
}


# Malefic/benefic classification for bullion
PLANET_BULLION_NATURE = {
    "Sun": "malefic",      # Authoritative, government gold
    "Moon": "variable",    # Liquidity, public sentiment
    "Mars": "malefic",     # Fire, volatility, mining
    "Mercury": "variable", # Trade, volatility
    "Jupiter": "benefic",  # Expansion, wealth, accumulation
    "Venus": "benefic",    # Silver, luxury, liquidity
    "Saturn": "malefic",   # Restriction, delays, mining costs
    "Rahu": "malefic",     # Speculation, manipulation
    "Ketu": "malefic",     # Detachment, sudden moves
}


@dataclass
class BullionVedhaSignal:
    """A detected bullion vedha signal."""
    vedha_type: VedhaType
    title: str
    mechanism: str
    market_impact: str
    intensity: str  # EXTREME, HIGH, MODERATE, LOW
    affected_metal: str  # Gold, Silver, Both
    triggering_planets: list[str]
    nakshatras_involved: list[str]
    duration_estimate: str
    confidence: float  # 0-1
    timestamp: str
    details: dict[str, Any]


def _julian_at_noon(date: datetime.date) -> float:
    """Get Julian day at noon IST."""
    local = datetime.datetime.combine(date, datetime.time(12, 0), tzinfo=ZoneInfo('Asia/Kolkata'))
    utc = local.astimezone(datetime.UTC)
    return swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)


def _get_planets(date: datetime.date):
    """Get planetary positions with natures for a date."""
    jul = _julian_at_noon(date)
    planets, ayanamsa = positions(jul)
    sun = next(p for p in planets if p["name"] == "Sun")
    moon = next(p for p in planets if p["name"] == "Moon")
    tithi = tithi_of(sun["longitude"], moon["longitude"])
    planets = all_planets_with_natures(planets, tithi, sun["longitude"])
    return planets, tithi, ayanamsa


def _get_vedha_map(planets):
    """Compute vedha map for current planetary positions."""
    vedha_map, _ = compute_vedhas(planets, school="classical")
    return vedha_map


def _angle(lon1: float, lon2: float) -> float:
    """Shortest angular distance between two longitudes."""
    return abs((lon1 - lon2 + 180) % 360 - 180)


def _is_retrograde(planet) -> bool:
    return planet.get("retrograde", False)


def _is_in_fire_sign(planet) -> bool:
    return planet["sign"] in ("Aries", "Leo", "Sagittarius")


def _is_in_same_nakshatra_line(p1, p2) -> bool:
    """Check if two planets are on same nakshatra line (same nakshatra or trine nakshatras)."""
    n1 = p1["nakshatra"]
    n2 = p2["nakshatra"]
    # Only the same nakshatra counts for now; a trine (5/9 apart in the 27
    # nakshatra scheme) would need full nakshatra trine logic.
    return n1 == n2


# ============================================================
# 1. KRITTIKA VEDHA - PRIMARY GOLD TRIGGER
# ============================================================
def detect_krittika_vedha(planets, vedha_map) -> list[BullionVedhaSignal]:
    """
    Krittika Vedha: Malefic (Sun/Mars/Saturn) in Krittika Nakshatra
    Transits on Krittika cast direct diagonal (Sammukha/Vipreet) Vedha across the grid.
    Sharp Bullish Surge (Teji): Krittika directly rules Gold, gems, precious metals.
    Malefic transits create severe structural supply/price shocks lasting up to 8 months.
    """
    signals = []
    malefics = ["Sun", "Mars", "Saturn", "Rahu", "Ketu"]

    for p in planets:
        if p["name"] in malefics and p["nakshatra"] == "Krittika":
            # Check if this planet casts vedha on sensitive points
            vedha_hits = vedha_map.get(p["name"], [])
            hits_on_krittika_line = [h for h in vedha_hits if h.get("label") == "Krittika"]

            intensity = "EXTREME" if _is_retrograde(p) else "HIGH"
            if p["name"] in ("Mars", "Saturn") and _is_retrograde(p):
                intensity = "EXTREME"

            signals.append(BullionVedhaSignal(
                vedha_type=VedhaType.KRITTIKA_PRIMARY,
                title=f"Krittika Vedha: {p['name']} in Krittika",
                mechanism=f"{p['name']} transiting Krittika nakshatra casts Sammukha/Vipreet diagonal vedha across SBC grid",
                market_impact="Sharp Bullish Surge (Teji): Krittika directly rules Gold, gems, and precious metals. Malefic transits create severe structural supply/price shocks lasting up to 8 months.",
                intensity=intensity,
                affected_metal="Gold",
                triggering_planets=[p["name"]],
                nakshatras_involved=["Krittika"],
                duration_estimate="Up to 8 months structural effect",
                confidence=0.9 if _is_retrograde(p) else 0.75,
                timestamp=datetime.datetime.now().isoformat(),
                details={
                    "planet": p["name"],
                    "nakshatra": "Krittika",
                    "sign": p["sign"],
                    "degree": p["degree"],
                    "retrograde": p.get("retrograde", False),
                    "vedha_hits": len(hits_on_krittika_line),
                }
            ))
    return signals


# ============================================================
# 2. ROHINI VEDHA - LIQUIDITY & METALS
# ============================================================
def detect_rohini_vedha(planets, vedha_map) -> list[BullionVedhaSignal]:
    """
    Rohini Vedha: Kroora Graha (Mars/Saturn/Rahu) in Rohini Nakshatra
    Casts Parshwa (Side) and Sammukha Vedha on key liquid metal axis.
    High Volatility / Speculative Rally: Rohini rules liquids and elemental metals.
    Malefic Vedha sparks sharp 7-14 day momentum spikes, especially in Silver.
    """
    signals = []
    kroora = ["Mars", "Saturn", "Rahu"]

    for p in planets:
        if p["name"] in kroora and p["nakshatra"] == "Rohini":

            intensity = "HIGH"
            if _is_retrograde(p):
                intensity = "EXTREME"

            signals.append(BullionVedhaSignal(
                vedha_type=VedhaType.ROHINI_LIQUIDITY,
                title=f"Rohini Vedha: {p['name']} in Rohini",
                mechanism=f"{p['name']} in Rohini casts Parshwa (side) and Sammukha vedha on liquid metal axis",
                market_impact="High Volatility / Speculative Rally: Rohini rules liquids and elemental metals. Malefic Vedha sparks sharp 7-14 day momentum spikes, especially in Silver.",
                intensity=intensity,
                affected_metal="Silver",
                triggering_planets=[p["name"]],
                nakshatras_involved=["Rohini"],
                duration_estimate="7-14 days acute, residual up to 30 days",
                confidence=0.85 if _is_retrograde(p) else 0.7,
                timestamp=datetime.datetime.now().isoformat(),
                details={
                    "planet": p["name"],
                    "nakshatra": "Rohini",
                    "sign": p["sign"],
                    "degree": p["degree"],
                    "retrograde": p.get("retrograde", False),
                }
            ))
    return signals


# ============================================================
# 3. ADITYA-GURU VEDHA - SUN-JUPITER CONJUNCTION/VEDHA
# ============================================================
def detect_aditya_guru_vedha(planets, vedha_map) -> list[BullionVedhaSignal]:
    """
    Aditya-Guru Vedha: Transiting Sun casting Subha Vedha on Jupiter (or same Nakshatra line)
    Direct Sammukha ray between the Sun line and Jupiter line.
    Macro Gold Accumulation: Triggers central bank buying and institutional store-of-value flows into Gold ETF and spot physical markets.
    """
    signals = []

    sun = next((p for p in planets if p["name"] == "Sun"), None)
    jupiter = next((p for p in planets if p["name"] == "Jupiter"), None)

    if not sun or not jupiter:
        return signals

    # Check conjunction (same nakshatra or very close)
    same_nakshatra = sun["nakshatra"] == jupiter["nakshatra"]
    close_conjunction = _angle(sun["longitude"], jupiter["longitude"]) < 8

    # Check if Sun casts vedha on Jupiter's nakshatra
    sun_vedha_hits = vedha_map.get("Sun", [])
    jupiter_vedha_hits = vedha_map.get("Jupiter", [])

    sun_hits_jupiter_nakshatra = any(h.get("label") == jupiter["nakshatra"] for h in sun_vedha_hits)
    jupiter_hits_sun_nakshatra = any(h.get("label") == sun["nakshatra"] for h in jupiter_vedha_hits)

    if same_nakshatra or close_conjunction or sun_hits_jupiter_nakshatra or jupiter_hits_sun_nakshatra:
        intensity = "EXTREME" if same_nakshatra else "HIGH"

        signals.append(BullionVedhaSignal(
            vedha_type=VedhaType.ADITYA_GURU,
            title="Aditya-Guru Vedha: Sun-Jupiter Alignment",
            mechanism="Direct Sammukha ray between Sun line and Jupiter line (conjunction or mutual vedha)",
            market_impact="Macro Gold Accumulation: Triggers central bank buying and institutional store-of-value flows into Gold ETF and spot physical markets.",
            intensity=intensity,
            affected_metal="Gold",
            triggering_planets=["Sun", "Jupiter"],
            nakshatras_involved=[sun["nakshatra"], jupiter["nakshatra"]],
            duration_estimate="30-90 days accumulation phase",
            confidence=0.9 if same_nakshatra else 0.75,
            timestamp=datetime.datetime.now().isoformat(),
            details={
                "sun_nakshatra": sun["nakshatra"],
                "jupiter_nakshatra": jupiter["nakshatra"],
                "separation_deg": round(_angle(sun["longitude"], jupiter["longitude"]), 2),
                "same_nakshatra": same_nakshatra,
                "mutual_vedha": sun_hits_jupiter_nakshatra or jupiter_hits_sun_nakshatra,
            }
        ))
    return signals


# ============================================================
# 4. SHUKI-CHANDRA VEDHA - VENUS-MOON SILVER MULTIPLIER
# ============================================================
def detect_shuki_chandra_vedha(planets, vedha_map) -> list[BullionVedhaSignal]:
    """
    Shuki-Chandra Vedha: Transiting Venus in high-strength Pada casting Vedha on Moon Nakshatra
    Direct horizontal or diagonal SBC intersection with Moon/Liquid Nakshatra.
    Silver Outperformance: Silver historically outperforms Gold when Venus creates a benefic Subha Vedha with Moon/Rohini/Shravana.
    """
    signals = []

    venus = next((p for p in planets if p["name"] == "Venus"), None)
    moon = next((p for p in planets if p["name"] == "Moon"), None)

    if not venus or not moon:
        return signals

    # Check if Venus is benefic (well-placed, not debilitated/combust)
    venus_benefic = venus.get("nature") == "benefic"

    # Check Venus-Moon vedha connection
    venus_vedha_hits = vedha_map.get("Venus", [])
    moon_nakshatra = moon["nakshatra"]

    venus_hits_moon_nakshatra = any(h.get("label") == moon_nakshatra for h in venus_vedha_hits)

    # Liquid nakshatras for Moon
    liquid_nakshatras = {"Rohini", "Shravana", "Pushya", "Revati", "Hasta"}
    moon_in_liquid = moon_nakshatra in liquid_nakshatras

    if venus_benefic and (venus_hits_moon_nakshatra or moon_in_liquid):
        # Check Venus strength (exalted, own sign, retrograde)
        venus_strong = venus["sign"] in ("Taurus", "Libra", "Pisces") or _is_retrograde(venus)

        intensity = "HIGH" if venus_strong else "MODERATE"
        if _is_retrograde(venus):
            intensity = "EXTREME"

        signals.append(BullionVedhaSignal(
            vedha_type=VedhaType.SHUKI_CHANDRA,
            title=f"Shuki-Chandra Vedha: Venus {venus['nakshatra']} -> Moon {moon_nakshatra}",
            mechanism=f"Venus in {venus['nakshatra']} (Pada {venus['pada']}) casts benefic Subha Vedha on Moon in {moon_nakshatra} via direct horizontal/diagonal SBC intersection",
            market_impact="Silver Outperformance: Silver historically outperforms Gold when Venus creates a benefic Subha Vedha with Moon/Rohini/Shravana. Expect Silver beta > Gold.",
            intensity=intensity,
            affected_metal="Silver",
            triggering_planets=["Venus", "Moon"],
            nakshatras_involved=[venus["nakshatra"], moon_nakshatra],
            duration_estimate="While Venus transits current nakshatra (~13 days) + Moon transit window",
            confidence=0.8 if venus_strong else 0.6,
            timestamp=datetime.datetime.now().isoformat(),
            details={
                "venus_nakshatra": venus["nakshatra"],
                "venus_pada": venus["pada"],
                "venus_sign": venus["sign"],
                "venus_benefic": venus_benefic,
                "venus_strong": venus_strong,
                "moon_nakshatra": moon_nakshatra,
                "moon_in_liquid_nakshatra": moon_in_liquid,
                "direct_vedha": venus_hits_moon_nakshatra,
            }
        ))
    return signals


# ============================================================
# 5. RETROGRADE MALEFIC VEDHA (VAKRA KROORA VEDHA)
# ============================================================
def detect_retrograde_malefic_vedha(planets, vedha_map) -> list[BullionVedhaSignal]:
    """
    Retrograde Malefic Vedha: Retrograde Mars, Saturn, or Ketu entering Fire Signs (Aries/Leo/Sagittarius)
    Retrograde motion increases Vedha intensity by 3x.
    Panic Buying / Safe-Haven Spikes: Triggers flight-to-safety capital flows into Gold during geopolitical or currency uncertainty.
    """
    signals = []
    retrograde_malefics = ["Mars", "Saturn", "Ketu", "Rahu"]

    for p in planets:
        if p["name"] in retrograde_malefics and _is_retrograde(p) and _is_in_fire_sign(p):
            # Check if this retrograde malefic casts vedha on bullion nakshatras
            vedha_hits = vedha_map.get(p["name"], [])
            bullion_hits = [h for h in vedha_hits if h.get("label") in BULLION_NAKSHATRAS]

            # Fire sign retrograde = maximum intensity
            intensity = "EXTREME"

            signals.append(BullionVedhaSignal(
                vedha_type=VedhaType.RETROGRADE_MALEFIC,
                title=f"Vakra Kroora Vedha: Retrograde {p['name']} in {p['sign']}",
                mechanism=f"Retrograde {p['name']} in fire sign {p['sign']} ({p['nakshatra']}) increases Vedha intensity 3x. Casts aggressive Sammukha/Vipreet rays on bullion nakshatras.",
                market_impact="Panic Buying / Safe-Haven Spikes: Triggers flight-to-safety capital flows into Gold during geopolitical or currency uncertainty. Sharp intraday gaps up in Gold.",
                intensity=intensity,
                affected_metal="Gold",
                triggering_planets=[p["name"]],
                nakshatras_involved=[p["nakshatra"]] + [h["label"] for h in bullion_hits[:3]],
                duration_estimate="Duration of retrograde period (~60-120 days for Mars, ~140 days for Saturn, ~18 months for Ketu/Rahu)",
                confidence=0.95,
                timestamp=datetime.datetime.now().isoformat(),
                details={
                    "planet": p["name"],
                    "sign": p["sign"],
                    "nakshatra": p["nakshatra"],
                    "degree": p["degree"],
                    "retrograde": True,
                    "speed": p.get("speed", 0),
                    "bullion_nakshatra_hits": len(bullion_hits),
                    "target_nakshatras": [h["label"] for h in bullion_hits[:5]],
                }
            ))
    return signals


# ============================================================
# 6. VIPREET OBSTRUCTIVE VEDHA (MANDI / PRICE DUMP TRIGGER)
# ============================================================
def detect_vipreet_obstructive_vedha(planets, vedha_map) -> list[BullionVedhaSignal]:
    """
    Vipreet Obstructive Vedha: Benefic (Venus/Jupiter/Mercury) casting Vedha without counter-malefic pressure
    Softening Subha Vedha over Krittika or Rohini axis.
    Cooling / Correction (Mandi): Induces profit booking and price compression across bullion counters.
    """
    signals = []
    benefics = ["Venus", "Jupiter", "Mercury"]

    for p in planets:
        if p["name"] in benefics:
            # Check if benefic is casting vedha on Krittika or Rohini
            vedha_hits = vedha_map.get(p["name"], [])
            krittika_hit = any(h.get("label") == "Krittika" for h in vedha_hits)
            rohini_hit = any(h.get("label") == "Rohini" for h in vedha_hits)

            if krittika_hit or rohini_hit:
                # Check for counter-malefic pressure on same nakshatra
                counter_malefic = False
                for mp in planets:
                    if mp["name"] in ("Sun", "Mars", "Saturn", "Rahu", "Ketu"):
                        m_vedha = vedha_map.get(mp["name"], [])
                        if krittika_hit and any(h.get("label") == "Krittika" for h in m_vedha):
                            counter_malefic = True
                        if rohini_hit and any(h.get("label") == "Rohini" for h in m_vedha):
                            counter_malefic = True

                if not counter_malefic:
                    intensity = "HIGH" if p["name"] == "Jupiter" else "MODERATE"

                    signals.append(BullionVedhaSignal(
                        vedha_type=VedhaType.VIPREET_OBSTRUCTIVE,
                        title=f"Vipreet Obstructive Vedha: {p['name']} softening {'Krittika' if krittika_hit else 'Rohini'} axis",
                        mechanism=f"Benefic {p['name']} in {p['nakshatra']} casts unopposed Subha Vedha on {'Krittika (Gold axis)' if krittika_hit else 'Rohini (Silver axis)'}, softening malefic pressure",
                        market_impact="Cooling / Correction (Mandi): Induces profit booking and price compression across bullion counters. Soft top formation, distribution phase.",
                        intensity=intensity,
                        affected_metal="Gold" if krittika_hit else "Silver",
                        triggering_planets=[p["name"]],
                        nakshatras_involved=["Krittika"] if krittika_hit else ["Rohini"],
                        duration_estimate="5-15 days while benefic transits nakshatra",
                        confidence=0.75,
                        timestamp=datetime.datetime.now().isoformat(),
                        details={
                            "planet": p["name"],
                            "nakshatra": p["nakshatra"],
                            "target_axis": "Krittika" if krittika_hit else "Rohini",
                            "counter_malefic_absent": True,
                            "benefic_nature": p.get("nature", "benefic"),
                        }
                    ))
    return signals


# ============================================================
# 7. MERCURY-KETU-SUN TRIANGLE IN LEO (VOLATILITY CLUSTER)
# ============================================================
def detect_mercury_ketu_sun_triangle(planets, vedha_map) -> list[BullionVedhaSignal]:
    """
    Mercury-Ketu-Sun Triangle in Leo: All three in Leo/Magha nakshatra
    Creates a volatile cluster affecting Gold (Sun/Ketu in Magha) and trading/communication (Mercury).
    High Volatility / Sudden Moves / Trend Changes: Combines authority (Sun), detachment (Ketu),
    and trading intellect (Mercury) in the same nakshatra. Triggers sharp intraday reversals in bullion.
    """
    signals = []

    sun = next((p for p in planets if p["name"] == "Sun"), None)
    mercury = next((p for p in planets if p["name"] == "Mercury"), None)
    ketu = next((p for p in planets if p["name"] == "Ketu"), None)

    if not all([sun, mercury, ketu]):
        return signals

    # Check if all three in Leo
    if sun["sign"] == "Leo" and mercury["sign"] == "Leo" and ketu["sign"] == "Leo":
        # Check if in same or adjacent nakshatras (Magha)
        sun_mer = abs((sun["longitude"] - mercury["longitude"] + 180) % 360 - 180)
        sun_ketu = abs((sun["longitude"] - ketu["longitude"] + 180) % 360 - 180)
        mer_ketu = abs((mercury["longitude"] - ketu["longitude"] + 180) % 360 - 180)

        # All in Magha nakshatra = tight triangle
        in_magha = sun["nakshatra"] == "Magha" and mercury["nakshatra"] == "Magha" and ketu["nakshatra"] == "Magha"

        if in_magha or max(sun_mer, sun_ketu, mer_ketu) < 10:
            intensity = "EXTREME" if in_magha else "HIGH"

            signals.append(BullionVedhaSignal(
                vedha_type=VedhaType.MERCURY_KETU_SUN_TRIANGLE,
                title="Mercury-Ketu-Sun Triangle in Leo (Magha)",
                mechanism=f"Sun ({sun['degree']:.1f}°), Mercury ({mercury['degree']:.1f}°), Ketu ({ketu['degree']:.1f}°) all in Leo/Magha. Sun-Mercury {sun_mer:.1f}°, Sun-Ketu {sun_ketu:.1f}°, Mercury-Ketu {mer_ketu:.1f}°. Combines authority, detachment, and trading intellect.",
                market_impact="High Volatility / Sudden Moves / Trend Changes: Combines authority (Sun), detachment (Ketu), and trading intellect (Mercury) in Magha. Triggers sharp intraday reversals in Gold/Silver. Watch for policy announcements, central bank news, algorithm-driven spikes.",
                intensity=intensity,
                affected_metal="Both",
                triggering_planets=["Sun", "Mercury", "Ketu"],
                nakshatras_involved=["Magha"],
                duration_estimate="While cluster persists in Leo (~3-4 weeks until Mercury exits Leo)",
                confidence=0.9,
                timestamp=datetime.datetime.now().isoformat(),
                details={
                    "sun_degree": sun["degree"],
                    "mercury_degree": mercury["degree"],
                    "ketu_degree": ketu["degree"],
                    "sun_mercury_sep": round(sun_mer, 1),
                    "sun_ketu_sep": round(sun_ketu, 1),
                    "mercury_ketu_sep": round(mer_ketu, 1),
                    "in_magha": in_magha,
                }
            ))
    return signals


# ============================================================
# MASTER DETECTION FUNCTION
# ============================================================
def scan_bullion_vedha_matrix(date: datetime.date = None) -> dict[str, Any]:
    """
    Scan all 6 Bullion Vedha Matrix signals for a given date.

    Returns comprehensive bullion vedha analysis.
    """
    if date is None:
        date = datetime.date.today()

    planets, tithi, ayanamsa = _get_planets(date)
    vedha_map = _get_vedha_map(planets)

    # Run all detectors
    all_signals = []
    all_signals.extend(detect_krittika_vedha(planets, vedha_map))
    all_signals.extend(detect_rohini_vedha(planets, vedha_map))
    all_signals.extend(detect_aditya_guru_vedha(planets, vedha_map))
    all_signals.extend(detect_shuki_chandra_vedha(planets, vedha_map))
    all_signals.extend(detect_retrograde_malefic_vedha(planets, vedha_map))
    all_signals.extend(detect_vipreet_obstructive_vedha(planets, vedha_map))
    all_signals.extend(detect_mercury_ketu_sun_triangle(planets, vedha_map))

    # Sort by intensity
    intensity_order = {"EXTREME": 4, "HIGH": 3, "MODERATE": 2, "LOW": 1}
    all_signals.sort(key=lambda s: intensity_order.get(s.intensity, 0), reverse=True)

    # Summarize by metal
    gold_signals = [s for s in all_signals if s.affected_metal in ("Gold", "Both")]
    silver_signals = [s for s in all_signals if s.affected_metal in ("Silver", "Both")]

    # Overall bias
    gold_bullish = sum(1 for s in gold_signals if "Bullish" in s.market_impact or "Surge" in s.market_impact or "Accumulation" in s.market_impact or "Safe-Haven" in s.market_impact)
    gold_bearish = sum(1 for s in gold_signals if "Correction" in s.market_impact or "Mandi" in s.market_impact or "Cooling" in s.market_impact)

    silver_bullish = sum(1 for s in silver_signals if "Bullish" in s.market_impact or "Outperformance" in s.market_impact or "Rally" in s.market_impact)
    silver_bearish = sum(1 for s in silver_signals if "Correction" in s.market_impact or "Mandi" in s.market_impact or "Cooling" in s.market_impact)

    gold_bias = "BULLISH" if gold_bullish > gold_bearish else ("BEARISH" if gold_bearish > gold_bullish else "NEUTRAL")
    silver_bias = "BULLISH" if silver_bullish > silver_bearish else ("BEARISH" if silver_bearish > silver_bullish else "NEUTRAL")

    return {
        "date": date.isoformat(),
        "ayanamsa": round(ayanamsa, 4),
        "total_signals": len(all_signals),
        "signals": [
            {
                "vedha_type": s.vedha_type.value,
                "title": s.title,
                "mechanism": s.mechanism,
                "market_impact": s.market_impact,
                "intensity": s.intensity,
                "affected_metal": s.affected_metal,
                "triggering_planets": s.triggering_planets,
                "nakshatras_involved": s.nakshatras_involved,
                "duration_estimate": s.duration_estimate,
                "confidence": s.confidence,
                "details": s.details,
            } for s in all_signals
        ],
        "summary": {
            "gold": {
                "bias": gold_bias,
                "signal_count": len(gold_signals),
                "extreme_count": sum(1 for s in gold_signals if s.intensity == "EXTREME"),
                "high_count": sum(1 for s in gold_signals if s.intensity == "HIGH"),
            },
            "silver": {
                "bias": silver_bias,
                "signal_count": len(silver_signals),
                "extreme_count": sum(1 for s in silver_signals if s.intensity == "EXTREME"),
                "high_count": sum(1 for s in silver_signals if s.intensity == "HIGH"),
            },
            "overall_bullion_bias": "BULLISH" if gold_bias == "BULLISH" and silver_bias == "BULLISH" else
                                   "BEARISH" if gold_bias == "BEARISH" and silver_bias == "BEARISH" else "MIXED",
        },
        "matrix_reference": {
            "1_krittika_primary": "Malefic in Krittika -> Gold Teji (8 months)",
            "2_rohini_liquidity": "Kroora in Rohini -> Silver Volatility (7-14 days)",
            "3_aditya_guru": "Sun-Jupiter Vedha -> Gold Accumulation (30-90 days)",
            "4_shuki_chandra": "Venus-Moon Vedha -> Silver Outperformance",
            "5_retrograde_malefic": "Retrograde Mars/Saturn/Ketu/Rahu in Fire -> Gold Safe-Haven Spikes",
            "6_vipreet_obstructive": "Unopposed Benefic on Krittika/Rohini -> Mandi/Correction",
            "7_mercury_ketu_sun_triangle": "Mercury-Ketu-Sun in Leo/Magha -> Extreme Volatility/Both",
        }
    }


# ============================================================
# WEEKLY SCAN
# ============================================================
def scan_bullion_vedha_week(start_date: datetime.date = None) -> dict[str, Any]:
    """Scan bullion vedha matrix for full week (7 days)."""
    if start_date is None:
        start_date = datetime.date.today()

    # Adjust to Monday
    monday = start_date - datetime.timedelta(days=start_date.weekday())

    daily_scans = []
    for day_offset in range(7):
        day = monday + datetime.timedelta(days=day_offset)
        scan = scan_bullion_vedha_matrix(day)
        daily_scans.append(scan)

    # Aggregate weekly signals
    all_signals = []
    for scan in daily_scans:
        all_signals.extend(scan["signals"])

    # Deduplicate by vedha_type + triggering planets
    unique_signals = {}
    for s in all_signals:
        key = f"{s['vedha_type']}_{'-'.join(sorted(s['triggering_planets']))}"
        if key not in unique_signals or s["confidence"] > unique_signals[key]["confidence"]:
            unique_signals[key] = s

    # Weekly summary
    gold_signals = [s for s in unique_signals.values() if s["affected_metal"] in ("Gold", "Both")]
    silver_signals = [s for s in unique_signals.values() if s["affected_metal"] in ("Silver", "Both")]

    return {
        "week_start": monday.isoformat(),
        "week_end": (monday + datetime.timedelta(days=6)).isoformat(),
        "daily_scans": daily_scans,
        "weekly_unique_signals": list(unique_signals.values()),
        "weekly_summary": {
            "total_unique_signals": len(unique_signals),
            "gold_signals": len(gold_signals),
            "silver_signals": len(silver_signals),
            "extreme_intensity": sum(1 for s in unique_signals.values() if s["intensity"] == "EXTREME"),
            "high_intensity": sum(1 for s in unique_signals.values() if s["intensity"] == "HIGH"),
        }
    }


# ============================================================
# API INTEGRATION HELPER
# ============================================================
def format_bullion_vedha_for_ui(scan_result: dict) -> str:
    """Format bullion vedha scan for UI display."""
    lines = []
    lines.append("=" * 70)
    lines.append("BULLION VEDHA MATRIX - SBC PRECIOUS METALS ANALYSIS")
    lines.append(f"Date: {scan_result['date']} | Ayanamsa: {scan_result['ayanamsa']}°")
    lines.append("=" * 70)

    summary = scan_result["summary"]
    lines.append(f"\nOVERALL BULLION BIAS: {summary['overall_bullion_bias']}")
    lines.append(f"  Gold: {summary['gold']['bias']} ({summary['gold']['signal_count']} signals, {summary['gold']['extreme_count']} EXTREME)")
    lines.append(f"  Silver: {summary['silver']['bias']} ({summary['silver']['signal_count']} signals, {summary['silver']['extreme_count']} EXTREME)")

    if not scan_result["signals"]:
        lines.append("\nNo active bullion vedha signals detected.")
        return "\n".join(lines)

    lines.append(f"\nACTIVE VEDHA SIGNALS ({len(scan_result['signals'])}):")
    lines.append("-" * 70)

    for i, s in enumerate(scan_result["signals"], 1):
        intensity_marker = {"EXTREME": "[!!!]", "HIGH": "[!!]", "MODERATE": "[!]", "LOW": "[ ]"}.get(s["intensity"], "[ ]")
        metal_emoji = "GOLD" if "Gold" in s["affected_metal"] else ("SILVER" if "Silver" in s["affected_metal"] else "BOTH")

        lines.append(f"\n{i}. {intensity_marker} {s['title']} ({metal_emoji})")
        lines.append(f"   Type: {s['vedha_type'].replace('_', ' ').title()}")
        lines.append(f"   Intensity: {s['intensity']} | Confidence: {s['confidence']:.0%}")
        lines.append(f"   Mechanism: {s['mechanism']}")
        lines.append(f"   Impact: {s['market_impact']}")
        lines.append(f"   Duration: {s['duration_estimate']}")
        lines.append(f"   Planets: {', '.join(s['triggering_planets'])} | Nakshatras: {', '.join(s['nakshatras_involved'])}")

    lines.append("\n" + "=" * 70)
    lines.append("MATRIX REFERENCE:")
    for k, v in scan_result["matrix_reference"].items():
        lines.append(f"  {k}: {v}")
    lines.append("=" * 70)

    return "\n".join(lines)


# ============================================================
# DEMO
# ============================================================
if __name__ == "__main__":
    # Scan for current week
    result = scan_bullion_vedha_week(datetime.date(2026, 8, 24))
    print(format_bullion_vedha_for_ui(result["daily_scans"][0]))  # Monday scan
    print("\n\nWEEKLY SUMMARY:")
    print(f"  Unique signals: {result['weekly_summary']['total_unique_signals']}")
    print(f"  Gold signals: {result['weekly_summary']['gold_signals']}")
    print(f"  Silver signals: {result['weekly_summary']['silver_signals']}")
