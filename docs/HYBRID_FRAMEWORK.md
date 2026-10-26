# Hybrid Vedic-Western Framework

## Overview

The SBC_Tool uses a **hybrid Vedic-Western framework** to enable validation of financial astrology research examples while maintaining the precision of Vedic nakshatra-based timing.

## Rationale

Traditional Vedic astrology does not use outer planets (Uranus, Neptune, Pluto). However, financial astrology research (e.g., the speech's examples) relies on these planets for macro-cycle analysis:

- **Saturn-Pluto conjunctions** (systemic crises): 2020 COVID crash, 1982 recession
- **Neptune in Aquarius** (technology bubbles): 1990s dot-com bubble
- **Uranus-Mars aspects** (volatility): Flash crashes, sudden market moves

To enable validation of these examples while preserving the Vedic core, we adopt a hybrid approach.

## Implementation

### Core Engine: Vedic Sidereal
- **Zodiac:** Sidereal Lahiri ayanamsa (traditional Vedic)
- **Primary planets:** Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu
- **Timing system:** Sarvatobhadra Chakra, nakshatras, vedha
- **Dignity:** Vedic exaltation/debilitation for classical planets

### Macro-Cycle Layer: Western Outer Planets
- **Zodiac:** Sidereal Lahiri ayanamsa (consistent with core)
- **Outer planets:** Uranus, Neptune, Pluto (geocentric sidereal)
- **Dignity:** Western astrology equivalents adapted to sidereal
- **Purpose:** Macro-cycle analysis, systemic crisis detection, bubble identification

### Lunar Bias: Academic Research
- **Convention:** New Moon = BULLISH, Full Moon = BEARISH
- **Source:** University of Michigan lunar cycle studies
- **Rationale:** Aligns with empirical research on market returns
- **Note:** This reverses traditional Vedic interpretation

### Economic & Sentiment Data: Validation Layer
- **Economic data:** FRED API (US rates), RBI (Indian rates)
- **Sentiment data:** VIX, news sentiment, Twitter (keyword-based)
- **Purpose:** Validate psychological mechanism premise
- **Integration:** Correlate astro signals with actual economic/sentiment conditions

## Compatibility

### Backward Compatibility
- **Existing Vedic calculations:** Unchanged (core 7 planets + nodes)
- **Outer planets:** Additive, not replacements
- **API endpoints:** Existing endpoints unchanged
- **Database schemas:** Only additions, no breaking changes

### Framework Choice
- **Decision:** Always hybrid (no user toggle)
- **Rationale:** Simpler implementation, consistent behavior
- **Future:** Could add Vedic-only mode if requested by users

## Technical Details

### Outer Planet Dignity
Outer planets do not have traditional Vedic exaltation/debilitation. We use Western astrology equivalents adapted to sidereal Lahiri:

```python
EXALT = {
    "Uranus": 10,  # Scorpio (Western: Aquarius)
    "Neptune": 8,  # Cancer (Western: Pisces)
    "Pluto": 9,    # Leo (Western: Scorpio)
}
DEBIL = {
    "Uranus": 4,   # Taurus (Western: Leo)
    "Neptune": 2,  # Taurus (Western: Virgo)
    "Pluto": 3,    # Cancer (Western: Taurus)
}
```

### Outer Planet Transit Rules
Each outer planet has sign-based bias and sector mappings:

- **Uranus:** Volatility/disruption themes (Tech, Startups, Defense)
- **Neptune:** Bubble/illusion themes (Tech, Crypto, Media)
- **Pluto:** Transformation/destruction themes (Banks, Government, Infrastructure)

### Outer Planet Triggers
Outer planet aspects are included in backtest scoring:

- `saturn_pluto_conjunction` (weight: 4) - Systemic crisis
- `neptune_aquarius_ingress` (weight: 3) - Bubble risk
- `uranus_mars_aspect` (weight: 3) - Volatility

## Validation Strategy

### Historical Examples
The hybrid framework enables validation of speech examples:

1. **Saturn-Pluto 2020:** Check conjunction date and COVID crash correlation
2. **Neptune-Aquarius 1999-2000:** Check Neptune position and dot-com bubble
3. **Uranus-Mars volatility:** Check aspects and flash crash correlation

### Economic Correlation
- **Saturn signals:** Correlate with actual interest rate changes
- **Jupiter signals:** Correlate with earnings data
- **Acceptance criteria:** Correlation >= 0.3

### Sentiment Correlation
- **Planetary positions:** Correlate with VIX, news sentiment
- **Mercury retrograde:** Correlate with negative sentiment (glitches, miscommunication)
- **Acceptance criteria:** Correlation >= 0.3

## Documentation

### User-Facing Documentation
- **README.md:** Hybrid framework overview
- **API Reference:** New endpoints for economic/sentiment data
- **Debate Document:** Tracks Vedic vs hybrid discussion

### Developer Documentation
- **This file:** Technical implementation details
- **Exact Anchor Times:** Research into exact birth times
- **Validation Reports:** Historical validation results

## Future Enhancements

### Potential Additions
- Tropical zodiac option for outer planets (Western purists)
- User toggle for Vedic-only vs hybrid mode
- Additional outer planet aspects (Uranus-Neptune, Neptune-Pluto)
- Station detection for outer planets

### Research Opportunities
- Compare hybrid vs Vedic-only performance
- Validate outer planet dignity in sidereal vs tropical
- Test lunar bias reversal on different markets (US, India, global)
- Correlate outer planet cycles with long-term market regimes

## References

### Academic Research
- University of Michigan lunar cycle studies (New Moon = higher returns)
- Financial astrology research papers on outer planets
- Behavioral finance literature on market psychology

### Traditional Sources
- Vedic astrology texts (Brihat Parashara Hora Shastra, etc.)
- Western astrology texts (outer planet interpretations)
- Swiss Ephemeris documentation (geocentric vs heliocentric)

## Conclusion

The hybrid framework enables SBC_Tool to validate financial astrology research examples while maintaining the precision of Vedic nakshatra-based timing. This approach respects both traditional Vedic methodology and modern financial astrology research.

---

**Last Updated:** 2026-10-13 (Phase 1-3 implementation complete)
