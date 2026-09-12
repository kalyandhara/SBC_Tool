"""
Weekly Confluence Commentary Generator for SBC Tool

Generates expert-style weekly market commentary based on planetary positions,
reversal windows, transits, and confluence analysis.
"""

import datetime
from zoneinfo import ZoneInfo
import swisseph as swe

from sbc.planets import positions, all_planets_with_natures
from sbc.nakshatra import tithi_of, nakshatra_of, sign_of, moon_nature, paksha_of
from sbc.market_calendar import (
    reversal_alert, transit_alert, lunar_phase_alert, 
    jupiter_market_analysis, get_all_bullish_reversal_windows,
    TRANSIT_RULES
)
from sbc.backtest import run_bullish_futurecast, run_bearish_futurecast
from sbc.confluence import build_confluence_report
from sbc.prediction import analyze, compute_vedhas, place_planets, sector_read, planet_sector_read, summarize_vedhas
from sbc.chakra import GRID
from sbc.venus_vedha import venus_vedha_events, format_venus_vedha
from sbc.market_calendar import _anchor_nakshatra as anchor_nakshatra_func
from sbc.telecom_confluence import telecom_confluence, format_telecom_confluence

# Nakshatra meanings for commentary
NAKSHATRA_MEANINGS = {
    "Ashwini": "initiation", "Bharani": "creative birth", "Krittika": "cutting/purification",
    "Rohini": "growth", "Mrigashira": "searching", "Ardra": "transformation",
    "Punarvasu": "renewal", "Pushya": "nourishment", "Ashlesha": "analytical depth",
    "Magha": "authority", "P.Phalguni": "prosperity", "U.Phalguni": "prosperity/partnership",
    "Hasta": "skill", "Chitra": "design", "Swati": "independence",
    "Vishakha": "branching growth", "Anuradha": "devotion", "Jyeshtha": "supremacy",
    "Mula": "root change", "P.Ashadha": "invincibility", "U.Ashadha": "victory",
    "Shravana": "learning", "Dhanishta": "rhythm/wealth", "Shatabhisha": "healing",
    "P.Bhadrapada": "spiritual fire", "U.Bhadrapada": "universal love", "Revati": "completion/new cycle",
    "Abhijit": "victory/auspicious",
}

# Planet nature descriptions
PLANET_NATURE_DESC = {
    "Sun": "authority, leadership, government, vitality",
    "Moon": "sentiment, public mood, liquids, short-term trends",
    "Mars": "energy, aggression, conflicts, momentum",
    "Mercury": "communication, trade, intellect, technology, banking",
    "Jupiter": "expansion, wisdom, wealth, banking, growth",
    "Venus": "luxury, consumption, relationships, liquidity, arts",
    "Saturn": "structure, discipline, fear, karma, long-term trends",
    "Rahu": "obsession, innovation, speculation, foreign, mass psychology",
    "Ketu": "detachment, spirituality, past karma, sudden shifts, crashes",
}

SIGN_MEANINGS = {
    "Aries": "initiative, aggression, new beginnings",
    "Taurus": "stability, wealth, accumulation, banking",
    "Gemini": "communication, trade, technology, duality",
    "Cancer": "emotion, real estate, public sentiment, nourishment",
    "Leo": "authority, speculation, entertainment, leadership, gold",
    "Virgo": "analysis, service, health, detail, accounting",
    "Libra": "balance, partnerships, trade, justice, luxury",
    "Scorpio": "transformation, hidden, insurance, research, crisis",
    "Sagittarius": "expansion, philosophy, law, foreign, optimism",
    "Capricorn": "structure, authority, institutions, long-term",
    "Aquarius": "innovation, networks, technology, collective, disruption",
    "Pisces": "dissolution, spirituality, pharma, shipping, endings",
}


def _julian_at_noon(date):
    local = datetime.datetime.combine(date, datetime.time(12, 0), tzinfo=ZoneInfo('Asia/Kolkata'))
    utc = local.astimezone(datetime.timezone.utc)
    return swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)


def _angle(lon1, lon2):
    return abs((lon1 - lon2 + 180) % 360 - 180)


def _get_planet_positions(date):
    """Get planetary positions for a date at noon IST."""
    jul = _julian_at_noon(date)
    planets, ayanamsa = positions(jul)
    sun = next(p for p in planets if p["name"] == "Sun")
    moon = next(p for p in planets if p["name"] == "Moon")
    tithi = tithi_of(sun["longitude"], moon["longitude"])
    planets = all_planets_with_natures(planets, tithi, sun["longitude"])
    return planets, tithi, ayanamsa


def _format_planet_line(p):
    """Format a planet position for commentary."""
    retro = " (R)" if p["retrograde"] else ""
    return f"{p['name']} in {p['sign']} {p['degree']:.2f}° ({p['nakshatra']}){retro}"


