"""Ephemeris-based transit date calculations for historical studies.

Computes, for any planet, the dates it enters a new sidereal sign or
nakshatra (ingresses) and the periods during which two planets share a
sign — the building blocks for transit-wise historical price studies
such as the Mars-Jupiter same-sign XAU/USD study.

Ephemeris: Swiss Ephemeris (Moshier), geocentric sidereal with the
Lahiri ayanamsa — the same pipeline as sbc.planets.  Ingress moments
are located by scanning at 3-hour steps and bisecting to 1-minute
precision; event dates are reported in both UTC and IST.  Historical
studies should use the first available trading day on or after an
event date as the actionable open (weekend/holiday adjustment).
"""

import datetime
from zoneinfo import ZoneInfo

import swisseph as swe

from .nakshatra import RASHIS, nakshatra_of

_BODIES = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
    "Rahu": swe.MEAN_NODE,
}

_STEP_HOURS = 3.0
_BISECT_DAYS = 1.0 / 1440.0  # 1 minute


def _flags():
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED


def _to_jd(dt_utc):
    h = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, h)


def _from_jd(jd):
    y, m, d, h = swe.revjul(jd)
    return datetime.datetime(y, m, d, int(h))


def _planet_lon(jd, planet_name):
    if planet_name == "Ketu":
        return (_planet_lon(jd, "Rahu") + 180.0) % 360.0
    xx, _ret = swe.calc_ut(jd, _BODIES[planet_name], _flags())
    return xx[0] % 360.0


def _scan(planet_names, start_date, end_date, step_hours=_STEP_HOURS):
    """Return [(jd, longitudes tuple)] at each scan step from start to end."""
    start_dt = datetime.datetime.combine(start_date, datetime.time(0, 0))
    jd0 = _to_jd(start_dt)
    jd1 = _to_jd(datetime.datetime.combine(end_date, datetime.time(0, 0)))
    step = step_hours / 24.0
    n = int(round((jd1 - jd0) / step)) + 1
    flags = _flags()
    out = []
    for k in range(n):
        jd = jd0 + k * step
        lons = []
        for name in planet_names:
            xx, _ret = swe.calc_ut(jd, _BODIES[name], flags)
            lons.append(xx[0] % 360.0)
        out.append((jd, tuple(lons)))
    return out


def _bisect(jd_a, jd_b, state_fn, target_state):
    """Locate the moment in (jd_a, jd_b] where state_fn leaves target_state."""
    lo, hi = jd_a, jd_b
    while hi - lo > _BISECT_DAYS:
        mid = (lo + hi) / 2.0
        if state_fn(mid) == target_state:
            lo = mid
        else:
            hi = mid
    return hi


def _event(jd, planet, kind, label, from_label, longitude, pada=1):
    dt_utc = _from_jd(jd).replace(tzinfo=datetime.UTC)
    dt_ist = dt_utc.astimezone(ZoneInfo("Asia/Kolkata"))
    return {
        "planet": planet,
        "kind": kind,
        "label": label,
        "from_label": from_label,
        "longitude": round(longitude, 4),
        "pada": pada,
        "utc": dt_utc.isoformat(),
        "utc_date": dt_utc.date().isoformat(),
        "ist_date": dt_ist.date().isoformat(),
    }


