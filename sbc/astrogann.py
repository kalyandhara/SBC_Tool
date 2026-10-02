"""AstroGann Pro - unified astro + Gann confluence signal.

Combines the SBC/KP astro bias (vedha net score) with the price position
relative to Gann precision zones into a single swing/positional signal with
strength. Research output, not investment advice.
"""

from typing import Any

# Zone readings for the price position within the Gann precision zones,
# signed: positive = supportive of longs, negative = stretched/short bias.
GANN_ZONE_SCORE = {
    "deep_discount": 1.0,
    "discount": 0.5,
    "neutral": 0.0,
    "stretched": -0.5,
    "deep_stretched": -1.0,
}

ASTRO_SCORE_SCALE = 3.0  # SBC net score range mapped to -1..+1
SIGNAL_THRESHOLD = 0.25
STRONG_THRESHOLD = 0.6


def combine_astrogann(
    astro_score: float,
    gann_score: float,
    astro_weight: float = 0.6,
    gann_weight: float = 0.4,
) -> dict[str, Any]:
    """Blend a signed astro net score and a signed Gann zone score.

    Both inputs are normalised to -1..+1 (astro divided by ASTRO_SCORE_SCALE,
    Gann already in that range), then combined with the given weights.
    Returns the unified signal: BULLISH/BEARISH/NEUTRAL with strength.
    """
    if astro_weight < 0 or gann_weight < 0 or (astro_weight + gann_weight) == 0:
        raise ValueError("weights must be non-negative with a positive sum")

    total = astro_weight + gann_weight
    astro_norm = max(-1.0, min(1.0, astro_score / ASTRO_SCORE_SCALE))
    gann_norm = max(-1.0, min(1.0, gann_score))
    net = (astro_norm * astro_weight + gann_norm * gann_weight) / total
    net = round(net, 4)

    if net >= SIGNAL_THRESHOLD:
        signal = "BULLISH"
    elif net <= -SIGNAL_THRESHOLD:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"

    magnitude = abs(net)
    strength = "STRONG" if magnitude >= STRONG_THRESHOLD else (
        "MODERATE" if magnitude >= SIGNAL_THRESHOLD else "WEAK")

    return {
        "signal": signal,
        "strength": strength,
        "net": net,
        "astro_component": round(astro_norm, 4),
        "gann_component": round(gann_norm, 4),
        "astro_weight": astro_weight,
        "gann_weight": gann_weight,
    }


def gann_zone_score_for_price(
    price: float, zones: dict[str, Any]
) -> dict[str, Any]:
    """Read the price position within classified Gann precision zones.

    Returns {"zone": <label>, "score": <-1..+1>, "trend": zones trend}.
    """
    initiation = [lvl["price"] for lvl in zones.get("initiation", [])]
    targets = [lvl["price"] for lvl in zones.get("target", [])]
    trend = zones.get("trend", "bullish")

    if not initiation or not targets:
        return {"zone": "unknown", "score": 0.0, "trend": trend}

    init_low, init_high = min(initiation), max(initiation)
    target_high, target_low = max(targets), min(targets)

    if trend == "bullish":
        if price <= init_low:
            label, score = "deep_discount", GANN_ZONE_SCORE["deep_discount"]
        elif price <= init_high:
            label, score = "discount", GANN_ZONE_SCORE["discount"]
        elif price < target_high:
            label, score = "neutral", GANN_ZONE_SCORE["neutral"]
        else:
            label, score = "stretched", GANN_ZONE_SCORE["stretched"]
    else:
        if price >= init_high:
            label, score = "deep_stretched", GANN_ZONE_SCORE["deep_stretched"]
        elif price >= init_low:
            label, score = "stretched", GANN_ZONE_SCORE["stretched"]
        elif price > target_low:
            label, score = "neutral", GANN_ZONE_SCORE["neutral"]
        else:
            label, score = "deep_discount", GANN_ZONE_SCORE["deep_discount"]

    return {"zone": label, "score": score, "trend": trend}


def astrogann_signal(
    date_str: str,
    instrument: str = "NIFTY",
    time_str: str = "09:15",
    tz_name: str = "Asia/Kolkata",
    astro_weight: float = 0.6,
    gann_weight: float = 0.4,
    ticker: str | None = None,
) -> dict[str, Any]:
    """Build the unified AstroGann Pro signal for a day/instrument.

    Astro component: SBC vedha net score from the daily planetary read.
    Gann component: price position within the Gann precision zones from
    recent daily bars. Blended via combine_astrogann.
    """
    # Astro: SBC net vedha score
    from .market_calendar import _anchor_nakshatra
    from .planets import positioned_planets
    from .prediction import analyze, compute_vedhas

    anchor_key = "nifty" if (instrument or "NIFTY").upper().replace(" ", "") == "NIFTY" else "nse"
    planets, ayanamsa, sun, moon, tithi = positioned_planets(date_str, time_str, tz_name)
    vedha_map, _ = compute_vedhas(planets, school="classical")
    analysis = analyze(planets, vedha_map, _anchor_nakshatra(anchor_key), school="classical")
    astro_score = float(analysis["net"])

    # Gann: price position within precision zones
    gann_score = 0.0
    zone_label = None
    trend = None
    ref_price = None
    try:
        import yfinance as yf

        from .gann_zones import classify_gann_zones
        symbol = ticker or ("^NSEI" if anchor_key == "nifty" else "^NSEBANK")
        df = yf.download(symbol, period="3mo", interval="1d", auto_adjust=True, progress=False)
        if not df.empty:
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            high, low = float(df["High"].max()), float(df["Low"].min())
            ref_price = float(df["Close"].iloc[-1])
            zones, _, bullish = classify_gann_zones(high, low, ref_price, "indices")
            read = gann_zone_score_for_price(ref_price, zones)
            gann_score = read["score"]
            zone_label = read["zone"]
            trend = read["trend"]
    except Exception:
        gann_score = 0.0

    combined = combine_astrogann(astro_score, gann_score, astro_weight, gann_weight)
    return {
        "date": date_str,
        "instrument": (instrument or "NIFTY").upper().replace(" ", ""),
        "astro_score": astro_score,
        "gann_score": gann_score,
        "gann_zone": zone_label,
        "gann_trend": trend,
        "ref_price": ref_price,
        **combined,
    }


__all__ = [
    "combine_astrogann",
    "gann_zone_score_for_price",
    "astrogann_signal",
    "GANN_ZONE_SCORE",
]
