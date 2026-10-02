"""Cable & telecom confluence analysis (Mercury / Rahu / Jupiter / Saturn).

Encodes the financial-astrology reading that cable & telecom (and broader
communication-infrastructure) sectors react to:

1. Mercury's dignity  - the classical significator of communication, networks,
   IT, media, trading. A strong / well-placed Mercury is read as favouring
   these sectors; a combust / debilitated / malefic-company Mercury is read as
   confusion, glitches, miscommunication and short-term volatility.

2. Rahu's placement  - Rahu amplifies technology, innovation, disruption,
   foreign capital and mass communication. In air/tech-friendly signs it puts
   communication infrastructure in the "obsession zone", attracting speculative
   flows.

3. Guru-Chandal yoga - Jupiter conjunct Rahu (within orb). Expansion (Jupiter)
   corrupted by obsession (Rahu): euphoric but ungrounded rallies in tech /
   communication themes that tend to reverse sharply.

4. Shrapit yoga       - Saturn conjunct Rahu (within orb). Karma (Saturn)
   entangled with the shadow node (Rahu): structural drag, policy/regulatory
   opacity and squeeze (over-leverage) that weighs on the sector.

This is symbolic correlation, not a causal mechanism.  Research aid only.
"""


# Mercury signification: communication, networks, IT, media, trading.
# Rahu signification: technology, innovation, disruption, foreign capital,
# mass communication / telecom-infrastructure obsession.
TELECOM_SECTORS = ["Telecom", "Cable & Media", "Communication Infrastructure",
                   "IT", "Media", "Digital Infrastructure"]

# Signs that make Mercury strong for communication themes (own + exalted).
MERCURY_STRONG_SIGNS = {"Gemini", "Virgo"}          # own signs
MERCURY_WEAK_SIGNS = {"Pisces"}                      # debilitation
# Signs where Rahu inflames tech / communication obsession (air + tech rulers).
RAHU_TECH_SIGNS = {"Gemini", "Aquarius", "Aries", "Leo", "Virgo"}

GURU_CHANDAL_ORB = 8.0      # Jupiter-Rahu conjunction orb (degrees)
SHRAPIT_ORB = 8.0           # Saturn-Rahu conjunction orb (degrees)


def _angle(lon1, lon2):
    return abs((lon1 - lon2 + 180) % 360 - 180)


def _get(planets, name):
    return next((p for p in planets if p["name"] == name), None)


def mercury_telecom_read(mercury, sun_lon):
    """Classify Mercury's condition for cable/telecom/communication themes.

    Returns (state, note) where state is one of:
      strong   - own/exalted sign, not combust, benefic company
      combust  - within the combustion orb of the Sun
      weak     - debilitated sign
      tense    - malefic (harsh company) or retrograde confusion
      neutral  - default
    """
    if mercury is None:
        return "neutral", "Mercury position unavailable"
    orb_note = f"Mercury in {mercury['sign']} {mercury['degree']:.2f}° ({mercury['nakshatra']})"

    reasons = []
    if mercury["sign"] in MERCURY_STRONG_SIGNS:
        state = "strong"
        reasons.append("own sign")
    elif mercury["sign"] in MERCURY_WEAK_SIGNS:
        state = "weak"
        reasons.append("debilitated")
    else:
        state = "neutral"

    # Combustion (Sun) blanks out Mercury's expression.
    from .planets import COMBUST_ORB
    orb = COMBUST_ORB.get("Mercury", 14.0)
    if _angle(mercury["longitude"], sun_lon) < orb:
        state = "combust"
        reasons.append("combust")

    # Harsh company flips a natural benefic; retrograde = confusion.
    if mercury.get("nature") == "malefic":
        state = "tense"
        reasons.append("harsh company")
    if mercury["retrograde"]:
        state = "tense"
        reasons.append("retrograde")

    note = orb_note + (" — " + ", ".join(reasons) if reasons else "")
    return state, note


def rahu_telecom_read(rahu):
    """Classify Rahu's influence on tech / communication themes."""
    if rahu is None or rahu.get("sign") is None:
        return "neutral", "Rahu position unavailable"
    if rahu["sign"] in RAHU_TECH_SIGNS:
        return "amplify", f"Rahu in {rahu['sign']} {rahu['degree']:.2f}° ({rahu['nakshatra']}) — tech/communication obsession zone"
    return "neutral", f"Rahu in {rahu['sign']} {rahu['degree']:.2f}° ({rahu['nakshatra']}) — no special tech emphasis"


