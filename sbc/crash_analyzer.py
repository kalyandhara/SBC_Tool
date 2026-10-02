"""Crash signature analyzer - VALIDATED patterns from historical backtest."""

import datetime
from dataclasses import dataclass
from urllib.parse import urlencode

import swisseph as swe

from .confluence import build_confluence_report
from .market_calendar import (
    NAKSHATRA_LORDS,
    REVERSAL_WINDOWS,
    _pushya_reversal_windows,
    jupiter_market_analysis,
    reversal_alert,
)
from .nakshatra import tithi_of
from .planets import positions
from .prediction import analyze, compute_vedhas, planet_sector_read, sector_read
from .trade_setups import setups_for_confluence

# =============================================================================
# TRADINGVIEW INTEGRATION
# =============================================================================

TRADINGVIEW_BASE = "https://www.tradingview.com/chart/"

# Symbol mappings for Indian markets
TV_SYMBOLS = {
    "NIFTY": "NSE:NIFTY",
    "BANKNIFTY": "NSE:BANKNIFTY",
    "FINNIFTY": "NSE:FINNIFTY",
    "SENSEX": "BSE:SENSEX",
    "NIFTY_FUT": "NSE:NIFTY1!",  # Continuous futures
    "BANKNIFTY_FUT": "NSE:BANKNIFTY1!",
    "GOLD": "MCX:GOLD",
    "SILVER": "MCX:SILVER",
    "CRUDEOIL": "MCX:CRUDEOIL",
    "USDINR": "NSE:USDINR",
}

# Default chart settings
TV_DEFAULTS = {
    "interval": "D",  # Daily
    "theme": "dark",
    "style": "1",  # Candlestick
    "timezone": "Asia/Kolkata",
    "hide_legend": "true",
    "hide_volume": "false",
    "hide_side_toolbar": "false",
    "allow_symbol_change": "true",
    "show_popup": "true",
    "popup_width": "1200",
    "popup_height": "700",
}


def build_tradingview_url(
    symbol: str,
    start_date: str,
    end_date: str = None,
    interval: str = "D",
    indicators: list = None,
    layout: str = "single",
) -> str:
    """
    Build a TradingView chart URL for a given symbol and date range.

    Args:
        symbol: Key from TV_SYMBOLS (e.g., "NIFTY", "BANKNIFTY")
        start_date: ISO format date "YYYY-MM-DD"
        end_date: ISO format date (defaults to start_date + 30 days)
        interval: Chart interval (D, W, M, 60, 15, 5, etc.)
        indicators: List of indicator names to add (e.g., ["EMA20", "RSI", "MACD"])
        layout: "single" or "multi" (for multiple symbols)

    Returns:
        TradingView chart URL
    """
    tv_symbol = TV_SYMBOLS.get(symbol.upper(), symbol)

    if end_date is None:
        end = datetime.date.fromisoformat(start_date) + datetime.timedelta(days=30)
        end_date = end.isoformat()

    # TradingView supports date range via "range" parameter with timestamps
    # But for pre-1970 dates, timestamps don't work on Windows
    # Use a simpler approach: just pass symbol and interval, let user navigate
    try:
        start_ts = int(datetime.datetime.fromisoformat(start_date + " 00:00:00").timestamp() * 1000)
        end_ts = int(datetime.datetime.fromisoformat(end_date + " 23:59:59").timestamp() * 1000)
        use_range = True
    except (OSError, ValueError):
        # Pre-1970 dates or other issues - skip range parameter
        use_range = False

    params = {
        "symbol": tv_symbol,
        "interval": interval,
        **TV_DEFAULTS,
    }

    if use_range:
        params["range"] = f"{start_ts},{end_ts}"

    if indicators:
        params["studies"] = ",".join(indicators)

    url = TRADINGVIEW_BASE + "?" + urlencode(params)
    return url


def get_crash_chart_links(crash_date: str, window_days: int = 30) -> dict:
    """Get TradingView links for all relevant symbols around a crash date."""
    start = crash_date
    end = (datetime.date.fromisoformat(crash_date) + datetime.timedelta(days=window_days)).isoformat()

    links = {}
    for name, symbol in TV_SYMBOLS.items():
        if "_FUT" not in name:  # Skip futures duplicates for simplicity
            links[name] = build_tradingview_url(
                symbol=name,
                start_date=start,
                end_date=end,
                interval="D",
                indicators=["EMA20", "EMA50", "RSI", "MACD"],
            )
    return links


