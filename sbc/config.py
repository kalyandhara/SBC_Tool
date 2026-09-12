"""Central configuration for SBC engine rules and constants."""

# Moon rashi trend mapping
RASHI_TREND = {
    "Aries": "bullish",
    "Taurus": "bullish",
    "Gemini": "bearish",
    "Cancer": "bearish",
    "Leo": "bullish",
    "Virgo": "bearish",
    "Libra": "bearish",
    "Scorpio": "bullish",
    "Sagittarius": "bullish",
    "Capricorn": "bullish",
    "Aquarius": "bearish",
    "Pisces": "bearish",
}

# Western dignity tables
_WESTERN_EXALT = {
    "Sun": "Aries",
    "Moon": "Taurus",
    "Mercury": "Virgo",
    "Venus": "Pisces",
    "Mars": "Capricorn",
    "Jupiter": "Cancer",
    "Saturn": "Libra",
    "Rahu": "",
    "Ketu": "",
}

_WESTERN_DEBIL = {
    "Sun": "Libra",
    "Moon": "Scorpio",
    "Mercury": "Pisces",
    "Venus": "Virgo",
    "Mars": "Cancer",
    "Jupiter": "Capricorn",
    "Saturn": "Aries",
    "Rahu": "",
    "Ketu": "",
}

# Sector mappings for backtests
SECTOR_NAME_MAP = {
    "^NSEBANK": "Nifty Bank",
    "^CNXIT": "Nifty IT",
    "^CNXAUTO": "Nifty Auto",
    "^CNXMETAL": "Nifty Metal",
    "^CNXFMCG": "Nifty FMCG",
    "^CNXPHARMA": "Nifty Pharma",
    "^CNXENERGY": "Nifty Energy",
    "^CNXREALTY": "Nifty Realty",
    "^NSEI": "Nifty Large Caps",
}

# Anchor presets
ANCHOR_PRESETS = [
    {"key": "nse", "name": "NSE"},
    {"key": "bse", "name": "BSE"},
    {"key": "nifty", "name": "Nifty"},
    {"key": "sensex", "name": "Sensex"},
    {"key": "india", "name": "India"},
]


__all__ = [
    "RASHI_TREND",
    "_WESTERN_EXALT",
    "_WESTERN_DEBIL",
    "SECTOR_NAME_MAP",
    "ANCHOR_PRESETS",
]
