"""AstroCycle Pro - Mercury & Moon intraday cycle time bars.

Generates auto-plotted intraday reversal time bars from planetary horas
(Chaldean weekday sequence) and Moon nakshatra ingresses during NSE market
hours (09:15-15:30 IST). Each bar carries entry rules: buy above / sell
below with SL and target, in the style of the AstroCycle Pro product.

Research astro-timing output, not investment advice.
"""

import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .intraday_projection import (
    MARKET_CLOSE_MIN,
    MARKET_OPEN_MIN,
    _hour_hora_lord,
    _local_aware,
)

CYCLE_PLANETS = ("Mercury", "Moon")

# Entry-rule geometry: how far above/below the reference price the
# buy-above / sell-below triggers sit, expressed in index points.
DEFAULT_SL_POINTS = 15.0


def _safe_tz(tz_name: str):
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("Asia/Kolkata")


def cycle_bars(
    date_str: str,
    tz_name: str = "Asia/Kolkata",
    ref_price: float | None = None,
    sl_points: float = DEFAULT_SL_POINTS,
) -> list[dict[str, Any]]:
    """Return Mercury & Moon cycle time bars for one trading day.

    Mercury and Moon planetary horas within market hours become reversal
    windows, aligned to hour boundaries and clipped to the session. Each
    bar carries: time (start HH:MM), end, type, ref_price, entry_above,
    entry_below, stop_loss, target_above/below, and the entry rule text.
    """
    if sl_points <= 0:
        raise ValueError("sl_points must be positive")
    if ref_price is not None and ref_price <= 0:
        raise ValueError("ref_price must be positive when provided")

    tz = _safe_tz(tz_name)
    day = datetime.date.fromisoformat(date_str) if isinstance(date_str, str) else date_str
    ref = round(float(ref_price or 0.0), 2)

    bars: list[dict[str, Any]] = []
    for hour in range(9, 16):
        lord = _hour_hora_lord(day.isoformat(), hour * 60, tz)
        if lord not in CYCLE_PLANETS:
            continue
        start_min = max(hour * 60, MARKET_OPEN_MIN)
        end_min = min((hour + 1) * 60, MARKET_CLOSE_MIN)
        if start_min >= end_min:
            continue
        start = _local_aware(day.isoformat(), start_min, tz)
        end = _local_aware(day.isoformat(), end_min, tz)
        bars.append({
            "time": start.strftime("%H:%M"),
            "end": end.strftime("%H:%M"),
            "type": lord.lower(),
            "lord": lord,
            "ref_price": ref,
            "entry_above": round(ref + sl_points, 2),
            "entry_below": round(ref - sl_points, 2),
            "stop_loss": round(ref, 2),
            "target_above": round(ref + 2 * sl_points, 2),
            "target_below": round(ref - 2 * sl_points, 2),
            "entry_rule": (
                f"Buy above {ref + sl_points:.2f} / Sell below {ref - sl_points:.2f}; "
                f"SL {ref:.2f}, target 2x ({ref + 2 * sl_points:.2f} / {ref - 2 * sl_points:.2f})."
            ),
        })
    return bars


def moon_ingress_bars(
    date_str: str,
    tz_name: str = "Asia/Kolkata",
    step_minutes: int = 5,
) -> list[dict[str, Any]]:
    """Return Moon nakshatra ingress time bars within market hours.

    Scans the Moon's sidereal longitude through the session and emits a bar
    at each nakshatra boundary crossing. The bar marks a high-probability
    reversal window: buy above / sell below the open of the next 5 minutes
    is decided by the trader; the bar itself only flags the time.
    """
    if step_minutes <= 0:
        raise ValueError("step_minutes must be positive")

    from .planets import positions

    tz = _safe_tz(tz_name)
    day = datetime.date.fromisoformat(date_str) if isinstance(date_str, str) else date_str

    def _moon_nakshatra(minutes: int):
        jd = _jd_utc(day, minutes, tz)
        planets, _ = positions(jd)
        moon = next((p for p in planets if p["name"] == "Moon"), None)
        return moon.get("nakshatra") if moon else None

    def _jd_utc(day, minutes, tz):
        local = _local_aware(day.isoformat(), minutes, tz)
        utc = local.astimezone(datetime.UTC)
        import swisseph as swe
        return swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute / 60.0)

    bars: list[dict[str, Any]] = []
    prev = None
    minute = MARKET_OPEN_MIN
    while minute <= MARKET_CLOSE_MIN:
        nak = _moon_nakshatra(minute)
        if prev is not None and nak is not None and nak != prev:
            t = _local_aware(day.isoformat(), minute, tz).strftime("%H:%M")
            bars.append({
                "time": t,
                "type": "moon_ingress",
                "lord": nak,
                "into_nakshatra": nak,
                "from_nakshatra": prev,
                "entry_rule": (
                    f"Moon entered {nak} at {t} - reversal window; "
                    "trade only with 5-candle price confirmation."
                ),
            })
        if nak is not None:
            prev = nak
        minute += step_minutes
    return bars


__all__ = ["cycle_bars", "moon_ingress_bars", "DEFAULT_SL_POINTS", "CYCLE_PLANETS"]
