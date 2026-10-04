"""
Transit Vedha Matrix - SBC Sector-Specific Transit Triggers
Maps specific planetary transits in key nakshatras to sectoral market impacts.
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


class TransitVedhaType(Enum):
    """Sector-specific transit vedha classifications."""
    ASHLESHA_HEAT = "ashlesha_heat"           # Sun/Mars in Ashlesha -> Agri commodities
    DHANISHTA_CHITRA_INDUSTRIAL = "dhanishta_chitra"  # Mars in Dhanishta/Chitra -> Industrial/Metals
    ROHINI_LIQUID = "rohini_liquid"           # Saturn/Rahu in Rohini -> Crude/Silver
    SWATI_AIR_TECH = "swati_air_tech"         # Sun/Mercury in Swati -> Chemicals/IT/Spices
    PUSHYA_PUNARVASU_FINANCIAL = "pushya_punarvasu"   # Jupiter in Pushya/Punarvasu -> Banking
    KRITTIKA_BULLION = "krittika_bullion"     # Mars/Sun in Krittika -> Gold/Copper
    MAGHA_PURVA_AUTO = "magha_purva_auto"     # Venus in Magha/P.Phalguni -> Auto/FMCG
    UTTARA_BHADRAPADA_REALTY = "uttara_bhadrapada"    # Saturn in U.Bhadrapada -> Realty/Cement


@dataclass
class TransitVedhaSignal:
    """A detected transit vedha signal for sector markets."""
    vedha_type: TransitVedhaType
    title: str
    transit_trigger: str
    key_nakshatra: str
    directional_vedha_target: str
    primary_market_impact: str
    affected_sectors: list[str]
    intensity: str
    confidence: float
    duration_estimate: str
    details: dict[str, Any]


# Sector mappings for each vedha type
VEDHA_SECTOR_MAP = {
    TransitVedhaType.ASHLESHA_HEAT: ["Sugar", "Gur", "Ethanol", "Wheat", "Agricultural", "Fertilizers"],
    TransitVedhaType.DHANISHTA_CHITRA_INDUSTRIAL: ["Steel", "Defence", "Heavy Machinery", "Capital Goods", "Metals", "Infrastructure"],
    TransitVedhaType.ROHINI_LIQUID: ["Crude Oil", "Natural Gas", "Silver", "Oil & Gas", "Petroleum"],
    TransitVedhaType.SWATI_AIR_TECH: ["Chemicals", "IT", "Specialty Oils", "Spices", "Export-oriented", "Technology"],
    TransitVedhaType.PUSHYA_PUNARVASU_FINANCIAL: ["Banking", "Financial Services", "Nifty Bank", "PSU Banks", "Private Banks", "NBFC"],
    TransitVedhaType.KRITTIKA_BULLION: ["Gold", "Bullion ETFs", "Copper Mining", "Precious Metals"],
    TransitVedhaType.MAGHA_PURVA_AUTO: ["Auto", "FMCG", "Consumer Durables", "Passenger Vehicles", "Luxury Consumption"],
    TransitVedhaType.UTTARA_BHADRAPADA_REALTY: ["Realty", "Cement", "Construction Materials", "Infrastructure", "Real Estate"],
}


# Trigger conditions: (planet, nakshatra) pairs
TRIGGER_CONDITIONS = {
    TransitVedhaType.ASHLESHA_HEAT: [
        ("Sun", "Ashlesha"), ("Mars", "Ashlesha"),
    ],
    TransitVedhaType.DHANISHTA_CHITRA_INDUSTRIAL: [
        ("Mars", "Dhanishta"), ("Mars", "Chitra"),
        ("Rahu", "Dhanishta"),  # Rahu in Dhanishta also triggers industrial volatility
    ],
    TransitVedhaType.ROHINI_LIQUID: [
        ("Saturn", "Rohini"), ("Rahu", "Rohini"),
    ],
    TransitVedhaType.SWATI_AIR_TECH: [
        ("Sun", "Swati"), ("Mercury", "Swati"),
    ],
    TransitVedhaType.PUSHYA_PUNARVASU_FINANCIAL: [
        ("Jupiter", "Pushya"), ("Jupiter", "Punarvasu"),
    ],
    TransitVedhaType.KRITTIKA_BULLION: [
        ("Mars", "Krittika"), ("Sun", "Krittika"),
    ],
    TransitVedhaType.MAGHA_PURVA_AUTO: [
        ("Venus", "Magha"), ("Venus", "P.Phalguni"),
        ("Mercury", "Magha"),  # Mercury in Magha also affects auto/communication
    ],
    TransitVedhaType.UTTARA_BHADRAPADA_REALTY: [
        ("Saturn", "U.Bhadrapada"),
    ],
}


# Extended triggers for "approaching" detection (adjacent nakshatras)
APPROACHING_TRIGGERS = {
    TransitVedhaType.ASHLESHA_HEAT: ["Magha", "Punarvasu"],
    TransitVedhaType.DHANISHTA_CHITRA_INDUSTRIAL: ["Shravana", "Shatabhisha", "Swati", "Vishakha"],
    TransitVedhaType.ROHINI_LIQUID: ["Krittika", "Mrigashira"],
    TransitVedhaType.SWATI_AIR_TECH: ["Vishakha", "Chitra"],
    TransitVedhaType.PUSHYA_PUNARVASU_FINANCIAL: ["Ashlesha", "Magha"],
    TransitVedhaType.KRITTIKA_BULLION: ["Bharani", "Rohini"],
    TransitVedhaType.MAGHA_PURVA_AUTO: ["Ashlesha", "Hasta", "U.Phalguni"],
    TransitVedhaType.UTTARA_BHADRAPADA_REALTY: ["P.Bhadrapada", "Revati"],
}


# Vedha mechanism descriptions
VEDHA_MECHANISMS = {
    TransitVedhaType.ASHLESHA_HEAT: "Sammukha (Frontal): Pierces Mula and Sagittarian commodity lines.",
    TransitVedhaType.DHANISHTA_CHITRA_INDUSTRIAL: "Cross-Grid (Parshwa): Cuts through Mars-Venus industrial nodes.",
    TransitVedhaType.ROHINI_LIQUID: "Diagonal (Vipreet): Targets liquid and elemental metal indicators.",
    TransitVedhaType.SWATI_AIR_TECH: "Horizontal: Pierces air/tech lines and chemical/spices sectors.",
    TransitVedhaType.PUSHYA_PUNARVASU_FINANCIAL: "Benefic (Subha) Vedha: Soft, expanding ray over financial signs.",
    TransitVedhaType.KRITTIKA_BULLION: "Direct Center Axis: Hits central gold and copper nodes.",
    TransitVedhaType.MAGHA_PURVA_AUTO: "Subha-Sammukha: Crosses consumer durables and auto axis.",
    TransitVedhaType.UTTARA_BHADRAPADA_REALTY: "Deep Parshwa Vedha: Hits real estate and construction materials.",
}


# Market impact descriptions
MARKET_IMPACTS = {
    TransitVedhaType.ASHLESHA_HEAT: "Sugar, Gur, Ethanol and Wheat Rallies: Direct high-intensity heat on sugarcane refining and agricultural policy.",
    TransitVedhaType.DHANISHTA_CHITRA_INDUSTRIAL: "Steel, Defence and Heavy Machinery: Triggers rapid short-squeezes in metals, infrastructure, and capital goods counters.",
    TransitVedhaType.ROHINI_LIQUID: "Crude Oil and Silver Rallies: Severe supply compression, driving sharp speculative surges in oil, gas, and silver.",
    TransitVedhaType.SWATI_AIR_TECH: "Chemicals, IT and Specialty Oils: Drives momentum in export-oriented tech platforms, specialty chemicals, and spices.",
    TransitVedhaType.PUSHYA_PUNARVASU_FINANCIAL: "Banking and Financial Services (Nifty Bank): Large-cap private banks and PSU banking liquidity surges.",
    TransitVedhaType.KRITTIKA_BULLION: "Gold and Bullion Surge: Multi-month structural bull runs in physical Gold, Bullion ETFs, and Copper mining.",
    TransitVedhaType.MAGHA_PURVA_AUTO: "Auto and FMCG Rally: Strong consumer demand shifts driving passenger vehicle manufacturers and luxury consumption stocks.",
    TransitVedhaType.UTTARA_BHADRAPADA_REALTY: "Realty and Cement Expansion: Long-term institutional accumulation in cement, real estate, and structural infrastructure.",
}


DURATION_ESTIMATES = {
    TransitVedhaType.ASHLESHA_HEAT: "While Sun/Mars transit Ashlesha (~13-14 days)",
    TransitVedhaType.DHANISHTA_CHITRA_INDUSTRIAL: "While Mars transits Dhanishta/Chitra (~26-28 days total)",
    TransitVedhaType.ROHINI_LIQUID: "While Saturn/Rahu transit Rohini (~2.5 years for Saturn, ~18 months for Rahu)",
    TransitVedhaType.SWATI_AIR_TECH: "While Sun/Mercury transit Swati (~13-14 days each)",
    TransitVedhaType.PUSHYA_PUNARVASU_FINANCIAL: "While Jupiter transits Pushya/Punarvasu (~13 months total)",
    TransitVedhaType.KRITTIKA_BULLION: "Multi-month structural (while Mars/Sun in Krittika + residual)",
    TransitVedhaType.MAGHA_PURVA_AUTO: "While Venus transits Magha/P.Phalguni (~26-28 days total)",
    TransitVedhaType.UTTARA_BHADRAPADA_REALTY: "While Saturn transits U.Bhadrapada (~2.5 years)",
}


INTENSITY_DEFAULTS = {
    TransitVedhaType.ASHLESHA_HEAT: "HIGH",
    TransitVedhaType.DHANISHTA_CHITRA_INDUSTRIAL: "HIGH",
    TransitVedhaType.ROHINI_LIQUID: "EXTREME",
    TransitVedhaType.SWATI_AIR_TECH: "MODERATE-HIGH",
    TransitVedhaType.PUSHYA_PUNARVASU_FINANCIAL: "HIGH",
    TransitVedhaType.KRITTIKA_BULLION: "EXTREME",
    TransitVedhaType.MAGHA_PURVA_AUTO: "HIGH",
    TransitVedhaType.UTTARA_BHADRAPADA_REALTY: "MODERATE-HIGH",
}


def _julian_at_noon(date: datetime.date) -> float:
    local = datetime.datetime.combine(date, datetime.time(12, 0), tzinfo=ZoneInfo('Asia/Kolkata'))
    utc = local.astimezone(datetime.UTC)
    return float(swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0))


def _get_planets(date: datetime.date) -> tuple[list[dict], int, float]:
    jul = _julian_at_noon(date)
    planets, ayanamsa = positions(jul)
    sun = next(p for p in planets if p["name"] == "Sun")
    moon = next(p for p in planets if p["name"] == "Moon")
    tithi = tithi_of(sun["longitude"], moon["longitude"])
    planets = all_planets_with_natures(planets, tithi, sun["longitude"])
    return planets, tithi, ayanamsa


def scan_transit_vedha_matrix(date: datetime.date | None = None) -> dict[str, Any]:
    """
    Scan all Transit Vedha Matrix signals for a given date.
    """
    if date is None:
        date = datetime.date.today()

    planets, tithi, ayanamsa = _get_planets(date)
    vedha_map = compute_vedhas(planets, school="classical")[0]

    all_signals = []

    # Exact matches
    for vedha_type, triggers in TRIGGER_CONDITIONS.items():
        for planet_name, nakshatra in triggers:
            planet = next((p for p in planets if p["name"] == planet_name), None)
            if not planet:
                continue

            if planet["nakshatra"] == nakshatra:
                vedha_hits = vedha_map.get(planet_name, [])

                signal = TransitVedhaSignal(
                    vedha_type=vedha_type,
                    title=f"{planet_name} in {nakshatra} ({planet['sign']} {planet['degree']:.2f}°)",
                    transit_trigger=f"{planet_name} transiting {nakshatra}",
                    key_nakshatra=nakshatra,
                    directional_vedha_target=VEDHA_MECHANISMS[vedha_type],
                    primary_market_impact=MARKET_IMPACTS[vedha_type],
                    affected_sectors=VEDHA_SECTOR_MAP[vedha_type],
                    intensity=INTENSITY_DEFAULTS[vedha_type],
                    confidence=0.85,
                    duration_estimate=DURATION_ESTIMATES[vedha_type],
                    details={
                        "planet": planet_name,
                        "nakshatra": nakshatra,
                        "sign": planet["sign"],
                        "degree": planet["degree"],
                        "retrograde": planet.get("retrograde", False),
                        "vedha_hits_count": len(vedha_hits),
                        "target_sectors": VEDHA_SECTOR_MAP[vedha_type],
                        "match_type": "EXACT",
                    }
                )
                all_signals.append(signal)

    # Approaching matches (adjacent nakshatras)
    for vedha_type, approach_nakshatras in APPROACHING_TRIGGERS.items():
        for planet_name in {t[0] for t in TRIGGER_CONDITIONS.get(vedha_type, [])}:
            planet = next((p for p in planets if p["name"] == planet_name), None)
            if not planet:
                continue

            if planet["nakshatra"] in approach_nakshatras:
                # Find which trigger nakshatra this is approaching
                target_nakshatra = next((t[1] for t in TRIGGER_CONDITIONS.get(vedha_type, []) if t[0] == planet_name), None)

                vedha_hits = vedha_map.get(planet_name, [])

                signal = TransitVedhaSignal(
                    vedha_type=vedha_type,
                    title=f"{planet_name} in {planet['nakshatra']} ({planet['sign']} {planet['degree']:.2f} deg) approaching {target_nakshatra}",
                    transit_trigger=f"{planet_name} in {planet['nakshatra']} approaching {target_nakshatra}",
                    key_nakshatra=planet["nakshatra"],
                    directional_vedha_target=VEDHA_MECHANISMS[vedha_type],
                    primary_market_impact=MARKET_IMPACTS[vedha_type],
                    affected_sectors=VEDHA_SECTOR_MAP[vedha_type],
                    intensity=INTENSITY_DEFAULTS[vedha_type],
                    confidence=0.65,  # Lower confidence for approaching
                    duration_estimate="Approaching: {} to {} (1-2 weeks)".format(planet['nakshatra'], target_nakshatra),
                    details={
                        "planet": planet_name,
                        "current_nakshatra": planet["nakshatra"],
                        "target_nakshatra": target_nakshatra,
                        "sign": planet["sign"],
                        "degree": planet["degree"],
                        "retrograde": planet.get("retrograde", False),
                        "vedha_hits_count": len(vedha_hits),
                        "target_sectors": VEDHA_SECTOR_MAP[vedha_type],
                        "match_type": "APPROACHING",
                    }
                )
                all_signals.append(signal)

    # Sort by intensity
    intensity_order = {"EXTREME": 4, "HIGH": 3, "MODERATE-HIGH": 2, "MODERATE": 1, "LOW": 0}
    all_signals.sort(key=lambda s: intensity_order.get(s.intensity, 0), reverse=True)

    # Group by sector impact
    sector_signals: dict = {}
    for s in all_signals:
        for sector in s.affected_sectors:
            if sector not in sector_signals:
                sector_signals[sector] = []
            sector_signals[sector].append(s)

    return {
        "date": date.isoformat(),
        "ayanamsa": round(ayanamsa, 4),
        "total_signals": len(all_signals),
        "signals": [
            {
                "vedha_type": s.vedha_type.value,
                "title": s.title,
                "transit_trigger": s.transit_trigger,
                "key_nakshatra": s.key_nakshatra,
                "directional_vedha_target": s.directional_vedha_target,
                "primary_market_impact": s.primary_market_impact,
                "affected_sectors": s.affected_sectors,
                "intensity": s.intensity,
                "confidence": s.confidence,
                "duration_estimate": s.duration_estimate,
                "details": s.details,
            } for s in all_signals
        ],
        "by_sector": {
            sector: [
                {
                    "vedha_type": s.vedha_type.value,
                    "title": s.title,
                    "intensity": s.intensity,
                    "impact": s.primary_market_impact,
                } for s in signals
            ] for sector, signals in sector_signals.items()
        },
        "matrix_reference": {
            "1_ashlesha_heat": "Sun/Mars in Ashlesha -> Agri Commodities (Sugar, Ethanol, Wheat)",
            "2_dhanishta_chitra": "Mars in Dhanishta/Chitra -> Steel, Defence, Heavy Machinery",
            "3_rohini_liquid": "Saturn/Rahu in Rohini -> Crude Oil, Silver",
            "4_swati_air_tech": "Sun/Mercury in Swati -> Chemicals, IT, Spices",
            "5_pushya_punarvasu": "Jupiter in Pushya/Punarvasu -> Banking, Financial Services",
            "6_krittika_bullion": "Mars/Sun in Krittika -> Gold, Copper",
            "7_magha_purva_auto": "Venus in Magha/P.Phalguni -> Auto, FMCG",
            "8_uttara_bhadrapada": "Saturn in U.Bhadrapada -> Realty, Cement",
        }
    }


def scan_transit_vedha_week(start_date: datetime.date | None = None) -> dict[str, Any]:
    """Scan transit vedha matrix for full week (7 days)."""
    if start_date is None:
        start_date = datetime.date.today()

    monday = start_date - datetime.timedelta(days=start_date.weekday())

    daily_scans = []
    all_signals = []

    for day_offset in range(7):
        day = monday + datetime.timedelta(days=day_offset)
        scan = scan_transit_vedha_matrix(day)
        daily_scans.append(scan)
        all_signals.extend(scan["signals"])

    # Deduplicate by vedha_type + planet + nakshatra
    unique_signals = {}
    for s in all_signals:
        key = f"{s['vedha_type']}_{s['details']['planet']}_{s['key_nakshatra']}"
        if key not in unique_signals:
            unique_signals[key] = s

    # Weekly sector summary
    sector_summary: dict[str, dict[str, Any]] = {}
    for s in unique_signals.values():
        for sector in s["affected_sectors"]:
            if sector not in sector_summary:
                sector_summary[sector] = {"count": 0, "max_intensity": "LOW", "signals": []}
            sector_summary[sector]["count"] += 1
            sector_summary[sector]["signals"].append(s["title"])
            # Track max intensity
            intensity_order = {"EXTREME": 4, "HIGH": 3, "MODERATE-HIGH": 2, "MODERATE": 1, "LOW": 0}
            if intensity_order.get(s["intensity"], 0) > intensity_order.get(sector_summary[sector]["max_intensity"], 0):
                sector_summary[sector]["max_intensity"] = s["intensity"]

    return {
        "week_start": monday.isoformat(),
        "week_end": (monday + datetime.timedelta(days=6)).isoformat(),
        "daily_scans": daily_scans,
        "weekly_unique_signals": list(unique_signals.values()),
        "weekly_sector_summary": sector_summary,
        "weekly_summary": {
            "total_unique_signals": len(unique_signals),
            "extreme_count": sum(1 for s in unique_signals.values() if s["intensity"] == "EXTREME"),
            "high_count": sum(1 for s in unique_signals.values() if s["intensity"] == "HIGH"),
            "sectors_activated": len(sector_summary),
        }
    }


def format_transit_vedha_for_ui(scan_result: dict) -> str:
    """Format transit vedha scan for UI display."""
    lines = []
    lines.append("=" * 70)
    lines.append("TRANSIT VEDHA MATRIX - SECTOR TRIGGERS")
    lines.append("Date: {} | Ayanamsa: {}°".format(scan_result['date'], scan_result['ayanamsa']))
    lines.append("=" * 70)

    if not scan_result["signals"]:
        lines.append("\nNo active transit vedha signals detected.")
        return "\n".join(lines)

    lines.append("\nACTIVE TRANSIT VEDHA SIGNALS ({}):".format(len(scan_result['signals'])))
    lines.append("-" * 70)

    for i, s in enumerate(scan_result["signals"], 1):
        intensity_marker = {"EXTREME": "[!!!]", "HIGH": "[!!]", "MODERATE-HIGH": "[!]", "MODERATE": "[+]"}.get(s["intensity"], "[ ]")

        lines.append(f"\n{i}. {intensity_marker} {intensity_marker}")
        lines.append("   Title: {}".format(s['title']))
        lines.append("   Type: {}".format(s['vedha_type'].replace('_', ' ').title()))
        lines.append("   Intensity: {} | Confidence: {:.0%}".format(s['intensity'], s['confidence']))
        lines.append("   Nakshatra: {}".format(s['key_nakshatra']))
        lines.append("   Vedha Mechanism: {}".format(s['directional_vedha_target']))
        lines.append("   Market Impact: {}".format(s['primary_market_impact']))
        lines.append("   Affected Sectors: {}".format(', '.join(s['affected_sectors'])))
        lines.append("   Duration: {}".format(s['duration_estimate']))
        if 'match_type' in s.get('details', {}):
            lines.append("   Match: {}".format(s['details']['match_type']))

    # By sector
    lines.append("\n" + "-" * 70)
    lines.append("BY SECTOR:")
    lines.append("-" * 70)
    for sector, signals in scan_result["by_sector"].items():
        if signals:
            max_int = max(s["intensity"] for s in signals)
            lines.append(f"  {sector}: {len(signals)} signal(s), max {max_int}")
            for s in signals:
                lines.append("    - {} ({})".format(s['title'], s['intensity']))

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
    result = scan_transit_vedha_matrix(datetime.date(2026, 8, 24))
    print(format_transit_vedha_for_ui(result))
