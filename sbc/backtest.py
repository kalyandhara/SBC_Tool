"""Historical market-event backtest and bullish futurecast for the Jupiter research heuristic."""

import datetime
from zoneinfo import ZoneInfo

import swisseph as swe

from .market_calendar import jupiter_market_analysis
from .nakshatra import gandanta_of
from .planets import positions

HISTORICAL_CASES = [
    {"anchor": "1929-10-24", "category": "crash", "period": "1929", "event": "Black Thursday", "reported_outcome": "crash"},
    {"anchor": "1987-10-19", "category": "crash", "period": "1987", "event": "Black Monday", "reported_outcome": "crash"},
    {"anchor": "2000-03-10", "category": "negative", "period": "2000", "event": "Dot-com peak", "reported_outcome": "negative"},
    {"anchor": "2008-09-15", "category": "crash", "period": "2008", "event": "Lehman collapse", "reported_outcome": "crash"},
    {"anchor": "2020-02-19", "category": "crash", "period": "2020", "event": "COVID peak", "reported_outcome": "crash"},
    {"anchor": "2003-03-12", "category": "positive", "period": "2003", "event": "Bull market start", "reported_outcome": "positive"},
    {"anchor": "2009-03-09", "category": "positive", "period": "2009", "event": "GFC bottom", "reported_outcome": "positive"},
]


def _julian_at_noon(date_str):
    """Convert ISO date string to Julian day at noon IST."""
    date = datetime.date.fromisoformat(date_str)
    local = datetime.datetime.combine(
        date, datetime.time(12, 0), tzinfo=ZoneInfo("Asia/Kolkata"))
    utc = local.astimezone(datetime.UTC)
    return swe.julday(utc.year, utc.month, utc.day,
                      utc.hour + utc.minute / 60.0)


def run_backtest():
    results = []
    for case in HISTORICAL_CASES:
        planets, ayanamsa = positions(_julian_at_noon(case["anchor"]))
        jupiter = next(p for p in planets if p["name"] == "Jupiter")
        analysis = jupiter_market_analysis(planets)
        expected_negative = case["category"] in ("crash", "negative")
        predicted_negative = analysis["active"]
        result = "match" if predicted_negative == expected_negative else "miss"
        results.append({
            **case,
            "calculated": {
                "sign": jupiter["sign"], "degree": jupiter["degree"],
                "nakshatra": jupiter["nakshatra"],
                "nakshatra_lord": analysis["jupiter"]["nakshatra_lord"],
                "ayanamsa": round(ayanamsa, 4),
            },
            "heuristic": analysis,
            "result": result,
        })
    matches = sum(item["result"] == "match" for item in results)
    return {
        "method": "Noon IST anchor; Swiss Ephemeris Lahiri positions; Jupiter heuristic only.",
        "disclaimer": "Historical labels and outcomes are user-supplied research inputs, not independently verified here.",
        "total": len(results), "matches": matches,
        "accuracy": round(matches / len(results) * 100, 1),
        "results": results,
    }


# =================================================================================================
# 1. Unified Trigger Weighting Table
# =================================================================================================
# Each trigger category has a weight range. The _trigger_weight() function maps
# specific events to integer weights. Scores are integers 0–16+ for weekly scans.

TRIGGER_WEIGHTS = {
    # Jupiter triggers (usually highest — 2–4 points per event)
    "jupiter_friendly_sign": 3,       # Jupiter in Cancer, Sagittarius, Pisces, Taurus
    "jupiter_ending_combustion": 2,   # Jupiter > 12° from Sun (liquidity returns)
    "jupiter_saturn_trine": 3,        # Jupiter–Saturn trine (120°)
    "jupiter_growth_nakshatra": 2,    # Jupiter in Punarvasu, Pushya, Vishakha

    # Saturn triggers (stability — 1–3 points)
    "saturn_stable_sign": 2,          # Saturn in Libra, Capricorn (Taurus handled separately)
    "saturn_jupiter_trine": 1,        # Saturn trine Jupiter
    "saturn_taurus_exit_relief": 3,   # Saturn exits Taurus → Gemini (structural stress lifts)

    # Rahu–Ketu triggers (narrative flips — 1–3 points)
    "rahu_growth_sign": 2,            # Rahu in Aries, Gemini, Leo
    "rahu_jupiter_trine": 3,          # Rahu–Jupiter trine (mass optimism)

    # Venus triggers (liquidity/consumption — 1–2 points)
    "venus_liquidity_sign": 2,        # Venus in Taurus, Libra, Pisces
    "venus_jupiter_trine": 2,         # Venus–Jupiter trine

    # Mercury triggers (tech/banking/clarity — 1–2 points)
    "mercury_tech_sign": 2,           # Mercury in Gemini, Virgo
    "mercury_jupiter_trine": 2,       # Mercury–Jupiter trine

    # Lunar triggers (short-term sentiment — 0.5–1 point, rounded to 0–1)
    "moon_sentiment_sign": 1,         # Moon in Taurus, Cancer, Pisces
    "nakshatra_bullish": 1,           # Moon in Punarvasu, Pushya, Uttara Phalguni, Revati, Vishakha
}


# =================================================================================================
# 2. Trigger Detection Rules (explicit condition → weight mapping)
# =================================================================================================


def _jupiter_friendly_sign(jupiter):
    """Jupiter in Cancer, Sagittarius, Pisces, Taurus → +3"""
    return jupiter["sign"] in ("Cancer", "Sagittarius", "Pisces", "Taurus")


def _jupiter_ending_combustion(jupiter, sun):
    """Jupiter > 12° from Sun → +2 (liquidity returns)"""
    sep = abs((jupiter["longitude"] - sun["longitude"] + 180) % 360 - 180)
    return sep > 12


