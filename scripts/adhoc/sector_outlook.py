"""
Sector-wise financial astro-trend outlook generator
"""
import sys
sys.path.insert(0, r'D:\SBC_Tool')

from sbc.planets import positions, all_planets_with_natures
from sbc.nakshatra import tithi_of
from sbc.market_calendar import transit_alert
from sbc.prediction import sector_read, planet_sector_read
from sbc.confluence import build_confluence_report
from sbc.chakra import GRID
from sbc.prediction import analyze, compute_vedhas, place_planets, summarize_vedhas
from sbc.market_calendar import _anchor_nakshatra, reversal_alert, lunar_phase_alert, jupiter_market_analysis
from sbc.telecom_confluence import telecom_confluence
import swisseph as swe
import datetime
from zoneinfo import ZoneInfo


def _julian_at_noon(date):
    local = datetime.datetime.combine(date, datetime.time(12, 0), tzinfo=ZoneInfo('Asia/Kolkata'))
    utc = local.astimezone(datetime.timezone.utc)
    return swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute/60.0)


def generate_sector_outlook(date=None):
    """Generate sector-wise financial astro-trend outlook for the week."""
    if date is None:
        date = datetime.date.today()
    
    # Get planetary positions for Monday of the week
    start = date - datetime.timedelta(days=date.weekday())
    planets, tithi, ayanamsa = _get_planet_positions(start)
    
    # Get all analyses
    vedha_map, _ = compute_vedhas(planets, school="classical")
    grid = place_planets(GRID, planets)
    analysis = analyze(planets, vedha_map, _anchor_nakshatra("nse"), school="classical")
    sector_read_data = sector_read(vedha_map, planets)
    planet_sector_read_data = planet_sector_read(planets)
    
    alert = reversal_alert(start.isoformat(), planets, tithi)
    transits = transit_alert(planets)
    lunar = lunar_phase_alert(tithi)
    jupiter_analysis = jupiter_market_analysis(planets)
    
    confluence = build_confluence_report(
        analysis=analysis,
        sector_read=sector_read_data,
        planet_sector_read=planet_sector_read_data,
        reversal_data={"windows": alert.get("windows", []), "upcoming_windows": alert.get("upcoming_windows", [])},
        transits=transits,
        jupiter_analysis=jupiter_analysis,
        lunar_phase=lunar,
    )
    
    # Get planet positions for narrative
    by_name = {p["name"]: p for p in planets}

    # Cable & telecom confluence (Mercury / Rahu / Guru-Chandal / Shrapit)
    telecom = telecom_confluence(planets)

    # Build sector outlook table
    sectors_outlook = _build_sector_outlook(by_name, sector_read_data, planet_sector_read_data, confluence, transits, alert, telecom)
    
    return {
        "week_start": start.isoformat(),
        "week_end": (start + datetime.timedelta(days=6)).isoformat(),
        "ayanamsa": round(ayanamsa, 4),
        "planetary_positions": {name: f"{p['sign']} {p['degree']:.2f}° ({p['nakshatra']}){' ℞' if p['retrograde'] else ''}" 
                                 for name, p in by_name.items()},
        "sectors": sectors_outlook,
        "telecom_confluence": telecom,
        "general_strategy": _generate_general_strategy(by_name, confluence, alert),
        "nifty_levels": _get_nifty_levels_guidance(confluence, by_name),
    }


def _get_planet_positions(date):
    jul = _julian_at_noon(date)
    planets, ayanamsa = positions(jul)
    sun = next(p for p in planets if p["name"] == "Sun")
    moon = next(p for p in planets if p["name"] == "Moon")
    tithi = tithi_of(sun["longitude"], moon["longitude"])
    planets = all_planets_with_natures(planets, tithi, sun["longitude"])
    return planets, tithi, ayanamsa