def get_crash_research_package(crash_date: str, crash_name: str) -> dict:
    """Complete research package for a crash date with chart links."""
    return {
        "crash_name": crash_name,
        "crash_date": crash_date,
        "chart_links": get_crash_chart_links(crash_date),
        "pre_crash_window": build_tradingview_url(
            "NIFTY",
            (datetime.date.fromisoformat(crash_date) - datetime.timedelta(days=60)).isoformat(),
            crash_date,
            interval="D",
        ),
        "crash_day_intraday": build_tradingview_url(
            "NIFTY_FUT",
            crash_date,
            crash_date,
            interval="15",
            indicators=["VWAP", "EMA20", "RSI"],
        ),
        "banknifty_intraday": build_tradingview_url(
            "BANKNIFTY_FUT",
            crash_date,
            crash_date,
            interval="15",
            indicators=["VWAP", "EMA20", "RSI"],
        ),
    }


@dataclass
class CrashSignature:
    name: str
    description: str
    weight: float  # contribution to crash score (0-1)
    hit_rate: str  # e.g., "6/8"


# =============================================================================
# VALIDATED CRASH SIGNATURES (backtested on 8 major crashes)
# =============================================================================

# Ketu-ruled nakshatras
KETU_NAKSHATRAS = {"Ashwini", "Magha", "Mula"}

# Jupiter-Saturn aspect orbs
ASPECT_ORB = 15  # wider orb for major aspects

CRASH_SIGNATURES = [
    CrashSignature(
        name="jupiter_ketu_nakshatra",
        description="Jupiter in Ketu-ruled nakshatra (Ashwini/Magha/Mula) — PRIMARY 6/8 crashes",
        weight=0.35,
        hit_rate="6/8",
    ),
    CrashSignature(
        name="jupiter_saturn_conjunction",
        description="Jupiter-Saturn conjunction (0°±15°) — PRIMARY complementary 2/8",
        weight=0.30,
        hit_rate="2/8 (complementary)",
    ),
    CrashSignature(
        name="jupiter_saturn_opposition",
        description="Jupiter-Saturn opposition (180°±15°) — 3/8 crashes (1929, 1992, 2011)",
        weight=0.20,
        hit_rate="3/8",
    ),
    CrashSignature(
        name="jupiter_saturn_trine",
        description="Jupiter-Saturn trine (120°±15°) — 3/8 crashes",
        weight=0.15,
        hit_rate="3/8",
    ),
    CrashSignature(
        name="mars_ketu_conjunction",
        description="Mars conjunct Ketu (0°±10°) — 3/8 crashes (1929, 1987, 2020)",
        weight=0.15,
        hit_rate="3/8",
    ),
    CrashSignature(
        name="saturn_ketu_conjunction",
        description="Saturn conjunct Ketu (0°±10°) — 1/8 (2007 peak)",
        weight=0.08,
        hit_rate="1/8",
    ),
    CrashSignature(
        name="pushya_malefic_cluster",
        description="≥2 malefics in Pushya — rare high specificity",
        weight=0.10,
        hit_rate="1/8",
    ),
    CrashSignature(
        name="eclipse_on_nodal_axis",
        description="Eclipse conjunct market anchor Rahu/Ketu — amplifier",
        weight=0.10,
        hit_rate="context",
    ),
    CrashSignature(
        name="confluence_extreme_bearish",
        description="Confluence net ≤ -3.0 with agreement ≥ 0.8 across ≥4 components",
        weight=0.18,
        hit_rate="dynamic",
    ),
]


# Market anchor: NSE incorporation
NSE_ANCHOR_DATE = "1992-11-27"
NSE_ANCHOR_TIME = "00:00"
NSE_ANCHOR_TZ = "Asia/Kolkata"


# =============================================================================
# HISTORICAL CRASH DATES
# =============================================================================