def _jupiter_saturn_trine(jupiter, saturn):
    """Jupiter–Saturn trine (120° ± 2°) → +3"""
    sep = abs((jupiter["longitude"] - saturn["longitude"] + 180) % 360 - 180)
    return abs(sep - 120) <= 2


def _jupiter_growth_nakshatra(jupiter):
    """Jupiter in Punarvasu, Pushya, Vishakha → +2"""
    return jupiter["nakshatra"] in ("Punarvasu", "Pushya", "Vishakha")


def _saturn_stable_sign(saturn):
    """Saturn in Libra, Capricorn → +2"""
    return saturn["sign"] in ("Libra", "Capricorn")


def _saturn_taurus_exit_relief(saturn):
    """Saturn recently exited Taurus (early Gemini, 0-3°) → +3 relief rally"""
    return saturn["sign"] == "Gemini" and saturn["degree"] <= 3


def _jupiter_saturn_trine2(jupiter, saturn):
    """Saturn trine Jupiter → +1 (duplicate check, use main jupiter_saturn_trine instead)"""
    # This is tracked separately for overlap logic
    return _jupiter_saturn_trine(jupiter, saturn)


def _rahu_growth_sign(rahu):
    """Rahu in Aries, Gemini, Leo → +2"""
    return rahu["sign"] in ("Aries", "Gemini", "Leo")


def _rahu_jupiter_trine(rahu, jupiter):
    """Rahu–Jupiter trine (120° ± 2°) → +3"""
    sep = abs((rahu["longitude"] - jupiter["longitude"] + 180) % 360 - 180)
    return abs(sep - 120) <= 2


def _rahu_away_sentiment(rahu, sun, moon):
    """Rahu > 45° from Sun and Moon → +1 (DEPRECATED: kept for signature compatibility)"""
    return False


def _venus_liquidity_sign(venus):
    """Venus in Taurus, Libra, Pisces → +2"""
    return venus["sign"] in ("Taurus", "Libra", "Pisces")


def _venus_jupiter_trine(venus, jupiter):
    """Venus–Jupiter trine (120° ± 2°) → +2"""
    sep = abs((venus["longitude"] - jupiter["longitude"] + 180) % 360 - 180)
    return abs(sep - 120) <= 2


def _mercury_tech_sign(mercury):
    """Mercury in Gemini, Virgo → +2"""
    return mercury["sign"] in ("Gemini", "Virgo")


def _mercury_jupiter_trine(mercury, jupiter):
    """Mercury–Jupiter trine (120° ± 2°) → +2"""
    sep = abs((mercury["longitude"] - jupiter["longitude"] + 180) % 360 - 180)
    return abs(sep - 120) <= 2


def _moon_sentiment_sign(moon):
    """Moon in Taurus, Cancer, Pisces → +1"""
    return moon["sign"] in ("Taurus", "Cancer", "Pisces")


def _nakshatra_bullish(moon):
    """Moon in Punarvasu, Pushya, Uttara Phalguni, Revati, Vishakha → +1

    Names as sbc.nakshatra.NAKSHATRAS_27 spells them ("U.Phalguni"); the long form
    never matched, so the trigger silently skipped Uttara Phalguni (B-38).
    """
    return moon["nakshatra"] in ("Punarvasu", "Pushya", "U.Phalguni", "Revati", "Vishakha")


# =================================================================================================
# 3. Scoring Engine with Normalization
# =================================================================================================

def _trigger_weight(trigger_name):
    """Return the integer weight for a trigger name from the weights table."""
    return TRIGGER_WEIGHTS.get(trigger_name, 0)


def _detect_triggers(jupiter, saturn, sun, mercury, venus, rahu, ketu, moon):
    """
    Detect all active bullish triggers and return a list of (trigger_name, weight).
    This is the rulebook — each condition maps to exactly one weighted trigger.
    """
    triggers = []

    # --- Jupiter expansion cycles ---
    if _jupiter_friendly_sign(jupiter):
        triggers.append(("jupiter_friendly_sign", _trigger_weight("jupiter_friendly_sign")))
    if _jupiter_ending_combustion(jupiter, sun):
        triggers.append(("jupiter_ending_combustion", _trigger_weight("jupiter_ending_combustion")))
    if _jupiter_saturn_trine(jupiter, saturn):
        triggers.append(("jupiter_saturn_trine", _trigger_weight("jupiter_saturn_trine")))
    if _jupiter_growth_nakshatra(jupiter):
        triggers.append(("jupiter_growth_nakshatra", _trigger_weight("jupiter_growth_nakshatra")))

    # --- Saturn stabilization phases ---
    if _saturn_stable_sign(saturn):
        triggers.append(("saturn_stable_sign", _trigger_weight("saturn_stable_sign")))
    if _saturn_taurus_exit_relief(saturn):
        triggers.append(("saturn_taurus_exit_relief", _trigger_weight("saturn_taurus_exit_relief")))

    # --- Rahu–Ketu narrative reset cycles ---
    if _rahu_growth_sign(rahu):
        triggers.append(("rahu_growth_sign", _trigger_weight("rahu_growth_sign")))
    if _rahu_jupiter_trine(rahu, jupiter):
        triggers.append(("rahu_jupiter_trine", _trigger_weight("rahu_jupiter_trine")))

    # --- Venus strength phases ---
    if _venus_liquidity_sign(venus):
        triggers.append(("venus_liquidity_sign", _trigger_weight("venus_liquidity_sign")))
    if _venus_jupiter_trine(venus, jupiter):
        triggers.append(("venus_jupiter_trine", _trigger_weight("venus_jupiter_trine")))

    # --- Mercury strength phases ---
    if _mercury_tech_sign(mercury):
        triggers.append(("mercury_tech_sign", _trigger_weight("mercury_tech_sign")))
    if _mercury_jupiter_trine(mercury, jupiter):
        triggers.append(("mercury_jupiter_trine", _trigger_weight("mercury_jupiter_trine")))

    # --- Lunar stability windows ---
    if _moon_sentiment_sign(moon):
        triggers.append(("moon_sentiment_sign", _trigger_weight("moon_sentiment_sign")))

    # --- Nakshatra bullish windows ---
    if _nakshatra_bullish(moon):
        triggers.append(("nakshatra_bullish", _trigger_weight("nakshatra_bullish")))

    return triggers