def detect_guru_chandal(jupiter, rahu):
    """Guru-Chandal yoga: Jupiter conjunct Rahu (euphoric, ungrounded tech rally)."""
    if jupiter is None or rahu is None:
        return None
    sep = _angle(jupiter["longitude"], rahu["longitude"])
    if sep <= GURU_CHANDAL_ORB:
        return {
            "active": True,
            "name": "Guru-Chandal (Jupiter-Rahu)",
            "separation": round(sep, 2),
            "note": f"Jupiter in {jupiter['sign']} conj Rahu in {rahu['sign']} ({sep:.1f}°) — expansion corrupted by obsession; euphoric, ungrounded tech/communication rallies prone to sharp reversal.",
            "sectors": TELECOM_SECTORS,
            "bias": "VOLATILE BULLISH (reversal risk)",
        }
    return None


def detect_shrapit(saturn, rahu):
    """Shrapit yoga: Saturn conjunct Rahu (structural drag / squeeze / opacity)."""
    if saturn is None or rahu is None:
        return None
    sep = _angle(saturn["longitude"], rahu["longitude"])
    if sep <= SHRAPIT_ORB:
        return {
            "active": True,
            "name": "Shrapit (Saturn-Rahu)",
            "separation": round(sep, 2),
            "note": f"Saturn in {saturn['sign']} conj Rahu in {rahu['sign']} ({sep:.1f}°) — karma entangled with the shadow node; structural drag, policy/regulatory opacity, over-leverage squeeze.",
            "sectors": TELECOM_SECTORS,
            "bias": "BEARISH (structural drag)",
        }
    return None


def telecom_confluence(planets):
    """Assemble the cable & telecom confluence read for a set of positioned planets.

    Returns a dict with Mercury condition, Rahu condition, active yogas, an
    overall bias, and a human-readable narrative string.
    """
    by_name = {p["name"]: p for p in planets}
    sun = by_name.get("Sun", {})
    sun_lon = sun.get("longitude", 0.0)
    mercury = by_name.get("Mercury")
    rahu = by_name.get("Rahu")
    jupiter = by_name.get("Jupiter")
    saturn = by_name.get("Saturn")

    mercury_state, mercury_note = mercury_telecom_read(mercury, sun_lon)
    rahu_state, rahu_note = rahu_telecom_read(rahu)

    guru_chandal = detect_guru_chandal(jupiter, rahu)
    shrapit = detect_shrapit(saturn, rahu)
    yogas = [y for y in (guru_chandal, shrapit) if y]

    # Weight Mercury + Rahu + yogas into a rough bias.
    bullish = 0.0
    bearish = 0.0
    if mercury_state == "strong":
        bullish += 1.0
    elif mercury_state in ("combust", "tense", "weak"):
        bearish += 0.75
    if rahu_state == "amplify":
        bullish += 0.5
    for y in yogas:
        if "BEARISH" in y["bias"]:
            bearish += 1.0
        elif "BULLISH" in y["bias"]:
            bullish += 0.5
            bearish += 0.25   # reversal risk embedded

    net = round(bullish - bearish, 2)
    if net > 0.25:
        bias = "BULLISH"
    elif net < -0.25:
        bias = "BEARISH"
    else:
        bias = "MIXED / VOLATILE"

    narrative = _narrative(mercury_state, mercury_note, rahu_state, rahu_note, yogas, bias)

    return {
        "sectors": TELECOM_SECTORS,
        "mercury": {"state": mercury_state, "note": mercury_note},
        "rahu": {"state": rahu_state, "note": rahu_note},
        "yogas": yogas,
        "guru_chandal": guru_chandal,
        "shrapit": shrapit,
        "bias": bias,
        "net": net,
        "bullish_weight": round(bullish, 2),
        "bearish_weight": round(bearish, 2),
        "narrative": narrative,
    }


def _narrative(mercury_state, mercury_note, rahu_state, rahu_note, yogas, bias):
    parts = [mercury_note, rahu_note]
    if mercury_state == "strong":
        parts.append("Favourable Mercury — expect momentum in telecom/cable/IT and communication infrastructure.")
    elif mercury_state in ("combust", "tense", "weak"):
        parts.append("Weak/combust Mercury — glitches, miscommunication and volatility in telecom/cable names rather than clean trends.")
    if rahu_state == "amplify":
        parts.append("Rahu amplifies tech/communication — speculative flows into optical fibre, digital infra and cable/telecom.")
    for y in yogas:
        parts.append(y["name"] + ": " + y["note"])
    parts.append(f"Net read: {bias}.")
    return " ".join(parts)


def format_telecom_confluence(result):
    """Render the telecom confluence result as a list of text lines."""
    if not result:
        return ["No telecom confluence data."]
    lines = [
        f"Bias: {result['bias']} (Net {result['net']:+.2f})",
        f"Mercury: {result['mercury']['note']}",
        f"Rahu: {result['rahu']['note']}",
    ]
    for y in result["yogas"]:
        lines.append(f"Yoga: {y['name']} ({y['separation']}°) — {y['bias']}")
    lines.append(f"Narrative: {result['narrative']}")
    return lines
