"""Weekly bullion astro brief for gold and silver on MCX (B-56).

    build(monday) -> {
      week_of, session, location, days, events, positions, econ, track, caveat
    }

Per trading day (Mon-Fri): Mumbai sunrise and sunset, Rahu Kaal, the 24 horas,
tithi at sunrise, the Moon's nakshatra and pada changes, and the Moon's KP
sub-lord segments across the day. Per week: sign changes and stations of the
Sun to Saturn and Rahu (mean node), Moon conjunctions, planet positions at
Monday sunrise, US data releases from data/econ_events.json, and each
nakshatra's gold and silver record over its last 50 sessions next to the base
rate.

Conventions: sidereal Lahiri set on every call (sbc.kp_ephemeris switches the
global mode to Krishnamurti, which would move Moon timings by ~10 minutes),
Moshier ephemeris, sunrise and sunset from sbc.kp_ephemeris (NSE Mumbai, disc
centre), times as naive IST. A session's nakshatra is the Moon's at 09:15 IST,
the repo-wide convention.

Checked against a published daily bullion sheet for 18 Sep 2026: Rahu Kaal,
the Jupiter and Mercury horas, all three pada changes and all eight sub-lord
changes agree to within two minutes.

The sub-lord "reading" applies that sheet's rules (Venus, Jupiter up; Sun,
Ketu, Rahu pressure; Moon volatile; Mars, Saturn stable or range-bound;
Mercury no rule). They are untested hypotheses, labelled as such in the UI.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import math
from functools import lru_cache
from pathlib import Path

import swisseph as swe

from sbc.kp_ephemeris import CHALDEAN, DASHA_ORDER, DASHA_YEARS, WEEKDAY_LORD, sunrise_ist
from sbc.nakshatra import NAKSHATRAS_27

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ECON_FILE = DATA_DIR / "econ_events.json"
SESSION = (9.0, 23.5)  # MCX hours IST while the US is on daylight time (see session_for)


def us_daylight(day: dt.date) -> bool:
    """US daylight time: second Sunday of March to first Sunday of November."""
    def nth_sunday(year: int, month: int, n: int) -> dt.date:
        d = dt.date(year, month, 1)
        d += dt.timedelta(days=(6 - d.weekday()) % 7)
        return d + dt.timedelta(weeks=n - 1)
    return nth_sunday(day.year, 3, 2) <= day < nth_sunday(day.year, 11, 1)


def session_for(day: dt.date) -> tuple[float, float]:
    """MCX bullion session in IST hours: 09:00 to 23:30 on US daylight time, else 23:55 (B-59)."""
    return (9.0, 23.5) if us_daylight(day) else (9.0, 23 + 55 / 60)
NSE_LAT, NSE_LON = 18.9300, 72.8333
SPAN = 360.0 / 27.0
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
RAHU_SEG = [2, 7, 5, 6, 4, 3, 8]  # Mon..Sun: which eighth of daytime is Rahu Kaal
TITHI = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami",
         "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi"]
PLANETS = [("Sun", swe.SUN), ("Mercury", swe.MERCURY), ("Venus", swe.VENUS), ("Mars", swe.MARS),
           ("Jupiter", swe.JUPITER), ("Saturn", swe.SATURN), ("Rahu", swe.MEAN_NODE)]
READING = {
    "Venus": ("up", "Positive direction", "Buying may emerge"),
    "Jupiter": ("up", "Positive direction", "Buying may emerge"),
    "Sun": ("down", "Pressure possible", "Watch for pressure"),
    "Ketu": ("down", "Pressure possible", "Monitor closely"),
    "Rahu": ("down", "Pressure / volatility", "Protect positions"),
    "Moon": ("volatile", "Sharp volatility", "Monitor positions"),
    "Mars": ("stable", "Relative stability", "Stability may return"),
    "Saturn": ("stable", "Pressure / range-bound", "Watch profit-taking"),
    "Mercury": ("none", "No rule", "No traditional reading"),
}
CAVEAT = ("Sub-lord readings follow a published bullion sheet and have not been tested "
          "against gold or silver prices. Research only, not investment advice.")


def _flags() -> int:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED


def _jd(t: dt.datetime) -> float:
    u = t - dt.timedelta(hours=5, minutes=30)
    return swe.julday(u.year, u.month, u.day, u.hour + u.minute / 60 + u.second / 3600)


def _ist(jd: float) -> dt.datetime:
    y, m, d, h = swe.revjul(jd)
    t = dt.datetime(y, m, d) + dt.timedelta(hours=h, minutes=330)
    return (t + dt.timedelta(seconds=30)).replace(second=0, microsecond=0)


def _lon(jd: float, body: int) -> tuple[float, float]:
    r = swe.calc_ut(jd, body, _flags())[0]
    return r[0] % 360.0, r[3]


def _wrap(x: float) -> float:
    return (x + 180.0) % 360.0 - 180.0


def _bisect(f, a: float, b: float, n: int = 36) -> float:
    fa = f(a)
    for _ in range(n):
        m = (a + b) / 2
        fm = f(m)
        if (fa < 0) == (fm < 0):
            a, fa = m, fm
        else:
            b = m
    return (a + b) / 2


def _hm(t: dt.datetime) -> str:
    return t.strftime("%H:%M")


def _hours(t: dt.datetime, day: dt.date) -> float:
    return round((t - dt.datetime.combine(day, dt.time())).total_seconds() / 3600, 3)


def sunset_ist(day: dt.date) -> dt.datetime:
    """Mumbai sunset (disc centre), the same convention as kp_ephemeris.sunrise_ist."""
    jd0 = _jd(sunrise_ist(day))
    res, tret = swe.rise_trans(jd0, swe.SUN, swe.CALC_SET | swe.BIT_DISC_CENTER,
                               (NSE_LON, NSE_LAT, 0.0), 0.0, 0.0, swe.FLG_MOSEPH)
    return _ist(tret[0]) if res == 0 else sunrise_ist(day) + dt.timedelta(hours=12)


def _sub_bounds() -> list[tuple[float, str]]:
    out = []
    for i in range(27):
        i0 = DASHA_ORDER.index(DASHA_ORDER[i % 9])
        a = i * SPAN
        for k in range(9):
            lord = DASHA_ORDER[(i0 + k) % 9]
            out.append((a, lord))
            a += SPAN * DASHA_YEARS[lord] / 120.0
    return out


SUBS = _sub_bounds()


def sub_lord(lon: float) -> str:
    lon %= 360.0
    lord = SUBS[0][1]
    for start, name in SUBS:
        if start <= lon + 1e-9:
            lord = name
        else:
            break
    return lord


def _nak(lon: float) -> str:
    return NAKSHATRAS_27[min(int(lon // SPAN), 26)]


def tithi_name(jd: float) -> str:
    t = int(((_lon(jd, swe.MOON)[0] - _lon(jd, swe.SUN)[0]) % 360) // 12)
    if t == 14:
        return "Shukla Purnima"
    if t == 29:
        return "Krishna Amavasya"
    return ("Shukla " if t < 15 else "Krishna ") + TITHI[t % 15]


def moon_day(day: dt.date) -> tuple[list[dict], list[dict]]:
    """Pada changes and merged sub-lord segments of the Moon over 00:00-24:00 IST."""
    t0 = dt.datetime.combine(day, dt.time())
    j0, j1 = _jd(t0), _jd(t0 + dt.timedelta(days=1))
    pada_edges = {round(k * 360 / 108, 9) for k in range(108)}
    edges = sorted(pada_edges | {round(s, 9) for s, _ in SUBS})
    l0, l1 = _lon(j0, swe.MOON)[0], _lon(j1, swe.MOON)[0]
    if l1 < l0:
        l1 += 360
    crossings = []
    for e in edges + [e + 360 for e in edges]:
        if l0 < e < l1:
            jd = _bisect(lambda j, e=e: _wrap(_lon(j, swe.MOON)[0] - e % 360), j0, j1)
            crossings.append((jd, e % 360))
    padas = []
    for jd, e in crossings:
        q = e / (360 / 108)
        if abs(q - round(q)) < 1e-6:
            n = int(round(q)) % 108
            if padas and padas[-1]["nakshatra"] == NAKSHATRAS_27[n // 4] and padas[-1]["pada"] == n % 4 + 1:
                continue
            t = _ist(jd)
            padas.append({"time": _hm(t), "h": _hours(t, day), "nakshatra": NAKSHATRAS_27[n // 4],
                          "pada": n % 4 + 1, "enters": n % 4 == 0})
    cuts = [j0] + [jd for jd, _ in crossings] + [j1]
    segs: list[dict] = []
    for a, b in zip(cuts, cuts[1:]):
        lon = _lon((a + b) / 2, swe.MOON)[0]
        lord = sub_lord(lon)
        ta, tb = _ist(a), _ist(b)
        if segs and segs[-1]["lord"] == lord:
            segs[-1].update(to=_hm(tb), b=_hours(tb, day))
            continue
        tone, label, guidance = READING[lord]
        segs.append({"from": _hm(ta), "to": _hm(tb), "a": _hours(ta, day), "b": _hours(tb, day),
                     "lord": lord, "nakshatra": _nak(lon), "tone": tone, "reading": label,
                     "guidance": guidance})
    return padas, segs


def day_block(day: dt.date) -> dict:
    rise, set_ = sunrise_ist(day), sunset_ist(day)
    rise2 = sunrise_ist(day + dt.timedelta(days=1))
    wd = day.weekday()
    eighth = (set_ - rise) / 8
    rk = (rise + eighth * (RAHU_SEG[wd] - 1), rise + eighth * RAHU_SEG[wd])
    horas, i0, t = [], CHALDEAN.index(WEEKDAY_LORD[wd]), rise
    for k in range(24):
        step = (set_ - rise) / 12 if k < 12 else (rise2 - set_) / 12
        horas.append({"lord": CHALDEAN[(i0 + k) % 7], "from": _hm(t), "to": _hm(t + step),
                      "a": _hours(t, day), "b": _hours(t + step, day)})
        t += step
    padas, segs = moon_day(day)
    mlon = _lon(_jd(rise), swe.MOON)[0]
    open_lon = _lon(_jd(dt.datetime.combine(day, dt.time(9, 15))), swe.MOON)[0]
    s0, s1 = session_for(day)
    return {"date": day.isoformat(), "weekday": day.strftime("%A"),
            "session": [s0, round(s1, 4)], "session_label": f"09:00–{'23:30' if s1 == 23.5 else '23:55'}",
            "sunrise": _hm(rise), "sunset": _hm(set_),
            "rahu_kaal": {"from": _hm(rk[0]), "to": _hm(rk[1]), "a": _hours(rk[0], day), "b": _hours(rk[1], day)},
            "horas": horas, "tithi": tithi_name(_jd(rise)),
            "moon_sign": SIGNS[int(mlon // 30)], "moon_nakshatra": _nak(mlon),
            "session_nakshatra": _nak(open_lon), "padas": padas, "subs": segs}


def week_events(monday: dt.date) -> list[dict]:
    t0 = dt.datetime.combine(monday, dt.time())
    j0, j1 = _jd(t0), _jd(t0 + dt.timedelta(days=7))
    step = 1 / 24
    grid = [j0 + i * step for i in range(int((j1 - j0) / step) + 1)]
    out = []
    for name, body in PLANETS:
        prev = _lon(grid[0], body)
        for g in grid[1:]:
            cur = _lon(g, body)
            if int(prev[0] // 30) != int(cur[0] // 30):
                fwd = _wrap(cur[0] - prev[0]) > 0
                edge = (int(cur[0] // 30) if fwd else int(prev[0] // 30)) * 30
                jd = _bisect(lambda j, b=body, e=edge: _wrap(_lon(j, b)[0] - e), g - step, g)
                out.append((jd, "ingress", f"{name} enters {SIGNS[int(cur[0] // 30)]}"))
            if name != "Rahu" and (prev[1] < 0) != (cur[1] < 0):
                jd = _bisect(lambda j, b=body: _lon(j, b)[1], g - step, g)
                out.append((jd, "station", f"{name} turns {'retrograde' if cur[1] < 0 else 'direct'}"))
            prev = cur
    for name, body in PLANETS[:6]:
        prev = _wrap(_lon(grid[0], swe.MOON)[0] - _lon(grid[0], body)[0])
        for g in grid[1:]:
            cur = _wrap(_lon(g, swe.MOON)[0] - _lon(g, body)[0])
            if prev < 0 <= cur and cur - prev < 90:
                jd = _bisect(lambda j, b=body: _wrap(_lon(j, swe.MOON)[0] - _lon(j, b)[0]), g - step, g)
                out.append((jd, "conjunction", f"Moon conjunct {name}"))
            prev = cur
    out.sort()
    return [{"date": _ist(jd).date().isoformat(), "time": _hm(_ist(jd)), "kind": k, "text": text}
            for jd, k, text in out]


def econ_events(monday: dt.date, path: Path = ECON_FILE) -> list[dict]:
    """US data releases this week from data/econ_events.json (times in IST)."""
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    end = monday + dt.timedelta(days=7)
    return sorted((r for r in rows if monday.isoformat() <= r.get("date", "") < end.isoformat()),
                  key=lambda r: (r["date"], r.get("time", "")))


@lru_cache(maxsize=4)
def _closes(asset: str) -> tuple[tuple[str, float], ...]:
    path = DATA_DIR / f"{asset}_ohlc.csv"
    try:
        with path.open(newline="", encoding="utf-8") as f:
            rows = [(r["Date"], float(r["Close"])) for r in csv.DictReader(f) if r.get("Close")]
    except (OSError, ValueError, KeyError):
        return ()
    return tuple(rows)


@lru_cache(maxsize=1)
def _session_naks(dates: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(_nak(_lon(_jd(dt.datetime.fromisoformat(d + "T09:15")), swe.MOON)[0]) for d in dates)


def _binom_two_sided(k: int, n: int, p: float) -> float:
    """Exact two-sided binomial p-value (sum of outcomes no more likely than k)."""
    pk = math.comb(n, k) * p ** k * (1 - p) ** (n - k)
    total = 0.0
    for i in range(n + 1):
        pi = math.comb(n, i) * p ** i * (1 - p) ** (n - i)
        if pi <= pk * (1 + 1e-9):
            total += pi
    return min(1.0, total)


def track_record(nakshatras: list[str], before: dt.date, last: int = 50) -> dict:
    """Up and down closes on each nakshatra's last `last` sessions before `before`, per asset."""
    out: dict = {}
    for asset in ("gold", "silver"):
        rows = [r for r in _closes(asset) if r[0] < before.isoformat()]
        if len(rows) < 2:
            out[asset] = {"available": False}
            continue
        naks = _session_naks(tuple(d for d, _ in rows))
        changes = [(naks[i], rows[i][1] > rows[i - 1][1]) for i in range(1, len(rows))
                   if rows[i][1] != rows[i - 1][1]]
        base = sum(up for _, up in changes) / len(changes)
        per = {}
        for n in nakshatras:
            hits = [up for nk, up in changes if nk == n][-last:]
            k = sum(hits)
            per[n] = {"sessions": len(hits), "up": k, "down": len(hits) - k,
                      "up_rate": round(k / len(hits), 3) if hits else None,
                      "p_value": round(_binom_two_sided(k, len(hits), base), 3) if hits else None}
        out[asset] = {"available": True, "as_of": rows[-1][0], "base_up_rate": round(base, 3),
                      "sessions_in_base": len(changes), "by_nakshatra": per}
    return out