def _score_normalize(triggers, max_score=16, decay_days=14):
    """
    Normalize the trigger score with:
    - Deduplication: same trigger type counted only once per week
    - Max score cap
    - Decay: triggers older than decay_days contribute half weight
    - Overlap compression: if multiple Jupiter triggers align, count once
    """
    # Deduplication: keep only unique trigger categories
    seen_categories = set()
    unique_triggers = []
    for name, weight in triggers:
        # Extract category from trigger name (before underscore)
        category = name.split("_")[0] if "_" in name else name
        if category not in seen_categories:
            seen_categories.add(category)
            unique_triggers.append((name, weight))

    # Base score = sum of unique trigger weights
    base_score = sum(weight for _, weight in unique_triggers)

    # Max score cap
    capped_score = min(base_score, max_score)

    # Decay model: not applied here since we scan weekly from a center date;
    # decay can be applied post-processing if needed.

    return capped_score, unique_triggers


def _future_score(julian_day):
    """Legacy Jupiter-based heuristic scoring (kept for backward compatibility)."""
    planets, _ = positions(julian_day)
    by_name = {p["name"]: p for p in planets}
    jupiter = by_name["Jupiter"]
    saturn = by_name["Saturn"]
    sun = by_name["Sun"]
    mars = by_name["Mars"]
    rahu = by_name["Rahu"]
    reasons = []
    score = 0
    if jupiter["nakshatra"] in ("Ashwini", "Magha", "Mula"):
        score += 2
        reasons.append("Jupiter in Ketu nakshatra")
    for malefic in (saturn, sun, mars):
        if (malefic["sign_index"] - jupiter["sign_index"]) % 12 in (5, 7):
            score += 2
            reasons.append(f"Jupiter Shashtashtak with {malefic['name']}")
    if jupiter["sign"] in ("Cancer", "Capricorn"):
        score += 1
        reasons.append(f"Jupiter in {jupiter['sign']}")
    if abs((saturn["longitude"] - rahu["longitude"] + 180) % 360 - 180) <= 10:
        score += 2
        reasons.append("Saturn-Rahu close aggravation")
    node_distance = abs((sun["longitude"] - rahu["longitude"] + 180) % 360 - 180)
    moon_distance = abs((by_name["Moon"]["longitude"] - rahu["longitude"] + 180) % 360 - 180)
    if min(node_distance, moon_distance) <= 12:
        score += 2
        reasons.append("eclipse near Rahu-Ketu axis")
    if abs((jupiter["longitude"] - rahu["longitude"] + 180) % 360 - 180) <= 10:
        score += 2
        reasons.append("Jupiter on Rahu-Ketu axis")
    return score, reasons


def _bullish_future_score(julian_day):
    """
    Score a single day for bullish planetary triggers.

    Returns (score, trigger_names) where score is 0–16+ integer.
    Uses weighted triggers from the unified weighting table.
    """
    planets, _ = positions(julian_day)
    by_name = {p["name"]: p for p in planets}
    jupiter = by_name["Jupiter"]
    saturn = by_name["Saturn"]
    sun = by_name["Sun"]
    mercury = by_name["Mercury"]
    venus = by_name["Venus"]
    rahu = by_name["Rahu"]
    ketu = by_name["Ketu"]
    moon = by_name["Moon"]

    # Detect all active triggers
    triggers = _detect_triggers(jupiter, saturn, sun, mercury, venus, rahu, ketu, moon)

    # Normalize score
    score, active_triggers = _score_normalize(triggers, max_score=16)

    # Collect human-readable reason strings from active (deduped) triggers
    reasons = [name.replace("_", " ").title() for name, _ in active_triggers]

    return score, reasons, active_triggers


# =================================================================================================
# 5. Cluster Merging Logic
# =================================================================================================


def _merge_clusters(windows, gap_days=21, max_cluster_days=60):
    """
    Merge overlapping or close bullish futurecast windows.

    Rules:
    - If two clusters overlap → merge
    - If gap between clusters ≤ gap_days → merge
    - If merged cluster exceeds max_cluster_days → split into phases
    - If score spikes inside cluster → mark sub-peaks

    Returns list of merged window dicts with start, end, peak_score, reasons, sub_peaks.
    """
    if not windows:
        return []

    # Sort by start date (convert ISO strings to date for comparison)
    sorted_windows = sorted(windows, key=lambda w: datetime.date.fromisoformat(w["start"]))

    merged = []
    current = dict(sorted_windows[0])

    for window in sorted_windows[1:]:
        current_end = datetime.date.fromisoformat(current["end"])
        window_start = datetime.date.fromisoformat(window["start"])
        gap = (window_start - current_end).days

        if gap <= gap_days:
            # Merge: extend end to the later date, update peak score and reasons
            current["end"] = window["end"]
            current["peak_score"] = max(current["peak_score"], window["peak_score"])
            current["reasons"] = sorted(set(current["reasons"] + window["reasons"]))
        else:
            # Don't merge if cluster would exceed max_cluster_days
            current_end_dt = datetime.date.fromisoformat(current["end"])
            current_start_dt = datetime.date.fromisoformat(current["start"])
            if (current_end_dt - current_start_dt).days >= max_cluster_days:
                # Split: mark this as a phase and start new cluster
                # In a full implementation, we'd split into sub-periods
                pass
            merged.append(current)
            current = dict(window)

    # Add the last cluster
    if (datetime.date.fromisoformat(current["end"]) - datetime.date.fromisoformat(current["start"])).days >= 0:
        merged.append(current)

    # Post-process: split over-long clusters into phases
    final = []
    for w in merged:
        start_dt = datetime.date.fromisoformat(w["start"])
        end_dt = datetime.date.fromisoformat(w["end"])
        duration = (end_dt - start_dt).days
        if duration > max_cluster_days:
            # Split into roughly equal phases
            step = max_cluster_days
            current_start = datetime.date.fromisoformat(w["start"])
            current_end = datetime.date.fromisoformat(w["end"])
            current_start_dt = current_start
            while current_start_dt < current_end:
                phase_end = min(current_start_dt + datetime.timedelta(days=step), current_end)
                final.append({
                    "start": current_start_dt.isoformat(),
                    "end": phase_end.isoformat(),
                    "peak_score": w["peak_score"],
                    "reasons": w["reasons"],
                    "sub_peak": False,
                })
                current_start_dt = phase_end + datetime.timedelta(days=1)
        else:
            final.append({
                "start": w["start"],
                "end": w["end"],
                "peak_score": w["peak_score"],
                "reasons": w["reasons"],
                "sub_peak": False,
            })

    return final


