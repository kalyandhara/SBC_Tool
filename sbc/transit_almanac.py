"""Yearly transit almanac: sign changes, stations, aspects and eclipses (B-55).

    build(year, zodiac="sidereal") -> {year, zodiac, bodies: [...]}

Each body (Pluto to Mercury, then Moon nodes and eclipses) carries:
  segments  stretches of the year in one sign and one direction, as fractions
            of the year, for drawing the timeline
  events    stations, sign changes, exact aspects (listed under the faster
            planet) and, on the node row, node sign changes and eclipses

Conventions: Swiss Ephemeris (Moshier), sidereal Lahiri or tropical, mean
node, dates in IST. The Lahiri mode is set on every call because
sbc.kp_ephemeris switches the global mode to Krishnamurti.

Checked against a published 2026 tropical aspects chart: every station, sign
change, aspect and eclipse date matches, and the node change on 19 Aug.

Meanings are traditional readings in plain words, not tested market signals.
"""

from __future__ import annotations

import datetime as dt
from functools import lru_cache

import swisseph as swe

IST_DAYS = 5.5 / 24
STEP = 0.25  # days
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
BODIES = [("Pluto", swe.PLUTO), ("Neptune", swe.NEPTUNE), ("Uranus", swe.URANUS),
          ("Saturn", swe.SATURN), ("Jupiter", swe.JUPITER), ("Mars", swe.MARS),
          ("Venus", swe.VENUS), ("Mercury", swe.MERCURY)]
ASPECTS = [(0, "conjunction"), (60, "sextile"), (90, "square"), (120, "trine"), (180, "opposition")]
ZODIACS = ("sidereal", "tropical")
MIN_YEAR, MAX_YEAR = 1990, 2050


def _flags(sidereal: bool) -> int:
    if sidereal:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        return swe.FLG_MOSEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
    return swe.FLG_MOSEPH | swe.FLG_SPEED


def _lon(jd: float, body: int, sid: bool) -> tuple[float, float]:
    r = swe.calc_ut(jd, body, _flags(sid))[0]
    return r[0] % 360.0, r[3]


def _wrap(x: float) -> float:
    return (x + 180.0) % 360.0 - 180.0


def _bisect(f, a: float, b: float, n: int = 40) -> float:
    fa = f(a)
    for _ in range(n):
        m = (a + b) / 2
        fm = f(m)
        if (fa < 0) == (fm < 0):
            a, fa = m, fm
        else:
            b = m
    return (a + b) / 2


def _date(jd: float) -> str:
    y, m, d, _ = swe.revjul(jd + IST_DAYS)
    return dt.date(y, m, d).isoformat()


def _frac(jd: float, j0: float, j1: float) -> float:
    return round((jd - j0) / (j1 - j0), 5)


