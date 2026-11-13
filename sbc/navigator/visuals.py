"""Data for the Navigator's 3D views.

scatter(): every past session's weighted score against what Nifty did next
(open to the next open, the backtest's 1-session horizon, raw, no costs).
model(): the natal chart as a planet model, with each planet's Shadbala-based
strength at birth and the transit contacts active on each of the next days.

Both are descriptive research views, not signals.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np

from sbc.engine import _julday, _utc_from_local
from sbc.navigator import scoring as S
from sbc.navigator import signature as G
from sbc.navigator import weights as W
from sbc.navigator.analogs import Market, next_sessions
from sbc.navigator.ephemeris import build_sky
from sbc.navigator.profile import Profile, natal_points

STRENGTH_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
MODEL_DAYS = 30
SCATTER_NOTES = [
    "Each point is one past Nifty session: its weighted score against the return from that "
    "session's open to the next open (raw, no costs).",
    "Colour: green for scores of 61 and up, yellow for 41 to 60, red for 40 and below.",
    "Descriptive only: the backtest is the test of whether scores relate to returns.",
]
MODEL_NOTES = [
    "Natal planets sit on the inner ring at their sidereal longitudes; transiting planets "
    "move on the outer ring.",
    "Node size is each planet's strength at birth: Shadbala against its classical minimum, "
    "scaled by Baladi Avastha.",
    "Lines are transit contacts within the Phase 1 orb: green adds to the score, red subtracts.",
]


def colour_group(score: int) -> str:
    if score >= 61:
        return "green"
    if score >= 41:
        return "yellow"
    return "red"


def scatter(profile: Profile, market: Market) -> dict[str, Any]:
    dates = list(market.dates)
    sky = build_sky(dates)
    o = np.asarray(market.prices["open"], dtype=float)
    series = S.score_series(sky, profile, o, np.asarray(market.prices["close"], dtype=float), market.vix)
    ret = np.full(len(dates), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        ret[:-1] = o[1:] / o[:-1] - 1
    points = [{"date": d, "score": int(s), "group": colour_group(int(s)), "ret": round(float(r), 6)}
              for d, s, r in zip(dates, series.score, ret, strict=True) if np.isfinite(r)]
    return {"points": points, "data_asof": dates[-1], "notes": SCATTER_NOTES}


def natal_strength(profile: Profile) -> dict[str, dict[str, Any]]:
    """Shadbala-and-Avastha strength 0-100 per planet at birth, with the details."""
    import datetime as _dt
    from zoneinfo import ZoneInfo

    from sbc.navigator import shadbala as SB
    from sbc.navigator.terms import planet_strength_score
    jd = _julday(_utc_from_local(profile.birth_date, profile.birth_time, profile.tz))
    local = _dt.datetime.fromisoformat(f"{profile.birth_date}T{profile.birth_time}").replace(tzinfo=ZoneInfo(profile.tz))
    offset = local.utcoffset()
    tz_hours = offset.total_seconds() / 3600 if offset is not None else 0.0
    sb = SB.shadbala(jd, profile.lat, profile.lon, tz_hours)
    out = {}
    for name in STRENGTH_PLANETS:
        row = sb[name]
        out[name] = {"strength": round(planet_strength_score(row["ratio"], row["avastha_factor"]), 1),
                     "reasons": [f"Shadbala {row['ratio']:.2f}x minimum", row["avastha"]]}
    return out


def model(profile: Profile, last_session: str, days: int = MODEL_DAYS) -> dict[str, Any]:
    natal = natal_points(profile)
    strength = natal_strength(profile)
    nodes = [{"name": k, "lon": round(v, 3),
              "strength": strength.get(k, {}).get("strength"),
              "reasons": strength.get(k, {}).get("reasons", [])} for k, v in natal.items()]
    future = [dt.date.fromisoformat(last_session).isoformat()] + next_sessions(last_session, days - 1)
    sky = build_sky(future)
    keys, weights = G.contact_matrix(sky, natal)
    frames = []
    for i, day in enumerate(future):
        edges = []
        for k, (planet, point, aspect) in enumerate(keys):
            orb = float(weights[i, k])
            if orb <= 0:
                continue
            effect = W.ASPECT_WEIGHT(planet, point, aspect) * orb
            if effect == 0:
                continue
            edges.append({"planet": planet, "point": point, "aspect": aspect,
                          "effect": round(effect, 2)})
        frames.append({"date": day,
                       "transits": [{"name": b, "lon": round(float(sky.lon[b][i]), 3)}
                                    for b in W.TRANSIT_BODIES],
                       "edges": edges})
    return {"nodes": nodes, "frames": frames, "notes": MODEL_NOTES}
