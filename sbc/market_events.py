"""Canonical market-event structures used by research and validation flows."""

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

ASPECT_ANGLES = {
    "conjunction": 0.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "opposition": 180.0,
}

ASPECT_ORBS = {
    "conjunction": 8.0,
    "sextile": 6.0,
    "square": 8.0,
    "trine": 8.0,
    "opposition": 8.0,
}


@dataclass(frozen=True)
class MarketEvent:
    event_type: str
    date: str
    source: str
    phase: str | None = None
    planet_a: str | None = None
    planet_b: str | None = None
    angle: float | None = None
    orb: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def lunar_phase_event(day: date, tithi: int, sun_longitude: float, moon_longitude: float) -> MarketEvent | None:
    """Create a canonical New/Full Moon event for a daily observation."""
    if tithi in (30, 1):
        event_type = "new_moon"
        phase = "new_moon"
    elif tithi in (15, 16):
        event_type = "full_moon"
        phase = "full_moon"
    else:
        return None
    separation = abs(((moon_longitude - sun_longitude + 180) % 360) - 180)
    return MarketEvent(
        event_type=event_type,
        date=day.isoformat(),
        source="swiss_ephemeris",
        phase=phase,
        planet_a="Sun",
        planet_b="Moon",
        angle=round(separation, 4),
        metadata={"tithi": tithi},
    )


def applying_or_separating(
    separation_now: float | None, separation_prev: float | None, target_angle: float
) -> str | None:
    """Classify an aspect's motion relative to its target angle.

    Applying = the angular separation is moving toward the target angle,
    separating = moving away, stationary = unchanged. Returns None when the
    previous separation is unknown.
    """
    if separation_prev is None:
        return None
    now_gap = abs(separation_now - target_angle)
    prev_gap = abs(separation_prev - target_angle)
    if now_gap < prev_gap:
        return "applying"
    if now_gap > prev_gap:
        return "separating"
    return "stationary"


def planetary_aspect_events(
    day: date, planets: list[dict], prev_planets: list[dict] | None = None
) -> list[MarketEvent]:
    """Return canonical aspect events active on a daily planetary snapshot.

    When `prev_planets` (the previous trading day's snapshot) is provided,
    each event carries its applying/separating state in metadata.
    """
    events = []
    prev_by_name = {p["name"]: p for p in (prev_planets or [])}
    for index, first in enumerate(planets):
        for second in planets[index + 1:]:
            separation = abs(((first["longitude"] - second["longitude"] + 180) % 360) - 180)
            prev_first = prev_by_name.get(first["name"])
            prev_second = prev_by_name.get(second["name"])
            prev_sep = None
            if prev_first and prev_second:
                prev_sep = abs(((prev_first["longitude"] - prev_second["longitude"] + 180) % 360) - 180)
            for aspect, angle in ASPECT_ANGLES.items():
                orb = abs(separation - angle)
                if orb <= ASPECT_ORBS[aspect]:
                    metadata = {"aspect": aspect, "target_angle": angle}
                    state = applying_or_separating(separation, prev_sep, angle)
                    if state:
                        metadata["state"] = state
                    events.append(MarketEvent(
                        event_type="planetary_aspect",
                        date=day.isoformat(),
                        source="swiss_ephemeris",
                        planet_a=first["name"],
                        planet_b=second["name"],
                        angle=round(separation, 4),
                        orb=round(orb, 4),
                        metadata=metadata,
                    ))
    return events


SIGN_ORDER = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


def sign_of_longitude(longitude: float) -> str:
    """Return the zodiac sign for a sidereal longitude."""
    return SIGN_ORDER[int(longitude % 360 // 30) % 12]


def planetary_ingress_events(
    day: date, planets: list[dict], prev_planets: list[dict]
) -> list[MarketEvent]:
    """Return canonical sign-ingress events for a daily observation.

    A planet has ingressed when it changed sign between the previous trading
    day's snapshot and today's. Retrograde re-entries are flagged.
    """
    events = []
    prev_by_name = {p["name"]: p for p in (prev_planets or [])}
    for planet in planets:
        prev = prev_by_name.get(planet["name"])
        if not prev:
            continue
        curr_sign = planet.get("sign") or sign_of_longitude(planet["longitude"])
        prev_sign = prev.get("sign") or sign_of_longitude(prev["longitude"])
        if curr_sign and prev_sign and curr_sign != prev_sign:
            events.append(MarketEvent(
                event_type="planetary_ingress",
                date=day.isoformat(),
                source="swiss_ephemeris",
                planet_a=planet["name"],
                planet_b=None,
                metadata={
                    "from_sign": prev_sign,
                    "to_sign": curr_sign,
                    "retrograde": bool(planet.get("retrograde", False)),
                },
            ))
    return events
