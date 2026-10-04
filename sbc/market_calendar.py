"""Research-only market reversal windows from the 2026-2027 calendar."""

import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import swisseph as swe

from .confluence import build_confluence_report
from .nakshatra import tithi_of
from .planets import all_planets_with_natures, positions
from .prediction import (
    analyze,
    compute_vedhas,
    planet_sector_read,
    sector_read,
)

ANCHORS = {
    "nse": {"date": "1992-11-27", "time": "00:00", "tz": "Asia/Kolkata"},
    "bse": {"date": "1875-07-09", "time": "00:00", "tz": "Asia/Kolkata"},
    "nifty": {"date": "1995-11-03", "time": "00:00", "tz": "Asia/Kolkata"},
    "sensex": {"date": "1979-04-01", "time": "00:00", "tz": "Asia/Kolkata"},
    "india": {"date": "1947-08-15", "time": "00:00", "tz": "Asia/Kolkata"},
}

_anchor_cache: dict[str, str] = {}


def _utc_from_local(date_str, time_str, tz_name):
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("Asia/Kolkata")
    y, m, d = (int(x) for x in date_str.split("-"))
    hh, mm = (int(x) for x in time_str.split(":"))
    local = datetime.datetime(y, m, d, hh, mm, tzinfo=tz)
    return local.astimezone(datetime.UTC).replace(tzinfo=None)


def _julday(utc_dt):
    h = utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
    return swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, h)


def _anchor_nakshatra(anchor_key):
    if anchor_key in _anchor_cache:
        return _anchor_cache[anchor_key]
    info = ANCHORS[anchor_key]
    utc = _utc_from_local(info["date"], info["time"], info["tz"])
    jul = _julday(utc)
    planets, _ = positions(jul)
    moon = next(p for p in planets if p["name"] == "Moon")
    _anchor_cache[anchor_key] = moon["nakshatra"]
    return _anchor_cache[anchor_key]


REVERSAL_WINDOWS: list[dict[str, Any]] = [
    {
        "id": "cluster-a-2026",
        "start": "2026-02-17",
        "end": "2026-04-13",
        "title": "Cluster A: eclipse, Mercury retrograde and Saturn combustion",
        "level": "VERY HIGH",
        "bias": "BEARISH",
        "sectors": ["Banking", "PSU Banks", "Gold/MCX", "Metals"],
    },
    {
        "id": "cluster-b-2026",
        "start": "2026-07-26",
        "end": "2026-08-28",
        "title": "Cluster B: Saturn retrograde and double-eclipse pressure",
        "level": "EXTREME",
        "bias": "STRONGLY BEARISH",
        "sectors": ["Nifty 50", "Nifty Bank", "Real Estate", "FMCG"],
    },
    {
        "id": "cluster-c-2026",
        "start": "2026-10-03",
        "end": "2026-11-29",
        "title": "Cluster C: Venus and Mercury retrograde overlap",
        "level": "HIGH",
        "bias": "BEARISH -> BULLISH REVERSAL",
        "sectors": ["Banking", "Gold/MCX", "FMCG", "Auto"],
    },
    {
        "id": "cluster-d-2026",
        "start": "2026-12-05",
        "end": "2026-12-15",
        "title": "Cluster D: nodal shift, Saturn direct and Jupiter retrograde",
        "level": "HIGH",
        "bias": "VOLATILE / UNCLEAR",
        "sectors": ["All sectors"],
    },
    {
        "id": "cluster-e-2027",
        "start": "2027-01-10",
        "end": "2027-04-12",
        "title": "Cluster E: Mars retrograde, eclipses and Mercury retrograde",
        "level": "HIGH",
        "bias": "EXTENDED BEARISH",
        "sectors": ["Metals", "Energy", "Pharma", "IT", "Large Caps"],
    },
    {
        "id": "cluster-f-2027",
        "start": "2027-06-03",
        "end": "2027-08-17",
        "title": "Cluster F: Saturn enters Aries and eclipse pressure",
        "level": "EXTREME",
        "bias": "CRITICALLY BEARISH",
        "sectors": ["Nifty Bank", "Real Estate", "FMCG", "Large Caps", "PSU"],
    },
    {
        "id": "eclipse-2026-02-17",
        "start": "2026-02-14",
        "end": "2026-02-20",
        "title": "Annular solar eclipse watch window",
        "level": "MODERATE-HIGH",
        "bias": "BEARISH TRIGGER",
        "sectors": ["IT", "Pharma", "PSU Banks"],
    },
    {
        "id": "eclipse-2026-03-03",
        "start": "2026-02-28",
        "end": "2026-03-06",
        "title": "Total lunar eclipse watch window",
        "level": "HIGH",
        "bias": "BEARISH",
        "sectors": ["Gold/MCX", "PSU Banks", "Metals"],
    },
    {
        "id": "eclipse-2026-08-12",
        "start": "2026-08-09",
        "end": "2026-08-16",
        "title": "Total solar eclipse watch window",
        "level": "VERY HIGH",
        "bias": "CRITICAL BEARISH",
        "sectors": ["Nifty Bank", "Nifty 50", "Real Estate", "Large Caps"],
    },
    {
        "id": "double-direct-2026-11-13",
        "start": "2026-11-11",
        "end": "2026-11-15",
        "title": "Mercury and Venus direct-station watch window",
        "level": "HIGH",
        "bias": "BULLISH REVERSAL",
        "sectors": ["Banking", "Gold/MCX", "Auto", "FMCG"],
    },
    {
        "id": "eclipse-2027-08-02",
        "start": "2027-07-30",
        "end": "2027-08-06",
        "title": "Total solar eclipse conjunct Ketu watch window",
        "level": "CRITICAL",
        "bias": "CRITICAL BEARISH",
        "sectors": ["Nifty Bank", "FMCG", "Real Estate", "Large Caps"],
    },
]

