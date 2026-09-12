"""Panchanga daily-trend rule-book (Tithi + Phase -> Base Trend, then
Nakshatra modifier -> Final Trend).

This encodes the consensus "rule-book" the class arrived at for turning the
Panchanga into a simple intraday equity-index bias.  It is intentionally
small and tabular so the numbers can be tuned after a backtest.

Trend scale (ordered low -> high):
   -2  Super Bearish
   -1  Bearish
    0  Mixed / Range-Bound (no directional edge, high volatility)
   +1  Bullish
   +2  Super Bullish
"""

# Tithi name for tithi 1-30 (1-15 Shukla, 16-30 Krishna).
TITHI_NAMES = [
    "Pratipada", "Dvitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dvadashi", "Trayodashi", "Chaturdashi", "Purnima",
    "Pratipada", "Dvitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dvadashi", "Trayodashi", "Chaturdashi", "Amavasya",
]

# Base-trend bias sign by tithi index 1-15 (same for both pakshas, but the
# strength/sign differs).  This maps tithis 1..15 to a numeric bias.
# For tithis 16..30 we look up the same 1..15 offset and apply the Krishna
# adjustment.
_TITHI_BIAS = {
    1:  +1,   # Pratipada
    2:  -1,   # Dvitiya
    3:  +1,   # Tritiya
    4:  +1,   # Chaturthi
    5:   0,   # Panchami (mixed / both-sides)
    6:  +1,   # Shashthi
    7:   0,   # Saptami (mixed)
    8:  +1,   # Ashtami
    9:   0,   # Navami (mixed / high volatility)
    10: -1,   # Dashami (range-bound down)
    11:  0,   # Ekadashi (mixed / high volatility)
    12:  0,   # Dvadashi (mixed)
    13: +1,   # Trayodashi
    14:  0,   # Chaturdashi (range-bound either side)
    15: -1,   # Purnima (bearish sell-rise)
}

# "Super" tithis (give a full +2 / -2 when the phase reinforces them).
SUPER_SHUKLA = {1, 3, 4, 6, 8}      # Pratipada, Tritiya, Chaturthi, Shashthi, Ashtami
SUPER_KRISHNA = {1, 7, 11, 13, 15}  # Pratipada, Saptami, Ekadashi, Trayodashi, Amavasya


def tithi_bias(tithi):
    """Return the base numeric bias (-2..+2) for a tithi number 1-30."""
    # tithi 30 (Amavasya) is index 15 in the 1-15 offset table = Krishna.
    offset = tithi if tithi <= 15 else (30 if tithi == 30 else tithi - 15)
    bias = _TITHI_BIAS.get(offset, 0)
    if tithi <= 15:  # Shukla
        if tithi in SUPER_SHUKLA and bias == +1:
            return +2
        return bias
    # Krishna
    if offset == 30:  # Amavasya -> mirror Purnima (bearish)
        return -1
    # Invert the shukla bias sign for the dark half.
    bias = -bias
    if tithi in SUPER_KRISHNA and bias == -1:
        return -2
    return bias


# Nakshatra modifier: how the star layer adjusts the base-tithi bias.
# +1 = reinforces bullish, -1 = reinforces bearish, 0 = neutral.
NAKSHATRA_MOD = {
    "Ashwini":       +1,
    "Bharani":       -1,
    "Krittika":      +1,
    "Rohini":        +1,
    "Mrigashira":     0,
    "Ardra":          0,
    "Punarvasu":     +1,
    "Pushya":        +1,
    "Ashlesha":      -1,
    "Magha":          0,
    "P.Phalguni":    +1,
    "U.Phalguni":    +1,   # Uttara Phalguni: bullish
    "Hasta":          0,   # neutral
    "Chitra":         0,
    "Swati":         -1,   # bearish pull
    "Vishakha":      +1,   # bullish
    "Anuradha":       0,   # mixed / volatility
    "Jyeshtha":      +1,   # bullish
    "Mula":          -1,   # bearish pressure
    "P.Ashadha":      0,   # neutral
    "U.Ashadha":     +1,   # bullish
    "Shravana":      -1,   # modest bearish
    "Dhanishta":     +1,   # bullish
    "Shatabhisha":    0,   # range-bound
    "P.Bhadrapada":  -1,   # sell-off
    "U.Bhadrapada":  +1,   # bullish
    "Revati":         0,   # mixed / high volatility
    "Abhijit":       +1,   # auspicious gap -> slight bullish
}


_TREND_LABELS = {
    -2: "Super Bearish", -1: "Bearish", 0: "Mixed/Range",
    +1: "Bullish", +2: "Super Bullish",
}


def final_trend(tithi, nakshatra):
    """Combine tithi bias with the nakshatra modifier.

    Modifier rules (from the transcript):
      * neutral  (0) -> keep the base trend unchanged.
      * bullish  (+1) -> upgrade Bullish/Mixed -> Super Bullish; downgrade Bearish -> Mixed.
      * bearish  (-1) -> the opposite.
    Clamps to the -2..+2 range.
    """
    base = tithi_bias(tithi)
    mod = NAKSHATRA_MOD.get(nakshatra, 0)
    if mod == 0:
        return base
    if mod == +1:
        if base >= +1:
            return +2
        if base <= -1:
            return 0
        return +1          # base == 0 -> nudge bullish
    # mod == -1
    if base <= -1:
        return -2
    if base >= +1:
        return 0
    return -1              # base == 0 -> nudge bearish


def trend_label(score):
    return _TREND_LABELS.get(score, "Mixed/Range")


def panchang_signal(planets):
    """Compute (tithi, paksha, nakshatra, base_bias, final_score, final_label)
    from a list of planet dicts produced by sbc.planets.positions()."""
    sun = next(p for p in planets if p["name"] == "Sun")
    moon = next(p for p in planets if p["name"] == "Moon")
    from .nakshatra import tithi_of, paksha_of
    tithi = tithi_of(sun["longitude"], moon["longitude"])
    paksha = paksha_of(tithi)
    nakshatra = moon["nakshatra"]
    base = tithi_bias(tithi)
    score = final_trend(tithi, nakshatra)
    return {
        "tithi": tithi,
        "tithi_name": TITHI_NAMES[tithi - 1],
        "paksha": paksha,
        "nakshatra": nakshatra,
        "base_bias": base,
        "final_score": score,
        "final_label": trend_label(score),
    }