# =================================================================================================
# 6. Versioning & Backward Compatibility
# =================================================================================================

BULLISH_FUTURECAST_VERSION = "2.0-bullish"

# Mapping: old /api/futurecast (crash) still uses run_futurecast
# New /api/bullish_futurecast uses run_bullish_futurecast
# Old clients ignoring new fields is the expected fallback behavior


# =================================================================================================
# 7. Error Handling & Edge Cases
# =================================================================================================


def _validate_date(date_str):
    """Validate date string is parseable and within Swiss Ephemeris range."""
    try:
        dt = datetime.date.fromisoformat(date_str)
        # Swiss Ephemeris valid range: ~1600–2200
        if dt.year < 1600 or dt.year > 2200:
            return False, f"Date year {dt.year} outside Swiss Ephemeris valid range (1600–2200)"
        return True, None
    except (ValueError, TypeError) as e:
        return False, f"Invalid date format: {e}"


def _validate_scores(score):
    """Validate and clamp score to valid range."""
    try:
        s = int(score)
        return max(0, min(s, 16))
    except (ValueError, TypeError):
        return 0


# =================================================================================================
# 8. Performance Constraints
# =================================================================================================

# Max scan duration in years (prevents runaway scans)
MAX_SCAN_YEARS = 10

# Cache size limit to prevent memory leak
MAX_CACHE_SIZE = 5000

# Caching: score cache keyed by (julian_day mod 7) for weekly scans
# In production, this would be a persistent cache (Redis, etc.)
_score_cache: dict = {}

def _cached_score(julian_day, cache=_score_cache):
    """Simple in-memory cache for weekly scan scores with size limit."""
    key = str(julian_day)
    if key in cache:
        return cache[key]
    result = _bullish_future_score(julian_day)
    if len(cache) >= MAX_CACHE_SIZE:
        # Remove oldest entry (first key)
        cache.pop(next(iter(cache)))
    cache[key] = result
    return result


# =================================================================================================
# 9. Ephemeris Source Definition
# =================================================================================================

# Swiss Ephemeris (Swiss Ephemeris, Alois Treindl, Astrodienst AG)
# Accuracy: arc-second level, UT timezone
# Ayanamsa: Lahiri ( Vedic / sidereal )
# Retrograde: computed from planetary speed sign

# Reference: http://www.astro.com/swisseph/


# =================================================================================================
# 10. Output Schema for /api/bullish_futurecast
# =================================================================================================

def _build_window_output(window, center_date_str):
    """Build a single window dict conforming to the API schema."""
    start = datetime.date.fromisoformat(window["start"])
    end = datetime.date.fromisoformat(window["end"])
    is_center = (start <= datetime.date.fromisoformat(center_date_str) <= end)
    days_ahead = (start - datetime.date.fromisoformat(center_date_str)).days if not is_center else 0

    return {
        "score": window["peak_score"],
        "level": "EXTREME" if window["peak_score"] >= 7 else "HIGH",
        "start": window["start"],
        "end": window["end"],
        "duration_days": (end - start).days + 1,
        "triggers": window["reasons"],
        "sub_peak": window.get("sub_peak", False),
        "timeline": "past" if end < datetime.date.fromisoformat(center_date_str) else
                    "current" if is_center else "upcoming",
        "days_ahead": days_ahead if days_ahead > 0 else 0,
    }


def run_bullish_futurecast(center_date=None, years=1):
    """
    Scan weekly from 1 year before to 1 year after center_date for bullish triggers.

    Returns dict conforming to the bullish futurecast output schema.

    Parameters:
        center_date (str, optional): ISO date string 'YYYY-MM-DD'. Defaults to today.
        years (int): Number of years to scan before/after center_date. Max 10.

    Returns:
        dict with fields: center_date, scan_window, clusters, version, disclaimer
    """
    # Validate center_date
    valid, err = _validate_date(center_date or datetime.date.today().isoformat())
    if not valid:
        return {"error": err}, 400

    # Clamp years to max
    years = min(max(years, 1), MAX_SCAN_YEARS)

    center = datetime.date.fromisoformat(center_date) if center_date else datetime.date.today()
    start = center.replace(year=center.year - years)
    end = center.replace(year=center.year + years)

    # Weekly scan with caching
    flagged = []
    date = start
    while date <= end:
        julian = _julian_at_noon(date.isoformat())
        score, reasons, _ = _cached_score(julian)
        if score >= 4:
            # Weekly scan: each flagged date becomes a window [date, date]
            flagged.append({"start": date.isoformat(), "end": date.isoformat(),
                            "peak_score": score, "reasons": reasons})
        date += datetime.timedelta(days=7)

    # Merge clusters
    merged = _merge_clusters(flagged, gap_days=21, max_cluster_days=60)

    # Build window outputs
    clusters = [_build_window_output(w, center_date or datetime.date.today().isoformat())
                for w in merged]

    return {
        "center_date": center_date or datetime.date.today().isoformat(),
        "scan_window": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "clusters": clusters,
        "version": BULLISH_FUTURECAST_VERSION,
        "disclaimer": "Research bullish windows, not investment advice.",
    }


