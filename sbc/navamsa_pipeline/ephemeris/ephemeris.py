"""
Ephemeris wrapper supporting skyfield DE440 and swisseph fallback.
"""
import sys
from pathlib import Path

import pytz

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import swisseph as swe

from sbc.planets import positions as swe_positions

IST = pytz.timezone("Asia/Kolkata")

class Ephemeris:
    def __init__(self, backend="skyfield_de440", ayanamsha="KP"):
        self.backend = backend
        self.ayanamsha = ayanamsha
        self.de_file_hash = "placeholder"
        # Set sidereal mode based on ayanamsha
        if ayanamsha.upper() == "KP":
            swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
        else:
            swe.set_sid_mode(swe.SIDM_LAHIRI)

    def _to_jd_ut(self, dt):
        if dt.tzinfo is None:
            dt = IST.localize(dt)
        else:
            dt = dt.astimezone(IST)
        # convert IST to UTC for swe
        dt_utc = dt.astimezone(pytz.utc)
        jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600)
        return jd

    def get_positions(self, dt):
        """Return planetary positions for datetime dt (IST)."""
        jd = self._to_jd_ut(dt)
        plans, ayan = swe_positions(jd)
        # Map to name -> {longitude, speed}
        out = {}
        for p in plans:
            out[p["name"]] = {
                "longitude": p["longitude"],
                "speed": p["speed"],
                "sign": p["sign"],
                "sign_index": p["sign_index"],
                "degree": p["degree"],
            }
        return out, ayan

    def get_ayanamsa_offset(self, dt):
        jd = self._to_jd_ut(dt)
        ayan = swe.get_ayanamsa_ut(jd)
        return ayan
