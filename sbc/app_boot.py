"""Single boot entrypoint for SBC app."""
from datetime import date, timedelta
from sbc.db import _bootstrap
from sbc.series_cache import get_many, put_many

def _warm_prediction_series(build_response, days=180):
    try:
        today = date.today()
        start = today - timedelta(days=days)
        anchors = ["nifty", "nse"]
        schools = ["classical", "allthree"]
        for anchor in anchors:
            for school in schools:
                dates = [(start + timedelta(days=i)).isoformat() for i in range(days+1)]
                cached = get_many(dates, anchor, school)
                missing = [d for d in dates if d not in cached]
                if missing:
                    items = {}
                    for d in missing:
                        try:
                            r = build_response(d, "09:15", "Asia/Kolkata", anchor, school)
                            items[d] = {
                                "date": d,
                                "score": r.get("score"),
                                "net": r.get("net"),
                                "verdict": r.get("sentiment", {}).get("verdict"),
                                "strength": r.get("sentiment", {}).get("strength"),
                                "rec": (r.get("recommendation") or {}).get("summary"),
                            }
                        except Exception:
                            continue
                    if items:
                        put_many(items, anchor, school)
    except Exception:
        import logging
        logging.exception("Series warmup failed")

def boot(app, build_response):
    _bootstrap()
    # Warm series cache
    _warm_prediction_series(build_response, days=180)
    # App configs
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    # Ensure jinja env
    app.jinja_env.auto_reload = True
    app.jinja_env.cache = {}
