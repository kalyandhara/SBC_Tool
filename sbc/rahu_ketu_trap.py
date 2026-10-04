"""
Rahu/Ketu Trap Calendar Engine
Industry-wise daily trap detection based on nodal transits, vedha, and lunar confluence.
Backtestable with configurable rule weights.
"""

from __future__ import annotations

import datetime
from collections.abc import Callable
from dataclasses import asdict, dataclass

from sbc.backtest import _julian_at_noon
from sbc.market_holidays import is_trading_day
from sbc.nakshatra import NAKSHATRAS_27
from sbc.planets import positions

# Industry → ruling planet mapping (customizable)
INDUSTRY_RULING_PLANET: dict[str, str] = {
    "BANKING": "Mercury",
    "FINANCIAL SERVICES": "Mercury",
    "IT": "Mercury",
    "PHARMA": "Jupiter",
    "HEALTHCARE": "Jupiter",
    "ENERGY": "Sun",
    "OIL & GAS": "Sun",
    "METALS": "Mars",
    "MINING": "Mars",
    "AUTO": "Mars",
    "FMCG": "Venus",
    "CONSUMER DURABLES": "Venus",
    "REAL ESTATE": "Saturn",
    "CONSTRUCTION": "Saturn",
    "PSU BANKS": "Mercury",
    "POWER": "Sun",
    "TELECOM": "Mercury",
    "MEDIA": "Mercury",
    "DEFENCE": "Mars",
}

# Rule weights v1
WEIGHTS = {
    "node_proximity": 3,
    "vedha": 2,
    "moon_conjunction": 2,
    "tithi": 1,
    "node_speed": 1,
}

@dataclass
class TrapSignal:
    date: str
    industry: str
    ruling_planet: str
    rahu_nakshatra: str
    ketu_nakshatra: str
    moon_nakshatra: str
    tithi: int
    score: int
    level: str
    reasons: list[str]

def _angular_distance(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)

def _get_planet_longitude(planets: list[dict], name: str) -> float:
    for p in planets:
        if p["name"] == name:
            return float(p["longitude"])
    raise ValueError(f"{name} missing from the planet list")

def _nakshatra_of_longitude(lon: float) -> str:
    # Simplified mapping: 27 nakshatras each 13.333°
    idx = int(lon // (360/27))
    idx = idx % 27
    return NAKSHATRAS_27[idx]

def compute_daily_trap(date_str: str, industries: list[str] | None = None) -> list[TrapSignal]:
    jul = _julian_at_noon(date_str)
    planets, ayanamsa = positions(jul)

    # Get Rahu/Ketu/Moon positions
    rahu_lon = _get_planet_longitude(planets, "Rahu")
    ketu_lon = _get_planet_longitude(planets, "Ketu")
    moon_lon = _get_planet_longitude(planets, "Moon")
    sun_lon = _get_planet_longitude(planets, "Sun")

    # Tithi
    from sbc.nakshatra import tithi_of
    tithi = tithi_of(sun_lon, moon_lon)

    rahu_nak = _nakshatra_of_longitude(rahu_lon) if rahu_lon is not None else "Unknown"
    ketu_nak = _nakshatra_of_longitude(ketu_lon) if ketu_lon is not None else "Unknown"
    moon_nak = _nakshatra_of_longitude(moon_lon) if moon_lon is not None else "Unknown"

    if industries is None:
        industries = list(INDUSTRY_RULING_PLANET.keys())

    signals = []
    for industry in industries:
        ruling = INDUSTRY_RULING_PLANET.get(industry.upper(), "Saturn")
        planet_lon = _get_planet_longitude(planets, ruling)

        score = 0
        reasons = []

        # Node proximity
        if planet_lon is not None:
            d_rahu = _angular_distance(planet_lon, rahu_lon)
            d_ketu = _angular_distance(planet_lon, ketu_lon)
            if d_rahu <= 5 or d_ketu <= 5:
                score += WEIGHTS["node_proximity"]
                reasons.append(f"Rahu/Ketu within 5° of {ruling}")

        # Vedha proxy: same nakshatra or 180°
        if planet_lon is not None:
            planet_nak = _nakshatra_of_longitude(planet_lon)
            if planet_nak in (rahu_nak, ketu_nak):
                score += WEIGHTS["vedha"]
                reasons.append(f"{ruling} in Rahu/Ketu nakshatra")
            if _angular_distance(planet_lon, rahu_lon) >= 175 and _angular_distance(planet_lon, rahu_lon) <= 185:
                score += WEIGHTS["vedha"]
                reasons.append(f"Rahu opposite {ruling}")

        # Moon conjunction
        if moon_lon is not None and planet_lon is not None and (
                _angular_distance(moon_lon, rahu_lon) <= 10
                or _angular_distance(moon_lon, ketu_lon) <= 10):
            score += WEIGHTS["moon_conjunction"]
            reasons.append("Moon conjunct Rahu/Ketu")

        # Tithi
        if 8 <= tithi <= 14:
            score += WEIGHTS["tithi"]
            reasons.append("Krishna Paksha 8-14")

        # Level
        if score >= 9:
            level = "RED"
        elif score >= 6:
            level = "ORANGE"
        elif score >= 3:
            level = "AMBER"
        else:
            level = "GREEN"

        signals.append(TrapSignal(
            date=date_str,
            industry=industry,
            ruling_planet=ruling,
            rahu_nakshatra=rahu_nak,
            ketu_nakshatra=ketu_nak,
            moon_nakshatra=moon_nak,
            tithi=tithi,
            score=score,
            level=level,
            reasons=reasons
        ))

    return signals

def generate_calendar(start_date: str, end_date: str, industries: list[str] | None = None) -> dict:
    start = datetime.date.fromisoformat(start_date)
    end = datetime.date.fromisoformat(end_date)
    delta = datetime.timedelta(days=1)
    calendar = []
    cur = start
    while cur <= end:
        # Skip days NSE is closed (weekends and exchange holidays)
        if not is_trading_day(cur):
            cur += delta
            continue
        signals = compute_daily_trap(cur.isoformat(), industries)
        # Aggregate per day
        day_entry = {
            "date": cur.isoformat(),
            "signals": [asdict(s) for s in signals],
            "red_count": sum(1 for s in signals if s.level == "RED"),
            "orange_count": sum(1 for s in signals if s.level == "ORANGE"),
        }
        calendar.append(day_entry)
        cur += delta
    return {
        "start_date": start_date,
        "end_date": end_date,
        "industries": industries or list(INDUSTRY_RULING_PLANET.keys()),
        "calendar": calendar,
    }

# Backtest stub
def backtest_trap_correlation(start_date: str, end_date: str,
                              price_data_fn: Callable[[str, str], float]) -> dict:
    """
    price_data_fn(date, industry) -> next_day_return
    Returns correlation metrics.
    """
    cal = generate_calendar(start_date, end_date)
    hits = []
    for day in cal["calendar"]:
        for s in day["signals"]:
            if s["level"] in ("RED", "ORANGE"):
                ret = price_data_fn(day["date"], s["industry"])
                hits.append({"date": day["date"], "industry": s["industry"], "score": s["score"], "return": ret})
    # Simple metrics
    if hits:
        avg_ret = sum(h["return"] for h in hits) / len(hits)
    else:
        avg_ret = 0.0
    return {
        "total_signals": len(hits),
        "avg_next_day_return": avg_ret,
        "signals": hits,
    }

__all__ = ["compute_daily_trap", "generate_calendar", "backtest_trap_correlation", "TrapSignal"]
