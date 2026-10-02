"""Intraday NIFTY 50 astro-projection.

Hourly forecast of market-hours (09:15-15:30 IST) astro bias derived from the
Sarvatobhadra Chakra, plus all yogas (Panchanga + muhurta) that fall inside the
trading session, forward-projected for the requested number of days.

The "projection" value is a signed score (bullish positive / bearish negative)
built from:
  - the SBC chakra net vedha bias at that hour,
  - whether a yoga window (Abhijit Muhurta, Bhadra/Vishti Karana, Pushkara)
    is active at that hour,
  - and the planetary hora quality (KP-style, benefic vs malefic lord) for the
    hour.

No real intraday NIFTY price feed is used; this is a forecast overlay in the
style of the daily NIFTY astro-price chart.
"""

import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import swisseph as swe

from .bhadra import bhadra_windows
from .market_calendar import daily_yoga_glyphs
from .nakshatra import tithi_of
from .planets import positions

MARKET_OPEN_MIN = 9 * 60 + 15   # 09:15
MARKET_CLOSE_MIN = 15 * 60 + 30  # 15:30
MARKET_HOURS = (MARKET_CLOSE_MIN - MARKET_OPEN_MIN) / 60.0  # 6.25 hours

# Abhijit Muhurta: fixed 48-minute window centered on local clock noon.
ABHIJIT_START_MIN = 11 * 60 + 36
ABHIJIT_END_MIN = 12 * 60 + 24

# Hora quality by lord (KP-style simplification).
HORA_QUALITY = {
    "Sun": 0.5, "Moon": 0.5, "Mars": -0.5, "Mercury": 0.4,
    "Jupiter": 0.8, "Venus": 0.8, "Saturn": -0.6,
}

# Hora lords in weekday order (Sunday=0 .. Saturday=6), starting at sunrise.
WEEKDAY_HORA_ORDER = [
    ["Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn"],
    ["Moon", "Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars", "Sun"],
    ["Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"],
    ["Mercury", "Moon", "Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars"],
    ["Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury"],
    ["Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter"],
    ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars", "Sun", "Venus"],
]


def _flags():
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return swe.FLG_MOSEPH | swe.FLG_SIDEREAL


def _local_aware(date_str, minutes, tz):
    hh = minutes // 60
    mm = minutes % 60
    d = datetime.date.fromisoformat(date_str)
    return datetime.datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz)


def _jd_at(date_str, minutes, tz):
    local = _local_aware(date_str, minutes, tz)
    utc = local.astimezone(datetime.UTC)
    h = utc.hour + utc.minute / 60.0
    return swe.julday(utc.year, utc.month, utc.day, h)


def _hour_hora_lord(date_str, minutes, tz):
    """Return the planetary hora lord for a given IST time (approximate).

    Uses a fixed 06:00 sunrise and 1-hour horas; the daytime sequence from
    sunrise through sunset follows the weekday order.
    """
    noon_local = _local_aware(date_str, minutes, tz)
    weekday = noon_local.weekday()  # Monday=0
    # Map Python weekday (Mon=0) to our order index (Sun=0).
    order_index = (weekday + 1) % 7
    seq = WEEKDAY_HORA_ORDER[order_index]
    # Approximate sunrise at 06:00 local, one hora = 1 hour.
    elapsed = minutes - 6 * 60
    if elapsed < 0:
        return None
    idx = elapsed // 60
    if idx >= len(seq):
        idx = idx % len(seq)
    return seq[idx]


