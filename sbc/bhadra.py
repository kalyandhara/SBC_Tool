"""Bhadra (Vishti Karana) calendar.

Bhadra / Vishti is the seventh of the seven movable karanas in the Vedic
Panchanga.  Each tithi is split into two half-tithis (each 6 deg of Moon-Sun
elongation); the second half of a tithi carries one of the seven movable
karanas, repeating eight times over a lunar month.

Vishti (Bhadra) is considered inauspicious for new undertakings and is
widely avoided in muhurta.  This module computes the exact begin/end local
times of every Bhadra window for a requested calendar month using the Swiss
Ephemeris (Lahiri sidereal) Sun and Moon longitudes.
"""

import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import swisseph as swe

# The seven movable karanas, in order (index 0..6).  Vishti (Bhadra) is last.
MOVABLE_KARANAS = ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti"]

VISHTI_INDEX = 6  # index of "Vishti" within MOVABLE_KARANAS


def _flags():
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return swe.FLG_MOSEPH | swe.FLG_SIDEREAL


def _elongation(jd_ut):
    """Return the Moon-Sun elongation in degrees (0..360)."""
    flags = _flags()
    sun, _ = swe.calc_ut(jd_ut, swe.SUN, flags)
    moon, _ = swe.calc_ut(jd_ut, swe.MOON, flags)
    return (moon[0] - sun[0]) % 360.0


def _karana_index(jd_ut):
    """Return the 1-based karana index (1..60) for a UT Julian day."""
    elong = _elongation(jd_ut)
    return int(elong // 6.0) + 1


def _is_vishti(jd_ut):
    idx = _karana_index(jd_ut)
    if idx < 2 or idx > 57:
        return False
    return (idx - 2) % 7 == VISHTI_INDEX


def _local_to_jd(dt_local):
    """Convert an aware local datetime into a UT Julian day."""
    utc = dt_local.astimezone(datetime.UTC)
    h = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
    return swe.julday(utc.year, utc.month, utc.day, h)


def _jd_to_local(jd_ut, tz):
    """Convert a UT Julian day into an aware local datetime."""
    y, m, d, h = swe.revjul(jd_ut)
    hh = int(h)
    mm = int((h - hh) * 60)
    ss = int(((h - hh) * 60 - mm) * 60)
    utc = datetime.datetime(y, m, d, hh, mm, ss, tzinfo=datetime.UTC)
    return utc.astimezone(tz)


def _boundary(jd_lo, jd_hi, inside):
    """Bisect [jd_lo, jd_hi] to find where `inside` flips to True."""
    for _ in range(40):
        mid = (jd_lo + jd_hi) / 2.0
        if inside(mid):
            jd_hi = mid
        else:
            jd_lo = mid
    return (jd_lo + jd_hi) / 2.0


def bhadra_windows(month_start_local, tz, step_minutes=4):
    """Return every Bhadra window (begin/end local datetimes) within a month.

    `month_start_local` is an aware datetime at the start of the calendar
    month.  `tz` is a tzinfo for the output local times (defaults to the
    month's own tzinfo if not supplied).
    """
    if tz is None:
        tz = month_start_local.tzinfo
    year = month_start_local.year
    month = month_start_local.month

    def month_end_local():
        if month == 12:
            nxt = datetime.datetime(year + 1, 1, 1, tzinfo=tz)
        else:
            nxt = datetime.datetime(year, month + 1, 1, tzinfo=tz)
        return nxt - datetime.timedelta(seconds=1)

    # Add a small margin before/after so windows crossing month boundaries
    # are captured (they are later clipped to the month).
    margin = datetime.timedelta(days=1)
    start_scan = datetime.datetime(
        month_start_local.year, month_start_local.month, 1, tzinfo=tz
    ) - margin
    end_scan = month_end_local() + margin

    step = datetime.timedelta(minutes=step_minutes)
    windows = []
    cur_start = None

    t = start_scan
    jd = _local_to_jd(t)
    end_jd = _local_to_jd(end_scan)
    step_jd = step.total_seconds() / 86400.0

    prev_inside = _is_vishti(jd)
    if prev_inside:
        cur_start = t

    # Sweep through the scan window to find Vishti run boundaries, then
    # refine each boundary with bisection for sub-minute accuracy.
    raw_starts = []
    raw_ends = []
    while jd <= end_jd:
        inside = _is_vishti(jd)
        if inside and not prev_inside:
            raw_starts.append(jd)
        elif not inside and prev_inside and raw_starts:
            raw_ends.append(jd)
        prev_inside = inside
        jd += step_jd
    if prev_inside:
        raw_ends.append(jd)

    # ------------------------------------------------------------------
    # Refine boundaries by bisection.
    # ------------------------------------------------------------------
    steps = max(int(step_minutes / 4), 1)  # bisection bracket ~4 min
    for s_jd, e_jd in zip(raw_starts, raw_ends):
        # Refine start (going backwards to the crossing point)
        lo = s_jd - steps * step_jd
        hi = s_jd
        start_jd = _boundary(lo, hi, _is_vishti)
        # Refine end
        lo = e_jd - steps * step_jd
        hi = e_jd
        end_jd_final = _boundary(lo, hi, lambda j: not _is_vishti(j))

        begin_local = _jd_to_local(start_jd, tz)
        end_local = _jd_to_local(end_jd_final, tz)

        # Keep only windows overlapping the actual month.
        if end_local < month_start_local or begin_local > month_end_local():
            continue
        windows.append({
            "begin": begin_local,
            "end": end_local,
        })

    # De-duplicate & sort by begin time.
    seen = set()
    unique = []
    for w in sorted(windows, key=lambda w: w["begin"]):
        key = (w["begin"].isoformat(), w["end"].isoformat())
        if key not in seen:
            seen.add(key)
            unique.append(w)
    return unique


def format_windows(windows):
    """Serialize Bhadra windows into a UI-friendly JSON structure."""
    out = []
    for w in windows:
        start = w["begin"]
        end = w["end"]
        out.append({
            "begin_date": f"{start.strftime('%B')} {start.day}, {start.year}",
            "begin_weekday": start.strftime("%A"),
            "begin_time": start.strftime("%I:%M %p"),
            "end_date": f"{end.strftime('%B')} {end.day}, {end.year}",
            "end_weekday": end.strftime("%A"),
            "end_time": end.strftime("%I:%M %p"),
            "begin_iso": start.isoformat(),
            "end_iso": end.isoformat(),
            "spans_midnight": start.date() != end.date(),
        })
    return out


def bhadra_calendar(date_str="today", tz_name="Asia/Kolkata", month_offset=0):
    """Return the Bhadra calendar for a month.

    Args:
        date_str: reference date (ISO) or "today".
        tz_name: IANA timezone name for local times.
        month_offset: -1 (prev month), 0 (current), +1 (next month).
    """
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("Asia/Kolkata")

    if date_str in ("", "today", None):
        ref = datetime.datetime.now(tz)
    else:
        ref = datetime.datetime.fromisoformat(date_str)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=tz)
        else:
            ref = ref.astimezone(tz)

    # Compute first day of the reference month, then apply offset.
    first = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year = first.year
    month = first.month + month_offset
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    month_start = datetime.datetime(year, month, 1, tzinfo=tz)

    windows = bhadra_windows(month_start, tz)
    return {
        "location": "Mumbai, India" if tz_name == "Asia/Kolkata" else tz_name,
        "timezone": tz_name,
        "month_year": month_start.strftime("%B %Y"),
        "month_start": month_start.date().isoformat(),
        "windows": format_windows(windows),
        "count": len(windows),
    }