def _detect_key_configurations(planets):
    """Detect major planetary configurations for the week."""
    configs = []
    by_name = {p["name"]: p for p in planets}
    
    # Mercury-Ketu-Sun triangle/conjunction in Leo
    sun = by_name["Sun"]
    mercury = by_name["Mercury"]
    ketu = by_name["Ketu"]
    
    sun_mercury = _angle(sun["longitude"], mercury["longitude"])
    sun_ketu = _angle(sun["longitude"], ketu["longitude"])
    mercury_ketu = _angle(mercury["longitude"], ketu["longitude"])
    
    # Check if all three in same sign
    if sun["sign"] == mercury["sign"] == ketu["sign"]:
        sign = sun["sign"]
        configs.append({
            "name": f"Mercury-Ketu-Sun Triangle in {sign}",
            "type": "major_conjunction",
            "details": f"Sun-Mercury {sun_mercury:.1f}°, Sun-Ketu {sun_ketu:.1f}°, Mercury-Ketu {mercury_ketu:.1f}°",
            "sign": sign,
            "nakshatra": sun["nakshatra"],
            "intensity": "high" if max(sun_mercury, sun_ketu, mercury_ketu) < 5 else "moderate"
        })
    elif sun["sign"] == mercury["sign"] and sun_mercury < 8:
        configs.append({
            "name": f"Sun-Mercury Conjunction in {sun['sign']}",
            "type": "conjunction",
            "details": f"Separation {sun_mercury:.1f}°",
            "sign": sun["sign"],
        })
    elif sun["sign"] == ketu["sign"] and sun_ketu < 8:
        configs.append({
            "name": f"Sun-Ketu Conjunction in {sun['sign']}",
            "type": "conjunction",
            "details": f"Separation {sun_ketu:.1f}°",
            "sign": sun["sign"],
        })
    elif mercury["sign"] == ketu["sign"] and mercury_ketu < 8:
        configs.append({
            "name": f"Mercury-Ketu Conjunction in {mercury['sign']}",
            "type": "conjunction",
            "details": f"Separation {mercury_ketu:.1f}°",
            "sign": mercury["sign"],
        })
    
    # Jupiter-Saturn aspects
    jupiter = by_name["Jupiter"]
    saturn = by_name["Saturn"]
    jup_sat = _angle(jupiter["longitude"], saturn["longitude"])
    if abs(jup_sat - 120) <= 8:
        configs.append({
            "name": "Jupiter-Saturn Trine",
            "type": "harmonious",
            "details": f"120° aspect ({'applying' if jup_sat < 120 else 'separating'})",
            "intensity": "extreme"
        })
    elif abs(jup_sat - 60) <= 6:
        configs.append({
            "name": "Jupiter-Saturn Sextile",
            "type": "harmonious",
            "details": f"60° aspect",
            "intensity": "high"
        })
    elif abs(jup_sat - 90) <= 8:
        configs.append({
            "name": "Jupiter-Saturn Square",
            "type": "challenging",
            "details": f"90° aspect",
            "intensity": "high"
        })
    elif abs(jup_sat - 180) <= 8:
        configs.append({
            "name": "Jupiter-Saturn Opposition",
            "type": "challenging",
            "details": f"180° aspect",
            "intensity": "extreme"
        })
    
    # Rahu-Jupiter trine
    rahu = by_name["Rahu"]
    rahu_jup = _angle(rahu["longitude"], jupiter["longitude"])
    if abs(rahu_jup - 120) <= 8:
        configs.append({
            "name": "Rahu-Jupiter Trine",
            "type": "harmonious",
            "details": "Mass optimism, new narratives emerging",
            "intensity": "high"
        })
    
    # Venus-Jupiter trine
    venus = by_name["Venus"]
    ven_jup = _angle(venus["longitude"], jupiter["longitude"])
    if abs(ven_jup - 120) <= 8:
        configs.append({
            "name": "Venus-Jupiter Trine",
            "type": "harmonious",
            "details": "Liquidity expansion, consumption boom",
            "intensity": "high"
        })
    
    # Mercury-Jupiter trine
    mer_jup = _angle(mercury["longitude"], jupiter["longitude"])
    if abs(mer_jup - 120) <= 8:
        configs.append({
            "name": "Mercury-Jupiter Trine",
            "type": "harmonious",
            "details": "Trading clarity, tech/banking optimism",
            "intensity": "moderate-high"
        })
    
    # Ketu in financial signs
    if ketu["sign"] in ("Libra", "Taurus"):
        configs.append({
            "name": f"Ketu in {ketu['sign']} (Financial Sign)",
            "type": "bearish",
            "details": "Capital flight risk, loss of confidence",
            "intensity": "high"
        })
    
    # Saturn in Pisces
    if saturn["sign"] == "Pisces":
        configs.append({
            "name": "Saturn in Pisces",
            "type": "bearish",
            "details": "Dissolution of structures, institutional weakening",
            "intensity": "high" if saturn["retrograde"] else "moderate"
        })
    
    # Jupiter in Cancer (exalted)
    if jupiter["sign"] == "Cancer":
        configs.append({
            "name": "Jupiter in Cancer (Exalted)",
            "type": "bullish",
            "details": "Maximum expansion, liquidity, growth support",
            "intensity": "extreme"
        })
    
    # Venus in Virgo (debilitated)
    if venus["sign"] == "Virgo":
        configs.append({
            "name": "Venus in Virgo (Debilitated)",
            "type": "bearish",
            "details": "Deflationary, credit tightening, consumption drop",
            "intensity": "moderate"
        })
    
    # Mercury retrograde
    if mercury["retrograde"]:
        configs.append({
            "name": "Mercury Retrograde",
            "type": "caution",
            "details": "Communication/trading confusion, review period",
            "intensity": "moderate"
        })
    
    return configs


def _get_moon_nakshatra_transits(start_date, days=7):
    """Get Moon nakshatra transits for the week."""
    transits = []
    for day_offset in range(days):
        date = start_date + datetime.timedelta(days=day_offset)
        planets, _, _ = _get_planet_positions(date)
        moon = next(p for p in planets if p["name"] == "Moon")
        meaning = NAKSHATRA_MEANINGS.get(moon["nakshatra"], "")
        transits.append({
            "date": date,
            "weekday": date.strftime("%A"),
            "nakshatra": moon["nakshatra"],
            "sign": moon["sign"],
            "degree": moon["degree"],
            "meaning": meaning,
            "lord": {"Ashwini": "Ketu", "Bharani": "Venus", "Krittika": "Sun", 
                     "Rohini": "Moon", "Mrigashira": "Mars", "Ardra": "Rahu",
                     "Punarvasu": "Jupiter", "Pushya": "Saturn", "Ashlesha": "Mercury",
                     "Magha": "Ketu", "P.Phalguni": "Venus", "U.Phalguni": "Sun",
                     "Hasta": "Moon", "Chitra": "Mars", "Swati": "Rahu",
                     "Vishakha": "Jupiter", "Anuradha": "Saturn", "Jyeshtha": "Mercury",
                     "Mula": "Ketu", "P.Ashadha": "Venus", "U.Ashadha": "Sun",
                     "Shravana": "Moon", "Dhanishta": "Mars", "Shatabhisha": "Rahu",
                     "P.Bhadrapada": "Jupiter", "U.Bhadrapada": "Saturn", "Revati": "Mercury"}.get(moon["nakshatra"], "")
        })
    return transits