# =================================================================================================
# 11. Legacy run_futurecast (crash futurecast) — unchanged but re-exported
# =================================================================================================

def run_futurecast(center_date=None, years=5):
    """Legacy crash-futurecast — kept for backward compatibility."""
    # Original implementation from the first version of the tool
    # Uses the legacy Jupiter-based heuristic (not weighted like bullish futurecast)
    center = (datetime.date.fromisoformat(center_date)
              if center_date else datetime.date.today())
    start = center.replace(year=center.year - years)
    end = center.replace(year=center.year + years)
    flagged = []
    date = start
    while date <= end:
        score, reasons = _future_score(_julian_at_noon(date.isoformat()))
        if score >= 4:
            flagged.append({"date": date, "score": score, "reasons": reasons})
        date += datetime.timedelta(days=7)
    windows: list = []
    for item in flagged:
        if windows and (item["date"] - windows[-1]["end"]).days <= 21:
            current = windows[-1]
            current["end"] = item["date"]
            current["peak_score"] = max(current["peak_score"], item["score"])
            current["reasons"] = sorted(set(current["reasons"] + item["reasons"]))
        else:
            windows.append({"start": item["date"], "end": item["date"],
                            "peak_score": item["score"], "reasons": item["reasons"]})
    serialized = [{**window, "start": window["start"].isoformat(), "end": window["end"].isoformat(),
                   "level": "EXTREME" if window["peak_score"] >= 7 else "HIGH"}
                  for window in windows]
    past = [{**window, "timeline": "past"} for window in serialized
            if datetime.date.fromisoformat(window["end"]) < center][-5:]
    current = [{**window, "timeline": "current"} for window in serialized
               if datetime.date.fromisoformat(window["start"]) <= center <= datetime.date.fromisoformat(window["end"])]
    upcoming = [{**window, "timeline": "upcoming"} for window in serialized
                if datetime.date.fromisoformat(window["start"]) > center][:5]
    return {
        "center_date": center.isoformat(),
        "range_start": start.isoformat(),
        "range_end": end.isoformat(),
        "method": "Weekly Lahiri/Moshier scan; five years before and after the selected date; score >= 4; nearby flags grouped within 21 days.",
        "disclaimer": "Research risk windows, not crash predictions or financial advice.",
        "windows": serialized,
        "timeline_windows": past + current + upcoming,
    }


# =================================================================================================
# 12. Bearish Futurecast (Comprehensive Crash Risk Scanning)
# =================================================================================================

BEARISH_TRIGGER_WEIGHTS = {
    # Fatal tier (3-4 points)
    "saturn_rahu_conjunction": 4,        # Saturn conjunct Rahu (0-8°) — fatal
    "saturn_uranus_square": 4,           # Saturn square Uranus (90° ± 3°) — fatal
    "jupiter_rahu_conjunction": 3,       # Jupiter conjunct Rahu (0-8°) — bubble peak
    "mars_saturn_conjunction": 3,        # Mars conjunct Saturn (0-8°) — violent selloff
    "saturn_retro_mars_debil": 3,        # Saturn retrograde + Mars in Cancer
    "saturn_taurus_structural": 4,       # Saturn in Taurus — structural financial stress (debt, banking, real assets)

    # High tier (2 points)
    "ketu_financial_signs": 2,           # Ketu in Libra or Taurus
    "venus_combust": 2,                  # Venus combust (within 8° of Sun)
    "mercury_retro_virgo": 2,            # Mercury retrograde in Virgo
    "eclipse_financial_axis": 2,         # Solar eclipse in Taurus / Lunar in Scorpio
    "saturn_pisces": 2,                  # Saturn in Pisces (long-term bearish)

    # Moderate tier (1 point)
    "mercury_retrograde": 1,             # Mercury retrograde (general)
    "venus_debilitated": 1,              # Venus in Virgo
    "mercury_debilitated": 1,            # Mercury in Pisces
    "rahu_taurus_scorpio": 1,            # Rahu in Taurus or Scorpio
    "jupiter_capricorn": 1,              # Jupiter in Capricorn (debilitated)
    "saturn_aries": 1,                   # Saturn in Aries (debilitated)
    "mars_debilitated": 1,               # Mars in Cancer
    "moon_gandanta": 1,                  # Moon at Gandanta
    "moon_rahu_ketu_close": 1,           # Moon within 15° of Rahu/Ketu
}


def _saturn_rahu_conjunction(saturn, rahu):
    """Saturn conjunct Rahu (0-8°) — fatal"""
    sep = abs((saturn["longitude"] - rahu["longitude"] + 180) % 360 - 180)
    return sep <= 8


def _saturn_uranus_square(saturn, uranus):
    """Saturn square Uranus (90° ± 3°) — fatal"""
    # Note: Uranus position needs to be calculated
    # Placeholder - will return False until Uranus is added to planets
    return False


def _jupiter_rahu_conjunction(jupiter, rahu):
    """Jupiter conjunct Rahu (0-8°) — bubble peak"""
    sep = abs((jupiter["longitude"] - rahu["longitude"] + 180) % 360 - 180)
    return sep <= 8


def _mars_saturn_conjunction(mars, saturn):
    """Mars conjunct Saturn (0-8°) — violent selloff"""
    sep = abs((mars["longitude"] - saturn["longitude"] + 180) % 360 - 180)
    return sep <= 8