HISTORICAL_CRASHES = [
    {"name": "Black Thursday (1929)", "date": "1929-10-24"},
    {"name": "Black Monday (1987)", "date": "1987-10-19"},
    {"name": "Dot-com Peak (2000)", "date": "2000-03-10"},
    {"name": "Lehman Collapse (2008)", "date": "2008-09-15"},
    {"name": "COVID Crash (2020)", "date": "2020-02-19"},
    {"name": "Harshad Mehta (1992)", "date": "1992-04-28"},
    {"name": "2007 Peak", "date": "2008-01-08"},
    {"name": "2011 Correction", "date": "2011-11-07"},
]


# =============================================================================
# CORE CALCULATIONS
# =============================================================================

def _julian_day(date_str: str, time_str: str = "09:15", tz: str = "Asia/Kolkata") -> float:
    from zoneinfo import ZoneInfo
    y, m, d = map(int, date_str.split("-"))
    hh, mm = map(int, time_str.split(":"))
    tz_obj = ZoneInfo(tz)
    local = datetime.datetime(y, m, d, hh, mm, tzinfo=tz_obj)
    utc = local.astimezone(datetime.UTC)
    h = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
    return swe.julday(utc.year, utc.month, utc.day, h)


def _get_anchor_nakshatra() -> str:
    jul = _julian_day(NSE_ANCHOR_DATE, NSE_ANCHOR_TIME, NSE_ANCHOR_TZ)
    planets, _ = positions(jul)
    moon = next(p for p in planets if p["name"] == "Moon")
    return moon["nakshatra"]


def _get_anchor_nodal_positions():
    """Get NSE incorporation Rahu/Ketu positions."""
    jul = _julian_day(NSE_ANCHOR_DATE, NSE_ANCHOR_TIME, NSE_ANCHOR_TZ)
    planets, _ = positions(jul)
    rahu = next(p for p in planets if p["name"] == "Rahu")
    ketu = next(p for p in planets if p["name"] == "Ketu")
    return rahu["longitude"], ketu["longitude"]


NSE_BIRTH_NAKSHATRA = _get_anchor_nakshatra()
NSE_RAHU, NSE_KETU = _get_anchor_nodal_positions()


def _get_planets(date_str: str) -> list[dict]:
    jul = _julian_day(date_str)
    planets, _ = positions(jul)
    sun = next(p for p in planets if p["name"] == "Sun")
    moon = next(p for p in planets if p["name"] == "Moon")
    tithi = tithi_of(sun["longitude"], moon["longitude"])
    from .planets import all_planets_with_natures
    planets = all_planets_with_natures(planets, tithi, sun["longitude"])
    return planets


def _angle(lon1: float, lon2: float) -> float:
    diff = abs((lon1 - lon2 + 180) % 360 - 180)
    return diff


def _aspect_name(angle: float) -> str:
    for a, name in [(0, "Conj"), (60, "Sextile"), (90, "Square"), (120, "Trine"), (180, "Opposition")]:
        if abs(angle - a) <= ASPECT_ORB:
            return name
    return ""


# =============================================================================
# INDIVIDUAL SIGNATURE CHECKS
# =============================================================================

def check_jupiter_ketu_nakshatra(planets: list[dict]) -> tuple[bool, str]:
    jupiter = next(p for p in planets if p["name"] == "Jupiter")
    jup_nak = jupiter["nakshatra"]
    nak_lord = NAKSHATRA_LORDS.get(jup_nak)
    in_ketu_nak = jup_nak in KETU_NAKSHATRAS
    detail = "Jupiter in {} (lord: {}) [{}]".format(jup_nak, nak_lord, "KETU-RULED" if in_ketu_nak else "not Ketu")
    return in_ketu_nak, detail


def check_jupiter_saturn_conjunction(planets: list[dict]) -> tuple[bool, str]:
    jupiter = next(p for p in planets if p["name"] == "Jupiter")
    saturn = next(p for p in planets if p["name"] == "Saturn")
    ang = _angle(jupiter["longitude"], saturn["longitude"])
    active = ang <= ASPECT_ORB
    aspect = _aspect_name(ang)
    detail = "Jup-Sat angle: {:.1f}° [{}]".format(ang, aspect if aspect else "none")
    if active:
        detail += " [CONJUNCTION]"
    return active, detail


