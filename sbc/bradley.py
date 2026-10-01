"""Simplified Bradley-style market barometer (experimental).

A deterministic approximation of Donald Bradley's barometer: weighted
planetary aspect geometry summed into a daily score. Hard aspects
(0/90/180) contribute negatively, soft aspects (60/120) positively, scaled
by closeness (1 - orb/orb_max). Turning-point candidates are local extremes
of the daily score series.

EXPERIMENTAL ONLY - keep separate from the primary SBC score. Research
output, not investment advice.
"""

from typing import Any

# Planet weights for the barometer (outer cycles dominate).
BRADLEY_WEIGHTS = {
    "Sun": 0.5, "Moon": 0.5, "Mercury": 0.4, "Mars": 0.8,
    "Jupiter": 1.0, "Saturn": 1.2, "Uranus": 1.0,
    "Neptune": 0.8, "Pluto": 0.6, "Rahu": 0.6, "Ketu": 0.6,
}

ASPECT_TARGETS = (0.0, 60.0, 90.0, 120.0, 180.0)
HARD_ASPECTS = (0.0, 90.0, 180.0)
ASPECT_ORB_MAX = 8.0


def _angular_distance(lon_a: float, lon_b: float) -> float:
    return abs(((lon_a - lon_b + 180) % 360) - 180)


def bradley_score(day_planets: list[dict[str, Any]]) -> float:
    """Compute the simplified Bradley score for a daily planetary snapshot.

    For each weighted planet pair within orb of an aspect target:
    contribution = w_a * w_b * sign * (1 - orb / ASPECT_ORB_MAX), where sign
    is -1 for hard aspects (0/90/180) and +1 for soft aspects (60/120).
    """
    total = 0.0
    for index, first in enumerate(day_planets):
        weight_a = BRADLEY_WEIGHTS.get(first["name"], 0.0)
        if not weight_a:
            continue
        for second in day_planets[index + 1:]:
            weight_b = BRADLEY_WEIGHTS.get(second["name"], 0.0)
            if not weight_b:
                continue
            separation = _angular_distance(first["longitude"], second["longitude"])
            for target in ASPECT_TARGETS:
                orb = abs(separation - target)
                if orb <= ASPECT_ORB_MAX:
                    sign = -1.0 if target in HARD_ASPECTS else 1.0
                    total += weight_a * weight_b * sign * (1 - orb / ASPECT_ORB_MAX)
    return round(total, 4)


def turning_point_candidates(
    scores_by_date: list[dict[str, Any]], min_swing: float = 0.5
) -> list[dict[str, Any]]:
    """Detect local extremes (turning-point candidates) in a score series.

    `scores_by_date` is a list of {"date", "bradley_score"} ordered by date.
    A day is a candidate when its score is a local extreme by at least
    `min_swing` against both neighbours.
    """
    candidates = []
    for i in range(1, len(scores_by_date) - 1):
        prev_score = scores_by_date[i - 1]["bradley_score"]
        curr_score = scores_by_date[i]["bradley_score"]
        next_score = scores_by_date[i + 1]["bradley_score"]
        if curr_score >= prev_score + min_swing and curr_score >= next_score + min_swing:
            kind = "high"
        elif curr_score <= prev_score - min_swing and curr_score <= next_score - min_swing:
            kind = "low"
        else:
            continue
        candidates.append({"date": scores_by_date[i]["date"], "kind": kind,
                           "bradley_score": curr_score})
    return candidates


def forward_return_validation(
    scores_by_date: list[dict[str, Any]],
    closes_by_date: dict[str, float],
    horizon: int = 5,
) -> dict[str, Any]:
    """Historical validation: correlate barometer sign with forward returns.

    High (low) candidates are validated when the close `horizon` trading days
    later is lower (higher) - i.e. the barometer flagged a real turning point.
    """
    dates = sorted(closes_by_date)
    rank = {d: i for i, d in enumerate(dates)}
    validated = hits = 0
    details = []
    for candidate in turning_point_candidates(scores_by_date):
        d = candidate["date"]
        idx = rank.get(d)
        if idx is None or idx + horizon >= len(dates):
            continue
        base = closes_by_date[dates[idx]]
        future = closes_by_date[dates[idx + horizon]]
        move = (future / base - 1) * 100
        is_hit = (candidate["kind"] == "high" and move < 0) or \
                 (candidate["kind"] == "low" and move > 0)
        validated += 1
        hits += 1 if is_hit else 0
        details.append({"date": d, "kind": candidate["kind"],
                        "forward_move_pct": round(move, 4), "hit": is_hit})
    return {
        "horizon_days": horizon,
        "candidates_evaluated": validated,
        "hits": hits,
        "hit_rate": round(hits / validated, 4) if validated else None,
        "details": details,
    }


__all__ = [
    "bradley_score",
    "turning_point_candidates",
    "forward_return_validation",
    "BRADLEY_WEIGHTS",
]