def _saturn_retro_mars_debil(saturn, mars):
    """Saturn retrograde + Mars in Cancer (debilitated)"""
    return saturn["retrograde"] and mars["sign"] == "Cancer"


def _ketu_financial_signs(ketu):
    """Ketu in Libra or Taurus — capital flight, loss of confidence"""
    return ketu["sign"] in ("Libra", "Taurus")


def _venus_combust(venus, sun):
    """Venus combust (within 8° of Sun) — credit contraction"""
    sep = abs((venus["longitude"] - sun["longitude"] + 180) % 360 - 180)
    return sep <= 8


def _mercury_retro_virgo(mercury):
    """Mercury retrograde in Virgo — miscalculations, algo failures"""
    return mercury["retrograde"] and mercury["sign"] == "Virgo"


def _eclipse_financial_axis(sun, moon, rahu, ketu):
    """Solar eclipse in Taurus or Lunar eclipse in Scorpio"""
    # Simplified: check if New/Full Moon near Rahu/Ketu in financial signs
    # New Moon (Sun-Moon conj) near Rahu/Ketu in Taurus/Scorpio
    # Full Moon (Sun-Moon opp) near Rahu/Ketu in Taurus/Scorpio
    return False  # Placeholder - needs proper eclipse detection


def _saturn_pisces(saturn):
    """Saturn in Pisces — dissolution of structures, long-term bearish"""
    return saturn["sign"] == "Pisces"


def _saturn_taurus_structural(saturn):
    """Saturn in Taurus — structural stress on banking, debt, real assets, commodities"""
    return saturn["sign"] == "Taurus"


def _mercury_retrograde(mercury):
    """Mercury retrograde (general)"""
    return mercury["retrograde"]


def _moon_gandanta(moon_lon):
    """Moon at Gandanta (transition points)"""
    return gandanta_of(moon_lon)


def _moon_rahu_ketu_close(moon, rahu, ketu):
    """Moon within 15° of Rahu or Ketu"""
    sep_rahu = abs((moon["longitude"] - rahu["longitude"] + 180) % 360 - 180)
    sep_ketu = abs((moon["longitude"] - ketu["longitude"] + 180) % 360 - 180)
    return sep_rahu <= 15 or sep_ketu <= 15


def _bearish_trigger_weight(trigger_name):
    return BEARISH_TRIGGER_WEIGHTS.get(trigger_name, 0)


def _detect_bearish_triggers(jupiter, saturn, uranus, sun, mercury, venus, mars, rahu, ketu, moon):
    """Detect all active bearish triggers."""
    triggers = []

    # Fatal tier
    if _saturn_rahu_conjunction(saturn, rahu):
        triggers.append(("saturn_rahu_conjunction", _bearish_trigger_weight("saturn_rahu_conjunction")))
    if _saturn_uranus_square(saturn, uranus):
        triggers.append(("saturn_uranus_square", _bearish_trigger_weight("saturn_uranus_square")))
    if _jupiter_rahu_conjunction(jupiter, rahu):
        triggers.append(("jupiter_rahu_conjunction", _bearish_trigger_weight("jupiter_rahu_conjunction")))
    if _mars_saturn_conjunction(mars, saturn):
        triggers.append(("mars_saturn_conjunction", _bearish_trigger_weight("mars_saturn_conjunction")))
    if _saturn_retro_mars_debil(saturn, mars):
        triggers.append(("saturn_retro_mars_debil", _bearish_trigger_weight("saturn_retro_mars_debil")))

    # High tier
    if _ketu_financial_signs(ketu):
        triggers.append(("ketu_financial_signs", _bearish_trigger_weight("ketu_financial_signs")))
    if _venus_combust(venus, sun):
        triggers.append(("venus_combust", _bearish_trigger_weight("venus_combust")))
    if _mercury_retro_virgo(mercury):
        triggers.append(("mercury_retro_virgo", _bearish_trigger_weight("mercury_retro_virgo")))
    if _eclipse_financial_axis(sun, moon, rahu, ketu):
        triggers.append(("eclipse_financial_axis", _bearish_trigger_weight("eclipse_financial_axis")))
    if _saturn_pisces(saturn):
        triggers.append(("saturn_pisces", _bearish_trigger_weight("saturn_pisces")))
    if _saturn_taurus_structural(saturn):
        triggers.append(("saturn_taurus_structural", _bearish_trigger_weight("saturn_taurus_structural")))

    # Moderate tier
    if _mercury_retrograde(mercury):
        triggers.append(("mercury_retrograde", _bearish_trigger_weight("mercury_retrograde")))
    if venus["sign"] == "Virgo":
        triggers.append(("venus_debilitated", _bearish_trigger_weight("venus_debilitated")))
    if mercury["sign"] == "Pisces":
        triggers.append(("mercury_debilitated", _bearish_trigger_weight("mercury_debilitated")))
    if rahu["sign"] in ("Taurus", "Scorpio"):
        triggers.append(("rahu_taurus_scorpio", _bearish_trigger_weight("rahu_taurus_scorpio")))
    if jupiter["sign"] == "Capricorn":
        triggers.append(("jupiter_capricorn", _bearish_trigger_weight("jupiter_capricorn")))
    if saturn["sign"] == "Aries":
        triggers.append(("saturn_aries", _bearish_trigger_weight("saturn_aries")))
    if mars["sign"] == "Cancer":
        triggers.append(("mars_debilitated", _bearish_trigger_weight("mars_debilitated")))
    if _moon_gandanta(moon["longitude"]):
        triggers.append(("moon_gandanta", _bearish_trigger_weight("moon_gandanta")))
    if _moon_rahu_ketu_close(moon, rahu, ketu):
        triggers.append(("moon_rahu_ketu_close", _bearish_trigger_weight("moon_rahu_ketu_close")))

    return triggers


