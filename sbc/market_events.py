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


def planetary_aspect_events(day: date, planets: list[dict]) -> list[MarketEvent]:
    """Return canonical aspect events active on a daily planetary snapshot."""
    events = []
    for index, first in enumerate(planets):
        for second in planets[index + 1:]:
            separation = abs(((first["longitude"] - second["longitude"] + 180) % 360) - 180)
            for aspect, angle in ASPECT_ANGLES.items():
                orb = abs(separation - angle)
                if orb <= ASPECT_ORBS[aspect]:
                    events.append(MarketEvent(
                        event_type="planetary_aspect",
                        date=day.isoformat(),
                        source="swiss_ephemeris",
                        planet_a=first["name"],
                        planet_b=second["name"],
                        angle=round(separation, 4),
                        orb=round(orb, 4),
                        metadata={"aspect": aspect, "target_angle": angle},
                    ))
    return events