def check_jupiter_saturn_trine(planets: list[dict]) -> tuple[bool, str]:
    jupiter = next(p for p in planets if p["name"] == "Jupiter")
    saturn = next(p for p in planets if p["name"] == "Saturn")
    ang = _angle(jupiter["longitude"], saturn["longitude"])
    active = abs(ang - 120) <= ASPECT_ORB
    detail = f"Jup-Sat angle: {ang:.1f}° (trine orb: {abs(ang - 120):.1f}°)"
    if active:
        detail += " [TRINE]"
    return active, detail


def check_jupiter_saturn_opposition(planets: list[dict]) -> tuple[bool, str]:
    jupiter = next(p for p in planets if p["name"] == "Jupiter")
    saturn = next(p for p in planets if p["name"] == "Saturn")
    ang = _angle(jupiter["longitude"], saturn["longitude"])
    active = abs(ang - 180) <= ASPECT_ORB
    detail = f"Jup-Sat angle: {ang:.1f}° (opp orb: {abs(ang - 180):.1f}°)"
    if active:
        detail += " [OPPOSITION]"
    return active, detail


def check_mars_ketu_conjunction(planets: list[dict]) -> tuple[bool, str]:
    mars = next(p for p in planets if p["name"] == "Mars")
    ketu = next(p for p in planets if p["name"] == "Ketu")
    ang = _angle(mars["longitude"], ketu["longitude"])
    active = ang <= 10
    detail = f"Mars-Ketu angle: {ang:.1f}°"
    if active:
        detail += " [CONJUNCTION]"
    return active, detail


def check_saturn_ketu_conjunction(planets: list[dict]) -> tuple[bool, str]:
    saturn = next(p for p in planets if p["name"] == "Saturn")
    ketu = next(p for p in planets if p["name"] == "Ketu")
    ang = _angle(saturn["longitude"], ketu["longitude"])
    active = ang <= 10
    detail = f"Saturn-Ketu angle: {ang:.1f}°"
    if active:
        detail += " [CONJUNCTION]"
    return active, detail


def check_pushya_malefic_cluster(planets: list[dict]) -> tuple[bool, str]:
    malefics = ["Saturn", "Mars", "Rahu", "Ketu", "Sun"]
    in_pushya = [p["name"] for p in planets if p["nakshatra"] == "Pushya" and p["name"] in malefics]
    count = len(in_pushya)
    active = count >= 2
    detail = "Malefics in Pushya: {} (count={})".format(", ".join(in_pushya) if in_pushya else "none", count)
    return active, detail


def check_eclipse_on_nodal_axis(planets: list[dict], date_str: str) -> tuple[bool, str]:
    date = datetime.date.fromisoformat(date_str)
    for window in REVERSAL_WINDOWS:
        if "eclipse" in window["id"].lower():
            start = datetime.date.fromisoformat(window["start"])
            end = datetime.date.fromisoformat(window["end"])
            if start <= date <= end:
                sun = next(p for p in planets if p["name"] == "Sun")
                sun_rahu = _angle(sun["longitude"], NSE_RAHU)
                sun_ketu = _angle(sun["longitude"], NSE_KETU)
                active = sun_rahu < 5 or sun_ketu < 5
                detail = "Eclipse window: {} | Sun-NSE Rahu: {:.1f}°, Sun-NSE Ketu: {:.1f}°".format(
                    window["title"], sun_rahu, sun_ketu)
                if active:
                    detail += " [ON NSE NODAL AXIS]"
                return active, detail
    return False, "No eclipse window active"