TRANSIT_RULES = {
    "Jupiter": {
        "Taurus": ("MAJOR BULLISH", "Jupiter in Taurus — stable growth, banking expansion, wealth accumulation", ["Large Caps", "Banking", "FMCG", "Real Estate", "Consumer"]),
        "Cancer": ("MAJOR BULLISH", "Exalted Jupiter supports expansion and liquidity", ["Large Caps", "Banking", "FMCG", "Real Estate"]),
        "Sagittarius": ("MAJOR BULLISH", "Jupiter in own sign Sagittarius — optimism, FII flows, growth sectors lead", ["Large Caps", "Banking", "Financial Services", "Education", "Travel"]),
        "Pisces": ("MAJOR BULLISH", "Jupiter in own sign Pisces — liquidity expansion, spiritual/consumer growth", ["Large Caps", "FMCG", "Pharma", "Consumer", "Shipping"]),
        "Capricorn": ("MAJOR BEARISH", "Debilitated Jupiter weakens expansion themes", ["Large Caps", "Banking", "FMCG"]),
    },
    "Saturn": {
        "Libra": ("STRUCTURALLY BULLISH", "Exalted Saturn supports orderly financial structure", ["Banking", "Infrastructure", "Metals"]),
        "Capricorn": ("STRUCTURALLY BULLISH", "Saturn in own sign Capricorn — discipline, long-term trend formation", ["Banking", "Infrastructure", "Metals", "PSU", "Manufacturing"]),
        "Taurus": ("BULLISH", "Saturn in Taurus — stable accumulation, wealth preservation", ["Banking", "Real Estate", "Consumer", "PSU"]),
        "Aries": ("MAJOR BEARISH", "Debilitated Saturn signals structural tension", ["Banking", "Infrastructure", "Defense", "Real Estate"]),
        "Pisces": ("BEARISH", "Saturn in Pisces — dissolution of structures, institutional weakening, policy confusion", ["Pharma", "Shipping", "Healthcare", "Large Caps"]),
    },
    "Mars": {
        "Capricorn": ("MOMENTUM BULLISH", "Exalted Mars supports industrial momentum", ["Energy", "Metals", "Defense", "Engineering"]),
        "Aries": ("MOMENTUM BULLISH", "Mars in own sign Aries — aggressive risk-taking, new initiatives", ["Defense", "Engineering", "Auto", "Metals", "Startups"]),
        "Scorpio": ("MOMENTUM BULLISH", "Mars in own sign Scorpio — deep transformation, strategic moves", ["Energy", "Metals", "Insurance", "Research", "Pharma"]),
        "Cancer": ("MOMENTUM BEARISH", "Debilitated Mars can drain industrial momentum", ["Energy", "Metals", "Defense", "Engineering"]),
    },
    "Venus": {
        "Taurus": ("MAJOR BULLISH", "Venus in own sign Taurus — luxury, banking, consumption boom", ["Banking", "Consumer", "Auto", "Real Estate", "FMCG", "Luxury"]),
        "Libra": ("MAJOR BULLISH", "Venus in own sign Libra — partnerships, trade, consumption", ["Banking", "Consumer", "Auto", "Retail", "Trade", "Airlines"]),
        "Pisces": ("MAJOR BULLISH", "Exalted Venus — maximum liquidity, credit expansion, arts/luxury", ["Banking", "Consumer", "Real Estate", "Luxury", "Entertainment", "Shipping"]),
        "Virgo": ("BEARISH", "Debilitated Venus — deflationary, credit tightening, consumption drop", ["Consumer", "Auto", "Retail", "Banking"]),
    },
    "Mercury": {
        "Gemini": ("BULLISH", "Mercury in own sign Gemini — trading volume, IT/tech boom, communication", ["IT", "Telecom", "Media", "Banking", "Trading"]),
        "Virgo": ("BULLISH", "Mercury in own sign Virgo — analytical precision, banking systems, healthcare", ["IT", "Banking", "Healthcare", "Pharma", "Consulting"]),
        "Pisces": ("BEARISH", "Debilitated Mercury — confusion, miscommunication, trading errors", ["IT", "Banking", "Telecom", "Media"]),
    },
    "Rahu": {
        "Aries": ("BULLISH", "Rahu in Aries — innovation, risk appetite, new themes emerge", ["Defense", "Engineering", "Auto", "Startups", "Tech"]),
        "Gemini": ("BULLISH", "Rahu in Gemini — communication revolution, tech narratives, trading", ["IT", "Telecom", "Media", "Trading", "AI"]),
        "Leo": ("BULLISH", "Rahu in Leo — speculation, entertainment, creative industries", ["Entertainment", "Gaming", "Media", "Luxury", "Speculative"]),
        "Taurus": ("BEARISH", "Rahu in Taurus — material obsession, unstable values", ["Banking", "Real Estate", "Consumer"]),
        "Scorpio": ("BEARISH", "Rahu in Scorpio — manipulation, hidden risks, crashes", ["Insurance", "Research", "Pharma", "Banking"]),
    },
    "Ketu": {
        "Sagittarius": ("BULLISH", "Ketu in Sagittarius — spiritual reset, philosophy-driven growth", ["Education", "Financial Services", "Publishing", "Travel"]),
        "Pisces": ("BULLISH", "Ketu in Pisces — dissolution of fear, spiritual/market cleansing", ["Pharma", "Shipping", "Healthcare", "Spiritual"]),
        "Virgo": ("BEARISH", "Ketu in Virgo — over-analysis, perfectionism paralysis", ["IT", "Healthcare", "Banking", "Consulting"]),
        "Gemini": ("BEARISH", "Ketu in Gemini — communication breakdown, scattered focus", ["IT", "Telecom", "Media", "Trading"]),
    },
}


# =============================================================================
# Pushya Nakshatra Reversal Detection
# =============================================================================
# Pushya (ruled by Saturn) is a nourishment/turning-point nakshatra.
# Key reversal triggers involving Pushya:
# 1. Moon in Pushya - emotional turning point, sentiment reversal risk
# 2. Saturn in/aspecting Pushya - structural reversal (Saturn is lord of Pushya)
# 3. Jupiter in Pushya - growth nakshatra, bullish reversal potential
# 4. Ravi Pushya Yoga (Sunday + Moon in Pushya) - leadership/authority reversal
# 5. Guru Pushya Yoga (Thursday + Moon in Pushya) - wisdom/expansion reversal
# 6. Malefic planets in Pushya (Saturn, Mars, Rahu, Ketu, Sun) - bearish reversal pressure
# 6. Benefic planets in Pushya (Jupiter, Venus, Mercury) - bullish reversal potential
# 7. Saturn-Jupiter angle involving Pushya - major structural shift

PUSHYA_NAKSHATRA = "Pushya"
PUSHYA_LORD = "Saturn"


def _angle_between(lon1, lon2):
    """Return shortest angular distance between two longitudes (0-180)."""
    diff = abs((lon1 - lon2 + 180) % 360 - 180)
    return diff


def _planet_in_nakshatra(planets, nakshatra_name):
    """Return list of planets currently in the given nakshatra."""
    return [p for p in planets if p["nakshatra"] == nakshatra_name]


