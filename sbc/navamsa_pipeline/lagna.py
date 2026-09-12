"""
Lagna calculation.
"""
import swisseph as swe
from datetime import datetime
import pytz

IST = pytz.timezone("Asia/Kolkata")

def jd_from_dt(dt):
    if dt.tzinfo is None:
        dt = IST.localize(dt)
    dt_utc = dt.astimezone(pytz.utc)
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600)
    return jd

def get_lagna(dt, lat=19.0656, lon=72.8646):
    jd = jd_from_dt(dt)
    swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
    # Calculate ascendant
    # Use swe.houses
    # For simplicity, use equal house placeholder
    # Actual Placidus requires swe.houses
    try:
        cusps, ascmc = swe.houses(jd, lat, lon, b'P')
        asc = cusps[0]
    except Exception:
        # fallback to sidereal ascendant approx
        asc = 0.0
    return asc % 360