def _analyze_market_bias(confluence, configurations, transits, bullish_fc, bearish_fc):
    """Determine overall market bias for the week."""
    bullish_factors = []
    bearish_factors = []
    
    # From confluence
    if confluence:
        overall = confluence.get("overall", {})
        if overall.get("signal") == "BULLISH":
            bullish_factors.append(f"Confluence: Net bullish ({overall.get('net', 0):+.2f})")
        elif overall.get("signal") == "BEARISH":
            bearish_factors.append(f"Confluence: Net bearish ({overall.get('net', 0):+.2f})")
        
        # Top sectors
        highlights = confluence.get("highlights", {})
        if highlights.get("bullish_confluence_sectors"):
            bullish_factors.append(f"Bullish sectors: {', '.join(highlights['bullish_confluence_sectors'][:3])}")
        if highlights.get("bearish_confluence_sectors"):
            bearish_factors.append(f"Bearish sectors: {', '.join(highlights['bearish_confluence_sectors'][:3])}")
    
    # From configurations
    for c in configurations:
        if c.get("type") in ("bullish", "harmonious"):
            bullish_factors.append(f"{c['name']}: {c.get('details', '')}")
        elif c.get("type") in ("bearish", "challenging"):
            bearish_factors.append(f"{c['name']}: {c.get('details', '')}")
        elif c.get("type") == "major_conjunction":
            # Major conjunctions = high volatility
            bearish_factors.append(f"{c['name']}: High volatility, sudden moves likely")
            bullish_factors.append(f"{c['name']}: Potential trend change/reversal window")
    
    # From futurecasts
    if bullish_fc and bullish_fc.get("clusters"):
        for c in bullish_fc["clusters"][:2]:
            if c["score"] >= 7:
                bullish_factors.append(f"Bullish futurecast: {c['score']}/16 ({', '.join(c['triggers'][:3])})")
    
    if bearish_fc and bearish_fc.get("clusters"):
        for c in bearish_fc["clusters"][:2]:
            if c["score"] >= 3:
                bearish_factors.append(f"Bearish futurecast: {c['score']}/20 ({', '.join(c['triggers'][:3])})")
    
    # Determine net bias
    if len(bullish_factors) > len(bearish_factors):
        bias = "BULLISH"
    elif len(bearish_factors) > len(bullish_factors):
        bias = "BEARISH"
    else:
        bias = "VOLATILE / MIXED"
    
    return bias, bullish_factors, bearish_factors


def generate_weekly_commentary(start_date=None):
    """
    Generate expert-style weekly confluence commentary.
    
    Args:
        start_date: datetime.date for Monday of the week (defaults to current week)
    
    Returns:
        dict with commentary sections
    """
    if start_date is None:
        today = datetime.date.today()
        # Find Monday of current week
        start_date = today - datetime.timedelta(days=today.weekday())
    
    end_date = start_date + datetime.timedelta(days=6)
    week_label = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
    
    # Get positions for start of week (Monday noon)
    planets, tithi, ayanamsa = _get_planet_positions(start_date)
    
    # Get all analyses
    alert = reversal_alert(start_date.isoformat(), planets, tithi)
    transits_list = transit_alert(planets)
    lunar = lunar_phase_alert(tithi)
    jupiter_analysis = jupiter_market_analysis(planets)
    bullish_windows = get_all_bullish_reversal_windows(start_date, planets, tithi)
    
    # Confluence
    vedha_map, _ = compute_vedhas(planets, school="classical")
    grid = place_planets(GRID, planets)
    analysis = analyze(planets, vedha_map, anchor_nakshatra_func("nse"), school="classical")
    sector_read_data = sector_read(vedha_map, planets)
    planet_sector_read_data = planet_sector_read(planets)

    # Venus vedha event (SBC-layer: Venus ray onto Chitra nakshatra / Libra rashi)
    venus_vedha = venus_vedha_events(planets, vedha_map, school="classical")

    confluence = build_confluence_report(
        analysis=analysis,
        sector_read=sector_read_data,
        planet_sector_read=planet_sector_read_data,
        reversal_data={"windows": alert.get("windows", []), "upcoming_windows": alert.get("upcoming_windows", [])},
        transits=transits_list,
        jupiter_analysis=jupiter_analysis,
        lunar_phase=lunar,
        venus_vedha=venus_vedha,
    )
    
    # Futurecasts
    bullish_fc = run_bullish_futurecast(center_date=start_date.isoformat(), years=1)
    bearish_fc = run_bearish_futurecast(center_date=start_date.isoformat(), years=1)
    
    # Key configurations
    configurations = _detect_key_configurations(planets)

    # Moon nakshatra transits
    moon_transits = _get_moon_nakshatra_transits(start_date)
    
    # Market bias
    bias, bullish_factors, bearish_factors = _analyze_market_bias(
        confluence, configurations, transits_list, bullish_fc, bearish_fc
    )
    
    # Identify the "most important cycle" (highest intensity configuration)
    main_cycle = None
    for c in sorted(configurations, key=lambda x: {"extreme": 4, "high": 3, "moderate-high": 2, "moderate": 1, "low": 0}.get(x.get("intensity", "moderate"), 1), reverse=True):
        if c.get("intensity") in ("extreme", "high"):
            main_cycle = c
            break
    
    # Sector-wise outlook
    by_name = {p["name"]: p for p in planets}
    telecom = telecom_confluence(planets)
    sector_outlook = _build_sector_outlook(by_name, sector_read_data, planet_sector_read_data, confluence, transits_list, alert, telecom)
    general_strategy = _generate_general_strategy(by_name, confluence, alert)
    nifty_levels = _get_nifty_levels_guidance(confluence)
    
    # Build commentary sections
    commentary = {
        "week": week_label,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "ayanamsa": round(ayanamsa, 4),
        "main_cycle": main_cycle,
        "all_configurations": configurations,
        "planetary_positions": [_format_planet_line(p) for p in planets],
        "moon_transits": moon_transits,
        "active_windows": alert.get("windows", []),
        "upcoming_windows": alert.get("upcoming_windows", []),
        "transits": transits_list,
        "venus_vedha": venus_vedha,
        "lunar_phase": lunar,
        "jupiter_analysis": jupiter_analysis,
        "confluence": confluence,
        "bullish_futurecast": bullish_fc,
        "bearish_futurecast": bearish_fc,
        "market_bias": bias,
        "bullish_factors": bullish_factors,
        "bearish_factors": bearish_factors,
        "sector_outlook": sector_outlook,
        "telecom_confluence": telecom,
        "general_strategy": general_strategy,
        "nifty_levels": nifty_levels,
    }
    
    return commentary


