"""Canonical sector vocabulary and nakshatra -> sector keyword mapping.

Two layers, one source of truth:

* ``NAKSHATRA_SECTOR_KEYWORDS`` is the *display* layer -- the India-market
  phrasing shown in the UI (Daily Nakshatra + SBC Sector Confluence panel and
  its CSV export). Values here are free text for humans: "Banks, insurance".

* ``CANONICAL_SECTORS`` / ``SECTOR_ALIASES`` are the *scoring* layer. Every
  term any map anywhere uses resolves through ``canonical_sector()`` to exactly
  one canonical name, so contributions from different sources accumulate into
  the same score key instead of splitting ("Banking" from Jupiter and "Finance"
  from Punarvasu are both ``Banks``).

The scoring maps in ``sbc.lunar_forecast`` are derived from this module rather
than maintained separately, which is what keeps the two layers from drifting.

Terms that are not tradeable sectors -- "Growth", "Public Sentiment",
"Consolidation" -- are classified as ``THEMES``. They keep scoring exactly as
before but are tagged so callers can separate a sector call from a mood.

Covers all 27 nakshatras plus Abhijit (the 28-star ring entry), so every value
``nakshatra_of()`` or the RING_28 traversal can produce resolves to keywords.
"""

NAKSHATRA_SECTOR_KEYWORDS = {
    "Ashwini": ["Auto", "logistics", "EV"],
    "Bharani": ["Midcaps", "retail"],
    "Krittika": ["Metals", "oil", "energy"],
    "Rohini": ["Gold", "FMCG"],
    "Mrigashira": ["IT", "Telecom", "media"],
    "Ardra": ["Telecom", "IT", "cloud"],
    "Punarvasu": ["FMCG", "housing"],
    "Pushya": ["Banks", "large caps"],
    "Ashlesha": ["Pharma", "healthcare", "chemicals"],
    "Magha": ["PSU", "govt", "infra"],
    "P.Phalguni": ["Hotels", "travel", "consumption"],
    "U.Phalguni": ["Banks", "insurance"],
    "Hasta": ["Banks", "NBFC"],
    "Chitra": ["Cement", "infra", "construction"],
    "Swati": ["FMCG", "retail"],
    "Vishakha": ["Banks", "NBFC"],
    "Anuradha": ["Pharma", "chemicals"],
    "Jyeshtha": ["Defence", "power", "mining"],
    "Mula": ["Metals", "mining"],
    "P.Ashadha": ["Financials", "insurance"],
    "U.Ashadha": ["PSU", "defence"],
    "Abhijit": ["PSU", "govt", "large caps"],
    "Shravana": ["Large caps"],
    "Dhanishta": ["Metals", "steel", "energy"],
    "Shatabhisha": ["Pharma", "diagnostics"],
    "P.Bhadrapada": ["Speculative"],
    "U.Bhadrapada": ["IT", "Telecom", "utilities"],
    "Revati": ["Shipping", "logistics", "hospitality"],
}

# ---------------------------------------------------------------------------
# Canonical scoring vocabulary
# ---------------------------------------------------------------------------
#
# Canonical name -> every spelling that should score as it. Matching is
# case-insensitive and exact (no substring containment), so "IT" can never be
# swallowed by "Textiles".
#
# Keep names in the India-market phrasing the UI uses; that is the authoritative
# taxonomy for this tool.

SECTOR_ALIASES = {
    "Auto": ["Auto", "EV", "Mobility", "Auto & Mobility"],
    "Aviation": ["Aviation", "Airlines"],
    "Agriculture": ["Agriculture", "Agri", "Farming", "Agriculture (state-run)",
                    "Food & Agri", "Commodities (grains, pulses)"],
    "Alcohol": ["Alcohol", "Breweries"],
    "Banks": [
        "Banks", "Banking", "Bank Nifty", "Nifty Bank", "PSU Banks",
        "Private Banks", "NBFC", "Finance", "Financials",
        "Financial Services", "Insurance", "Finance & Banking",
        "Banks & Finance", "Banking & Management",
    ],
    "Chemicals": ["Chemicals", "Speciality Chemicals"],
    "Defence": ["Defence", "Defense", "Aerospace", "Defense & Aerospace"],
    "Education": ["Education", "Edtech"],
    "Energy": [
        "Energy", "Oil", "Gas", "Power", "Petroleum", "Oil & Gas",
        "Energy & Power", "Utilities", "Petroleum & Crude",
        "Coal & Railways",
    ],
    "Renewables": ["Renewables", "Solar", "Clean Energy"],
    "FMCG": [
        "FMCG", "Food", "Consumer", "Consumer Staples", "Staples",
        "Nourishment", "Consumption", "Consumer-FMCG",
    ],
    "Gold": [
        "Gold", "Precious Metals", "Gold/MCX", "MCX Gold", "Bullion",
        "Gold & Metals", "Gold (store of wealth)", "Gold (strong Mars)",
    ],
    "Hospitality": [
        "Hospitality", "Hotels", "Travel", "Tourism", "Leisure",
        "Travel & Aviation",
    ],
    "IT": [
        "IT", "Technology", "Software", "Cloud", "Communication", "Digital",
        "IT & Software", "IT & Media", "Semiconductors", "Consulting",
    ],
    "Infra": [
        "Infra", "Infrastructure", "Construction", "Cement", "Engineering",
        "Cement & Infra", "Defense & Infra", "Manufacturing",
    ],
    "Large Caps": ["Large Caps", "Large Cap", "Nifty 50", "Nifty"],
    "Luxury": ["Luxury", "Jewellery", "Gems", "Jewelry", "Luxury & Silver"],
    "Media": [
        "Media", "Entertainment", "Music", "Arts", "Design", "Fashion",
        "Cable & Media", "Cosmetics & Media",
    ],
    "Metals": [
        "Metals", "Steel", "Base Metals", "Metals & Mining",
        "Copper & Red Metals", "Steel & Energy",
        "Industrial / Base-Metal Index",
    ],
    "Midcaps": ["Midcaps", "Midcap", "Mid Caps"],
    "Mining": ["Mining"],
    "PSU": [
        "PSU", "Govt", "Government", "Authority", "Leadership", "Heritage",
        "Law", "Legal", "Contracts", "Sovereign", "Government-linked",
        "PSU & Sovereign", "PSU & Utilities",
    ],
    "Pharma": [
        "Pharma", "Healthcare", "Diagnostics", "Healthcare IT", "Medical",
        "Pharma & Alcohol",
    ],
    "Realty": ["Realty", "Real Estate", "Housing", "Realty & Housing"],
    "Retail": ["Retail", "Trade", "Retail & E-com", "Handicrafts", "Trade & Exports"],
    "Logistics": [
        "Logistics", "Shipping", "Transport", "Navigation", "Ports",
        "Shipping & Fisheries",
    ],
    "Speculative": ["Speculative", "Speculation", "Speculative Spikes"],
    "Telecom": [
        "Telecom", "Telecommunications", "Communication Infrastructure",
        "Digital Infrastructure",
    ],
    "Textiles": ["Textiles", "Apparel"],
}