def _sign(lon: float) -> str:
    return SIGNS[int(lon // 30) % 12]


@lru_cache(maxsize=16)
def build(year: int, zodiac: str = "sidereal") -> dict:
    if zodiac not in ZODIACS:
        raise ValueError(f"zodiac must be one of {ZODIACS}")
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise ValueError(f"year must be {MIN_YEAR}-{MAX_YEAR}")
    sid = zodiac == "sidereal"
    j0 = swe.julday(year, 1, 1, 0) - IST_DAYS
    j1 = swe.julday(year + 1, 1, 1, 0) - IST_DAYS
    grid = [j0 + i * STEP for i in range(int((j1 - j0) / STEP) + 1)]
    samples = {name: [_lon(j, body, sid) for j in grid] for name, body in BODIES}
    rows = []

    for name, body in BODIES:
        s = samples[name]
        events, marks = [], []
        for i in range(1, len(grid)):
            if (s[i - 1][1] < 0) != (s[i][1] < 0):
                t = _bisect(lambda j: _lon(j, body, sid)[1], grid[i - 1], grid[i])
                lon = _lon(t, body, sid)[0]
                marks.append(t)
                events.append({"t": _frac(t, j0, j1), "date": _date(t), "type": "station",
                               "kind": "Retrograde" if s[i][1] < 0 else "Direct", "body": name,
                               "degree": int(lon % 30), "sign": _sign(lon)})
            a, b = int(s[i - 1][0] // 30), int(s[i][0] // 30)
            if a != b:
                forward = (b - a) % 12 == 1
                edge = (b if forward else a) * 30
                t = _bisect(lambda j: _wrap(_lon(j, body, sid)[0] - edge), grid[i - 1], grid[i])
                marks.append(t)
                events.append({"t": _frac(t, j0, j1), "date": _date(t), "type": "ingress", "body": name,
                               "sign": SIGNS[b], "back": not forward})
        cuts = sorted({j0, *marks, j1})
        segments = []
        for a, b in zip(cuts, cuts[1:]):
            lon, speed = _lon((a + b) / 2, body, sid)
            segments.append({"a": _frac(a, j0, j1), "b": _frac(b, j0, j1),
                             "sign": int(lon // 30), "retro": speed < 0})
        rows.append({"name": name, "start": f"{_sign(s[0][0])} {int(s[0][0] % 30)}°",
                     "end": f"{_sign(s[-1][0])} {int(s[-1][0] % 30)}°",
                     "segments": segments, "events": events})

    by_name = {r["name"]: r for r in rows}
    for i, (slow, slow_body) in enumerate(BODIES):
        for fast, fast_body in BODIES[i + 1:]:
            ss, sf = samples[slow], samples[fast]
            for angle, aspect in ASPECTS:
                for side in ([1, -1] if angle not in (0, 180) else [1]):
                    def gap(j, angle=angle, side=side):
                        return _wrap(_lon(j, fast_body, sid)[0] - _lon(j, slow_body, sid)[0] - side * angle)
                    prev = _wrap(sf[0][0] - ss[0][0] - side * angle)
                    for k in range(1, len(grid)):
                        cur = _wrap(sf[k][0] - ss[k][0] - side * angle)
                        if (prev < 0) != (cur < 0) and abs(prev - cur) < 90:
                            t = _bisect(gap, grid[k - 1], grid[k])
                            lon = _lon(t, fast_body, sid)[0]
                            by_name[fast]["events"].append({
                                "t": _frac(t, j0, j1), "date": _date(t), "type": "aspect",
                                "aspect": aspect, "body": fast, "other": slow,
                                "degree": int(lon % 30), "sign": _sign(lon),
                                "other_retro": _lon(t, slow_body, sid)[1] < 0})
                        prev = cur

    def node(j):
        return _lon(j, swe.MEAN_NODE, sid)[0]

    coarse = grid[::4]
    cuts, node_events = [j0], []
    for k in range(1, len(coarse)):
        a, b = node(coarse[k - 1]), node(coarse[k])
        if int(a // 30) != int(b // 30):
            edge = int(a // 30) * 30
            t = _bisect(lambda j: _wrap(node(j) - edge), coarse[k - 1], coarse[k])
            cuts.append(t)
            node_events.append({"t": _frac(t, j0, j1), "date": _date(t), "type": "ingress",
                                "body": "Nodes", "sign": _sign(b), "back": True})
    cuts.append(j1)
    segments = [{"a": _frac(a, j0, j1), "b": _frac(b, j0, j1), "sign": int(node((a + b) / 2) // 30),
                 "retro": False} for a, b in zip(cuts, cuts[1:])]
    for kind, finder in (("Solar", lambda j: swe.sol_eclipse_when_glob(j, swe.FLG_MOSEPH)),
                         ("Lunar", lambda j: swe.lun_eclipse_when(j, swe.FLG_MOSEPH))):
        j = j0
        while True:
            t = finder(j)[1][0]
            if t >= j1:
                break
            lon = _lon(t, swe.SUN if kind == "Solar" else swe.MOON, sid)[0]
            node_events.append({"t": _frac(t, j0, j1), "date": _date(t), "type": "eclipse",
                                "kind": kind, "sign": _sign(lon), "degree": int(lon % 30)})
            j = t + 10
    rows.append({"name": "Nodes & Eclipses", "start": f"{_sign(node(j0))} {int(node(j0) % 30)}°",
                 "end": f"{_sign(node(j1))} {int(node(j1) % 30)}°",
                 "segments": segments, "events": node_events})
    for r in rows:
        r["events"].sort(key=lambda e: e["t"])
    return {"year": year, "zodiac": zodiac,
            "zodiac_label": "Sidereal, Lahiri" if sid else "Tropical (Western)",
            "node": "mean", "timezone": "IST", "bodies": rows}