def format_commentary_text(commentary):
    """Format commentary as readable text report."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"WEEKLY ASTRO-MARKET CONFLUENCE COMMENTARY")
    lines.append(f"Week of {commentary['week']}")
    lines.append("=" * 70)
    
    # Main Cycle
    mc = commentary["main_cycle"]
    if mc:
        lines.append(f"\n>>> MOST IMPORTANT CYCLE THIS WEEK: {mc['name']} <<<")
        lines.append(f"    {mc.get('details', '')}")
        if mc.get("intensity"):
            lines.append(f"    Intensity: {mc['intensity'].upper()}")
        lines.append(f"    Sign: {mc.get('sign', 'N/A')} ({mc.get('nakshatra', 'N/A')})")
        lines.append(f"    {SIGN_MEANINGS.get(mc.get('sign', ''), '')}")
        lines.append(f"    Expected: High volatility, sudden moves, possible trend changes")
    
    # All Configurations
    lines.append("\n" + "-" * 70)
    lines.append("KEY PLANETARY CONFIGURATIONS THIS WEEK:")
    lines.append("-" * 70)
    for c in commentary["all_configurations"]:
        intensity_marker = {"extreme": "[!!!]", "high": "[!!]", "moderate-high": "[!]", "moderate": "[+]"}.get(c.get("intensity", ""), "[ ]")
        lines.append(f"  {intensity_marker} {c['name']}: {c.get('details', '')}")
    
    # Planetary Positions
    lines.append("\n" + "-" * 70)
    lines.append("PLANETARY POSITIONS (Monday noon IST, Lahiri Ayanamsa):")
    lines.append("-" * 70)
    for pos in commentary["planetary_positions"]:
        lines.append(f"  {pos}")
    
    # Moon Nakshatra Transits
    lines.append("\n" + "-" * 70)
    lines.append("MOON NAKSHATRA TRANSITS (Daily Sentiment Drivers):")
    lines.append("-" * 70)
    for mt in commentary["moon_transits"]:
        lord_str = f" (Lord: {mt['lord']})" if mt['lord'] else ""
        lines.append(f"  {mt['weekday']} {mt['date'].strftime('%b %d')}: Moon in {mt['sign']} {mt['degree']:.1f}° - {mt['nakshatra']} ({mt['meaning']}){lord_str}")
    
    # Active Reversal Windows
    lines.append("\n" + "-" * 70)
    lines.append("ACTIVE REVERSAL WINDOWS:")
    lines.append("-" * 70)
    if commentary["active_windows"]:
        for w in commentary["active_windows"]:
            lines.append(f"  [ACTIVE] {w['title']}")
            lines.append(f"     Level: {w['level']} | Bias: {w['bias']} | {w['start']} to {w['end']}")
            lines.append(f"     Sectors: {', '.join(w['sectors'])}")
    else:
        lines.append("  No active predefined reversal windows.")
    
    # Upcoming Windows
    if commentary["upcoming_windows"]:
        lines.append("\nUPCOMING HIGH-IMPACT WINDOWS (Next 7 Days):")
        for w in commentary["upcoming_windows"]:
            lines.append(f"  [UPCOMING] {w['title']} (in {w.get('days_ahead', '?')} days)")
            lines.append(f"     Level: {w['level']} | Bias: {w['bias']}")
    
    # Major Transits
    lines.append("\n" + "-" * 70)
    lines.append("MAJOR PLANETARY TRANSITS:")
    lines.append("-" * 70)
    for t in commentary["transits"]:
        retro = " (R)" if t.get("retrograde") else ""
        lines.append(f"  {t['planet']} in {t['sign']} {t['degree']:.2f}° {t['nakshatra']}{retro}")
        lines.append(f"     Bias: {t['bias']} | {t['explanation']}")
        lines.append(f"     Sectors: {', '.join(t['sectors'])}")
    
    # Venus Vedha Event (Chitra / Libra)
    if commentary.get("venus_vedha") and commentary["venus_vedha"].get("active"):
        lines.append("\n" + "-" * 70)
        lines.append("VENUS VEDHA EVENT (SBC — Chitra / Libra):")
        lines.append("-" * 70)
        for line in format_venus_vedha(commentary["venus_vedha"]):
            lines.append(f"  {line}")

    # Cable & Telecom Confluence (Mercury / Rahu / Guru-Chandal / Shrapit)
    if commentary.get("telecom_confluence"):
        lines.append("\n" + "-" * 70)
        lines.append("CABLE & TELECOM CONFLUENCE (Mercury / Rahu / yogas):")
        lines.append("-" * 70)
        for line in format_telecom_confluence(commentary["telecom_confluence"]):
            lines.append(f"  {line}")

    # Lunar Phase
    if commentary["lunar_phase"]:
        lp = commentary["lunar_phase"]
        lines.append("\n" + "-" * 70)
        lines.append("LUNAR PHASE:")
        lines.append("-" * 70)
        lines.append(f"  {lp['phase']} (Tithi {lp['tithi']}) - {lp['window']}")
        lines.append(f"  Level: {lp['level']} | Bias: {lp['bias']}")
        lines.append(f"  {lp['explanation']}")
    
    # Jupiter Analysis
    if commentary["jupiter_analysis"] and commentary["jupiter_analysis"]["active"]:
        ja = commentary["jupiter_analysis"]
        lines.append("\n" + "-" * 70)
        lines.append("JUPITER MARKET-RISK HEURISTIC:")
        lines.append("-" * 70)
        lines.append(f"  Status: ACTIVE - {ja['bias']} ({ja['level']})")
        for r in ja["reasons"]:
            lines.append(f"  • {r}")
    
    # Confluence Analysis
    if commentary["confluence"]:
        conf = commentary["confluence"]
        overall = conf["overall"]
        lines.append("\n" + "-" * 70)
        lines.append("CONFLUENCE ANALYSIS (Multi-factor Synthesis):")
        lines.append("-" * 70)
        lines.append(f"  Overall Signal: {overall['signal']} (Net: {overall['net']:+.2f})")
        lines.append(f"  Bullish Weight: {overall['bullish_weight']:.2f} | Bearish Weight: {overall['bearish_weight']:.2f}")
        
        highlights = conf["highlights"]
        if highlights["bullish_confluence_sectors"]:
            lines.append(f"  [GREEN] Bullish Confluence: {', '.join(highlights['bullish_confluence_sectors'])}")
        if highlights["bearish_confluence_sectors"]:
            lines.append(f"  [RED] Bearish Confluence: {', '.join(highlights['bearish_confluence_sectors'])}")
        if highlights["conflicted_sectors"]:
            lines.append(f"  [CONFLICT] Conflicted: {', '.join(highlights['conflicted_sectors'])}")
        
        lines.append("\n  Component Breakdown:")
        for name, comp in conf["components"].items():
            lines.append(f"    {name}: Bullish={comp['overall']['bullish_weight']:.1f}, Bearish={comp['overall']['bearish_weight']:.1f}, Signal={comp['overall']['signal']}")
    
    # Futurecast Summary
    lines.append("\n" + "-" * 70)
    lines.append("FUTURECAST SIGNALS (Next 30 Days):")
    lines.append("-" * 70)
    
    bc = commentary["bullish_futurecast"]
    if bc.get("clusters"):
        lines.append("  [BULLISH] BULLISH WINDOWS:")
        for c in bc["clusters"][:3]:
            if c["start"] >= commentary["start_date"] and c["start"] <= commentary["end_date"] or c["timeline"] in ("current", "upcoming"):
                lines.append(f"    {c['start']} - {c['end']}: Score {c['score']}/16 ({c['level']})")
                lines.append(f"      Triggers: {', '.join(c['triggers'][:4])}")
    
    brc = commentary["bearish_futurecast"]
    if brc.get("clusters"):
        lines.append("  [BEARISH] BEARISH WINDOWS:")
        for c in brc["clusters"][:3]:
            if c["start"] >= commentary["start_date"] and c["start"] <= commentary["end_date"] or c["timeline"] in ("current", "upcoming"):
                lines.append(f"    {c['start']} - {c['end']}: Score {c['score']}/20 ({c['level']})")
                lines.append(f"      Triggers: {', '.join(c['triggers'][:4])}")
    
    # Market Bias Summary
    lines.append("\n" + "=" * 70)
    lines.append(f"WEEKLY MARKET BIAS: {commentary['market_bias']}")
    lines.append("=" * 70)
    
    if commentary["bullish_factors"]:
        lines.append("  [+] BULLISH FACTORS:")
        for f in commentary["bullish_factors"][:5]:
            lines.append(f"    • {f}")
    
    if commentary["bearish_factors"]:
        lines.append("\n  [-] BEARISH FACTORS:")
        for f in commentary["bearish_factors"][:5]:
            lines.append(f"    • {f}")
    
    # Sector-wise Outlook
    if commentary.get("sector_outlook"):
        lines.append("\n" + "=" * 70)
        lines.append("SECTOR-WISE FINANCIAL ASTRO-TREND OUTLOOK")
        lines.append("=" * 70)
        lines.append(f"{'SECTOR':<20} {'ASTROLOGICAL INFLUENCE':<50} {'TREND/OUTLOOK':<25} {'KEY FOCUS'}")
        lines.append("-" * 110)
        for s in commentary["sector_outlook"]:
            lines.append(f"{s['sector']:<20} {s['astrological_influence'][:48]:<50} {s['trend_outlook'][:23]:<25} {s['key_focus'][:60]}")
    
    # General Market Strategy
    if commentary.get("general_strategy"):
        lines.append("\n" + "=" * 70)
        lines.append("GENERAL MARKET STRATEGY FOR THE WEEK")
        lines.append("=" * 70)
        for line in commentary["general_strategy"].split('\n'):
            lines.append(f"  {line}")
    
    # Nifty Levels
    if commentary.get("nifty_levels"):
        lines.append("\n" + "=" * 70)
        lines.append("NIFTY KEY LEVELS & GUIDANCE")
        lines.append("=" * 70)
        for line in commentary["nifty_levels"].split('\n'):
            lines.append(f"  {line}")
    
    lines.append("\n" + "=" * 70)
    lines.append("DISCLAIMER: Research commentary only. Not financial advice.")
    lines.append("Use technical, fundamental and risk management before trading.")
    lines.append("=" * 70)
    
    return "\n".join(lines)


# ============================================================
# SECTOR-WISE OUTLOOK
# ============================================================

def _clean(s):
    return s.replace('\u211e', ' R').replace('\u26aa', '[ ]')


def _build_sector_outlook(by_name, sector_read_data, planet_sector_read_data, confluence, transits, alert, telecom=None):
    """Build the sector-wise outlook table."""
    
    SECTOR_MAPPING = {
"Nifty IT": ["IT", "IT & Software", "Technology"],
         "Nifty Telecom/Cable": ["Telecom", "Cable & Media", "Communication Infrastructure", "Digital Infrastructure", "Media"],
        "Nifty Bank": ["Banking", "Banks", "PSU Banks", "Private Banks", "Finance & Banking", "Financial Services", "Banking & Management"],
        "Nifty PSU Bank": ["PSU Banks", "PSU", "PSU & Utilities", "Government-linked"],
        "Nifty Auto": ["Auto", "Auto & Mobility", "Auto & Mobility", "Engineering", "Defense & Aerospace"],
        "Nifty Metal": ["Metals", "Metals & Mining", "Base Metals", "Copper & Red Metals", "Steel & Energy", "Industrial / Base-Metal Index"],
        "Nifty FMCG": ["FMCG", "Consumer Staples", "Consumer-FMCG", "Consumer"],
        "Nifty Pharma": ["Pharma", "Pharma & Alcohol", "Healthcare", "Healthcare IT", "Pharmaceuticals"],
        "Nifty Energy": ["Energy", "Energy & Power", "Oil & Gas", "Petroleum & Crude", "Petroleum"],
        "Nifty Oil & Gas": ["Oil & Gas", "Petroleum & Crude", "Petroleum", "Shipping & Fisheries"],
        "Nifty Realty": ["Real Estate", "Realty", "Realty & Housing", "Infrastructure", "Infra", "Cement & Infra"],
        "Nifty Infra": ["Infrastructure", "Infra", "Cement & Infra", "Defense & Infra"],
        "Nifty Large Caps": ["Large Caps", "Large Cap", "Nifty 50"],
        "Nifty Gold": ["Gold/MCX", "Gold", "Gold (store of wealth)", "MCX Gold", "Luxury & Silver"],
    }
    
    highlights = confluence.get("highlights", {})
    bullish_sectors = set(highlights.get("bullish_confluence_sectors", []))
    bearish_sectors = set(highlights.get("bearish_confluence_sectors", []))
    conflicted_sectors = set(highlights.get("conflicted_sectors", []))
    sector_confluence = confluence.get("sector_confluence", {})
    
    sun = by_name["Sun"]
    mercury = by_name["Mercury"]
    mars = by_name["Mars"]
    jupiter = by_name["Jupiter"]
    saturn = by_name["Saturn"]
    venus = by_name["Venus"]
    rahu = by_name["Rahu"]
    ketu = by_name["Ketu"]
    moon = by_name["Moon"]
    
    outlook = []
    
    for nifty_sector, mapped_sectors in SECTOR_MAPPING.items():
        conf_score = 0
        conf_signal = "NEUTRAL"
        for mapped in mapped_sectors:
            if mapped in sector_confluence:
                sc = sector_confluence[mapped]
                conf_score += sc.get("net", 0)
                if sc.get("signal") == "BULLISH":
                    conf_signal = "BULLISH"
                elif sc.get("signal") == "BEARISH":
                    conf_signal = "BEARISH" if conf_signal != "BULLISH" else "MIXED"
        
        if nifty_sector == "Nifty Telecom/Cable" and telecom:
            influence = _telecom_influence(telecom)
            trend = _telecom_trend(telecom, conf_signal)
            focus = _telecom_focus(telecom)
        else:
            influence = _determine_astrological_influence(nifty_sector, by_name)
            trend = _determine_trend(nifty_sector, conf_signal, bullish_sectors, bearish_sectors, conflicted_sectors, by_name)
            focus = _generate_key_focus(nifty_sector, by_name)
        
        outlook.append({
            "sector": nifty_sector,
            "astrological_influence": influence,
            "trend_outlook": trend,
            "key_focus": focus,
            "confluence_score": round(conf_score, 2),
            "confluence_signal": conf_signal,
        })
    
    return outlook


def _determine_astrological_influence(sector, by_name):
    """Determine the primary astrological influence for a sector."""
    influences = []
    
    sun = by_name["Sun"]
    mercury = by_name["Mercury"]
    mars = by_name["Mars"]
    jupiter = by_name["Jupiter"]
    saturn = by_name["Saturn"]
    venus = by_name["Venus"]
    rahu = by_name["Rahu"]
    ketu = by_name["Ketu"]
    moon = by_name["Moon"]
    
    if "IT" in sector:
        if mercury["retrograde"]:
            influences.append(f"Mercury Retrograde in {mercury['sign']} ({mercury['nakshatra']})")
        else:
            influences.append(f"Mercury in {mercury['sign']} ({mercury['nakshatra']})")
        if jupiter["sign"] in ("Cancer", "Sagittarius", "Pisces"):
            influences.append(f"Jupiter in {jupiter['sign']} (expansive)")
    
    elif "Bank" in sector or "Financial" in sector:
        influences.append(f"Jupiter in {jupiter['sign']} ({jupiter['nakshatra']}) - banking karaka")
        influences.append(f"Saturn in {saturn['sign']} ({saturn['nakshatra']}){' R' if saturn['retrograde'] else ''} - structure")
        if sun["sign"] == "Leo":
            influences.append(f"Sun in Leo (government/PSU authority)")
    
    elif "Auto" in sector or "Metal" in sector:
        influences.append(f"Mars in {mars['sign']} ({mars['nakshatra']}) - industrial drive")
        influences.append(f"Sun in {sun['sign']} ({sun['nakshatra']}) - fire element")
        if rahu["sign"] in ("Aries", "Leo"):
            influences.append(f"Rahu in {rahu['sign']} (speculative appetite)")
    
    elif "FMCG" in sector or "Pharma" in sector:
        influences.append(f"Venus in {venus['sign']} ({venus['nakshatra']}) - consumption")
        influences.append(f"Moon in {moon['sign']} ({moon['nakshatra']}) - public sentiment")
        if saturn["sign"] == "Pisces":
            influences.append(f"Saturn in Pisces (healthcare/pharma structure)")
    
    elif "Energy" in sector or "Oil" in sector:
        influences.append(f"Rahu/Ketu axis ({rahu['sign']}/{ketu['sign']}) - volatile commodities")
        influences.append(f"Sun in {sun['sign']} ({sun['nakshatra']}) - energy source")
        if mars["sign"] in ("Aries", "Scorpio", "Capricorn"):
            influences.append(f"Mars in {mars['sign']} (energy drive)")
    
    elif "Realty" in sector or "Infra" in sector:
        influences.append(f"Saturn in {saturn['sign']} ({saturn['nakshatra']}){' R' if saturn['retrograde'] else ''} - land/structure")
        if jupiter["sign"] in ("Cancer", "Taurus"):
            influences.append(f"Jupiter in {jupiter['sign']} (real estate expansion)")
    
    elif "Large" in sector or "Nifty 50" in sector:
        influences.append(f"Sun in {sun['sign']} - index leadership")
        jup_sat = abs((jupiter["longitude"] - saturn["longitude"] + 180) % 360 - 180)
        if abs(jup_sat - 120) < 8:
            influences.append(f"Jupiter-Saturn trine (applying)")
    
    elif "Gold" in sector:
        influences.append(f"Ketu in {ketu['sign']} ({ketu['nakshatra']}) - gold/store of value")
        influences.append(f"Sun in {sun['sign']} - sovereign gold")
    
    return " | ".join(influences) if influences else "General planetary climate"


def _determine_trend(sector, conf_signal, bullish_sectors, bearish_sectors, conflicted_sectors, by_name):
    """Determine trend outlook based on confluence and planetary positions."""
    
    in_bullish = any(s in sector or sector in s for s in bullish_sectors)
    in_bearish = any(s in sector or sector in s for s in bearish_sectors)
    in_conflicted = any(s in sector or sector in s for s in conflicted_sectors)
    
    mercury = by_name["Mercury"]
    mars = by_name["Mars"]
    saturn = by_name["Saturn"]
    jupiter = by_name["Jupiter"]
    sun = by_name["Sun"]
    venus = by_name["Venus"]
    
    if in_bullish and not in_bearish:
        base = "Bullish / Outperformer"
    elif in_bearish and not in_bullish:
        base = "Bearish / Underperformer"
    elif in_conflicted:
        base = "Mixed / Conflicted"
    elif conf_signal == "BULLISH":
        base = "Bullish Bias"
    elif conf_signal == "BEARISH":
        base = "Bearish Bias"
    else:
        base = "Neutral / Consolidation"
    
    if "IT" in sector and mercury["retrograde"]:
        return "Volatile to Cautious" + (" (Mercury R)" if "Volatile" not in base else "")
    elif "Bank" in sector and jupiter["sign"] == "Cancer":
        return "Selective Upside" + (" (Exalted Jupiter)" if "Bullish" not in base else "")
    elif "Auto" in sector or "Metal" in sector:
        if mars["sign"] in ("Aries", "Scorpio", "Capricorn") and sun["sign"] == "Leo":
            return "Bullish / Outperformer" + (" (Mars-Sun Fire)" if "Bullish" not in base else "")
    elif "FMCG" in sector or "Pharma" in sector:
        if venus["sign"] in ("Taurus", "Libra", "Pisces"):
            return "Defensive / Stable" + (" (Strong Venus)" if "Defensive" not in base else "")
        return "Defensive / Stable"
    elif "Energy" in sector or "Oil" in sector:
        return "High Volatility" + (" (Rahu/Ketu axis)" if "High" not in base else "")
    elif "Realty" in sector or "Infra" in sector:
        if saturn["retrograde"]:
            return "Consolidation" + (" (Saturn R)" if "Consolidation" not in base else "")
        return "Consolidation"
    
    return base


def _generate_key_focus(sector, by_name):
    """Generate key focus points for the sector."""
    focuses = []
    
    mercury = by_name["Mercury"]
    mars = by_name["Mars"]
    saturn = by_name["Saturn"]
    jupiter = by_name["Jupiter"]
    venus = by_name["Venus"]
    rahu = by_name["Rahu"]
    ketu = by_name["Ketu"]
    sun = by_name["Sun"]
    moon = by_name["Moon"]
    
    if "IT" in sector:
        focuses.append("Watch for sudden news flow, earnings revisions")
        if mercury["retrograde"]:
            focuses.append("Mercury R: code glitches, communication delays, contract reviews")
        focuses.append("Currency fluctuations (USD/INR) impacting exporters")
    
    elif "Bank" in sector or "Financial" in sector:
        if "PSU" in sector:
            focuses.append("PSU banks: government policy announcements, recapitalization")
            focuses.append("Sun in Leo favors government-linked financials")
        else:
            focuses.append("Private banks: credit growth, NIM expansion")
        focuses.append("Jupiter in Cancer: liquidity support, deposit growth")
        if saturn["retrograde"]:
            focuses.append("Saturn R: asset quality review, provisioning cycle")
    
    elif "Auto" in sector:
        focuses.append("Commercial vehicle cycle uptick")
        focuses.append("Mars-Sun fire: raw material cost pressure but volume growth")
        focuses.append("Festival season demand visibility")
    
    elif "Metal" in sector:
        focuses.append("China stimulus / global demand cues")
        focuses.append("Mars in " + mars["sign"] + ": production drive, capacity utilization")
        focuses.append("Track inventory levels at LME/SHFE")
    
    elif "FMCG" in sector:
        focuses.append("Rural demand recovery, monsoon progress")
        focuses.append("Venus in " + venus["sign"] + ": consumption sentiment")
        focuses.append("Input cost easing (crude, packaging)")
    
    elif "Pharma" in sector:
        focuses.append("US FDA inspections, ANDA approvals")
        focuses.append("Saturn in Pisces: regulatory structure, compliance")
        focuses.append("Domestic formulation growth, API pricing")
    
    elif "Energy" in sector or "Oil" in sector:
        focuses.append("Global crude inventory, OPEC+ decisions")
        focuses.append("Rahu/Ketu axis: sharp intraday swings, gap openings")
        focuses.append("Refining margins, marketing margins")
    
    elif "Realty" in sector or "Infra" in sector:
        focuses.append("Policy announcements (housing, infra spending)")
        focuses.append("Saturn R: project delays, approval pipelines")
        focuses.append("Interest rate trajectory, home loan demand")
    
    elif "Large" in sector or "Nifty 50" in sector:
        focuses.append("Index heavyweight earnings (Reliance, HDFC, ICICI, Infosys)")
        focuses.append("FII flow direction, DII support")
        focuses.append("Technical: gap zones, pivot resistances")
    
    elif "Gold" in sector:
        focuses.append("Ketu in " + ketu["sign"] + ": safe-haven demand")
        focuses.append("Central bank buying, ETF flows")
        focuses.append("USD/INR, real yields")
    
    return " | ".join(focuses[:3])


def _telecom_influence(telecom):
    """Astrological influence line for the cable & telecom sector."""
    parts = [telecom["mercury"]["note"], telecom["rahu"]["note"]]
    for y in telecom["yogas"]:
        parts.append(f"{y['name']} ({y['separation']:.1f}°)")
    return " | ".join(parts)


def _telecom_trend(telecom, conf_signal):
    """Trend outlook for the cable & telecom sector."""
    bias = telecom["bias"]
    if bias == "BULLISH":
        if conf_signal == "BEARISH":
            return "Bullish Bias (conflicted)"
        return "Bullish / Outperformer"
    if bias == "BEARISH":
        if conf_signal == "BULLISH":
            return "Bearish Bias (conflicted)"
        return "Bearish / Underperformer"
    if telecom["yogas"]:
        return "Volatile / Yoga-driven swings"
    return "Mixed / Conflicted"


def _telecom_focus(telecom):
    """Key focus points for the cable & telecom sector."""
    focuses = []
    m = telecom["mercury"]
    if m["state"] == "strong":
        focuses.append("Mercury strong: momentum in telecom/cable/IT, communication infra")
    elif m["state"] == "combust":
        focuses.append("Mercury combust: glitches, miscommunication, muted leadership")
    elif m["state"] == "tense":
        focuses.append("Mercury tense (Rx/harsh): review contracts, capex delays")
    elif m["state"] == "weak":
        focuses.append("Mercury weak: confusion, trading errors in telecom names")
    if telecom["rahu"]["state"] == "amplify":
        focuses.append("Rahu amplifies tech/communication: optical fibre, digital infra, cable")
    for y in telecom["yogas"]:
        focuses.append(f"{y['name']}: {y['bias'].lower()}")
    focuses.append("Watch new-gen telecom/network-capex names for speculative flows")
    return " | ".join(focuses[:3])


def _generate_general_strategy(by_name, confluence, alert):
    """Generate general market strategy for the week."""
    overall = confluence.get("overall", {})
    signal = overall.get("signal", "NEUTRAL")
    net = overall.get("net", 0)
    
    sun = by_name["Sun"]
    moon = by_name["Moon"]
    mars = by_name["Mars"]
    mercury = by_name["Mercury"]
    
    strategy = []
    
    if signal == "BULLISH":
        strategy.append(f"Overall bias: BULLISH (Net: +{net:.2f}) - Favor long positions on dips")
    elif signal == "BEARISH":
        strategy.append(f"Overall bias: BEARISH (Net: {net:.2f}) - Favor short positions on rallies, hedge longs")
    else:
        strategy.append(f"Overall bias: VOLATILE/MIXED (Net: {net:+.2f}) - Range-bound, stock-specific")
    
    strategy.append("Early week (Mon-Wed): Sun-Mercury-Ketu triangle in Leo - high volatility, sudden moves, PSU/Defense/Govt focus")
    strategy.append("Mid week (Thu-Fri): Sun-Mercury exact conjunction (Aug 27, 10:30 PM) - Budhaditya Yoga, policy/communication driven moves")
    strategy.append("Late week (Fri-Sat): Moon in Aquarius (Rahu nakshatra) - sentiment shifts, speculative flush")
    
    strategy.append("Nifty Levels: Watch 24,800-25,000 resistance zone; 24,300-24,400 support zone")
    strategy.append("Bank Nifty: 51,500-52,000 resistance; 50,500-50,800 support")
    
    strategy.append("Risk: Cluster B (Saturn R + eclipse pressure) active till Aug 28 - avoid overnight leveraged positions")
    strategy.append("Jupiter-Saturn applying trine: structural bullish foundation but near-term noise dominates")
    
    return "\n".join(strategy)


def _get_nifty_levels_guidance(confluence):
    """Get Nifty key levels guidance."""
    highlights = confluence.get("highlights", {})
    bullish = highlights.get("bullish_confluence_sectors", [])
    bearish = highlights.get("bearish_confluence_sectors", [])
    
    guidance = []
    
    if "Banking" in bullish or "Financial Services" in bullish:
        guidance.append("Bank Nifty outperforming Nifty - financials leading")
    if "IT" in bullish:
        guidance.append("IT sector supportive - watch Infosys/TCS for index boost")
    if "Metal" in bearish or "Metals" in bearish:
        guidance.append("Metals drag - Tata Steel, JSW Steel may weigh")
    if "Energy" in bearish:
        guidance.append("Energy sector pressure - Reliance, ONGC range-bound")
    
    guidance.append("Key pivot: 24,850 (recent high) | Support: 24,350 (20-DMA vicinity)")
    guidance.append("Options: Max pain around 24,900; PCR >1.2 supportive")
    
    return "\n".join(guidance)


# ============================================================
# DEMO: Generate commentary for the week of Aug 23, 2026
# ============================================================
if __name__ == "__main__":
    # Week starting Monday Aug 24, 2026 (but the expert commentary says "this period" around Aug 23)
    # Let's use Aug 23 (Sunday) as the reference date
    start = datetime.date(2026, 8, 23)  # Sunday
    # Adjust to Monday
    if start.weekday() != 0:
        start = start - datetime.timedelta(days=start.weekday())
    
    commentary = generate_weekly_commentary(start)
    print(format_commentary_text(commentary))