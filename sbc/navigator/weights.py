"""Hand-set research tables. Written before any return was examined; never fitted.
Change any value: bump WEIGHTS_VERSION and disclose the new table as in-sample."""
WEIGHTS_VERSION = "nav-1"
TERM_WEIGHTS = {"transit": .25, "moon": .20, "dasha": .20, "strength": .15, "histval": .10, "vol": .10}
ASPECTS = {"CONJ": 0.0, "SXT": 60.0, "SQ": 90.0, "TRI": 120.0, "OPP": 180.0}
ORB = 3.0
TRANSIT_BODIES = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
BENEFIC = {"Jupiter": 1.0, "Venus": .75, "Moon": .5, "Mercury": .4, "Sun": .1,
           "Mars": -.5, "Saturn": -.875, "Rahu": -.5, "Ketu": -.5}
NODE_FACTOR = 0.5
ASPECT_SIGN = {"TRI": 1.0, "SXT": .6, "CONJ": None, "SQ": -1.0, "OPP": -1.0}
_EXPLICIT = {("Jupiter", "Jupiter", "TRI"): 40.0, ("Mars", "Mercury", "SQ"): -20.0,
             ("Saturn", "Moon", "OPP"): -35.0}


def ASPECT_WEIGHT(planet, point, aspect) -> float:
    if (planet, point, aspect) in _EXPLICIT:
        return _EXPLICIT[(planet, point, aspect)]
    b = BENEFIC[planet]
    sign = ASPECT_SIGN[aspect]
    w = 30.0 * b if sign is None else 20.0 * sign * (1.0 + b if sign > 0 else 1.0 - b)
    # Ketu always mirrors Rahu, so each node carries half and the axis counts once.
    # Applies to a transiting node and to a natal Rahu/Ketu point; a node-to-node
    # contact gets both factors (0.25).
    if planet in ("Rahu", "Ketu"):
        w *= NODE_FACTOR
    if point in ("Rahu", "Ketu"):
        w *= NODE_FACTOR
    return w


# Moon Sentiment Score parts, summing to at most +/-100.
MOON_PHASE = 30.0    # waxing +, waning -, scaled by illumination distance from full/new
MOON_TITHI_RIKTA = -20.0   # tithis 4, 9, 14 of either paksha
MOON_TITHI_NANDA = 20.0    # tithis 1, 6, 11
MOON_SIGN = {0: 15, 1: 25, 2: 5, 3: 20, 4: 5, 5: 0, 6: 10, 7: -25, 8: 10, 9: 0, 10: 0, 11: -10}  # Aries=0
MOON_NAKSHATRA_DRUVA = 25.0   # fixed stars
MOON_NAKSHATRA_UGRA = -25.0   # fierce stars
DRUVA = {"Rohini", "U.Phalguni", "U.Ashadha", "U.Bhadrapada"}  # sbc.nakshatra spellings
UGRA = {"Bharani", "Magha", "P.Phalguni", "P.Ashadha", "P.Bhadrapada"}
DASHA_LORD = {"Jupiter": 40, "Venus": 30, "Mercury": 20, "Moon": 15, "Sun": 5, "Mars": -10,
              "Ketu": -20, "Rahu": -25, "Saturn": -30}
DASHA_LEVELS = {"maha": .5, "antar": .3, "pratyantar": .2}
STRENGTH_EXALTED, STRENGTH_DEBILITATED, STRENGTH_COMBUST, STRENGTH_RETRO = 20.0, -20.0, -15.0, 5.0
HIST_MIN_YEARS, HIST_HORIZON = 3, 5
