"""One daily position table, shared by every chart (spec: placebos)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sbc.engine import _julday, _utc_from_local
from sbc.navigator.weights import TRANSIT_BODIES
from sbc.planets import positions


@dataclass
class SkyTable:
    days: list[str]
    lon: dict[str, np.ndarray]
    retro: dict[str, np.ndarray]


def build_sky(days: list[str]) -> SkyTable:
    lon = {b: np.zeros(len(days)) for b in TRANSIT_BODIES}
    retro = {b: np.zeros(len(days), bool) for b in TRANSIT_BODIES}
    for i, day in enumerate(days):
        ps, _ = positions(_julday(_utc_from_local(day, "09:15", "Asia/Kolkata")))
        for p in ps:
            if p["name"] in lon:
                lon[p["name"]][i] = p["longitude"]
                retro[p["name"]][i] = p["retrograde"]
    return SkyTable(days, lon, retro)