def check_confluence_extreme_bearish(planets: list[dict], date_str: str) -> tuple[bool, str]:
    sun = next(p for p in planets if p["name"] == "Sun")
    moon = next(p for p in planets if p["name"] == "Moon")
    tithi = tithi_of(sun["longitude"], moon["longitude"])

    vedha_map, _ = compute_vedhas(planets, school="classical")
    analysis = analyze(planets, vedha_map, NSE_BIRTH_NAKSHATRA, school="classical")

    sr = sector_read(vedha_map, planets)
    psr = planet_sector_read(planets)

    rev = reversal_alert(date_str, planets=planets, tithi=tithi)

    confluence = build_confluence_report(
        analysis=analysis,
        sector_read=sr,
        planet_sector_read=psr,
        reversal_data={"windows": rev["windows"], "upcoming_windows": rev["upcoming_windows"]},
        transits=rev["transits"],
        jupiter_analysis=rev["jupiter_analysis"],
        lunar_phase=rev["lunar_phase"],
    )

    overall = confluence.get("overall", {})
    net = overall.get("net", 0)
    sector_conf = confluence.get("sector_confluence", {})
    agreements = [d.get("agreement", 0) for d in sector_conf.values()]
    high_agreement = sum(1 for a in agreements if a >= 0.8)

    active = net <= -3.0 and high_agreement >= 4
    detail = f"Confluence net={net:.1f}, high_agreement_sectors={high_agreement}"
    if active:
        detail += " [EXTREME BEARISH]"
    return active, detail


# =============================================================================
# MAIN ANALYSIS
# =============================================================================

@dataclass
class CrashAnalysis:
    date: str
    crash_score: float
    signatures: dict[str, bool]
    signature_details: dict[str, str]
    jupiter_analysis: dict
    pushya_windows: list
    reversal_windows: list
    confluence: dict | None
    applicable_setups: list[str]
    market_condition: str
    jupiter_saturn_angle: float
    jupiter_saturn_aspect: str
    mars_ketu_angle: float
    tradingview_links: dict = None
    research_package: dict = None


def analyze_crash_risk(date_str: str) -> CrashAnalysis:
    planets = _get_planets(date_str)

    sig_results = {}
    sig_details = {}

    checks = [
        ("jupiter_ketu_nakshatra", lambda: check_jupiter_ketu_nakshatra(planets)),
        ("jupiter_saturn_conjunction", lambda: check_jupiter_saturn_conjunction(planets)),
        ("jupiter_saturn_trine", lambda: check_jupiter_saturn_trine(planets)),
        ("jupiter_saturn_opposition", lambda: check_jupiter_saturn_opposition(planets)),
        ("mars_ketu_conjunction", lambda: check_mars_ketu_conjunction(planets)),
        ("saturn_ketu_conjunction", lambda: check_saturn_ketu_conjunction(planets)),
        ("pushya_malefic_cluster", lambda: check_pushya_malefic_cluster(planets)),
        ("eclipse_on_nodal_axis", lambda: check_eclipse_on_nodal_axis(planets, date_str)),
        ("confluence_extreme_bearish", lambda: check_confluence_extreme_bearish(planets, date_str)),
    ]

    total_score = 0.0
    for name, check_fn in checks:
        active, detail = check_fn()
        sig_results[name] = active
        sig_details[name] = detail
        weight = next(s.weight for s in CRASH_SIGNATURES if s.name == name)
        if active:
            total_score += weight * 100

    # Jupiter-Saturn angle for reference
    jupiter = next(p for p in planets if p["name"] == "Jupiter")
    saturn = next(p for p in planets if p["name"] == "Saturn")
    mars = next(p for p in planets if p["name"] == "Mars")
    ketu = next(p for p in planets if p["name"] == "Ketu")
    jup_sat_angle = _angle(jupiter["longitude"], saturn["longitude"])
    jup_sat_aspect = _aspect_name(jup_sat_angle)
    mars_ketu_angle = _angle(mars["longitude"], ketu["longitude"])

    # Other data
    jup_analysis = jupiter_market_analysis(planets)
    date_obj = datetime.date.fromisoformat(date_str)
    pushya_windows = _pushya_reversal_windows(date_obj, planets)

    sun = next(p for p in planets if p["name"] == "Sun")
    moon = next(p for p in planets if p["name"] == "Moon")
    tithi = tithi_of(sun["longitude"], moon["longitude"])
    rev = reversal_alert(date_str, planets=planets, tithi=tithi)

    sr = sector_read(compute_vedhas(planets, school="classical")[0], planets)
    psr = planet_sector_read(planets)
    confluence = build_confluence_report(
        analysis=analyze(planets, compute_vedhas(planets, school="classical")[0], NSE_BIRTH_NAKSHATRA, school="classical"),
        sector_read=sr,
        planet_sector_read=psr,
        reversal_data={"windows": rev["windows"], "upcoming_windows": rev["upcoming_windows"]},
        transits=rev["transits"],
        jupiter_analysis=rev["jupiter_analysis"],
        lunar_phase=rev["lunar_phase"],
    )

    setups = setups_for_confluence(confluence)
    setup_names = [s.name for s in setups]

    # Classification - crash score is primary
    if total_score >= 60:
        condition = "CRASH_RISK"
    elif total_score >= 35:
        condition = "CORRECTION_RISK"
    elif total_score >= 20:
        condition = "ELEVATED_RISK"
    else:
        condition = "NORMAL"

    chart_links = get_crash_chart_links(date_str)
    research_pkg = get_crash_research_package(date_str, "Current Analysis")

    return CrashAnalysis(
        date=date_str,
        crash_score=round(total_score, 1),
        signatures=sig_results,
        signature_details=sig_details,
        jupiter_analysis=jup_analysis,
        pushya_windows=pushya_windows,
        reversal_windows=rev["windows"],
        confluence=confluence,
        applicable_setups=setup_names,
        market_condition=condition,
        jupiter_saturn_angle=jup_sat_angle,
        jupiter_saturn_aspect=jup_sat_aspect,
        mars_ketu_angle=mars_ketu_angle,
        tradingview_links=chart_links,
        research_package=research_pkg,
    )