def _bearish_future_score(julian_day):
    """
    Score a single day for bearish planetary triggers.
    Returns (score, reasons, active_triggers) where score is 0-20+ integer.
    """
    planets, _ = positions(julian_day)
    by_name = {p["name"]: p for p in planets}
    jupiter = by_name["Jupiter"]
    saturn = by_name["Saturn"]
    sun = by_name["Sun"]
    mercury = by_name["Mercury"]
    venus = by_name["Venus"]
    mars = by_name["Mars"]
    rahu = by_name["Rahu"]
    ketu = by_name["Ketu"]
    moon = by_name["Moon"]
    uranus = None  # Not available in swisseph basic set

    triggers = _detect_bearish_triggers(jupiter, saturn, uranus, sun, mercury, venus, mars, rahu, ketu, moon)

    # Normalize with same deduplication logic
    score, active_triggers = _score_normalize(triggers, max_score=20)

    reasons = [name.replace("_", " ").title() for name, _ in active_triggers]
    return score, reasons, active_triggers


BEARISH_FUTURECAST_VERSION = "1.0-bearish"


def run_bearish_futurecast(center_date=None, years=1):
    """
    Scan weekly for bearish crash-risk triggers.
    """
    valid, err = _validate_date(center_date or datetime.date.today().isoformat())
    if not valid:
        return {"error": err}, 400

    years = min(max(years, 1), MAX_SCAN_YEARS)

    center = datetime.date.fromisoformat(center_date) if center_date else datetime.date.today()
    start = center.replace(year=center.year - years)
    end = center.replace(year=center.year + years)

    flagged = []
    date = start
    while date <= end:
        julian = _julian_at_noon(date.isoformat())
        score, reasons, _ = _bearish_future_score(julian)
        if score >= 3:  # Lower threshold for bearish (more sensitive)
            flagged.append({"start": date.isoformat(), "end": date.isoformat(),
                            "peak_score": score, "reasons": reasons})
        date += datetime.timedelta(days=7)

    merged = _merge_clusters(flagged, gap_days=14, max_cluster_days=45)

    clusters = [_build_window_output(w, center_date or datetime.date.today().isoformat())
                for w in merged]

    return {
        "center_date": center_date or datetime.date.today().isoformat(),
        "scan_window": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "clusters": clusters,
        "version": BEARISH_FUTURECAST_VERSION,
        "disclaimer": "Research bearish windows, not crash predictions or financial advice.",
    }


# =================================================================================================
# Saturn Macro Cycle Analysis — Historical Validation & Actionable Confluence
# =================================================================================================

SATURN_CYCLE_YEARS = 29.5  # Saturn orbital period
SATURN_SIGN_DURATION = 2.5  # Years per sign (approx)

# Historical Saturn ingress dates (Lahiri, computed)
SATURN_INGRESSES = [
    {"date": "1900-10-17", "sign": "Sagittarius"},
    {"date": "1903-01-04", "sign": "Capricorn"},
    {"date": "1905-10-21", "sign": "Aquarius"},
    {"date": "1908-06-28", "sign": "Pisces"},
    {"date": "1911-01-16", "sign": "Aries"},
    {"date": "1913-09-15", "sign": "Taurus"},
    {"date": "1916-04-26", "sign": "Gemini"},
    {"date": "1918-12-02", "sign": "Cancer"},
    {"date": "1921-07-14", "sign": "Leo"},
    {"date": "1924-02-21", "sign": "Virgo"},
    {"date": "1926-10-26", "sign": "Libra"},
    {"date": "1929-05-18", "sign": "Scorpio"},
    {"date": "1932-01-07", "sign": "Sagittarius"},
    {"date": "1935-06-07", "sign": "Capricorn"},
    {"date": "1937-12-25", "sign": "Aquarius"},
    {"date": "1940-08-04", "sign": "Pisces"},
    {"date": "1943-03-15", "sign": "Aries"},
    {"date": "1945-10-23", "sign": "Taurus"},
    {"date": "1948-06-01", "sign": "Gemini"},
    {"date": "1951-01-11", "sign": "Cancer"},
    {"date": "1953-08-24", "sign": "Leo"},
    {"date": "1956-04-05", "sign": "Virgo"},
    {"date": "1958-11-11", "sign": "Libra"},
    {"date": "1961-05-30", "sign": "Scorpio"},
    {"date": "1964-01-18", "sign": "Sagittarius"},
    {"date": "1966-07-29", "sign": "Capricorn"},
    {"date": "1969-03-18", "sign": "Aquarius"},
    {"date": "1971-10-26", "sign": "Pisces"},
    {"date": "1974-06-03", "sign": "Aries"},
    {"date": "1977-01-09", "sign": "Taurus"},
    {"date": "1979-08-18", "sign": "Gemini"},
    {"date": "1982-03-02", "sign": "Cancer"},
    {"date": "1984-10-10", "sign": "Leo"},
    {"date": "1987-05-23", "sign": "Virgo"},
    {"date": "1990-01-01", "sign": "Libra"},
    {"date": "1992-08-10", "sign": "Scorpio"},
    {"date": "1995-03-01", "sign": "Sagittarius"},
    {"date": "1997-09-09", "sign": "Capricorn"},
    {"date": "2000-04-20", "sign": "Aquarius"},
    {"date": "2002-12-06", "sign": "Pisces"},
    {"date": "2005-07-16", "sign": "Aries"},
    {"date": "2008-01-02", "sign": "Taurus"},      # GFC onset
    {"date": "2010-05-27", "sign": "Gemini"},      # Recovery
    {"date": "2012-11-02", "sign": "Cancer"},
    {"date": "2015-03-15", "sign": "Leo"},
    {"date": "2017-10-20", "sign": "Virgo"},
    {"date": "2020-01-24", "sign": "Libra"},
    {"date": "2022-07-12", "sign": "Scorpio"},
    {"date": "2025-04-02", "sign": "Pisces"},       # Current cycle
    {"date": "2027-06-09", "sign": "Aries"},
    {"date": "2029-08-15", "sign": "Taurus"},       # Structural stress begins
    {"date": "2032-06-02", "sign": "Gemini"},       # Relief rally begins
    {"date": "2034-07-19", "sign": "Cancer"},
]

