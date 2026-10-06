"""Daily planet series for charting: declination, ecliptic latitude, speed (B-45).

    series(metric, start, end) -> {metric, unit, time, dates, series: {planet: [value per date]},
                                   reference: {label, values}}

All values are geocentric at 09:15 IST, the same snapshot sbc.fingerprint uses:

  declination  equatorial (Kranti); |dec| > 23.44 is "out of bounds" (sbc.factors.OBLIQUITY)
  latitude     ecliptic (Sara / vikshepa); the Sun and the nodes sit on 0, so they're left out
  speed        sidereal Lahiri longitude speed, deg/day; negative = retrograde

Rahu is the true node, as in sbc.stations; Ketu is the opposite point, so its
declination is Rahu's with the sign flipped and its speed equals Rahu's.

Display only: no series here has been tested as a predictor.
"""

from __future__ import annotations

import datetime as dt

import swisseph as swe

from sbc import kp_ephemeris as kpe
from sbc.factors import OBLIQUITY

METRICS = {
    "declination": {"unit": "deg", "reference": {"label": "out of bounds", "values": [-OBLIQUITY, OBLIQUITY]}},
    "latitude": {"unit": "deg", "reference": {"label": "ecliptic", "values": [0.0]}},
    "speed": {"unit": "deg/day", "reference": {"label": "station", "values": [0.0]}},
}
BODIES = (
    ("Sun", swe.SUN), ("Moon", swe.MOON), ("Mercury", swe.MERCURY), ("Venus", swe.VENUS),
    ("Mars", swe.MARS), ("Jupiter", swe.JUPITER), ("Saturn", swe.SATURN), ("Uranus", swe.URANUS),
    ("Neptune", swe.NEPTUNE), ("Pluto", swe.PLUTO), ("Rahu", swe.TRUE_NODE),
)
NO_LATITUDE = {"Sun", "Rahu", "Ketu"}
MAX_DAYS = 400
SNAPSHOT = dt.time(9, 15)


def _value(metric: str, jd: float, body: int) -> float:
    if metric == "declination":
        return float(swe.calc_ut(jd, body, swe.FLG_MOSEPH | swe.FLG_EQUATORIAL)[0][1])
    if metric == "latitude":
        return float(swe.calc_ut(jd, body, swe.FLG_MOSEPH)[0][1])
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return float(swe.calc_ut(jd, body, swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED)[0][3])


def series(metric: str, start: dt.date, end: dt.date) -> dict:
    if metric not in METRICS:
        raise ValueError(f"metric must be one of {', '.join(METRICS)}")
    days = (end - start).days + 1
    if not 1 <= days <= MAX_DAYS:
        raise ValueError(f"end must be on or after start, at most {MAX_DAYS} days")
    dates = [start + dt.timedelta(days=i) for i in range(days)]
    jds = [kpe._julday_ist(dt.datetime.combine(d, SNAPSHOT)) for d in dates]
    out: dict[str, list[float]] = {}
    for name, body in BODIES:
        if metric == "latitude" and name in NO_LATITUDE:
            continue
        out[name] = [round(_value(metric, jd, body), 4) for jd in jds]
    if "Rahu" in out:
        out["Ketu"] = [-v for v in out["Rahu"]] if metric == "declination" else list(out["Rahu"])
    return {
        "metric": metric,
        "unit": METRICS[metric]["unit"],
        "time": "09:15 IST",
        "dates": [d.isoformat() for d in dates],
        "planets": list(out),
        "series": out,
        "reference": METRICS[metric]["reference"],
        "note": "Geocentric, Rahu = true node. Display only; not tested as a predictor.",
    }