def _pushya_reversal_windows(date, planets):
    """
    Detect Pushya Nakshatra based reversal signals for a given date.

    Returns list of reversal window dicts compatible with REVERSAL_WINDOWS format.
    These are dynamic single-day or multi-day windows based on planetary positions.
    """
    windows: list[dict] = []
    moon = next(p for p in planets if p["name"] == "Moon")
    saturn = next(p for p in planets if p["name"] == "Saturn")
    jupiter = next(p for p in planets if p["name"] == "Jupiter")
    sun = next(p for p in planets if p["name"] == "Sun")

    moon_in_pushya = moon["nakshatra"] == PUSHYA_NAKSHATRA

    # 1. Moon in Pushya - Sentiment Reversal Window
    if moon_in_pushya:
        # Moon in Pushya creates a 1-day reversal sensitivity window
        # Bias depends on Moon's nature (shubha/ashubha) and paksha
        from .nakshatra import moon_nature, paksha_of, tithi_of
        tithi = tithi_of(sun["longitude"], moon["longitude"])
        moon_nat = moon_nature(tithi)
        pk = paksha_of(tithi)

        if moon_nat == "malefic":
            level = "HIGH"
            bias = "BEARISH REVERSAL RISK"
            explanation = f"Moon in Pushya (Krishna {pk} paksha, ashubha) - emotional saturation, sentiment reversal risk"
        else:
            level = "MODERATE-HIGH"
            bias = "BULLISH REVERSAL POTENTIAL"
            explanation = f"Moon in Pushya (Shukla {pk} paksha, shubha) - nourishment phase, bullish reversal potential"

        windows.append({
            "id": f"pushya-moon-{date.isoformat()}",
            "start": date.isoformat(),
            "end": date.isoformat(),
            "title": f"Moon in Pushya Nakshatra - {explanation}",
            "level": level,
            "bias": bias,
            "sectors": ["All sectors", "Banking", "FMCG", "Large Caps"],
        })

    # 2. Saturn (Lord of Pushya) in Pushya - Structural Reversal
    saturn_in_pushya = saturn["nakshatra"] == PUSHYA_NAKSHATRA
    if saturn_in_pushya:
        # Saturn in its own nakshatra Pushya - major structural reversal
        bias = "STRUCTURAL REVERSAL" if not saturn["retrograde"] else "STRUCTURAL REVERSAL / RETROGRADE REVIEW"
        level = "EXTREME" if not saturn["retrograde"] else "VERY HIGH"
        windows.append({
            "id": f"pushya-saturn-{date.isoformat()}",
            "start": date.isoformat(),
            "end": (date + datetime.timedelta(days=30)).isoformat(),  # Saturn moves slowly
            "title": f"Saturn (Pushya Lord) in Pushya Nakshatra - {bias}",
            "level": level,
            "bias": bias,
            "sectors": ["Banking", "Infrastructure", "Metals", "Real Estate", "PSU"],
        })

    # 3. Jupiter in Pushya - Growth Reversal
    jupiter_in_pushya = jupiter["nakshatra"] == PUSHYA_NAKSHATRA
    if jupiter_in_pushya:
        # Jupiter in Pushya (growth nakshatra) - bullish reversal window
        windows.append({
            "id": f"pushya-jupiter-{date.isoformat()}",
            "start": date.isoformat(),
            "end": (date + datetime.timedelta(days=14)).isoformat(),
            "title": "Jupiter in Pushya Nakshatra - Growth/Bullish Reversal Window",
            "level": "HIGH",
            "bias": "BULLISH REVERSAL",
            "sectors": ["Large Caps", "Banking", "FMCG", "Financial Services", "Gold"],
        })

    # 4-5. Ravi / Guru Pushya Yoga: the Moon in Pushya at any time during the
    # Sunday / Thursday vara (sunrise to next sunrise), not just at the instant
    # `planets` was computed for. Windows carry the exact IST span.
    from .muhurta import format_window, guru_pushya_window, ravi_pushya_window
    ravi = ravi_pushya_window(date)
    if ravi:
        windows.append({
            "id": f"ravi-pushya-{date.isoformat()}",
            "start": date.isoformat(),
            "end": date.isoformat(),
            "start_time": ravi[0].isoformat(timespec="minutes"),
            "end_time": ravi[1].isoformat(timespec="minutes"),
            "title": f"Ravi Pushya Yoga {format_window(ravi)} (Sunday + Moon in Pushya)"
                     " - Authority/Leadership Reversal",
            "level": "HIGH",
            "bias": "REVERSAL - LEADERSHIP SHIFT",
            "sectors": ["PSU", "Government-linked", "Banking", "Large Caps"],
        })

    guru = guru_pushya_window(date)
    if guru:
        windows.append({
            "id": f"guru-pushya-{date.isoformat()}",
            "start": date.isoformat(),
            "end": date.isoformat(),
            "start_time": guru[0].isoformat(timespec="minutes"),
            "end_time": guru[1].isoformat(timespec="minutes"),
            "title": f"Guru Pushya Yoga {format_window(guru)} (Thursday + Moon in Pushya)"
                     " - Wisdom/Expansion Reversal",
            "level": "HIGH",
            "bias": "BULLISH REVERSAL",
            "sectors": ["Banking", "FMCG", "Financial Services", "Education", "Large Caps"],
        })

    # 6. Malefic planets in Pushya - Bearish Reversal Pressure
    malefics_in_pushya = _planet_in_nakshatra(planets, PUSHYA_NAKSHATRA)
    malefic_names = ["Saturn", "Mars", "Rahu", "Ketu", "Sun"]
    malefics_present = [p for p in malefics_in_pushya if p["name"] in malefic_names]
    if malefics_present and not moon_in_pushya:  # Avoid duplicate with Moon case
        names = ", ".join(p["name"] for p in malefics_present)
        windows.append({
            "id": f"pushya-malefics-{date.isoformat()}",
            "start": date.isoformat(),
            "end": date.isoformat(),
            "title": f"Malefics in Pushya ({names}) - Bearish Reversal Pressure",
            "level": "HIGH",
            "bias": "BEARISH REVERSAL",
            "sectors": ["Banking", "Metals", "Real Estate", "PSU", "Large Caps"],
        })

    # 7. Benefic planets in Pushya - Bullish Reversal Potential
    benefics_in_pushya = _planet_in_nakshatra(planets, PUSHYA_NAKSHATRA)
    benefic_names = ["Jupiter", "Venus", "Mercury"]
    benefics_present = [p for p in benefics_in_pushya if p["name"] in benefic_names]
    if benefics_present and not jupiter_in_pushya:  # Avoid duplicate
        names = ", ".join(p["name"] for p in benefics_present)
        windows.append({
            "id": f"pushya-benefics-{date.isoformat()}",
            "start": date.isoformat(),
            "end": date.isoformat(),
            "title": f"Benefics in Pushya ({names}) - Bullish Reversal Potential",
            "level": "MODERATE-HIGH",
            "bias": "BULLISH REVERSAL",
            "sectors": ["Banking", "FMCG", "IT", "Large Caps", "Consumer"],
        })

    # 8. Saturn-Jupiter angle involving Pushya
    sat_jup_angle = _angle_between(saturn["longitude"], jupiter["longitude"])
    # Check if either is in Pushya and they form a significant angle
    if (saturn_in_pushya or jupiter_in_pushya) and sat_jup_angle in (60, 90, 120, 180):
        angle_name = {60: "Sextile", 90: "Square", 120: "Trine", 180: "Opposition"}[sat_jup_angle]
        windows.append({
            "id": f"pushya-saturn-jupiter-{angle_name.lower()}-{date.isoformat()}",
            "start": date.isoformat(),
            "end": (date + datetime.timedelta(days=7)).isoformat(),
            "title": f"Saturn-Jupiter {angle_name} involving Pushya - Major Structural Shift",
            "level": "EXTREME",
            "bias": "VOLATILE / MAJOR REVERSAL",
            "sectors": ["All sectors", "Banking", "Infrastructure", "Large Caps"],
        })

    return windows


# =============================================================================
# Comprehensive Bullish Reversal Detection (from user's specification)
# =============================================================================

# Bullish nakshatras for each planet
BULLISH_NAKSHATRAS = {
    "Jupiter": {"Punarvasu", "Pushya", "Vishakha", "PurvaBhadrapada"},
    "Saturn": {"Pushya", "Anuradha", "UttaraBhadrapada"},
    "Venus": {"Bharani", "PurvaPhalguni", "PurvaAshadha"},
    "Mercury": {"Ashlesha", "Jyeshtha", "Revati"},
    "Moon": {"Rohini", "Pushya", "UttaraPhalguni", "Revati", "Hasta", "Shravana"},
    "Rahu": {"Ardra", "Swati", "Shatabhisha"},
    "Ketu": {"Ashwini", "Magha", "Mula"},
}

# Nakshatra meanings for output
NAKSHATRA_MEANINGS = {
    "Punarvasu": "renewal",
    "Pushya": "nourishment",
    "Vishakha": "branching growth",
    "PurvaBhadrapada": "spiritual fire",
    "Anuradha": "devotion",
    "UttaraBhadrapada": "universal love",
    "Bharani": "creative birth",
    "PurvaPhalguni": "prosperity",
    "PurvaAshadha": "invincibility",
    "Ashlesha": "analytical depth",
    "Jyeshtha": "supremacy",
    "Revati": "completion/new cycle",
    "Rohini": "growth",
    "UttaraPhalguni": "prosperity",
    "Hasta": "skill",
    "Shravana": "learning",
    "Ardra": "transformation",
    "Swati": "independence",
    "Shatabhisha": "healing",
    "Ashwini": "initiation",
    "Magha": "authority",
    "Mula": "root change",
}


def _detect_bullish_nakshatra_transits(planets, date):
    """Detect bullish nakshatra transits for all planets."""
    windows: list[dict] = []

    for planet_name, bullish_naks in BULLISH_NAKSHATRAS.items():
        planet = next((p for p in planets if p["name"] == planet_name), None)
        if not planet:
            continue

        if planet["nakshatra"] in bullish_naks:
            meaning = NAKSHATRA_MEANINGS.get(planet["nakshatra"], "favorable")

            # Determine level based on planet importance
            level_map = {
                "Jupiter": "HIGH", "Saturn": "HIGH", "Venus": "MODERATE-HIGH",
                "Mercury": "MODERATE", "Moon": "MODERATE", "Rahu": "HIGH", "Ketu": "MODERATE-HIGH"
            }
            level = level_map.get(planet_name, "MODERATE")

            # Sector mapping
            sector_map = {
                "Jupiter": ["Large Caps", "Banking", "FMCG", "Financial Services", "Gold"],
                "Saturn": ["Banking", "Infrastructure", "Metals", "PSU", "Real Estate"],
                "Venus": ["Banking", "Consumer", "Auto", "Real Estate", "FMCG", "Luxury"],
                "Mercury": ["IT", "Telecom", "Media", "Banking", "Trading"],
                "Moon": ["All sectors", "Banking", "FMCG", "Large Caps"],
                "Rahu": ["Defense", "Engineering", "Auto", "Tech", "Startups"],
                "Ketu": ["Pharma", "Shipping", "Healthcare", "Spiritual", "Large Caps"],
            }

            windows.append({
                "id": f"{planet_name.lower()}-nak-{planet['nakshatra'].lower()}-{date.isoformat()}",
                "start": date.isoformat(),
                "end": date.isoformat(),
                "title": f"{planet_name} in {planet['nakshatra']} ({meaning}) — {planet_name} bullish nakshatra transit",
                "level": level,
                "bias": "BULLISH REVERSAL POTENTIAL",
                "sectors": sector_map.get(planet_name, ["All sectors"]),
            })

    return windows


