"""Generate KP intraday data (data/kp/KP_Data_<Mon><YYYY>.csv) from Swiss Ephemeris.

Replaces the random sample files: every row is computed, so star/sign/sub
lords are consistent with the sky at that minute.

Conventions (all documented choices, edit the constants to change them):

* Ayanamsa: Krishnamurti (swe.SIDM_KRISHNAMURTI). Moshier ephemeris, same as
  sbc.planets, so no external data files are needed.
* Place: NSE, Mumbai (18.9300 N, 72.8333 E); IST (UTC+5:30); timestamps are
  naive local IST, which is what KPDataParser reads.
* Days: NSE trading days only (weekends and sbc.market_holidays excluded).
* Houses: Placidus cusps. A planet occupies the house whose cusp arc holds
  its longitude.
* Nodes: mean node (Krishnamurti's choice); Ketu = Rahu + 180.
* Sub / sub-sub lords: Vimshottari proportions of the 13deg20' star, starting
  from the star lord (sub) and from the sub lord (sub-sub).
* house_set: houses signified by the row's sub-lord, KP style: houses
  occupied and owned by the sub-lord's star lord, then by the sub-lord
  itself. Nodes own the houses of their sign dispositor.
* house_set_strength: market convention RISE_HOUSES minus FALL_HOUSES over
  that set (positive = rise).
* hora_lord: Chaldean planetary hours from local sunrise (day length / 12),
  first hora ruled by the weekday lord. Filled on every row.
* aspects: planets aspecting the row's planet by Vedic sign aspect (7th for
  all; Mars 4/8, Jupiter 5/9, Saturn 3/10, Rahu/Ketu 5/9) plus same-sign
  conjunction.
"""

from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

import swisseph as swe

NSE_LAT = 18.9300
NSE_LON = 72.8333
IST = dt.timedelta(hours=5, minutes=30)
MARKET_OPEN = dt.time(9, 15)
MARKET_CLOSE = dt.time(15, 30)

COLUMNS = [
    'timestamp', 'planet', 'sign', 'star', 'sublord', 'sub_sublord',
    'house_set', 'house_set_strength', 'moon_longitude', 'moon_speed',
    'asc_sign', 'asc_star', 'asc_sublord', 'asc_sub_sublord',
    'hora_lord', 'day_lord', 'aspects',
]

SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra',
         'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
STARS = ['Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra',
         'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni',
         'Uttara Phalguni', 'Hasta', 'Chitra', 'Swati', 'Vishakha', 'Anuradha',
         'Jyeshtha', 'Mula', 'Purva Ashadha', 'Uttara Ashadha', 'Shravana',
         'Dhanishta', 'Shatabhisha', 'Purva Bhadrapada', 'Uttara Bhadrapada',
         'Revati']
SIGN_LORD = ['Mars', 'Venus', 'Mercury', 'Moon', 'Sun', 'Mercury', 'Venus',
             'Mars', 'Jupiter', 'Saturn', 'Saturn', 'Jupiter']
DASHA_ORDER = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter',
               'Saturn', 'Mercury']
DASHA_YEARS = {'Ketu': 7, 'Venus': 20, 'Sun': 6, 'Moon': 10, 'Mars': 7,
               'Rahu': 18, 'Jupiter': 16, 'Saturn': 19, 'Mercury': 17}
STAR_LORD = {s: DASHA_ORDER[i % 9] for i, s in enumerate(STARS)}
STAR_SPAN = 360.0 / 27.0

# Weekday lords, Monday=0, and the Chaldean hora sequence.
WEEKDAY_LORD = ['Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Sun']
CHALDEAN = ['Saturn', 'Jupiter', 'Mars', 'Sun', 'Venus', 'Mercury', 'Moon']

# Market-rise and market-fall houses (weights) for house_set_strength.
RISE_HOUSES = {2: 1.0, 6: 1.0, 10: 1.0, 11: 1.5}
FALL_HOUSES = {5: 1.0, 8: 1.0, 12: 1.5}

# Vedic special aspects, as sign offsets counted inclusively (7th = +6).
SPECIAL_ASPECTS = {'Mars': (3, 7), 'Jupiter': (4, 8), 'Saturn': (2, 9),
                   'Rahu': (4, 8), 'Ketu': (4, 8)}

BODIES = [(swe.SUN, 'Sun'), (swe.MOON, 'Moon'), (swe.MARS, 'Mars'),
          (swe.MERCURY, 'Mercury'), (swe.JUPITER, 'Jupiter'),
          (swe.VENUS, 'Venus'), (swe.SATURN, 'Saturn'), (swe.MEAN_NODE, 'Rahu')]
