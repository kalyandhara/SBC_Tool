"""Bias scaling and synthetic Western zodiac-dignity bias helpers."""

# Exaltation / debilitation signs for the Western (zodiac-dignity) line.
_WESTERN_EXALT = {
    "Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
    "Jupiter": 3, "Venus": 11, "Saturn": 6, "Rahu": 1, "Ketu": 7
}
_WESTERN_DEBIL = {
    "Sun": 6, "Moon": 7, "Mars": 3, "Mercury": 11,
    "Jupiter": 9, "Venus": 5, "Saturn": 0, "Rahu": 7, "Ketu": 1
}


def _bias_scale(net):
    """Map a net astro score (roughly -6..+6) to a 0..6 bias scale.

    net=0 -> 3.0 (neutral midpoint), net=+2 -> 4.0 (bullish), net=-2 -> 2.0
    (bearish). Clamped to [0, 6].
    """
    return round(min(6.0, max(0.0, 3.0 + net / 2.0)), 4)


def _western_bias(planets):
    """Synthetic Western (tropical/zodiac-dignity) bias line.

    Sums planetary essential dignity: exaltation is strongly bullish,
    debilitation strongly bearish, then blends in each planet's signed
    strength. Scales to the same 0..6 range as the Vedic schools. The
    Western school is a light proxy (no true tropical zodiac here) so the
    three lines stay comparable in magnitude.
    """
    total = 0.0
    for p in planets:
        name = p.get("name")
        sign_idx = p.get("sign_index")
        if name in _WESTERN_EXALT and sign_idx == _WESTERN_EXALT[name]:
            total += 2.0
        elif name in _WESTERN_DEBIL and sign_idx == _WESTERN_DEBIL[name]:
            total -= 2.0
        else:
            total += (p.get("signed_strength", 0.0) or 0.0)
    # Normalise: 9 bodies, theoretical max ~ +4, min ~ -4.
    net = max(-6.0, min(6.0, total))
    return _bias_scale(net)


__all__ = ["_bias_scale", "_western_bias", "_WESTERN_EXALT", "_WESTERN_DEBIL"]