def _detect_venus_exiting_virgo(planets, date):
    """Venus exiting Virgo (debilitated) = bullish."""
    windows: list[dict] = []
    venus = next((p for p in planets if p["name"] == "Venus"), None)
    if not venus:
        return windows

    # Check if Venus just left Virgo (in Libra now, was in Virgo recently)
    # Since we only have current position, check if Venus is in Libra (next sign after Virgo)
    if venus["sign"] == "Libra" and venus["degree"] < 3:  # Just entered Libra
        windows.append({
            "id": f"venus-exit-virgo-{date.isoformat()}",
            "start": date.isoformat(),
            "end": (date + datetime.timedelta(days=7)).isoformat(),
            "title": "Venus exits Virgo (debilitated) — deflationary phase ends, consumption revives",
            "level": "HIGH",
            "bias": "BULLISH REVERSAL",
            "sectors": ["Consumer", "Auto", "Retail", "Banking", "Luxury", "Entertainment"],
        })
    return windows


def _detect_mercury_in_own_nakshatra(planets, date):
    """Mercury in Mercury-ruled nakshatras (Ashlesha, Jyeshtha, Revati)."""
    windows: list[dict] = []
    mercury = next((p for p in planets if p["name"] == "Mercury"), None)
    if not mercury:
        return windows

    if mercury["nakshatra"] in {"Ashlesha", "Jyeshtha", "Revati"}:
        meaning = NAKSHATRA_MEANINGS.get(mercury["nakshatra"], "favorable")
        windows.append({
            "id": f"mercury-nak-{mercury['nakshatra'].lower()}-{date.isoformat()}",
            "start": date.isoformat(),
            "end": date.isoformat(),
            "title": f"Mercury in {mercury['nakshatra']} ({meaning}) — analytical precision, tech/banking clarity",
            "level": "MODERATE",
            "bias": "BULLISH REVERSAL POTENTIAL",
            "sectors": ["IT", "Telecom", "Media", "Banking", "Trading", "Consulting"],
        })
    return windows


def _detect_moon_bullish_nakshatra(planets, date):
    """Moon in Taurus/Cancer/Pisces or bullish nakshatras."""
    windows: list[dict] = []
    moon = next((p for p in planets if p["name"] == "Moon"), None)
    if not moon:
        return windows

    # Moon in bullish signs
    bullish_signs = {"Taurus", "Cancer", "Pisces"}
    if moon["sign"] in bullish_signs:
        windows.append({
            "id": f"moon-sign-{moon['sign'].lower()}-{date.isoformat()}",
            "start": date.isoformat(),
            "end": date.isoformat(),
            "title": f"Moon in {moon['sign']} — sentiment stabilization, short-term bullish bias",
            "level": "MODERATE",
            "bias": "BULLISH REVERSAL POTENTIAL",
            "sectors": ["All sectors", "Banking", "FMCG", "Large Caps"],
        })

    # Moon in bullish nakshatras
    bullish_moon_naks = {"Rohini", "Pushya", "UttaraPhalguni", "Revati", "Hasta", "Shravana"}
    if moon["nakshatra"] in bullish_moon_naks:
        meaning = NAKSHATRA_MEANINGS.get(moon["nakshatra"], "favorable")
        windows.append({
            "id": f"moon-nak-{moon['nakshatra'].lower()}-{date.isoformat()}",
            "start": date.isoformat(),
            "end": date.isoformat(),
            "title": f"Moon in {moon['nakshatra']} ({meaning}) — emotional nourishment, sentiment bullish",
            "level": "MODERATE",
            "bias": "BULLISH REVERSAL POTENTIAL",
            "sectors": ["All sectors", "Banking", "FMCG", "Large Caps"],
        })
    return windows


def _detect_rahu_ketu_separation(planets, date):
    """Rahu/Ketu moving away from Sun/Moon = sentiment stabilizes."""
    windows: list[dict] = []
    rahu = next((p for p in planets if p["name"] == "Rahu"), None)
    ketu = next((p for p in planets if p["name"] == "Ketu"), None)
    sun = next((p for p in planets if p["name"] == "Sun"), None)
    moon = next((p for p in planets if p["name"] == "Moon"), None)

    if rahu is None or ketu is None or sun is None or moon is None:
        return windows

    def angle(lon1, lon2):
        return abs((lon1 - lon2 + 180) % 360 - 180)

    # Rahu moving away from Sun (was conjunct, now separating > 15°)
    rahu_sun = angle(rahu["longitude"], sun["longitude"])
    ketu_sun = angle(ketu["longitude"], sun["longitude"])

    if rahu_sun > 15 and rahu_sun < 30:  # Recently separated
        windows.append({
            "id": f"rahu-sep-sun-{date.isoformat()}",
            "start": date.isoformat(),
            "end": (date + datetime.timedelta(days=3)).isoformat(),
            "title": "Rahu separating from Sun — narrative confusion clearing, sentiment stabilizing",
            "level": "MODERATE",
            "bias": "BULLISH REVERSAL POTENTIAL",
            "sectors": ["All sectors", "Media", "Tech", "Speculative"],
        })

    if ketu_sun > 15 and ketu_sun < 30:
        windows.append({
            "id": f"ketu-sep-sun-{date.isoformat()}",
            "start": date.isoformat(),
            "end": (date + datetime.timedelta(days=3)).isoformat(),
            "title": "Ketu separating from Sun — fear dissolving, clarity returning",
            "level": "MODERATE",
            "bias": "BULLISH REVERSAL POTENTIAL",
            "sectors": ["All sectors", "Pharma", "Shipping", "Healthcare"],
        })

    return windows


def _detect_ketu_leaving_market_degrees(planets, date):
    """Ketu leaving market-sensitive degrees (0° Aries, 0° Cancer, 0° Libra, 0° Capricorn)."""
    windows: list[dict] = []
    ketu = next((p for p in planets if p["name"] == "Ketu"), None)
    if not ketu:
        return windows

    # Market sensitive degrees: cardinal signs 0°
    if ketu["sign"] in {"Aries", "Cancer", "Libra", "Capricorn"} and ketu["degree"] > 2:
        # Just left the 0° sensitive zone
        windows.append({
            "id": f"ketu-leave-cardinal-{date.isoformat()}",
            "start": date.isoformat(),
            "end": (date + datetime.timedelta(days=7)).isoformat(),
            "title": f"Ketu leaves {ketu['sign']} 0° — market-sensitive degree cleared, fear dissolving",
            "level": "MODERATE-HIGH",
            "bias": "BULLISH REVERSAL",
            "sectors": ["All sectors", "Banking", "Large Caps", "Pharma"],
        })
    return windows


def _detect_full_moon_stable_signs(planets, date, tithi):
    """Full Moon in stable signs (Taurus, Cancer, Leo, Scorpio, Capricorn, Pisces)."""
    windows: list[dict] = []
    if tithi not in (14, 15, 16):  # Only near Full Moon
        return windows

    moon = next((p for p in planets if p["name"] == "Moon"), None)
    if not moon:
        return windows

    stable_signs = {"Taurus", "Cancer", "Leo", "Scorpio", "Capricorn", "Pisces"}
    if moon["sign"] in stable_signs:
        windows.append({
            "id": f"fullmoon-{moon['sign'].lower()}-{date.isoformat()}",
            "start": date.isoformat(),
            "end": date.isoformat(),
            "title": f"Full Moon in {moon['sign']} — emotional peak in stable sign, sentiment extreme but grounded",
            "level": "HIGH",
            "bias": "BULLISH REVERSAL POTENTIAL" if moon["sign"] in {"Taurus", "Cancer", "Pisces"} else "NEUTRAL",
            "sectors": ["All sectors", "Gold/MCX", "Banking", "Large Caps"],
        })
    return windows