def build(monday: dt.date) -> dict:
    """The weekly brief for the Mon-Fri week starting on `monday` (any weekday is moved back)."""
    monday = monday - dt.timedelta(days=monday.weekday())
    days = [day_block(monday + dt.timedelta(days=i)) for i in range(5)]
    rise = _jd(sunrise_ist(monday))
    positions = []
    for name, body in PLANETS:
        lon, speed = _lon(rise, body)
        positions.append({"name": name, "sign": SIGNS[int(lon // 30)], "degree": int(lon % 30),
                          "retrograde": speed < 0 or name == "Rahu"})
    naks = []
    for d in days:
        for n in [d["moon_nakshatra"], d["session_nakshatra"], *[p["nakshatra"] for p in d["padas"]]]:
            if n not in naks:
                naks.append(n)
    return {"week_of": monday.isoformat(), "end": (monday + dt.timedelta(days=4)).isoformat(),
            "session": [days[0]["session"][0], days[0]["session"][1]], "location": "Mumbai (NSE)", "zodiac": "Sidereal, Lahiri",
            "days": days, "events": week_events(monday), "positions": positions,
            "econ": econ_events(monday), "track": track_record(naks, monday),
            "readings": {k: {"tone": v[0], "reading": v[1], "guidance": v[2]} for k, v in READING.items()},
            "caveat": CAVEAT}
