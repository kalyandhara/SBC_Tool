"""Modular aspect set library with configurable orbs, energies, and polarities.

Adapted from financial astrology research libraries for extensible transit and aspect scoring
while maintaining full backwards compatibility with classical Sarvatobhadra Chakra rules.
Exploratory research models only; not financial advice.
"""

CLASSICAL_ASPECTS = {
    0: {"angle": 0.0, "name": "Conjunction", "orb": 10.0, "energy": 2.0, "polarity": 2},
    30: {"angle": 30.0, "name": "Semi-sextile", "orb": 4.0, "energy": 1.0, "polarity": 1},
    45: {"angle": 45.0, "name": "Semi-square", "orb": 4.0, "energy": 1.0, "polarity": 0},
    60: {"angle": 60.0, "name": "Sextile", "orb": 6.0, "energy": 1.0, "polarity": 1},
    90: {"angle": 90.0, "name": "Square", "orb": 10.0, "energy": 2.0, "polarity": 0},
    120: {"angle": 120.0, "name": "Trine", "orb": 6.0, "energy": 1.5, "polarity": 1},
    135: {"angle": 135.0, "name": "Sesquiquadrate", "orb": 4.0, "energy": 1.0, "polarity": 0},
    150: {"angle": 150.0, "name": "Quincunx", "orb": 6.0, "energy": 2.0, "polarity": 1},
    180: {"angle": 180.0, "name": "Opposition", "orb": 10.0, "energy": 2.0, "polarity": 0},
}


def normalize_angle(deg: float) -> float:
    try:
        val = float(deg)
    except (TypeError, ValueError):
        return 0.0
    return val % 360.0


def angular_separation(deg1: float, deg2: float) -> float:
    d1 = normalize_angle(deg1)
    d2 = normalize_angle(deg2)
    diff = abs(d1 - d2)
    return 360.0 - diff if diff > 180.0 else diff


def evaluate_aspect(deg1: float, deg2: float, aspect_set: dict = CLASSICAL_ASPECTS) -> dict | None:
    """Evaluate separation between two longitudes against an aspect set, returning the tightest matching aspect.

    Tie-breaking rule for overlapping orbs: smallest orb_diff wins; if orb_diff is equal,
    lower canonical aspect angle wins.
    """
    sep = angular_separation(deg1, deg2)
    matches = []
    for base_angle, profile in aspect_set.items():
        orb_diff = abs(sep - profile["angle"])
        if orb_diff <= profile["orb"]:
            matches.append((orb_diff, base_angle, profile))
    if not matches:
        return None
    # Closest-orb priority (smallest orb_diff wins, then smallest base_angle)
    matches.sort(key=lambda x: (x[0], x[1]))
    _, _, best_profile = matches[0]
    return {
        "aspect": best_profile["name"],
        "angle": best_profile["angle"],
        "separation": sep,
        "orb_diff": abs(sep - best_profile["angle"]),
        "energy": best_profile["energy"],
        "polarity": best_profile["polarity"],
    }