def _detect_jupiter_saturn_trine(planets, date):
    """Jupiter trine Saturn (120°) - stable expansion, multi-year bull runs."""
    windows: list[dict] = []
    jupiter = next((p for p in planets if p["name"] == "Jupiter"), None)
    saturn = next((p for p in planets if p["name"] == "Saturn"), None)
    if not jupiter or not saturn:
        return windows

    def angle(lon1, lon2):
        return abs((lon1 - lon2 + 180) % 360 - 180)

    jup_sat_angle = angle(jupiter["longitude"], saturn["longitude"])

    # Trine (120°) with 8° orb
    if abs(jup_sat_angle - 120) <= 8:
        applying = jup_sat_angle < 120
        windows.append({
            "id": f"jup-sat-trine-{date.isoformat()}",
            "start": date.isoformat(),
            "end": (date + datetime.timedelta(days=30)).isoformat(),
            "title": f"Jupiter trine Saturn (120°{' applying' if applying else ' separating'}) — stable expansion, multi-year bull run foundation",
            "level": "EXTREME",
            "bias": "BULLISH REVERSAL" if applying else "BULLISH CONTINUATION",
            "sectors": ["Large Caps", "Banking", "Infrastructure", "FMCG", "Financial Services", "Real Estate"],
        })

    # Sextile (60°) - opportunity
    if abs(jup_sat_angle - 60) <= 6:
        windows.append({
            "id": f"jup-sat-sextile-{date.isoformat()}",
            "start": date.isoformat(),
            "end": (date + datetime.timedelta(days=14)).isoformat(),
            "title": "Jupiter sextile Saturn (60°) — structural opportunity, disciplined growth",
            "level": "HIGH",
            "bias": "BULLISH REVERSAL POTENTIAL",
            "sectors": ["Large Caps", "Banking", "Infrastructure", "Metals"],
        })

    return windows


def _detect_rahu_jupiter_trine(planets, date):
    """Rahu trine Jupiter — mass optimism + new narratives."""
    windows: list[dict] = []
    rahu = next((p for p in planets if p["name"] == "Rahu"), None)
    jupiter = next((p for p in planets if p["name"] == "Jupiter"), None)
    if not rahu or not jupiter:
        return windows

    def angle(lon1, lon2):
        return abs((lon1 - lon2 + 180) % 360 - 180)

    rahu_jup_angle = angle(rahu["longitude"], jupiter["longitude"])

    if abs(rahu_jup_angle - 120) <= 8:
        windows.append({
            "id": f"rahu-jup-trine-{date.isoformat()}",
            "start": date.isoformat(),
            "end": (date + datetime.timedelta(days=30)).isoformat(),
            "title": "Rahu trine Jupiter — mass optimism, new narratives (AI, tech, EV, biotech) emerging",
            "level": "HIGH",
            "bias": "BULLISH REVERSAL POTENTIAL",
            "sectors": ["IT", "Tech", "AI", "EV", "Biotech", "Startups", "Media"],
        })
    return windows


def _detect_venus_jupiter_trine(planets, date):
    """Venus trine Jupiter — liquidity + optimism."""
    windows: list[dict] = []
    venus = next((p for p in planets if p["name"] == "Venus"), None)
    jupiter = next((p for p in planets if p["name"] == "Jupiter"), None)
    if not venus or not jupiter:
        return windows

    def angle(lon1, lon2):
        return abs((lon1 - lon2 + 180) % 360 - 180)

    ven_jup_angle = angle(venus["longitude"], jupiter["longitude"])

    if abs(ven_jup_angle - 120) <= 8:
        windows.append({
            "id": f"venus-jup-trine-{date.isoformat()}",
            "start": date.isoformat(),
            "end": (date + datetime.timedelta(days=14)).isoformat(),
            "title": "Venus trine Jupiter — liquidity expansion, consumption boom, credit cycle turn",
            "level": "HIGH",
            "bias": "BULLISH REVERSAL POTENTIAL",
            "sectors": ["Banking", "Consumer", "Auto", "Real Estate", "FMCG", "Luxury", "Entertainment"],
        })
    return windows


def _detect_mercury_jupiter_trine(planets, date):
    """Mercury trine Jupiter — bullish for tech + banking."""
    windows: list[dict] = []
    mercury = next((p for p in planets if p["name"] == "Mercury"), None)
    jupiter = next((p for p in planets if p["name"] == "Jupiter"), None)
    if not mercury or not jupiter:
        return windows

    def angle(lon1, lon2):
        return abs((lon1 - lon2 + 180) % 360 - 180)

    mer_jup_angle = angle(mercury["longitude"], jupiter["longitude"])

    if abs(mer_jup_angle - 120) <= 8:
        windows.append({
            "id": f"mercury-jup-trine-{date.isoformat()}",
            "start": date.isoformat(),
            "end": (date + datetime.timedelta(days=7)).isoformat(),
            "title": "Mercury trine Jupiter — trading clarity, tech/banking optimism, communication expansion",
            "level": "MODERATE-HIGH",
            "bias": "BULLISH REVERSAL POTENTIAL",
            "sectors": ["IT", "Telecom", "Media", "Banking", "Trading", "Consulting"],
        })
    return windows


def _detect_jupiter_direct_after_retro(planets, date):
    """Jupiter direct after retrograde — risk appetite returns."""
    windows: list[dict] = []
    jupiter = next((p for p in planets if p["name"] == "Jupiter"), None)
    if not jupiter:
        return windows

    # This would need previous day's data to detect direction change
    # For now, flag if Jupiter is stationary direct (speed near 0, was negative)
    if not jupiter["retrograde"] and abs(jupiter["speed"]) < 0.01:
        windows.append({
            "id": f"jupiter-direct-{date.isoformat()}",
            "start": date.isoformat(),
            "end": (date + datetime.timedelta(days=14)).isoformat(),
            "title": "Jupiter turns direct after retrograde — risk appetite returns, growth resumes",
            "level": "EXTREME",
            "bias": "BULLISH REVERSAL",
            "sectors": ["Large Caps", "Banking", "FMCG", "Financial Services", "Gold", "Real Estate"],
        })
    return windows


def _detect_saturn_direct_after_retro(planets, date):
    """Saturn direct after retrograde — fear cycles end, accumulation begins."""
    windows: list[dict] = []
    saturn = next((p for p in planets if p["name"] == "Saturn"), None)
    if not saturn:
        return windows

    if not saturn["retrograde"] and abs(saturn["speed"]) < 0.01:
        windows.append({
            "id": f"saturn-direct-{date.isoformat()}",
            "start": date.isoformat(),
            "end": (date + datetime.timedelta(days=30)).isoformat(),
            "title": "Saturn turns direct after retrograde — fear cycles end, strong hands accumulate",
            "level": "EXTREME",
            "bias": "BULLISH REVERSAL",
            "sectors": ["Banking", "Infrastructure", "Metals", "PSU", "Real Estate", "Manufacturing"],
        })
    return windows


def _detect_mercury_direct_after_retro(planets, date):
    """Mercury direct after retrograde — clarity returns."""
    windows: list[dict] = []
    mercury = next((p for p in planets if p["name"] == "Mercury"), None)
    if not mercury:
        return windows

    if not mercury["retrograde"] and abs(mercury["speed"]) < 0.02:
        windows.append({
            "id": f"mercury-direct-{date.isoformat()}",
            "start": date.isoformat(),
            "end": (date + datetime.timedelta(days=7)).isoformat(),
            "title": "Mercury turns direct after retrograde — trading clarity returns, fewer shocks",
            "level": "HIGH",
            "bias": "BULLISH REVERSAL POTENTIAL",
            "sectors": ["IT", "Telecom", "Media", "Banking", "Trading"],
        })
    return windows


def _detect_jupiter_combustion_end(planets, date):
    """Jupiter emerging from combustion — liquidity returns."""
    windows: list[dict] = []
    jupiter = next((p for p in planets if p["name"] == "Jupiter"), None)
    sun = next((p for p in planets if p["name"] == "Sun"), None)
    if not jupiter or not sun:
        return windows

    def angle(lon1, lon2):
        return abs((lon1 - lon2 + 180) % 360 - 180)

    jup_sun_angle = angle(jupiter["longitude"], sun["longitude"])
    # Combustion orb for Jupiter is 11°
    if jup_sun_angle > 11 and jup_sun_angle < 15:  # Just emerged
        windows.append({
            "id": f"jupiter-combustion-end-{date.isoformat()}",
            "start": date.isoformat(),
            "end": (date + datetime.timedelta(days=14)).isoformat(),
            "title": "Jupiter emerges from combustion — liquidity returns, expansion resumes",
            "level": "HIGH",
            "bias": "BULLISH REVERSAL",
            "sectors": ["Large Caps", "Banking", "FMCG", "Financial Services", "Gold"],
        })
    return windows


