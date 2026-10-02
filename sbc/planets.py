"""Planetary position calculations using Swiss Ephemeris (Moshier).

All positions are geocentric sidereal with the Lahiri ayanamsa, the
standard for Vedic astrology.  The Moshier ephemeris (built into the
library) is accurate to arc-second level for this application over the
relevant date range and needs no external data files.
"""

import swisseph as swe

from .nakshatra import nakshatra_of, sign_of

SWE_BODIES = [
    (swe.SUN, "Sun"),
    (swe.MOON, "Moon"),
    (swe.MARS, "Mars"),
    (swe.MERCURY, "Mercury"),
    (swe.JUPITER, "Jupiter"),
    (swe.VENUS, "Venus"),
    (swe.SATURN, "Saturn"),
    (swe.MEAN_NODE, "Rahu"),
]

# Natural nature of each planet.
NATURAL_NATURE = {
    "Sun": "malefic",
    "Moon": "benefic",   # switches by phase, handled below
    "Mars": "malefic",
    "Mercury": "benefic",  # switches with company, handled below
    "Jupiter": "benefic",
    "Venus": "benefic",
    "Saturn": "malefic",
    "Rahu": "malefic",
    "Ketu": "malefic",
}

SYMBOLS = {
    "Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
    "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra",
    "Ketu": "Ke",
}

# Exaltation / debilitation signs (0=Aries .. 11=Pisces).
EXALT = {"Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5, "Jupiter": 3,
         "Venus": 11, "Saturn": 6, "Rahu": 1, "Ketu": 7}
DEBIL = {"Sun": 6, "Moon": 7, "Mars": 3, "Mercury": 11, "Jupiter": 9,
         "Venus": 5, "Saturn": 0, "Rahu": 7, "Ketu": 1}

# Combustion orbs (degrees from the Sun).
COMBUST_ORB = {"Moon": 12.0, "Mars": 17.0, "Mercury": 14.0,
               "Jupiter": 11.0, "Venus": 10.0, "Saturn": 15.0}

# Mercury turns harsh when within orb of a harsh planet.
MERCURY_MALEFIC_ORB = 8.0


def _flags():
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED


def positions(julian_day):
    """Return a list of planet dicts for the given (UT) Julian day.

    Ketu is derived as the opposite point of Rahu (the mean node) and
    shares the node's motion; it is appended after the eight SWE bodies.
    """
    flags = _flags()
    ayanamsa = swe.get_ayanamsa_ut(julian_day)
    out = []
    rahu = None
    for body, name in SWE_BODIES:
        xx, _ret = swe.calc_ut(julian_day, body, flags)
        planet = _planet_dict(name, xx[0] % 360.0, xx[3])
        if name == "Rahu":
            rahu = planet
        out.append(planet)
    if rahu is not None:
        out.append(_planet_dict("Ketu", rahu["longitude"] + 180.0, rahu["speed"]))
    return out, ayanamsa


def _planet_dict(name, lon, speed):
    nakshatra, pada = nakshatra_of(lon)
    rashi, sign_idx = sign_of(lon)
    return {
        "name": name,
        "symbol": SYMBOLS[name],
        "longitude": round(lon % 360.0, 4),
        "sign": rashi,
        "sign_index": sign_idx,
        "degree": round(lon % 30.0, 2),
        "nakshatra": nakshatra,
        "pada": pada,
        "speed": round(speed, 4),
        "retrograde": speed < 0,
    }


def refine_natures(planets, tithi):
    """Apply the classical nature switches for Mercury and the Moon."""
    moon_lon = next(p for p in planets if p["name"] == "Moon")["longitude"]
    malefic_lons = []
    for p in planets:
        if p["name"] in ("Sun", "Mars", "Saturn", "Rahu", "Ketu"):
            malefic_lons.append(p["longitude"])
    for p in planets:
        if p["name"] == "Moon":
            from .nakshatra import moon_nature
            p["nature"] = moon_nature(tithi)
            p["nature_note"] = (
                "waning moon (Krishna Ekadashi-Shukla Chaturthi)" if
                p["nature"] == "malefic" else "waxing/strong moon"
            )
        elif p["name"] == "Mercury":
            near = any(abs((p["longitude"] - ml + 180) % 360 - 180) <
                       MERCURY_MALEFIC_ORB for ml in malefic_lons)
            if near:
                p["nature"] = "malefic"
                p["nature_note"] = "conjunct a harsh planet"
            else:
                p["nature"] = "benefic"
                p["nature_note"] = "well-placed"
        else:
            p["nature"] = NATURAL_NATURE[p["name"]]
            p["nature_note"] = "natural " + p["nature"]


def dignity_multiplier(p, sun_lon):
    """Classical strength scaling: retrograde x2, exalted x3,
    debilitated x0.5, combust x0.5."""
    m = 1.0
    reasons = []
    if p["retrograde"]:
        m *= 2.0
        reasons.append("retrograde (x2)")
    if p["sign_index"] == EXALT[p["name"]]:
        m *= 3.0
        reasons.append("exalted (x3)")
    if p["sign_index"] == DEBIL[p["name"]]:
        m *= 0.5
        reasons.append("debilitated (x0.5)")
    orb = COMBUST_ORB.get(p["name"])
    if orb is not None:
        sep = abs((p["longitude"] - sun_lon + 180) % 360 - 180)
        if sep < orb:
            m *= 0.5
            reasons.append("combust (x0.5)")
    p["dignity_multiplier"] = round(m, 3)
    p["dignity_reasons"] = reasons
    return m


def all_planets_with_natures(planets, tithi, sun_lon):
    refine_natures(planets, tithi)
    for p in planets:
        m = dignity_multiplier(p, sun_lon)
        p["signed_strength"] = round(
            m * (1.0 if p["nature"] == "benefic" else -1.0), 3)
    return planets


def positioned_planets(date_str, time_str="09:15", tz_name="Asia/Kolkata"):
    """Return (planets, ayanamsa, sun, moon, tithi) for a local date/time.

    Encapsulates the common "local date -> UTC -> Julian day -> ephemeris
    positions -> tithi -> refined natures" pipeline used across the app.
    """
    import datetime
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    from .nakshatra import tithi_of

    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("Asia/Kolkata")
    y, m, d = (int(x) for x in date_str.split("-"))
    hh, mm = (int(x) for x in time_str.split(":"))
    local = datetime.datetime(y, m, d, hh, mm, tzinfo=tz)
    utc = local.astimezone(datetime.UTC).replace(tzinfo=None)
    h = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
    jul = swe.julday(utc.year, utc.month, utc.day, h)

    planets, ayanamsa = positions(jul)
    sun = next(p for p in planets if p["name"] == "Sun")
    moon = next(p for p in planets if p["name"] == "Moon")
    tithi = tithi_of(sun["longitude"], moon["longitude"])
    planets = all_planets_with_natures(planets, tithi, sun["longitude"])
    return planets, ayanamsa, sun, moon, tithi