PLANETS = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn',
           'Rahu', 'Ketu']


def _flags():
    swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
    return swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED


def _lords_in(span_start: float, span: float, first_lord: str, pos: float) -> tuple[str, float, float]:
    """Vimshottari division of [span_start, span_start+span) beginning at first_lord.

    Returns (lord, part_start, part_span) for the part containing pos.
    """
    i0 = DASHA_ORDER.index(first_lord)
    start = span_start
    for k in range(9):
        lord = DASHA_ORDER[(i0 + k) % 9]
        part = span * DASHA_YEARS[lord] / 120.0
        if pos < start + part or k == 8:
            return lord, start, part
        start += part
    raise AssertionError("unreachable")


def kp_point(lon: float) -> dict:
    """Sign, star, star lord, sub lord and sub-sub lord of a sidereal longitude."""
    lon %= 360.0
    star_idx = min(int(lon // STAR_SPAN), 26)
    star = STARS[star_idx]
    star_lord = STAR_LORD[star]
    sub, sub_start, sub_span = _lords_in(star_idx * STAR_SPAN, STAR_SPAN, star_lord, lon)
    subsub, _, _ = _lords_in(sub_start, sub_span, sub, lon)
    return {
        'sign': SIGNS[int(lon // 30) % 12],
        'sign_idx': int(lon // 30) % 12,
        'star': star,
        'star_lord': star_lord,
        'sublord': sub,
        'sub_sublord': subsub,
    }


def _julday_ist(when: dt.datetime) -> float:
    utc = when - IST
    return swe.julday(utc.year, utc.month, utc.day,
                      utc.hour + utc.minute / 60.0 + utc.second / 3600.0)


def _house_of(lon: float, cusps: list[float]) -> int:
    """Placidus house (1-12) whose cusp arc contains lon."""
    for h in range(12):
        a, b = cusps[h], cusps[(h + 1) % 12]
        if (lon - a) % 360.0 < (b - a) % 360.0:
            return h + 1
    return 12


def chart_at(when: dt.datetime) -> dict:
    """Planets (sidereal KP) and Placidus cusps for a naive IST datetime."""
    jd = _julday_ist(when)
    flags = _flags()
    lons, speeds = {}, {}
    for body, name in BODIES:
        xx, _ = swe.calc_ut(jd, body, flags)
        lons[name] = xx[0] % 360.0
        speeds[name] = xx[3]
    lons['Ketu'] = (lons['Rahu'] + 180.0) % 360.0
    speeds['Ketu'] = speeds['Rahu']
    cusps, ascmc = swe.houses_ex(jd, NSE_LAT, NSE_LON, b'P', swe.FLG_SIDEREAL)
    cusps = [c % 360.0 for c in cusps[:12]]
    return {'lons': lons, 'speeds': speeds, 'cusps': cusps, 'asc': ascmc[0] % 360.0}


def _significations(planet: str, chart: dict) -> set[int]:
    """Houses a planet signifies by occupation and ownership."""
    lons, cusps = chart['lons'], chart['cusps']
    houses = {_house_of(lons[planet], cusps)}
    owner = planet
    if planet in ('Rahu', 'Ketu'):
        owner = SIGN_LORD[int(lons[planet] // 30) % 12]
    for h in range(12):
        if SIGN_LORD[int(cusps[h] // 30) % 12] == owner:
            houses.add(h + 1)
    return houses


def house_set_for(sublord: str, chart: dict) -> list[int]:
    """KP houses signified by a sub-lord: via its star lord, then itself."""
    star_lord = kp_point(chart['lons'][sublord])['star_lord']
    return sorted(_significations(star_lord, chart) | _significations(sublord, chart))


def house_set_strength(houses: list[int]) -> float:
    return round(sum(RISE_HOUSES.get(h, 0.0) for h in houses)
                 - sum(FALL_HOUSES.get(h, 0.0) for h in houses), 1)


def _aspected_by(target_sign: int, chart: dict, exclude: str | None) -> list[str]:
    out = []
    for p in PLANETS:
        if p == exclude:
            continue
        s = int(chart['lons'][p] // 30) % 12
        offsets = (0, 6) + SPECIAL_ASPECTS.get(p, ())
        if (target_sign - s) % 12 in offsets:
            out.append(p)
    return out


def sunrise_ist(day: dt.date) -> dt.datetime:
    """Local sunrise at Mumbai (upper limb, no refraction tweaks) as naive IST."""
    jd0 = _julday_ist(dt.datetime(day.year, day.month, day.day, 0, 0))
    res, tret = swe.rise_trans(jd0, swe.SUN, swe.CALC_RISE | swe.BIT_DISC_CENTER,
                               (NSE_LON, NSE_LAT, 0.0), 0.0, 0.0, swe.FLG_MOSEPH)
    if res != 0:
        return dt.datetime(day.year, day.month, day.day, 6, 30)
    y, m, d, h = swe.revjul(tret[0])
    utc = dt.datetime(y, m, d) + dt.timedelta(hours=h)
    return (utc + IST).replace(microsecond=0)


def hora_schedule(day: dt.date) -> list[tuple[dt.datetime, str]]:
    """(start, lord) for the 12 day horas, sunrise to sunset."""
    rise = sunrise_ist(day)
    set_ = rise + dt.timedelta(hours=12)  # fallback if the set search fails
    jd0 = _julday_ist(rise)
    res, tret = swe.rise_trans(jd0, swe.SUN, swe.CALC_SET | swe.BIT_DISC_CENTER,
                               (NSE_LON, NSE_LAT, 0.0), 0.0, 0.0, swe.FLG_MOSEPH)
    if res == 0:
        y, m, d, h = swe.revjul(tret[0])
        set_ = (dt.datetime(y, m, d) + dt.timedelta(hours=h) + IST).replace(microsecond=0)
    length = (set_ - rise) / 12
    first = WEEKDAY_LORD[day.weekday()]
    i0 = CHALDEAN.index(first)
    return [(rise + length * k, CHALDEAN[(i0 + k) % 7]) for k in range(12)]


def _hora_at(schedule, when: dt.datetime) -> str:
    lord = schedule[0][1]
    for start, hora_lord in schedule:
        if when >= start:
            lord = hora_lord
    return lord


def day_rows(day: dt.date, step_minutes: int = 3) -> list[list]:
    """All rows for one trading day, market open to close inclusive."""
    schedule = hora_schedule(day)
    day_lord = WEEKDAY_LORD[day.weekday()]
    rows = []
    t = dt.datetime.combine(day, MARKET_OPEN)
    end = dt.datetime.combine(day, MARKET_CLOSE)
    while t <= end:
        chart = chart_at(t)
        lons = chart['lons']
        asc = kp_point(chart['asc'])
        moon_lon = round(lons['Moon'], 4)
        moon_speed = round(chart['speeds']['Moon'], 4)
        hora = _hora_at(schedule, t)
        ts = t.isoformat()
        entries = [(p, lons[p]) for p in PLANETS] + [('Ascendant', chart['asc'])]
        for name, lon in entries:
            pt = kp_point(lon)
            houses = house_set_for(pt['sublord'], chart)
            aspects = _aspected_by(pt['sign_idx'], chart,
                                   None if name == 'Ascendant' else name)
            rows.append([
                ts, name, pt['sign'], pt['star'], pt['sublord'], pt['sub_sublord'],
                ','.join(str(h) for h in houses), house_set_strength(houses),
                moon_lon, moon_speed,
                asc['sign'], asc['star'], asc['sublord'], asc['sub_sublord'],
                hora, day_lord, ', '.join(aspects),
            ])
        t += dt.timedelta(minutes=step_minutes)
    return rows


def trading_days(year: int, month: int, holidays: set[dt.date] | None = None) -> list[dt.date]:
    """Weekdays of the month minus holidays (default: NSE calendar, sbc.market_holidays)."""
    if holidays is None:
        from sbc.market_holidays import NSE_HOLIDAYS
        holidays = set(NSE_HOLIDAYS)
    d = dt.date(year, month, 1)
    out = []
    while d.month == month:
        if d.weekday() < 5 and d not in holidays:
            out.append(d)
        d += dt.timedelta(days=1)
    return out


def generate_kp_month(year: int, month: int, output_path: Path,
                      step_minutes: int = 3,
                      holidays: set[dt.date] | None = None) -> dict:
    """Write one month's KP CSV. Returns a small summary."""
    days = trading_days(year, month, holidays)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix('.csv.tmp')
    n = 0
    with open(tmp, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for day in days:
            for row in day_rows(day, step_minutes):
                w.writerow(row)
                n += 1
    tmp.replace(output_path)
    return {'file': str(output_path), 'days': len(days), 'rows': n,
            'step_minutes': step_minutes}


def month_file(kp_dir: Path, year: int, month: int) -> Path:
    return Path(kp_dir) / f"KP_Data_{dt.date(year, month, 1).strftime('%b%Y')}.csv"