# Master function to get all bullish reversal windows
def get_all_bullish_reversal_windows(date, planets, tithi):
    """Combine all bullish reversal detection functions."""
    all_windows = []

    # Existing Pushya windows (already comprehensive)
    all_windows.extend(_pushya_reversal_windows(date, planets))

    # New bullish detectors
    all_windows.extend(_detect_bullish_nakshatra_transits(planets, date))
    all_windows.extend(_detect_venus_exiting_virgo(planets, date))
    all_windows.extend(_detect_mercury_in_own_nakshatra(planets, date))
    all_windows.extend(_detect_moon_bullish_nakshatra(planets, date))
    all_windows.extend(_detect_rahu_ketu_separation(planets, date))
    all_windows.extend(_detect_ketu_leaving_market_degrees(planets, date))
    all_windows.extend(_detect_full_moon_stable_signs(planets, date, tithi))
    all_windows.extend(_detect_jupiter_saturn_trine(planets, date))
    all_windows.extend(_detect_rahu_jupiter_trine(planets, date))
    all_windows.extend(_detect_venus_jupiter_trine(planets, date))
    all_windows.extend(_detect_mercury_jupiter_trine(planets, date))
    all_windows.extend(_detect_jupiter_direct_after_retro(planets, date))
    all_windows.extend(_detect_saturn_direct_after_retro(planets, date))
    all_windows.extend(_detect_mercury_direct_after_retro(planets, date))
    all_windows.extend(_detect_jupiter_combustion_end(planets, date))

    return all_windows


NITYA_YOGAS = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarma", "Dhriti", "Shula", "Ganda", "Vriddhi",
    "Dhruva", "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata",
    "Variyana", "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha",
    "Shukla", "Brahma", "Indra", "Vaidhriti",
]

YOGA_GLYPHS = {
    "Indra Yoga": "I", "Ravi Yoga": "R", "Sarvartha Siddhi Yoga": "SS",
    "Amrit Siddhi Yoga": "AS", "Dwipushkar Yoga": "DP",
    "Tripushkar Yoga": "TP", "Ravi Pushya Yoga": "RP",
    "Guru Pushya Yoga": "GP", "Maitreya Yoga": "M",
    "Bhadra": "B",
    "Full Moon (Purnima)": "F", "New Moon (Amavasya)": "N",
}

# Common Panchanga weekday/nakshatra combinations. Weekday uses Monday=0.
SARVARTHA = {
    0: {"Rohini", "Mrigashira", "Shravana", "Dhanishta", "Shatabhisha"},
    1: {"Ashwini", "Pushya", "Anuradha"},
    2: {"Rohini", "Anuradha", "Hasta"},
    3: {"Revati", "Anuradha", "Punarvasu"},
    4: {"Ashwini", "Pushya", "Anuradha"},
    5: {"Bharani", "P.Phalguni", "Revati"},
    6: {"Rohini", "Shravana"},
}
AMRIT_SIDDHI = {
    6: "Hasta", 0: "Mrigashira", 1: "Ashlesha", 2: "Anuradha",
    3: "Pushya", 4: "Revati", 5: "Rohini",
}
PUSHKAR_NAKSHATRAS = {"Mrigashira", "Chitra", "Dhanishta"}
PUSHKAR_WEEKDAYS = {5, 1, 6}  # Sunday, Tuesday, Saturday

NAKSHATRA_LORDS = {
    "Ashwini": "Ketu", "Magha": "Ketu", "Mula": "Ketu",
    "Bharani": "Venus", "P.Phalguni": "Venus", "P.Ashadha": "Venus",
    "Krittika": "Sun", "U.Phalguni": "Sun", "U.Ashadha": "Sun",
    "Rohini": "Moon", "Hasta": "Moon", "Shravana": "Moon",
    "Mrigashira": "Mars", "Chitra": "Mars", "Dhanishta": "Mars",
    "Ardra": "Rahu", "Swati": "Rahu", "Shatabhisha": "Rahu",
    "Punarvasu": "Jupiter", "Vishakha": "Jupiter", "P.Bhadrapada": "Jupiter",
    "Pushya": "Saturn", "Anuradha": "Saturn", "U.Bhadrapada": "Saturn",
    "Ashlesha": "Mercury", "Jyeshtha": "Mercury", "Revati": "Mercury",
}


def _sign_distance(first, second):
    return (second - first) % 12


def jupiter_market_analysis(planets):
    """Apply the supplied Jupiter/Ketu/Shashtashtak research heuristic."""
    jupiter = next(p for p in planets if p["name"] == "Jupiter")
    malefics = [p for p in planets if p["name"] in ("Saturn", "Sun", "Mars")]
    reasons = []
    if NAKSHATRA_LORDS.get(jupiter["nakshatra"]) == "Ketu":
        reasons.append(f"Jupiter in Ketu-ruled {jupiter['nakshatra']}")
    shashtashtak = []
    for planet in malefics:
        distance = _sign_distance(jupiter["sign_index"], planet["sign_index"])
        if distance in (5, 7):
            shashtashtak.append(planet["name"])
    if shashtashtak:
        reasons.append("Shashtashtak (6/8 sign axis) with " + ", ".join(shashtashtak))
    close = []
    for planet in malefics:
        separation = abs((jupiter["longitude"] - planet["longitude"] + 180) % 360 - 180)
        if separation <= 8:
            close.append(f"{planet['name']} ({separation:.1f}°)")
    if close:
        reasons.append("close affliction by " + ", ".join(close))
    return {
        "active": bool(reasons),
        "title": "Jupiter market-crash heuristic",
        "level": "HIGH" if len(reasons) > 1 else "MODERATE",
        "bias": "BEARISH RISK" if reasons else "NO JUPITER CRASH FLAG",
        "jupiter": {
            "sign": jupiter["sign"],
            "degree": jupiter["degree"],
            "nakshatra": jupiter["nakshatra"],
            "nakshatra_lord": NAKSHATRA_LORDS.get(jupiter["nakshatra"]),
        },
        "reasons": reasons,
        "sectors": ["Large Caps", "Banking", "FMCG", "Financial Services"],
        "method": "Research heuristic only; not a causal or predictive market model.",
    }


def daily_yoga_glyphs(date, sun, moon, tithi):
    weekday = date.weekday()
    nakshatra = moon["nakshatra"]
    names = []
    nitya_index = int(((sun["longitude"] + moon["longitude"]) % 360.0) /
                      (360.0 / 27.0))
    if NITYA_YOGAS[nitya_index] == "Indra":
        names.append("Indra Yoga")
    if nakshatra in SARVARTHA[weekday]:
        names.append("Sarvartha Siddhi Yoga")
    if AMRIT_SIDDHI[weekday] == nakshatra:
        names.append("Amrit Siddhi Yoga")
    # Pushya yogas hold for any part of the vara (sunrise to sunrise), not
    # only when the Moon is in Pushya at the sampled instant.
    from .muhurta import guru_pushya_window, ravi_pushya_window
    if ravi_pushya_window(date):
        names.append("Ravi Pushya Yoga")
    if guru_pushya_window(date):
        names.append("Guru Pushya Yoga")
    if weekday == 2 and nakshatra == "Anuradha":
        names.append("Maitreya Yoga")
    if weekday in PUSHKAR_WEEKDAYS and nakshatra in PUSHKAR_NAKSHATRAS:
        if tithi in {2, 7, 12}:
            names.append("Dwipushkar Yoga")
        if tithi in {3, 8, 13}:
            names.append("Tripushkar Yoga")
    if tithi == 15:
        names.append("Full Moon (Purnima)")
    if tithi == 30:
        names.append("New Moon (Amavasya)")
    return names, "+".join(YOGA_GLYPHS[name] for name in names)

# Pushkara Navamsha positions, indexed by sidereal sign (0=Aries).
PUSHKARA_NAVAMSHAS = {
    0: (7, 9), 1: (3, 5), 2: (6, 8), 3: (1, 3),
    4: (7, 9), 5: (3, 5), 6: (6, 8), 7: (1, 3),
    8: (7, 9), 9: (3, 5), 10: (6, 8), 11: (1, 3),
}