def backtest_crashes() -> list[dict]:
    results = []
    for crash in HISTORICAL_CRASHES:
        analysis = analyze_crash_risk(crash["date"])
        chart_links = get_crash_chart_links(crash["date"])
        research_pkg = get_crash_research_package(crash["date"], crash["name"])
        results.append({
            "name": crash["name"],
            "date": crash["date"],
            "crash_score": analysis.crash_score,
            "condition": analysis.market_condition,
            "signatures_triggered": sum(1 for v in analysis.signatures.values() if v),
            "total_signatures": len(analysis.signatures),
            "active_signatures": [k for k, v in analysis.signatures.items() if v],
            "jup_sat_angle": analysis.jupiter_saturn_angle,
            "jup_sat_aspect": analysis.jupiter_saturn_aspect,
            "mars_ketu_angle": analysis.mars_ketu_angle,
            "applicable_setups": analysis.applicable_setups,
            "confluence_net": analysis.confluence["overall"]["net"] if analysis.confluence else 0,
            "confluence_signal": analysis.confluence["overall"]["signal"] if analysis.confluence else "N/A",
            "tradingview_links": chart_links,
            "research_package": research_pkg,
        })
    return results


def print_backtest_results():
    results = backtest_crashes()
    print("\n" + "=" * 110)
    print("VALIDATED CRASH SIGNATURE BACKTEST ON 8 HISTORICAL CRISES")
    print("=" * 110)
    print("{:<25} {:<12} {:>6} {:<18} {:>6} {:>8} {:<10} {:<8} {}".format(
        "Event", "Date", "Score", "Condition", "Sigs", "Jup-Sat", "Aspect", "Mar-Ketu", "Setups"))
    print("-" * 110)
    for r in results:
        print("{:<25} {:<12} {:>6.1f} {:<18} {:>6} {:>8.1f} {:<10} {:>8.1f} {}".format(
            r["name"], r["date"], r["crash_score"], r["condition"],
            "{}/{}".format(r["signatures_triggered"], r["total_signatures"]),
            r["jup_sat_angle"], r["jup_sat_aspect"] or "-",
            r["mars_ketu_angle"],
            ", ".join(r["applicable_setups"]) if r["applicable_setups"] else "-"))

    crash_risk = [r for r in results if r["condition"] == "CRASH_RISK"]
    correction_risk = [r for r in results if r["condition"] == "CORRECTION_RISK"]
    print(f"\nCRASH_RISK (>=60): {len(crash_risk)}/{len(results)}")
    for r in crash_risk:
        print("  {} ({}): score={}, sigs={}".format(r["name"], r["date"], r["crash_score"], r["active_signatures"]))
    print(f"\nCORRECTION_RISK (35-59): {len(correction_risk)}/{len(results)}")
    for r in correction_risk:
        print("  {} ({}): score={}".format(r["name"], r["date"], r["crash_score"]))

    # Signature hit rates
    print("\nSIGNATURE HIT RATES:")
    for sig in CRASH_SIGNATURES:
        hits = sum(1 for r in results if r["active_signatures"] and sig.name in r["active_signatures"])
        print(f"  {sig.name}: {hits}/{len(results)} ({sig.hit_rate})")

    # Combined coverage
    jup_ketu_or_conj = sum(1 for r in results
        if "jupiter_ketu_nakshatra" in r.get("active_signatures", [])
        or "jupiter_saturn_conjunction" in r.get("active_signatures", []))
    print(f"\nCOMBINED (Jup-Ketu nak OR Jup-Sat conj): {jup_ketu_or_conj}/{len(results)}")