def _build_sector_outlook(by_name, sector_read_data, planet_sector_read_data, confluence, transits, alert, telecom=None):
    """Build the sector-wise outlook table."""
    
    # Sector mappings for Nifty sectors
    SECTOR_MAPPING = {
         "Nifty IT": ["IT", "IT & Software", "Technology"],
         "Nifty Telecom/Cable": ["Telecom", "Cable & Media", "Communication Infrastructure", "Digital Infrastructure", "Media"],
        "Nifty Bank": ["Banking", "Banks", "PSU Banks", "Private Banks", "Finance & Banking", "Financial Services", "Banking & Management"],
        "Nifty PSU Bank": ["PSU Banks", "PSU", "PSU & Utilities", "Government-linked"],
        "Nifty PSU": ["PSU", "PSU & Utilities", "PSU & Sovereign", "Government-linked"],
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
    
    # Get confluence highlights
    highlights = confluence.get("highlights", {})
    bullish_sectors = set(highlights.get("bullish_confluence_sectors", []))
    bearish_sectors = set(highlights.get("bearish_confluence_sectors", []))
    conflicted_sectors = set(highlights.get("conflicted_sectors", []))
    
    # Get sector confluence scores
    sector_confluence = confluence.get("sector_confluence", {})
    
    # Planet positions for narrative
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
        # Find matching confluence data
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
        
        # Determine astrological influence
        if nifty_sector == "Nifty Telecom/Cable" and telecom:
            influence = _telecom_influence(telecom)
        else:
            influence = _determine_astrological_influence(nifty_sector, by_name, transits, alert)
        
        # Determine trend/outlook
        if nifty_sector == "Nifty Telecom/Cable" and telecom:
            trend = _telecom_trend(telecom, conf_signal)
        else:
            trend = _determine_trend(nifty_sector, conf_signal, bullish_sectors, bearish_sectors, conflicted_sectors, by_name)
        
        # Key focus
        if nifty_sector == "Nifty Telecom/Cable" and telecom:
            focus = _telecom_focus(telecom)
        else:
            focus = _generate_key_focus(nifty_sector, by_name, influence)
        
        outlook.append({
            "sector": nifty_sector,
            "astrological_influence": influence,
            "trend_outlook": trend,
            "key_focus": focus,
            "confluence_score": round(conf_score, 2),
            "confluence_signal": conf_signal,
        })
    
    return outlook


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


def _determine_astrological_influence(sector, by_name, transits, alert):
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
    
    # Sector-specific logic
    if "IT" in sector:
        if mercury["retrograde"]:
            influences.append(f"Mercury Retrograde in {mercury['sign']} ({mercury['nakshatra']})")
        else:
            influences.append(f"Mercury in {mercury['sign']} ({mercury['nakshatra']})")
        if jupiter["sign"] in ("Cancer", "Sagittarius", "Pisces"):
            influences.append(f"Jupiter in {jupiter['sign']} (expansive)")
    
    elif "Bank" in sector or "Financial" in sector:
        influences.append(f"Jupiter in {jupiter['sign']} ({jupiter['nakshatra']}) - banking karaka")
        influences.append(f"Saturn in {saturn['sign']} ({saturn['nakshatra']}){' ℞' if saturn['retrograde'] else ''} - structure")
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

    elif "PSU" in sector:
        influences.append(f"Sun in {sun['sign']} ({sun['nakshatra']}) - sovereign authority")
        influences.append(f"Jupiter in {jupiter['sign']} ({jupiter['nakshatra']}){' ℞' if jupiter['retrograde'] else ''} - PSU expansion")
        if sun["sign"] == "Leo":
            influences.append("Sun in Leo: strong government/PSU authority, policy tailwind")
        if saturn["sign"] in ("Aquarius", "Capricorn"):
            influences.append(f"Saturn in {saturn['sign']} (state structure, regulation)")

    elif "Realty" in sector or "Infra" in sector:
        influences.append(f"Saturn in {saturn['sign']} ({saturn['nakshatra']}){' ℞' if saturn['retrograde'] else ''} - land/structure")
        if jupiter["sign"] in ("Cancer", "Taurus"):
            influences.append(f"Jupiter in {jupiter['sign']} (real estate expansion)")
    
    elif "Large" in sector or "Nifty 50" in sector:
        influences.append(f"Sun in {sun['sign']} - index leadership")
        influences.append(f"Jupiter-Saturn {'trine' if abs((jupiter['longitude'] - saturn['longitude'] + 180) % 360 - 180 - 120) < 8 else 'aspect'}")
    
    elif "Gold" in sector:
        influences.append(f"Ketu in {ketu['sign']} ({ketu['nakshatra']}) - gold/store of value")
        influences.append(f"Sun in {sun['sign']} - sovereign gold")
    
    return " · ".join(influences) if influences else "General planetary climate"


def _determine_trend(sector, conf_signal, bullish_sectors, bearish_sectors, conflicted_sectors, by_name):
    """Determine trend outlook based on confluence and planetary positions."""
    
    # Check if sector is in confluence highlights
    in_bullish = any(s in sector or sector in s for s in bullish_sectors)
    in_bearish = any(s in sector or sector in s for s in bearish_sectors)
    in_conflicted = any(s in sector or sector in s for s in conflicted_sectors)
    
    mercury = by_name["Mercury"]
    mars = by_name["Mars"]
    saturn = by_name["Saturn"]
    jupiter = by_name["Jupiter"]
    sun = by_name["Sun"]
    venus = by_name["Venus"]
    
    # Base on confluence
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
    
    # Add planetary nuance
    if "IT" in sector and mercury["retrograde"]:
        return "Volatile to Cautious" + (" (Mercury Rx)" if "Volatile" not in base else "")
    elif "Bank" in sector and jupiter["sign"] == "Cancer":
        return "Selective Upside" + (" (Exalted Jupiter)" if "Bullish" not in base else "")
    elif "Auto" in sector or "Metal" in sector:
        if mars["sign"] in ("Aries", "Scorpio", "Capricorn") and sun["sign"] == "Leo":
            return "Bullish / Outperformer" + (" (Mars-Sun Fire)" if "Bullish" not in base else "")
    elif "FMCG" in sector or "Pharma" in sector:
        if venus["sign"] in ("Taurus", "Libra", "Pisces"):
            return "Defensive / Stable" + (" (Strong Venus)" if "Defensive" not in base else "")
        return "Defensive / Stable"
    elif "PSU" in sector:
        if sun["sign"] == "Leo":
            return "Bullish / Outperformer" + (" (Sun in Leo, PSU authority)" if "Bullish" not in base else "")
        if jupiter["sign"] in ("Cancer", "Sagittarius", "Pisces"):
            return "Bullish Bias" + (" (Jupiter exalted, PSU expansion)" if "Bullish" not in base else "")
        return base
    elif "Energy" in sector or "Oil" in sector:
        return "High Volatility" + (" (Rahu/Ketu axis)" if "High" not in base else "")
    elif "Realty" in sector or "Infra" in sector:
        if saturn["retrograde"]:
            return "Consolidation" + (" (Saturn Rx)" if "Consolidation" not in base else "")
        return "Consolidation"
    
    return base


def _generate_key_focus(sector, by_name, influence):
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
            focuses.append("Mercury Rx: code glitches, communication delays, contract reviews")
        focuses.append("Currency fluctuations (USD/INR) impacting exporters")
    
    elif "Bank" in sector or "Financial" in sector:
        if "PSU" in sector:
            focuses.append("PSU banks: government policy announcements, recapitalization")
            focuses.append("Sun in Leo favors government-linked financials")
        else:
            focuses.append("Private banks: credit growth, NIM expansion")
        focuses.append("Jupiter in Cancer: liquidity support, deposit growth")
        if saturn["retrograde"]:
            focuses.append("Saturn Rx: asset quality review, provisioning cycle")
    
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
        focuses.append("Saturn Rx: project delays, approval pipelines")
        focuses.append("Interest rate trajectory, home loan demand")
    
    elif "PSU" in sector:
        focuses.append("PSU: government policy announcements, divestment news, budget allocations")
        focuses.append("Sun in " + sun["sign"] + " (" + sun["nakshatra"] + "): sovereign authority favors PSU")
        if sun["sign"] == "Leo":
            focuses.append("Sun in Leo: strong state backing, PSU outperformance likely")
        if jupiter["sign"] in ("Cancer", "Sagittarius", "Pisces"):
            focuses.append("Jupiter in " + jupiter["sign"] + ": PSU expansion, capital infusion")
        if saturn["retrograde"]:
            focuses.append("Saturn Rx: structural reform cycle, PSU consolidation")
        focuses.append("Track: ONGC, IOC, BHEL, NTPC, SJVN, NHPC, PFC, REC")

    elif "Large" in sector or "Nifty 50" in sector:
        focuses.append("Index heavyweight earnings (Reliance, HDFC, ICICI, Infosys)")
        focuses.append("FII flow direction, DII support")
        focuses.append("Technical: gap zones, pivot resistances")
    
    elif "Gold" in sector:
        focuses.append("Ketu in " + ketu["sign"] + ": safe-haven demand")
        focuses.append("Central bank buying, ETF flows")
        focuses.append("USD/INR, real yields")
    
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
    
    # Market bias
    if signal == "BULLISH":
        strategy.append(f"Overall bias: BULLISH (Net: +{net:.2f}) - Favor long positions on dips")
    elif signal == "BEARISH":
        strategy.append(f"Overall bias: BEARISH (Net: {net:.2f}) - Favor short positions on rallies, hedge longs")
    else:
        strategy.append(f"Overall bias: VOLATILE/MIXED (Net: {net:+.2f}) - Range-bound, stock-specific")
    
    # Early vs late week
    strategy.append("Early week (Mon-Wed): Sun-Mercury-Ketu triangle in Leo - high volatility, sudden moves, PSU/Defense/Govt focus")
    strategy.append("Mid week (Thu-Fri): Sun-Mercury exact conjunction (Aug 27, 10:30 PM) - Budhaditya Yoga, policy/communication driven moves")
    strategy.append("Late week (Fri-Sat): Moon in Aquarius (Rahu nakshatra) - sentiment shifts, speculative flush")
    
    # Key levels
    strategy.append("Nifty Levels: Watch 24,800-25,000 resistance zone; 24,300-24,400 support zone")
    strategy.append("Bank Nifty: 51,500-52,000 resistance; 50,500-50,800 support")
    
    # Risk management
    strategy.append("Risk: Cluster B (Saturn Rx + eclipse pressure) active till Aug 28 - avoid overnight leveraged positions")
    strategy.append("Jupiter-Saturn applying trine: structural bullish foundation but near-term noise dominates")
    
    return "\n".join(strategy)


def _get_nifty_levels_guidance(confluence, by_name):
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


# Test
def _clean(s):
    return s.replace('\u211e', ' R').replace('\u26aa', '[ ]')

if __name__ == "__main__":
    outlook = generate_sector_outlook(datetime.date(2026, 8, 24))
    print(f"Week: {outlook['week_start']} to {outlook['week_end']}")
    print(f"Ayanamsa: {_clean(str(outlook['ayanamsa']))}°")
    print("\nPlanetary Positions:")
    for k, v in outlook['planetary_positions'].items():
        print(f"  {k}: {_clean(v)}")
    
    print("\n" + "="*100)
    print(f"{'SECTOR':<20} {'ASTROLOGICAL INFLUENCE':<50} {'TREND/OUTLOOK':<25} {'KEY FOCUS'}")
    print("="*100)
    for s in outlook['sectors']:
        print(f"{_clean(s['sector']):<20} {_clean(s['astrological_influence'])[:48]:<50} {_clean(s['trend_outlook'])[:23]:<25} {_clean(s['key_focus'])[:60]}")
    
    print("\n" + "="*100)
    print("CABLE & TELECOM CONFLUENCE (Mercury / Rahu / yogas):")
    from sbc.telecom_confluence import format_telecom_confluence
    for line in format_telecom_confluence(outlook.get('telecom_confluence')):
        print(_clean("  " + line))

    print("\n" + "="*100)
    print("GENERAL MARKET STRATEGY:")
    print(_clean(outlook['general_strategy']))
    print("\nNIFTY LEVELS:")
    print(_clean(outlook['nifty_levels']))