def _pushkara_navamsa(longitude):
    sign_index = int(longitude % 360.0) // 30
    degree = longitude % 30.0
    navamsa = int(degree / (30.0 / 9.0)) + 1
    return navamsa in PUSHKARA_NAVAMSHAS[sign_index]


def _local_julian(date, time_str, tz_name):
    tz = ZoneInfo(tz_name)
    hour, minute = (int(value) for value in time_str.split(":"))
    local = datetime.datetime.combine(date, datetime.time(hour, minute), tzinfo=tz)
    utc = local.astimezone(datetime.UTC)
    return swe.julday(utc.year, utc.month, utc.day,
                      utc.hour + utc.minute / 60.0)


def upcoming_yoga_alerts(date_str, time_str, tz_name, days=7):
    """Return daily yoga and muhurta events for the next seven days."""
    start = datetime.date.fromisoformat(date_str)
    events = []
    for offset in range(days + 1):
        date = start + datetime.timedelta(days=offset)
        planets, _ = positions(_local_julian(date, time_str, tz_name))
        sun = next(p for p in planets if p["name"] == "Sun")
        moon = next(p for p in planets if p["name"] == "Moon")
        from .nakshatra import tithi_of
        tithi = tithi_of(sun["longitude"], moon["longitude"])
        names, glyphs = daily_yoga_glyphs(date, sun, moon, tithi)
        yoga_details = {
            "Indra Yoga": "Nitya Yoga Indra – period of stability and sovereign influence; good for initiating long-term structures.",
            "Dwipushkar Yoga": "Two Pushkara nakshatras active with Tithi 2/7/12 – double auspicious energy; favorable for commitments.",
            "Tripushkar Yoga": "Three Pushkara nakshatras active with Tithi 3/8/13 – triple auspicious energy; highly favorable for new ventures.",
        }
        for name in names:
            events.append({
                "date": date.isoformat(), "type": name,
                "glyph": YOGA_GLYPHS.get(name, ""),
                "glyphs": glyphs,
                "basis": "Panchanga daily calculation",
                "details": yoga_details.get(name, f"Today is {name}."),
            })
        pushkara = []
        for planet in planets:
            if planet["name"] in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn") and _pushkara_navamsa(planet["longitude"]):
                pushkara.append(f"{planet['name']} in {planet['sign']}")
        if pushkara:
            events.append({
                "date": date.isoformat(),
                "type": "Pushkara Yoga",
                "glyph": "P",
                "glyphs": glyphs,
                "basis": "Pushkara Navamsha",
                "details": "; ".join(pushkara),
            })

    # Bhadra (Vishti Karana) windows — precise inauspicious periods within
    # the forward window (derived from Sun-Moon elongation via Swiss Ephemeris).
    events.extend(_bhadra_events(start, days, tz_name))
    return events


def _bhadra_events(start, days, tz_name):
    """Return per-day Bhadra (Vishti Karana) events overlapping the window."""
    from .bhadra import bhadra_windows
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("Asia/Kolkata")

    events = []
    # Bhadra windows recur ~4 times/scans; scan the full span's months.
    first_month = datetime.datetime(start.year, start.month, 1, tzinfo=tz)
    end = start + datetime.timedelta(days=days)
    last_month = datetime.datetime(end.year, end.month, 1, tzinfo=tz)
    start_dt = datetime.datetime(start.year, start.month, start.day, tzinfo=tz)

    windows: list[dict] = []
    seen = set()
    # Cover first and last month (windows crossing month boundaries handled too).
    cursor = first_month
    while cursor <= last_month:
        for w in bhadra_windows(cursor, tz):
            key = (w["begin"].isoformat(), w["end"].isoformat())
            if key not in seen:
                seen.add(key)
                windows.append(w)
        # advance one month
        y, m = cursor.year, cursor.month
        m += 1
        if m > 12:
            m = 1
            y += 1
        cursor = datetime.datetime(y, m, 1, tzinfo=tz)

    horizon_end = start_dt + datetime.timedelta(days=days + 1)
    for w in windows:
        b = w["begin"]
        e = w["end"]
        if e < start_dt or b >= horizon_end:
            continue
        # Clip to the start of the horizon.
        if b < start_dt:
            b = start_dt
        events.append({
            "date": b.date().isoformat(),
            "type": "Bhadra",
            "glyph": YOGA_GLYPHS.get("Bhadra", "B"),
            "glyphs": YOGA_GLYPHS.get("Bhadra", "B"),
            "basis": "Vishti Karana (inauspicious muhurta)",
            "details": f"Bhadra begins {b.strftime('%H:%M')} and ends "
                       f"{e.strftime('%H:%M')} ({tz_name}).",
            "start_time": b.strftime('%H:%M'),
            "end_time": e.strftime('%H:%M'),
            "start_iso": b.isoformat(),
            "end_iso": e.isoformat(),
        })
    return events


def transit_alert(planets):
    """Calculate major Jupiter, Saturn and Mars transit conditions."""
    alerts = []
    for planet in ("Jupiter", "Saturn", "Mars"):
        position = next(p for p in planets if p["name"] == planet)
        rule = TRANSIT_RULES[planet].get(position["sign"])
        if not rule:
            continue
        bias, explanation, sectors = rule
        if position["retrograde"]:
            explanation += "; retrograde motion increases review and volatility"
            bias += " / RETROGRADE"
        alerts.append({
            "planet": planet,
            "sign": position["sign"],
            "degree": position["degree"],
            "nakshatra": position["nakshatra"],
            "retrograde": position["retrograde"],
            "bias": bias,
            "level": "HIGH",
            "title": f"{planet} transit in {position['sign']}",
            "explanation": explanation,
            "sectors": sectors,
        })
    return alerts


def lunar_phase_alert(tithi):
    """Return a New Moon or Full Moon alert for the selected tithi."""
    if tithi in (14, 15, 16):
        exact = tithi == 15
        return {
            "active": True,
            "phase": "FULL MOON",
            "tithi": tithi,
            "window": "exact Purnima" if exact else "Purnima watch window",
            "level": "HIGH" if exact else "MODERATE",
            "bias": "SENTIMENT EXTREME",
            "title": "Full Moon / Purnima",
            "explanation": "Emotional liquidity and short-term price extremes may increase.",
            "sectors": ["All sectors", "Gold/MCX", "Banking"],
        }
    if tithi in (29, 30, 1):
        exact = tithi == 30
        return {
            "active": True,
            "phase": "NEW MOON",
            "tithi": tithi,
            "window": "exact Amavasya" if exact else "Amavasya watch window",
            "level": "HIGH" if exact else "MODERATE",
            "bias": "LOW VISIBILITY / REVERSAL RISK",
            "title": "New Moon / Amavasya",
            "explanation": "Lower visibility and thinner sentiment can amplify reversal risk.",
            "sectors": ["All sectors", "Banking", "Large Caps"],
        }
    return None