def sign_ingresses(planet, start_date, end_date):
    """Return events where `planet` enters a new sidereal sign.

    Each event dict: planet, kind='sign', label (sign entered),
    from_label, longitude, pada, utc_date, ist_date.  Includes
    retrograde re-entries, since every sign change is detected.
    """
    scan = _scan([planet], start_date, end_date)

    def state_fn(jd):
        return int(_planet_lon(jd, planet) // 30)

    events = []
    prev_jd, (prev_lon,) = scan[0]
    prev_state = int(prev_lon // 30)
    for jd, (lon,) in scan[1:]:
        state = int(lon // 30)
        if state != prev_state:
            jd_in = _bisect(prev_jd, jd, state_fn, prev_state)
            lon_in = _planet_lon(jd_in, planet)
            events.append(_event(jd_in, planet, "sign",
                                 RASHIS[int(lon_in // 30)],
                                 RASHIS[prev_state], lon_in))
            prev_state = state
        prev_jd = jd
    return events


def nakshatra_ingresses(planet, start_date, end_date):
    """Return events where `planet` enters a new nakshatra (28-star ring).

    Same event schema as sign_ingresses with kind='nakshatra'.  For the
    Moon this yields roughly one ingress per day — the basis for the
    Moon daily nakshatra study.
    """
    scan = _scan([planet], start_date, end_date)

    def nak_index(longitude):
        nak, _pada = nakshatra_of(longitude)
        return nak

    def state_fn(jd):
        return nak_index(_planet_lon(jd, planet))

    events = []
    prev_jd, (prev_lon,) = scan[0]
    prev_nak = nak_index(prev_lon)
    for jd, (lon,) in scan[1:]:
        nak = nak_index(lon)
        if nak != prev_nak:
            jd_in = _bisect(prev_jd, jd, state_fn, prev_nak)
            lon_in = _planet_lon(jd_in, planet)
            nak_in, pada = nakshatra_of(lon_in)
            events.append(_event(jd_in, planet, "nakshatra",
                                 nak_in, prev_nak, lon_in, pada))
            prev_nak = nak
        prev_jd = jd
    return events


def nakshatra_periods(planet, start_date, end_date):
    """Return nakshatra stay periods [{start, end, nakshatra, pada, days}].

    start_date/end_date are datetime.date objects; periods are clipped
    to the requested range (first and last may be partial).  The Moon
    yields roughly one period per day; Jupiter one per 5-6 months;
    fast-moving Mercury re-enters nakshatras through retrograde loops.
    """
    events = nakshatra_ingresses(planet, start_date, end_date)
    jd0 = _to_jd(datetime.datetime.combine(start_date, datetime.time(0, 0)))
    jd1 = _to_jd(datetime.datetime.combine(end_date, datetime.time(0, 0)))
    lon0 = _planet_lon(jd0, planet)
    nak0, pada0 = nakshatra_of(lon0)

    segments = [(jd0, nak0, pada0)]
    for e in events:
        segments.append((_to_jd(datetime.datetime.fromisoformat(e["utc"])),
                         e["label"], e["pada"]))

    out = []
    for i, (s_jd, nak, pada) in enumerate(segments):
        e_jd = segments[i + 1][0] if i + 1 < len(segments) else jd1
        if e_jd <= s_jd:
            continue
        out.append({
            "start": _from_jd(s_jd).date().isoformat(),
            "end": _from_jd(e_jd).date().isoformat(),
            "nakshatra": nak,
            "pada": pada,
            "days": round(e_jd - s_jd, 1),
        })
    return out


def same_sign_periods(planet_a, planet_b, start_date, end_date):
    """Return periods during which both planets occupy the same sign.

    Each period dict: start, end (exclusive), sign, days.  The end date
    is the moment the first of the two planets leaves the shared sign.
    Periods shorter than the scan step (3h) are not detected.
    """

    def state_fn(jd):
        lon_a = _planet_lon(jd, planet_a)
        lon_b = _planet_lon(jd, planet_b)
        if int(lon_a // 30) == int(lon_b // 30):
            return int(lon_a // 30)
        return -1  # sentinel: not co-present

    scan = _scan([planet_a, planet_b], start_date, end_date)
    periods = []
    start_jd = None
    prev_jd = scan[0][0]
    prev_state = state_fn(prev_jd)
    if prev_state >= 0:
        start_jd = prev_jd
    for jd, _lons in scan[1:]:
        state = state_fn(jd)
        if state != prev_state:
            jd_flip = _bisect(prev_jd, jd, state_fn, prev_state)
            if prev_state >= 0:
                periods.append((start_jd, jd_flip, prev_state))
            start_jd = jd_flip if state >= 0 else None
            prev_state = state
        prev_jd = jd
    if prev_state >= 0 and start_jd is not None:
        periods.append((start_jd, scan[-1][0], prev_state))

    out = []
    for s_jd, e_jd, sign_idx in periods:
        out.append({
            "start": _from_jd(s_jd).date().isoformat(),
            "end": _from_jd(e_jd).date().isoformat(),
            "sign": RASHIS[sign_idx],
            "days": round(e_jd - s_jd, 1),
        })
    return out


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Transit date calculator")
    parser.add_argument("--planet", default="Mars")
    parser.add_argument("--other", default="Jupiter",
                        help="second planet for same-sign periods")
    parser.add_argument("--start", default="2002-01-01")
    parser.add_argument("--end", default=datetime.date.today().isoformat())
    parser.add_argument("--ingresses", action="store_true",
                        help="also print sign ingress dates")
    parser.add_argument("--nakshatras", action="store_true",
                        help="also print nakshatra ingress dates")
    args = parser.parse_args()

    start_d = datetime.date.fromisoformat(args.start)
    end_d = datetime.date.fromisoformat(args.end)

    print(f"Same-sign periods {args.planet}-{args.other} "
          f"{start_d} .. {end_d}")
    for p in same_sign_periods(args.planet, args.other, start_d, end_d):
        print(f"  {p['start']} .. {p['end']}  {p['sign']:12s} "
              f"{p['days']:7.1f}d")
    if args.ingresses:
        print(f"{args.planet} sign ingresses (IST dates)")
        for e in sign_ingresses(args.planet, start_d, end_d):
            print(f"  {e['ist_date']}  enters {e['label']:12s} "
                  f"(from {e['from_label']})")
    if args.nakshatras:
        print(f"{args.planet} nakshatra ingresses (IST dates)")
        for e in nakshatra_ingresses(args.planet, start_d, end_d):
            print(f"  {e['ist_date']}  enters {e['label']:12s} "
                  f"(from {e['from_label']})")