def intraday_projection(start_date, tz_name="Asia/Kolkata", days=5, anchor_key="nse"):
    """Return hourly astro-projection points + yoga events for `days` forward.

    Returns dict: {location, timezone, start_date, days, hours: [...],
                   yogas: [...], method, disclaimer}.
    """
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("Asia/Kolkata")

    if isinstance(start_date, str):
        start_date = datetime.date.fromisoformat(start_date)
    else:
        start_date = start_date

    from .market_calendar import _anchor_nakshatra
    from .planets import all_planets_with_natures
    from .prediction import analyze, compute_vedhas

    hours = []
    yogas = []

    for day_offset in range(days):
        day = start_date + datetime.timedelta(days=day_offset)
        date_str = day.isoformat()

        # Day-level SBC chakra read at market open.
        planets_open, _ = positions(_jd_at(date_str, MARKET_OPEN_MIN, tz))
        sun = next(p for p in planets_open if p["name"] == "Sun")
        moon = next(p for p in planets_open if p["name"] == "Moon")
        tithi = tithi_of(sun["longitude"], moon["longitude"])
        planets = all_planets_with_natures(planets_open, tithi, sun["longitude"])
        vedha_map, _ = compute_vedhas(planets, school="classical")
        analysis = analyze(planets, vedha_map, _anchor_nakshatra(anchor_key),
                           school="classical")
        day_net = analysis["net"]  # signed

        # Day-level yoga names (Panchanga).
        names, glyphs = daily_yoga_glyphs(
            day, sun, moon, tithi)

        # Bhadra (Vishti Karana) windows overlapping today's session, clipped
        # to market hours — drives the Dahan (muted) momentum bars.
        month_start = datetime.datetime(day.year, day.month, 1, tzinfo=tz)
        day_bhadra = []
        for w in bhadra_windows(month_start, tz):
            if w["end"].date() < day or w["begin"].date() > day:
                continue
            bmin = (w["begin"].hour * 60 + w["begin"].minute
                    if w["begin"].date() == day else MARKET_OPEN_MIN)
            emin = (w["end"].hour * 60 + w["end"].minute
                    if w["end"].date() == day else MARKET_CLOSE_MIN)
            bmin = max(bmin, MARKET_OPEN_MIN)
            emin = min(emin, MARKET_CLOSE_MIN)
            if bmin < emin:
                day_bhadra.append((bmin, emin))

        # Intraday projection points across market hours (15-min steps for a
        # smooth cumulative path).
        cum = 0.0
        minute = MARKET_OPEN_MIN
        while minute <= MARKET_CLOSE_MIN:
            jd = _jd_at(date_str, minute, tz)
            pl, _ = positions(jd)
            s2 = next(p for p in pl if p["name"] == "Sun")
            m2 = next(p for p in pl if p["name"] == "Moon")
            t2 = tithi_of(s2["longitude"], m2["longitude"])

            hora_lord = _hour_hora_lord(date_str, minute, tz)
            hora_score = HORA_QUALITY.get(hora_lord, 0.0) if hora_lord else 0.0

            # Yoga adjustment at this minute.
            yoga_active = []
            yoga_bias = 0.0
            if ABHIJIT_START_MIN <= minute <= ABHIJIT_END_MIN:
                yoga_active.append("Abhijit Muhurta")
                yoga_bias += 1.0
            # Pushkara navamsa (approx day-level) is folded into day_net, but
            # a Bhadra/Vishti window is a negative intraday override.
            if tithi in (15, 30):
                yoga_active.append("Purnima" if tithi == 15 else "Amavasya")
                yoga_bias += 0.5 if tithi == 15 else -0.5
            dahan = any(bmin <= minute <= emin for bmin, emin in day_bhadra)
            if dahan:
                yoga_active.append("Bhadra (Dahan)")

            projection = day_net + hora_score * 2.0 + yoga_bias
            cum += projection

            local = _local_aware(date_str, minute, tz)
            unix_ts = int(local.astimezone(datetime.UTC).timestamp())

            hours.append({
                "time": unix_ts,
                "date": date_str,
                "minute": minute,
                "clock": local.strftime("%H:%M"),
                "projection": round(projection, 2),
                "cumulative": round(cum, 2),
                "momentum": round(hora_score * 2.0 + yoga_bias, 2),
                "day_net": round(day_net, 2),
                "hora_lord": hora_lord,
                "hora_score": round(hora_score, 2),
                "yoga_bias": round(yoga_bias, 2),
                "yoga_active": sorted(yoga_active),
                "dahan": dahan,
                "is_future": True,
            })
            minute += 15

        # Yoga events for the day.
        if names:
            yogas.append({
                "date": date_str,
                "offset": day_offset + 1,
                "type": "Panchanga Yoga",
                "names": names,
                "glyphs": glyphs,
                "day_level": True,
            })
        yogas.append({
            "date": date_str,
            "offset": day_offset + 1,
            "type": "Abhijit Muhurta",
            "names": ["Abhijit Muhurta"],
            "glyphs": "AM",
            "start": _local_aware(date_str, ABHIJIT_START_MIN, tz).strftime("%H:%M"),
            "end": _local_aware(date_str, ABHIJIT_END_MIN, tz).strftime("%H:%M"),
            "day_level": False,
        })

        # Bhadra (Vishti Karana) windows that fall within market hours.
        month_start = datetime.datetime(day.year, day.month, 1, tzinfo=tz)
        bw = bhadra_windows(month_start, tz)
        for w in bw:
            b = w["begin"]
            e = w["end"]
            if b.date() == day and e.date() == day:
                bmin = b.hour * 60 + b.minute
                emin = e.hour * 60 + e.minute
                if bmin < MARKET_CLOSE_MIN and emin > MARKET_OPEN_MIN:
                    yogas.append({
                        "date": date_str,
                        "offset": day_offset + 1,
                        "type": "Bhadra (Vishti Karana)",
                        "names": ["Bhadra"],
                        "glyphs": "B",
                        "start": b.strftime("%H:%M"),
                        "end": e.strftime("%H:%M"),
                        "day_level": False,
                    })
            elif b.date() == day and e.date() != day:
                # begins today, ends tomorrow
                bmin = b.hour * 60 + b.minute
                if bmin < MARKET_CLOSE_MIN:
                    yogas.append({
                        "date": date_str,
                        "offset": day_offset + 1,
                        "type": "Bhadra (Vishti Karana)",
                        "names": ["Bhadra"],
                        "glyphs": "B",
                        "start": b.strftime("%H:%M"),
                        "end": _local_aware(date_str, MARKET_CLOSE_MIN, tz).strftime("%H:%M"),
                        "day_level": False,
                        "spans_midnight": True,
                    })

    return {
        "location": "Mumbai, India" if tz_name == "Asia/Kolkata" else tz_name,
        "timezone": tz_name,
        "start_date": start_date.isoformat(),
        "days": days,
        "hours": hours,
        "yogas": yogas,
        "method": "15-min SBC chakra net-vedha + hora + yoga windows with cumulative path and momentum; market hours 09:15-15:30 IST; Swiss Ephemeris Lahiri.",
        "disclaimer": "Research astro-projection, not price data or investment advice.",
    }