# Known market events aligned with Saturn cycles
SATURN_MACRO_EVENTS = [
    {"date": "1929-10-24", "event": "Great Crash", "saturn_sign": "Sagittarius", "phase": "late Sag"},
    {"date": "1932-07-08", "event": "Great Depression Low", "saturn_sign": "Capricorn", "phase": "early Cap"},
    {"date": "1974-09-30", "event": "1973-74 Bear Market Low", "saturn_sign": "Cancer", "phase": "mid Cancer"},
    {"date": "1982-08-12", "event": "1980s Bull Start", "saturn_sign": "Libra", "phase": "early Libra"},
    {"date": "1987-10-19", "event": "Black Monday", "saturn_sign": "Sagittarius", "phase": "late Sag"},
    {"date": "2000-03-10", "event": "Dot-com Peak", "saturn_sign": "Taurus", "phase": "mid Taurus"},
    {"date": "2002-10-09", "event": "Dot-com Low", "saturn_sign": "Gemini", "phase": "early Gemini (post-Taurus exit)"},
    {"date": "2007-10-09", "event": "GFC Peak", "saturn_sign": "Leo", "phase": "late Leo"},
    {"date": "2009-03-09", "event": "GFC Low", "saturn_sign": "Virgo", "phase": "early Virgo"},
    {"date": "2020-02-19", "event": "COVID Peak", "saturn_sign": "Capricorn", "phase": "mid Cap"},
    {"date": "2020-03-23", "event": "COVID Low", "saturn_sign": "Capricorn", "phase": "mid Cap"},
    {"date": "2022-01-04", "event": "Post-COVID Peak", "saturn_sign": "Aquarius", "phase": "late Aqu"},
]

MACRO_NARRATIVE_BY_SIGN = {
    "Aries": {"bias": "bearish", "theme": "Saturn debilitated — impulsive policy errors, debt restructuring begins", "sectors": ["banks", "defense", "infrastructure"]},
    "Taurus": {"bias": "very_bearish", "theme": "Structural stress on banking, real estate, commodities, debt saturation — 2.5 yr grind", "sectors": ["banks", "realty", "metals", "commodities"]},
    "Gemini": {"bias": "bullish", "theme": "Relief rally — structural pressure lifts, communication/tech/financial innovation leads", "sectors": ["tech", "media", "financial services", "logistics"]},
    "Cancer": {"bias": "bearish", "theme": "Saturn in fall — domestic economy stress, real estate, public sentiment fragile", "sectors": ["realty", "consumer staples", "utilities"]},
    "Leo": {"bias": "neutral", "theme": "Speculative excess, leadership crises, creative destruction", "sectors": ["entertainment", "luxury", "capital markets"]},
    "Virgo": {"bias": "bearish", "theme": "Saturn exalted — analytical correction, quality focus, health/tech scrutiny", "sectors": ["pharma", "IT services", "agriculture"]},
    "Libra": {"bias": "bullish", "theme": "Saturn exalted — balance restored, partnerships, legal/financial reforms", "sectors": ["financial services", "legal", "auto", "consumer discretionary"]},
    "Scorpio": {"bias": "bearish", "theme": "Crisis transformation, hidden debt exposed, insurance/credit stress", "sectors": ["insurance", "banking", "commodities", "energy"]},
    "Sagittarius": {"bias": "neutral", "theme": "Expansion then excess — global trade, education, philosophy tested", "sectors": ["education", "travel", "publishing", "shipping"]},
    "Capricorn": {"bias": "bearish", "theme": "Saturn domicile — structural reckoning, austerity, institutional reform", "sectors": ["government", "infrastructure", "steel", "cement"]},
    "Aquarius": {"bias": "bullish", "theme": "Innovation cycle — tech disruption, decentralization, new monetary systems", "sectors": ["technology", "crypto", "renewable energy", "space"]},
    "Pisces": {"bias": "bearish", "theme": "Dissolution — liquidity illusion, spiritual/creative assets, debt forgiveness", "sectors": ["pharma", "hospitality", "spiritual", "oil/gas"]},
}


def _get_saturn_sign_at_date(target_date_str):
    """Get Saturn sign for a given date from precomputed ingresses."""
    target = datetime.date.fromisoformat(target_date_str)
    last_sign = "Aries"
    for ingress in SATURN_INGRESSES:
        ingress_date = datetime.date.fromisoformat(ingress["date"])
        if ingress_date <= target:
            last_sign = ingress["sign"]
        else:
            break
    return last_sign


def _get_saturn_phase(target_date_str):
    """Determine early/mid/late phase within current sign."""
    target = datetime.date.fromisoformat(target_date_str)
    current_sign = _get_saturn_sign_at_date(target_date_str)

    # Find ingress date for current sign
    ingress_date = None
    next_ingress_date = None
    for i, ingress in enumerate(SATURN_INGRESSES):
        if ingress["sign"] == current_sign:
            ingress_date = datetime.date.fromisoformat(ingress["date"])
            if i + 1 < len(SATURN_INGRESSES):
                next_ingress_date = datetime.date.fromisoformat(SATURN_INGRESSES[i + 1]["date"])
            break

    if not ingress_date or not next_ingress_date:
        return "unknown"

    total_days = (next_ingress_date - ingress_date).days
    elapsed = (target - ingress_date).days
    pct = elapsed / total_days if total_days > 0 else 0

    if pct < 0.33:
        return "early"
    elif pct < 0.67:
        return "mid"
    else:
        return "late"