CANONICAL_SECTORS = tuple(sorted(SECTOR_ALIASES))

# Terms that score but are not tradeable sectors -- market moods, qualities and
# planetary significations. They are kept (they carry real paksha and
# planet-nature signal) but classified apart from sector calls.
THEMES = {
    "Consolidation": "defensive posture",
    "Defensive": "defensive posture",
    "Expansion": "growth impulse",
    "Fluids": "liquidity",
    "Growth": "growth impulse",
    "Initiation": "new beginnings",
    "Isolation": "withdrawal",
    "Liquids": "liquidity",
    "Networking": "coordination",
    "New Ventures": "new beginnings",
    "Organizations": "coordination",
    "Corporate": "coordination",
    "Public Sentiment": "crowd mood",
    "Research": "discovery",
    "Spiritual": "withdrawal",
    "Spirituality": "withdrawal",
    "Water": "liquidity",
    # Signal-type tags that flow through the same normalizer but describe a
    # market condition, not a sector.
    "All sectors": "broad market",
    "Crash Risk / Corrections": "downside risk",
    "Reversal Risk": "downside risk",
    "Exit Zones": "downside risk",
    "Gap Plays": "momentum",
    "Intraday Momentum": "momentum",
    "Momentum Amplifiers": "momentum",
    "Startups": "new beginnings",
    "Water & Liquidity": "liquidity",
}

_ALIAS_LOOKUP = {
    alias.lower(): canon
    for canon, aliases in SECTOR_ALIASES.items()
    for alias in aliases
}
_THEME_LOOKUP = {name.lower(): name for name in THEMES}

__all__ = [
    "NAKSHATRA_SECTOR_KEYWORDS",
    "SECTOR_ALIASES",
    "CANONICAL_SECTORS",
    "THEMES",
    "keywords_for",
    "canonical_sector",
    "is_theme",
    "classify",
    "canonical_sectors_for",
    "normalize_sectors",
]


def keywords_for(nakshatra):
    """Return the display sector keyword list for a nakshatra ([] if unknown)."""
    return list(NAKSHATRA_SECTOR_KEYWORDS.get(nakshatra, []))


def canonical_sector(term):
    """Return the canonical sector name for *term*, or None if it is not one.

    A return of None means the term is a theme or simply unknown; use
    ``classify`` when the caller needs to tell those apart.
    """
    return _ALIAS_LOOKUP.get(str(term).strip().lower())


def is_theme(term):
    """True if *term* is a market theme rather than a tradeable sector."""
    return str(term).strip().lower() in _THEME_LOOKUP


def classify(term):
    """Return ``(kind, name)`` where kind is "sector", "theme" or "unknown"."""
    key = str(term).strip().lower()
    if key in _ALIAS_LOOKUP:
        return "sector", _ALIAS_LOOKUP[key]
    if key in _THEME_LOOKUP:
        return "theme", _THEME_LOOKUP[key]
    return "unknown", str(term).strip()


def canonical_sectors_for(nakshatra):
    """Canonical sector names for a nakshatra, deduped, display order kept.

    This is what the scoring maps are built from: the display keywords are the
    authoritative source, and this collapses them onto the scoring vocabulary.
    """
    seen = []
    for keyword in keywords_for(nakshatra):
        canon = canonical_sector(keyword)
        if canon and canon not in seen:
            seen.append(canon)
    return seen


def normalize_sectors(sectors):
    """Map arbitrary sector spellings onto the canonical vocabulary.

    Matching is exact and case-insensitive against SECTOR_ALIASES, then THEMES.
    There is deliberately no substring pass: the previous implementation's
    containment fallback made "IT" swallow "Exit Zones", "Water & Liquidity"
    and "Commodities (grains, pulses)", and made results depend on dict order.
    A name that matches nothing is passed through unchanged so no signal is
    silently dropped -- add it to SECTOR_ALIASES or THEMES to classify it.
    """
    out = []
    for s in sectors:
        kind, name = classify(s)
        if name not in out:
            out.append(name)
    return out