def reversal_alert(date_str, planets=None, tithi=None):
    """Return calendar windows containing date_str, or an inactive alert."""
    date = datetime.date.fromisoformat(date_str)
    active = []
    upcoming = []

    # Static REVERSAL_WINDOWS (predefined clusters)
    for window in REVERSAL_WINDOWS:
        start = datetime.date.fromisoformat(window["start"])
        end = datetime.date.fromisoformat(window["end"])
        if start <= date <= end:
            active.append({**window, "start": start.isoformat(), "end": end.isoformat()})
        horizon_end = date + datetime.timedelta(days=7)
        if date <= start <= horizon_end and start > date:
            upcoming.append({
                **window,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "days_ahead": (start - date).days,
            })

    # Dynamic Comprehensive Bullish/Bearish Reversal Windows
    all_dynamic_windows = get_all_bullish_reversal_windows(date, planets, tithi) if planets else []
    for pw in all_dynamic_windows:
        start = datetime.date.fromisoformat(pw["start"])
        end = datetime.date.fromisoformat(pw["end"])
        if start <= date <= end:
            active.append(pw)
        horizon_end = date + datetime.timedelta(days=7)
        if date <= start <= horizon_end and start > date:
            upcoming.append({
                **pw,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "days_ahead": (start - date).days,
            })

    transits = transit_alert(planets) if planets else []
    jupiter_analysis = jupiter_market_analysis(planets) if planets else None
    lunar_phase = lunar_phase_alert(tithi) if tithi is not None else None

    def _window_detail(window):
        """Return detailed astrological trigger/phenomenon for tooltip."""
        detail = window.get("title", "")
        if window.get("sectors"):
            detail += " | Sectors: " + ", ".join(window["sectors"])
        trigger = window.get("id", "")
        if "pushya" in trigger.lower():
            if "moon" in trigger.lower():
                detail += " | Trigger: Moon transiting Pushya nakshatra (Cancer 3°20'-16°40') - emotional sentiment reversal"
            elif "saturn" in trigger.lower():
                detail += " | Trigger: Saturn (Pushya lord) in own nakshatra - structural karmic reversal"
            elif "jupiter" in trigger.lower():
                detail += " | Trigger: Jupiter in Pushya (growth nakshatra) - expansive bullish reversal"
            elif "ravi" in trigger.lower():
                detail += " | Trigger: Ravi Pushya Yoga (Sunday + Moon in Pushya) - authority/leadership shift"
            elif "guru" in trigger.lower():
                detail += " | Trigger: Guru Pushya Yoga (Thursday + Moon in Pushya) - wisdom/expansion reversal"
            elif "malefic" in trigger.lower():
                detail += " | Trigger: Malefic planet in Pushya - bearish pressure on Saturn-ruled sectors"
            elif "benefic" in trigger.lower():
                detail += " | Trigger: Benefic planet in Pushya - bullish support for growth sectors"
            elif "saturn-jupiter" in trigger.lower():
                detail += " | Trigger: Saturn-Jupiter angle involving Pushya - major structural regime change"
            # New bullish reversal triggers
            elif "nak-" in trigger.lower() or "nakshatra" in trigger.lower():
                detail += " | Trigger: Planet in bullish nakshatra — micro reversal trigger"
            elif "venus-exit-virgo" in trigger.lower():
                detail += " | Trigger: Venus leaving debilitation (Virgo) — consumption/credit revival"
            elif "mercury-nak-" in trigger.lower():
                detail += " | Trigger: Mercury in own nakshatra (Ashlesha/Jyeshtha/Revati) — tech/banking clarity"
            elif "moon-sign-" in trigger.lower() or "moon-nak-" in trigger.lower():
                detail += " | Trigger: Moon in bullish sign/nakshatra — sentiment stabilization"
            elif "rahu-sep-sun" in trigger.lower() or "ketu-sep-sun" in trigger.lower():
                detail += " | Trigger: Node separating from Sun — narrative clearing, fear dissolving"
            elif "ketu-leave-cardinal" in trigger.lower():
                detail += " | Trigger: Ketu leaving 0° cardinal — market-sensitive degree cleared"
            elif "fullmoon-" in trigger.lower():
                detail += " | Trigger: Full Moon in stable sign — grounded sentiment extreme"
            elif "jup-sat-trine" in trigger.lower() or "jup-sat-sextile" in trigger.lower():
                detail += " | Trigger: Jupiter-Saturn harmonious aspect — stable expansion foundation"
            elif "rahu-jup-trine" in trigger.lower():
                detail += " | Trigger: Rahu-Jupiter trine — mass optimism, new narratives (AI/tech/EV)"
            elif "venus-jup-trine" in trigger.lower():
                detail += " | Trigger: Venus-Jupiter trine — liquidity + consumption boom"
            elif "mercury-jup-trine" in trigger.lower():
                detail += " | Trigger: Mercury-Jupiter trine — trading clarity, tech/banking optimism"
            elif "jupiter-direct" in trigger.lower():
                detail += " | Trigger: Jupiter direct after retrograde — growth resumes, risk appetite returns"
            elif "saturn-direct" in trigger.lower():
                detail += " | Trigger: Saturn direct after retrograde — fear cycles end, accumulation begins"
            elif "mercury-direct" in trigger.lower():
                detail += " | Trigger: Mercury direct after retrograde — trading clarity returns"
            elif "jupiter-combustion-end" in trigger.lower():
                detail += " | Trigger: Jupiter emerges from combustion — liquidity returns"
        elif "eclipse" in trigger.lower():
            detail += " | Trigger: Eclipse alignment - nodal karmic activation, sudden sentiment shift"
        elif "cluster" in trigger.lower():
            detail += " | Trigger: Multi-planetary cluster (retrogrades, combustions, nodal shifts) - compounding pressure"
        elif "double-direct" in trigger.lower():
            detail += " | Trigger: Mercury & Venus direct stations - liquidity return, trend resumption"
        elif "transit" in trigger.lower():
            detail += " | Trigger: Major planetary sign ingress/retrograde - trend structural change"
        return detail

    # Enrich active and upcoming windows with detail
    for w in active:
        w["detail"] = _window_detail(w)
    for w in upcoming:
        w["detail"] = _window_detail(w)

    bullish_active = bool(all_dynamic_windows) and any(
        datetime.date.fromisoformat(w["start"]) <= date <= datetime.date.fromisoformat(w["end"])
        for w in all_dynamic_windows
    )
    is_active = bool(active or transits or lunar_phase or (jupiter_analysis and jupiter_analysis["active"]))
    has_upcoming = bool(upcoming)
    combined = bool(lunar_phase and (active or transits))
    message = (
        "Selected date matches a calendar window, major transit, Pushya nakshatra signal, or Jupiter market-risk heuristic. "
        "Use technical, fundamental and risk checks before acting."
        if is_active else
        "Selected date is outside the configured high-impact windows and major planetary risk heuristics."
    )
    if has_upcoming and not is_active:
        message = "No active reversal window today. Upcoming high-impact windows are shown for the next 3 months."
    if combined:
        message += " Lunar phase overlaps another major alert; treat the combined signal as higher volatility."
    if bullish_active:
        message += " Bullish reversal signal active."

    # Build confluence analysis (only if planets provided)
    confluence = None
    if planets:
        moon_planet = next(p for p in planets if p["name"] == "Moon")
        sun_planet = next(p for p in planets if p["name"] == "Sun")
        tithi_val = tithi if tithi is not None else tithi_of(sun_planet["longitude"], moon_planet["longitude"])
        planets = all_planets_with_natures(planets, tithi_val, sun_planet["longitude"])
        vedha_map, _ = compute_vedhas(planets, school="classical")
        analysis = analyze(planets, vedha_map, _anchor_nakshatra("nse"), school="classical")
        sector_read_data = sector_read(vedha_map, planets)
        planet_sector_read_data = planet_sector_read(planets)

        confluence = build_confluence_report(
            analysis=analysis,
            sector_read=sector_read_data,
            planet_sector_read=planet_sector_read_data,
            reversal_data={
                "windows": active,
                "upcoming_windows": upcoming,
            },
            transits=transits,
            jupiter_analysis=jupiter_analysis,
            lunar_phase=lunar_phase,
        )

    # 3 months forward + 5 days = ~95 days
    WATCH_HORIZON_DAYS = 95

    all_windows = REVERSAL_WINDOWS + all_dynamic_windows
    watch_days = []
    for offset in range(WATCH_HORIZON_DAYS + 1):
        check_date = date + datetime.timedelta(days=offset)
        day_windows = []
        for window in all_windows:
            start = datetime.date.fromisoformat(window["start"])
            end = datetime.date.fromisoformat(window["end"])
            if start <= check_date <= end:
                day_windows.append({
                    "title": window["title"],
                    "level": window["level"],
                    "bias": window["bias"],
                    "detail": _window_detail(window),
                    "id": window.get("id", ""),
                    "start": window["start"],
                    "end": window["end"],
                    "sectors": window.get("sectors", []),
                })
        watch_days.append({
            "date": check_date.isoformat(),
            "offset": offset,
            "today": offset == 0,
            "windows": day_windows,
        })

    return {
        "active": is_active,
        "windows": active,
        "upcoming_windows": upcoming,
        "transits": transits,
        "jupiter_analysis": jupiter_analysis,
        "lunar_phase": lunar_phase,
        "combined_impact": combined,
        "message": message,
        "total_alerts": len(active) + len(upcoming) + len(transits) + (1 if lunar_phase else 0) + (1 if jupiter_analysis and jupiter_analysis["active"] else 0),
        "watch_days": watch_days,
        "confluence": confluence,
    }