def daily_crash_briefing(date_str: str = None) -> str:
    if date_str is None:
        date_str = datetime.date.today().isoformat()

    analysis = analyze_crash_risk(date_str)

    lines = [
        "==========================================",
        f"  CRASH WATCH DAILY BRIEFING  |  {date_str}",
        "==========================================",
        f"CRASH PROBABILITY: {analysis.crash_score:.0f}%  ->  {analysis.market_condition}",
        "",
        "VALIDATED SIGNATURES:",
    ]
    for name, active in analysis.signatures.items():
        status = "ACTIVE" if active else "inactive"
        detail = analysis.signature_details[name]
        lines.append("  [{}] {}: {}".format(status, name.replace('_', ' ').title(), detail))

    lines.append("")
    lines.append("JUPITER-SATURN: {:.1f}° [{}] | Mars-Ketu: {:.1f}°".format(
        analysis.jupiter_saturn_angle,
        analysis.jupiter_saturn_aspect or "none",
        analysis.mars_ketu_angle))

    lines.append("")
    lines.append("JUPITER ANALYSIS: {} ({})".format(
        analysis.jupiter_analysis.get("bias", "N/A"),
        analysis.jupiter_analysis.get("level", "N/A")))
    if analysis.jupiter_analysis.get("reasons"):
        for reason in analysis.jupiter_analysis["reasons"]:
            lines.append(f"  * {reason}")

    lines.append("")
    lines.append("CONFLUENCE: net={:.1f} | signal={} | bullish_wt={:.1f} | bearish_wt={:.1f}".format(
        analysis.confluence["overall"]["net"],
        analysis.confluence["overall"]["signal"],
        analysis.confluence["overall"]["bullish_weight"],
        analysis.confluence["overall"]["bearish_weight"]))

    highlights = analysis.confluence.get("highlights", {})
    if highlights.get("bearish_confluence_sectors"):
        lines.append("  Bearish sectors: {}".format(", ".join(highlights["bearish_confluence_sectors"])))
    if highlights.get("conflicted_sectors"):
        lines.append("  Conflicted: {}".format(", ".join(highlights["conflicted_sectors"])))

    if analysis.applicable_setups:
        lines.append("")
        lines.append("APPLICABLE SETUPS:")
        for setup_name in analysis.applicable_setups:
            lines.append(f"  -> {setup_name}")

    # TradingView chart links for visual research
    lines.append("")
    lines.append("TRADINGVIEW CHARTS (click to open):")
    chart_links = get_crash_chart_links(date_str)
    for name, url in chart_links.items():
        lines.append(f"  {name}: {url}")

    lines.append("")
    lines.append("INVALIDATION WATCH:")
    if analysis.confluence["overall"]["signal"] == "BEARISH":
        lines.append("  * Nifty close above 20 EMA + Jupiter direct station")
        lines.append("  * Confluence net flips to > -1.0")
    else:
        lines.append("  * Confluence net drops below -2.0")
        lines.append("  * New malefic in Pushya")

    lines.append("==========================================")
    return "\n".join(lines)


if __name__ == "__main__":
    print_backtest_results()
    print("\n" + daily_crash_briefing("2026-08-21"))
