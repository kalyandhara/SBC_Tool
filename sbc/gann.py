"""Gann / sector signal consolidation.

Provides a unified entry point for sector-specific signal endpoints
consuming positioned planets to avoid duplication in app.py.
"""

from .planets import positioned_planets


def get_sector_signals(sector, date_str, time_str="09:15", tz_name="Asia/Kolkata", school="classical"):
    """Return a unified sector signal dict.

    Args:
        sector: e.g. 'fmcg', 'tourism', 'chemical', 'alcohol'
        date_str: YYYY-MM-DD
        time_str: HH:MM
        tz_name: IANA timezone
        school: 'classical' or 'allthree'

    Returns:
        dict with planets, vedha, verdict, and sector metadata.
    """
    planets, ayanamsa, sun, moon, tithi = positioned_planets(date_str, time_str, tz_name)
    from .prediction import compute_vedhas, analyze
    from .nakshatra import sensitive_stars

    # Map sector to a representative anchor nakshatra
    sector_anchor = {
        "fmcg": "Mula",
        "tourism": "Ashwini",
        "chemical": "Krittika",
        "alcohol": "Punarvasu",
        "largecap": "Mula",
        "bullion": "Ashwini",
    }.get(sector.lower(), "Mula")

    vedha_map, ray_paths = compute_vedhas(planets, school=school)
    points = sensitive_stars(sector_anchor)
    analysis = analyze(planets, vedha_map, sector_anchor, school)
    from .prediction import sentiment_of
    verdict, strength = sentiment_of(analysis["net"])

    return {
        "sector": sector,
        "anchor_nakshatra": sector_anchor,
        "date": date_str,
        "time": time_str,
        "tz": tz_name,
        "school": school,
        "tithi": tithi,
        "ayanamsa": round(ayanamsa, 4),
        "planets": planets,
        "points": points,
        "vedha_hits": analysis["point_hits"],
        "net": analysis["net"],
        "verdict": verdict,
        "strength": strength,
        "scores": analysis["score"],
    }


__all__ = ["get_sector_signals"]
