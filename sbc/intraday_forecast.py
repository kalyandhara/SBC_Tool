"""Forward intraday forecast for the NSE session: SBC + KP transition confluence.

Everything here is a deterministic function of (date, weights), computed
straight from the ephemeris, so a forecast can be drawn for any future day.

Per 5-minute bucket (weights in FORECAST_WEIGHTS):

  hora      hora quality of the ruling planetary hour, modified by aspects
            the hora lord receives (KPRuleEngine.evaluate_hora_quality)
  asc_sub   direction of the Ascendant's sub-lord: benefic/malefic nature
            when its KP house set leans to rise (strength > 0), scaled by
            strength; 0 otherwise (same rule as KPRuleEngine)
  moon_sub  same rule for the Moon's sub-lord (the session "regime")
  impulse   one-off kick in the bucket where a Moon / Asc sub-lord changes,
            in the new sub-lord's direction
  sbc       SBC vedha net at the nearest hourly reading, squashed to [-1, 1]

bucket score = sum(weight * component); path = running sum of scores.
Flags (bands on the chart): DL-hora, Dahan, Chand/Vat, same rules as
sbc.kp_intraday.build_cumulative_path.

STATUS: experimental. The KP composite this is built from back-tested at
chance (docs/INTRADAY_PATH_VALIDATION.md); sbc.forecast_ledger freezes and
scores every forecast so the claim can be checked going forward.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from functools import lru_cache

from sbc import kp_ephemeris as kpe
from sbc.kp_intraday import (
    BENEFIC_HORAS,
    EXPERIMENTAL_NOTICE,
    HORA_QUALITY_SCORE,
    MALEFIC_HORAS,
    KPRuleEngine,
)

SESSION_OPEN = dt.time(9, 15)
SESSION_CLOSE = dt.time(15, 30)
DEFAULT_STEP = 5

FORECAST_WEIGHTS = {
    "hora": 1.0,
    "asc_sub": 1.0,
    "moon_sub": 1.5,
    "impulse_moon": 1.5,
    "impulse_asc": 0.5,
    "sbc": 0.5,
}
SBC_SCALE = 4.0  # vedha net of +/-4 maps to ~ +/-0.76 before weighting

_ENGINE = KPRuleEngine()
_NATURE = KPRuleEngine.PLANET_NATURE


def model_version(weights: dict | None = None) -> str:
    """Short hash of the scoring weights; a frozen forecast records it."""
    blob = json.dumps({"w": weights or FORECAST_WEIGHTS, "sbc_scale": SBC_SCALE,
                       "v": 1}, sort_keys=True)
    return hashlib.sha1(blob.encode()).hexdigest()[:10]


def sub_direction(sublord: str, strength: float) -> int:
    """+1 bullish, -1 bearish, 0 neutral (KPRuleEngine._direction_from_sublord)."""
    if strength <= 0:
        return 0
    nature = _NATURE.get(sublord, "neutral")
    return 1 if nature == "benefic" else -1 if nature == "malefic" else 0


def _sub_component(sublord: str, strength: float) -> float:
    d = sub_direction(sublord, strength)
    return d * (0.5 + 0.5 * min(strength, 3.0) / 3.0)


def _minutes(day: dt.date):
    t = dt.datetime.combine(day, SESSION_OPEN)
    end = dt.datetime.combine(day, SESSION_CLOSE)
    while t <= end:
        yield t
        t += dt.timedelta(minutes=1)


def _kp_minute(when: dt.datetime) -> dict:
    chart = kpe.chart_at(when)
    out = {}
    for name, lon in (("Moon", chart["lons"]["Moon"]), ("Ascendant", chart["asc"])):
        pt = kpe.kp_point(lon)
        houses = kpe.house_set_for(pt["sublord"], chart)
        out[name] = {"sublord": pt["sublord"], "star": pt["star"],
                     "sign": pt["sign"], "houses": houses,
                     "strength": kpe.house_set_strength(houses)}
    out["chart"] = chart
    return out


@lru_cache(maxsize=64)
def _sbc_readings(day_iso: str) -> tuple:
    """SBC vedha net at session open and every hour after (hh:15)."""
    from app import build_response  # late import: app imports blueprints
    readings = []
    t = dt.datetime.combine(dt.date.fromisoformat(day_iso), SESSION_OPEN)
    end = dt.datetime.combine(t.date(), SESSION_CLOSE)
    while t <= end:
        r = build_response(day_iso, t.strftime("%H:%M"), "Asia/Kolkata", "nifty", "allthree")
        readings.append((t.time(), float(r.get("net") or 0.0)))
        t += dt.timedelta(hours=1)
    return tuple(readings)


def _sbc_at(readings, t: dt.time) -> float:
    net = readings[0][1]
    for rt, rn in readings:
        if t >= rt:
            net = rn
    return net


def build_forecast(day: dt.date, step: int = DEFAULT_STEP,
                   weights: dict | None = None) -> dict:
    if step <= 0 or step > 60:
        raise ValueError("step must be 1..60 minutes")
    w = {**FORECAST_WEIGHTS, **(weights or {})}
    day_lord = kpe.WEEKDAY_LORD[day.weekday()]
    schedule = kpe.hora_schedule(day)

    # Minute-level KP scan: exact sub-lord transition times.
    minutes = [(m, _kp_minute(m)) for m in _minutes(day)]
    transitions = []
    for (_, prev), (m, cur) in zip(minutes, minutes[1:]):
        for body in ("Moon", "Ascendant"):
            a, b = prev[body], cur[body]
            if a["sublord"] != b["sublord"]:
                d = sub_direction(b["sublord"], b["strength"])
                transitions.append({
                    "time": m.strftime("%H:%M"), "body": body,
                    "old_sublord": a["sublord"], "new_sublord": b["sublord"],
                    "star": b["star"], "houses": b["houses"],
                    "strength": b["strength"],
                    "direction": {1: "Bullish", -1: "Bearish", 0: "Neutral"}[d],
                })

    # Horas touching the session, with aspect-modified quality.
    horas = []
    for i, (start, lord) in enumerate(schedule):
        end = schedule[i + 1][0] if i + 1 < len(schedule) else start + (schedule[1][0] - schedule[0][0])
        if end.time() <= SESSION_OPEN or start.time() >= SESSION_CLOSE:
            continue
        chart = kpe.chart_at(max(start, dt.datetime.combine(day, SESSION_OPEN)))
        lord_sign = int(chart["lons"][lord] // 30) % 12
        aspects = ", ".join(kpe._aspected_by(lord_sign, chart, lord))
        quality, *_ = _ENGINE.evaluate_hora_quality(lord, aspects)
        horas.append({
            "start": max(start.time(), SESSION_OPEN).strftime("%H:%M"),
            "end": min(end.time(), SESSION_CLOSE).strftime("%H:%M"),
            "lord": lord, "quality": quality.value, "aspects": aspects,
            "dl_hora": lord == day_lord and HORA_QUALITY_SCORE[quality.value] > 0,
            "dahan": lord in MALEFIC_HORAS and HORA_QUALITY_SCORE[quality.value] < 0,
            "chand_vat": lord in BENEFIC_HORAS and HORA_QUALITY_SCORE[quality.value] >= 0,
        })

    def hora_at(t: dt.time):
        clock = t.strftime("%H:%M")
        for h in horas:
            if h["start"] <= clock < h["end"]:
                return h
        return horas[-1] if horas else None

    readings = _sbc_readings(day.isoformat())
    by_minute = {m.time(): kp for m, kp in minutes}
    trans_by_time = {}
    for tr in transitions:
        trans_by_time.setdefault(tr["time"], []).append(tr)

    buckets, cumulative = [], 0.0
    for i in range(0, len(minutes) - 1, step):
        t0 = minutes[i][0].time()
        kp = by_minute[t0]
        h = hora_at(t0)
        comps = {
            "hora": HORA_QUALITY_SCORE.get(h["quality"], 0.0) if h else 0.0,
            "asc_sub": _sub_component(kp["Ascendant"]["sublord"], kp["Ascendant"]["strength"]),
            "moon_sub": _sub_component(kp["Moon"]["sublord"], kp["Moon"]["strength"]),
            "impulse_moon": 0.0, "impulse_asc": 0.0,
            "sbc": math.tanh(_sbc_at(readings, t0) / SBC_SCALE),
        }
        events = []
        for k in range(i + 1, min(i + step, len(minutes) - 1) + 1):
            for tr in trans_by_time.get(minutes[k][0].strftime("%H:%M"), []):
                key = "impulse_moon" if tr["body"] == "Moon" else "impulse_asc"
                comps[key] += {"Bullish": 1, "Bearish": -1}.get(tr["direction"], 0)
                events.append(tr)
        score = round(sum(w[c] * v for c, v in comps.items()), 3) + 0.0
        cumulative = round(cumulative + score, 3)
        buckets.append({
            "time": t0.strftime("%H:%M"), "score": score, "cumulative": cumulative,
            "components": {c: round(w[c] * v, 3) + 0.0 for c, v in comps.items()},  # +0.0: no -0.0
            "hora_lord": h["lord"] if h else None,
            "asc_sublord": kp["Ascendant"]["sublord"], "moon_sublord": kp["Moon"]["sublord"],
            "dl_hora": bool(h and h["dl_hora"]), "dahan": bool(h and h["dahan"]),
            "chand_vat": bool(h and h["chand_vat"]),
            "events": [f"{e['body']} sub {e['old_sublord']}→{e['new_sublord']} ({e['direction']})"
                       for e in events],
        })

    open_kp = minutes[0][1]
    return {
        "date": day.isoformat(), "session": "NSE", "tz": "Asia/Kolkata",
        "open": SESSION_OPEN.strftime("%H:%M"), "close": SESSION_CLOSE.strftime("%H:%M"),
        "step_minutes": step, "day_lord": day_lord,
        "moon": {"star": open_kp["Moon"]["star"], "sign": open_kp["Moon"]["sign"]},
        "weights": w, "model_version": model_version(w),
        "sbc_readings": [{"time": t.strftime("%H:%M"), "net": n} for t, n in readings],
        "horas": horas, "transitions": transitions, "buckets": buckets,
        "status": "experimental", "experimental_notice": EXPERIMENTAL_NOTICE,
    }
