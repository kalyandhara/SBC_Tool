"""Venus vedha events in the Sarvatobhadra Chakra (SBC).

Detects when Venus — the soft benefic of liquidity, luxury, harmony and
sentiment — casts a vedha (piercing) ray onto the Chitra nakshatra cell or
the Libra rashi cell, and produces the astro-finance interpretation.

Reference interpretation (from research notes):

  Venus vedha -> Chitra (Mars-ruled, architectural/design):
    * technical patterns become very reliable ("constructed beauty")
    * breakouts look textbook but may be deceptive (Mars energises,
      Venus beautifies -> false glamour rallies)
    * premium / luxury / design / real-estate-finishing sectors outperform
    * traders become aesthetic and impulsive (overtrust symmetry, enter early)

  Venus vedha -> Libra (Venus's own sign, balance/harmony):
    * trend stabilises, volatility drops
    * pullbacks become shallow; mean-reversion pairs-trading works well
    * traders become patient, wait for confirmation, prefer ranges/channels

  Venus vedha on BOTH -> "designed harmony": visually clean markets,
  soft but structured sentiment, best sectors = beauty/luxury/FMCG premium/
  fashion/jewellery/media/consumer-discretionary; main risk = beautiful but
  deceptive moves.
"""

from .chakra import NAKSHATRA_CELL, RASHI_CELL
from .prediction import compute_vedhas

# Sectors favoured under each event, per the research notes.
CHITRA_SECTORS = [
    "Luxury & Cosmetics", "Architecture & Design", "Real Estate (finishing)",
    "Fashion & Jewellery", "Media & Entertainment",
]
LIBRA_SECTORS = [
    "Consumer (FMCG premium)", "High-end Consumer Discretionary",
    "Fashion & Jewellery", "Media & Entertainment",
]

_NASHRATRA_MEANINGS = {"Chitra": "design/architecture"}


def venus_vedha_events(planets, vedha_map=None, school="classical"):
    """Detect Venus vedha onto Chitra (nakshatra) and/or Libra (rashi).

    Returns a dict with boolean flags and the interpretation text blocks,
    or None if neither event is active.
    """
    if vedha_map is None:
        vedha_map, _ = compute_vedhas(planets, school=school)

    venus = next((p for p in planets if p["name"] == "Venus"), None)
    if venus is None:
        return None

    hits = vedha_map.get("Venus", [])
    chitra_cell = NAKSHATRA_CELL.get("Chitra")
    libra_cell = RASHI_CELL.get("Libra")

    hits_chitra = any((h["row"], h["col"]) == chitra_cell for h in hits)
    hits_libra = any((h["row"], h["col"]) == libra_cell for h in hits)

    if not (hits_chitra or hits_libra):
        return None

    venus_lon = venus["longitude"]
    dignity = ", ".join(venus.get("dignity_reasons", [])) or "neutral dignity"
    retro = " retrograde" if venus["retrograde"] else ""

    return {
        "active": True,
        "venus_position": f"Venus in {venus['sign']} {venus['degree']:.2f}° "
                          f"({venus['nakshatra']}){retro}",
        "dignity": dignity,
        "hits_chitra": hits_chitra,
        "hits_libra": hits_libra,
        "chitra_sectors": CHITRA_SECTORS if hits_chitra else [],
        "libra_sectors": LIBRA_SECTORS if hits_libra else [],
        "combined": hits_chitra and hits_libra,
        "risk": ("Beautiful but deceptive moves: Venus beautifies traps, "
                 "Chitra's Mars energises false breakouts, Libra delays "
                 "confirmation." if hits_chitra or hits_libra else ""),
    }


def format_venus_vedha(event):
    """Render a Venus vedha event as text lines for the commentary."""
    if not event or not event.get("active"):
        return []

    lines = [
        "VENUS VEDHA EVENT (SBC): %s" % event["venus_position"],
        "  Dignity: %s" % event["dignity"],
    ]

    if event["hits_chitra"]:
        lines += [
            "  -> Venus vedha on CHITRA (Mars-ruled, architectural):",
            "     • Technical patterns look perfect; charts behave 'cleanly'.",
            "     • Breakouts are textbook but may be deceptive (false-glamour rallies).",
            "     • Premium sectors outperform; sentiment turns 'aesthetic'.",
            "     • Trader bias: overtrust symmetry, enter early because the chart looks right.",
            "     • Sectors: %s." % ", ".join(event["chitra_sectors"]),
        ]
    if event["hits_libra"]:
        lines += [
            "  -> Venus vedha on LIBRA (Venus's own sign, balance/harmony):",
            "     • Trend stabilises; volatility drops; pullbacks become shallow.",
            "     • Mean-reversion and pairs-trading work well.",
            "     • Trader bias: patient, wait for confirmation, prefer ranges/channels.",
            "     • Sectors: %s." % ", ".join(event["libra_sectors"]),
        ]
    if event["combined"]:
        lines += [
            "  -> COMBINED Chitra + Libra: 'designed harmony' — visually clean markets,",
            "     soft but structured sentiment, best sectors = beauty/luxury/FMCG premium.",
        ]
    lines += [
        "  Risk: %s" % event["risk"],
        "  Net effect: supportive/stabilising (soft benefic), unless malefics also hit the star.",
    ]
    return lines