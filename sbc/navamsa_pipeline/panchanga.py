"""
Basic Vedic Panchanga calculations using ephemeris positions.
"""

import pytz
import swisseph as swe

from sbc.planets import positions as swe_positions

IST = pytz.timezone("Asia/Kolkata")

def jd_from_dt(dt):
    if dt.tzinfo is None:
        dt = IST.localize(dt)
    dt_utc = dt.astimezone(pytz.utc)
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600)
    return jd

def get_panchanga(dt):
    jd = jd_from_dt(dt)
    # Set sidereal mode to KP for consistency
    swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
    plans, _ = swe_positions(jd)
    sun = next(p for p in plans if p['name']=='Sun')
    moon = next(p for p in plans if p['name']=='Moon')
    # Tithi: difference between Moon and Sun longitudes
    diff = (moon['longitude'] - sun['longitude']) % 360
    tithi_num = int(diff / 12) + 1
    tithi_name = f"Tithi {tithi_num}"
    # Nakshatra
    nakshatra = moon['nakshatra']
    pada = moon['pada']
    # Simplified Yoga, Karana placeholders
    yoga = "Shiva"
    karana = "Vanija"
    return {
        "tithi": tithi_name,
        "nakshatra": nakshatra,
        "pada": pada,
        "yoga": yoga,
        "karana": karana,
        "sun_lon": sun['longitude'],
        "moon_lon": moon['longitude'],
    }
