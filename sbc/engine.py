"""Prediction engine: market anchors, time helpers and build_response().

Moved out of app.py so blueprints and modules can import it without
importing the Flask app (running `python app.py` used to load app.py twice,
once as __main__ and once as `app`, creating two Flask apps). app.py
re-exports these names for existing callers.
"""

import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sbc.chakra import GRID
from sbc.market_calendar import reversal_alert, upcoming_yoga_alerts
from sbc.nakshatra import GROUP_OF_TITHI, GROUP_WEEKDAYS, paksha_of, tithi_of
from sbc.planets import all_planets_with_natures, positions
from sbc.prediction import (
    analyze,
    compute_vedhas,
    place_planets,
    planet_sector_read,
    recommendation,
    sector_read,
    summarize_vedhas,
)

# Market anchors: entity -> (incorporation/base date, description).
# The Moon's nakshatra at that moment becomes the market's birth star.
ANCHORS = {
    "nse": {
        "name": "NSE (National Stock Exchange)",
        "date": "1992-11-27",
        "time": "00:00",
        "tz": "Asia/Kolkata",
        "note": "Incorporated 27 Nov 1992",
    },
    "bse": {
        "name": "BSE (Bombay Stock Exchange)",
        "date": "1875-07-09",
        "time": "00:00",
        "tz": "Asia/Kolkata",
        "note": "Founded 9 Jul 1875",
    },
    "nifty": {
        "name": "NIFTY 50 Index",
        "date": "1995-11-03",
        "time": "00:00",
        "tz": "Asia/Kolkata",
        "note": "Base date 3 Nov 1995",
    },
    "sensex": {
        "name": "SENSEX Index",
        "date": "1979-04-01",
        "time": "00:00",
        "tz": "Asia/Kolkata",
        "note": "Base date 1 Apr 1979",
    },
    "india": {
        "name": "India (national market)",
        "date": "1947-08-15",
        "time": "00:00",
        "tz": "Asia/Kolkata",
        "note": "Independence 15 Aug 1947",
    },
}

_anchor_cache: dict = {}


def _utc_from_local(date_str, time_str, tz_name):
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("Asia/Kolkata")
    y, m, d = (int(x) for x in date_str.split("-"))
    hh, mm = (int(x) for x in time_str.split(":"))
    local = datetime.datetime(y, m, d, hh, mm, tzinfo=tz)
    return local.astimezone(datetime.UTC).replace(tzinfo=None)


def _anchor_nakshatra(anchor_key):
    if anchor_key in _anchor_cache:
        return _anchor_cache[anchor_key]
    info = ANCHORS[anchor_key]
    utc = _utc_from_local(info["date"], info["time"], info["tz"])
    jul = _julday(utc)
    planets, _ = positions(jul)
    moon = next(p for p in planets if p["name"] == "Moon")
    _anchor_cache[anchor_key] = moon["nakshatra"]
    return _anchor_cache[anchor_key]


def _julday(utc_dt):
    import swisseph as swe
    h = utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
    return swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, h)


WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
            "Saturday", "Sunday"]


def _tithi_info(planets, tithi):
    from sbc.nakshatra import moon_nature
    group = GROUP_OF_TITHI.get(tithi, "Purna")
    pk = paksha_of(tithi)
    moon_n = moon_nature(tithi)
    return {
        "tithi": tithi,
        "paksha": pk,
        "group": group,
        "group_weekdays": GROUP_WEEKDAYS[group],
        "moon_note": (
            "ashubha Moon (Krishna Ekadashi through Shukla Chaturthi)"
            if moon_n == "malefic"
            else "shubha Moon (Shukla Panchami through Krishna Dashami)"
        ),
    }


def build_response(date_str, time_str, tz_name, anchor_key, school):
    utc = _utc_from_local(date_str, time_str, tz_name)
    jul = _julday(utc)
    planets, ayanamsa = positions(jul)

    sun = next(p for p in planets if p["name"] == "Sun")
    moon = next(p for p in planets if p["name"] == "Moon")
    tithi = tithi_of(sun["longitude"], moon["longitude"])
    tithi_info = _tithi_info(planets, tithi)

    planets = all_planets_with_natures(planets, tithi, sun["longitude"])

    anchor = ANCHORS[anchor_key]
    birth_nakshatra = _anchor_nakshatra(anchor_key)

    grid = place_planets(GRID, planets)
    vedha_map, ray_paths = compute_vedhas(planets, school=school)

    # Analysis
    analysis = analyze(planets, vedha_map, birth_nakshatra, school)

    weekday = WEEKDAYS[datetime.date.fromisoformat(date_str).weekday()]

    # mark points on grid
    for pt in analysis["points"]:
        cell = analysis["point_cells"][pt["name"]]
        if cell:
            r, c = cell
            grid[r - 1][c - 1].setdefault("points", []).append(pt["name"])

    for p in planets:
        for hit in vedha_map[p["name"]]:
            r, c = hit["row"], hit["col"]
            cell = grid[r - 1][c - 1]
            cell.setdefault("vedha", []).append({
                "planet": p["name"],
                "symbol": p["symbol"],
                "nature": p["nature"],
                "ray": hit["ray"],
            })

    rec = recommendation(analysis, anchor, date_str, weekday, tithi_info)
    calendar_alert = reversal_alert(date_str, planets, tithi)
    yoga_alerts = upcoming_yoga_alerts(date_str, time_str, tz_name)

    # Get applicable trade setups for current confluence
    trade_setups_data = []
    if calendar_alert.get("confluence"):
        from sbc.trade_setups import format_setup_for_display, setups_for_confluence
        applicable = setups_for_confluence(calendar_alert["confluence"])
        for setup in applicable:
            trade_setups_data.append({
                "name": setup.name,
                "direction": setup.direction,
                "trigger": setup.trigger,
                "entry": setup.entry,
                "stop": setup.stop,
                "target": setup.target,
                "sizing": setup.sizing,
                "filters": setup.filters,
                "historical": setup.historical,
                "markets": setup.applicable_markets,
                "timeframes": setup.timeframes,
                "formatted": format_setup_for_display(setup),
            })

    # attach ray paths for drawing
    for p in planets:
        p["rays"] = ray_paths.get(p["name"], [])

    def _serialize_cell(cell):
        out = {
            "row": cell["row"],
            "col": cell["col"],
            "type": cell["type"],
            "label": cell["label"],
            "weekdays": cell.get("weekdays"),
        }
        if "planets" in cell:
            out["planets"] = [{
                "name": p["name"],
                "symbol": p["symbol"],
                "nature": p["nature"],
            } for p in cell["planets"]]
        if "points" in cell:
            out["points"] = cell["points"]
        if "vedha" in cell:
            out["vedha"] = cell["vedha"]
        return out

    return {
        "date": date_str,
        "time": time_str,
        "timezone": tz_name,
        "weekday": weekday,
        "ayanamsa": round(ayanamsa, 4),
        "school": school,
        "anchor": {
            "key": anchor_key,
            "name": anchor["name"],
            "note": anchor["note"],
            "nakshatra": birth_nakshatra,
        },
        "tithi": tithi_info,
        "planets": planets,
        "grid": [[_serialize_cell(c) for c in row] for row in grid],
        "points": analysis["points"],
        "point_hits": analysis["point_hits"],
        "per_point": analysis["per_point"],
        "vedhas": summarize_vedhas(vedha_map, planets, analysis["points"]),
        "sectors": sector_read(vedha_map, planets),
        "planet_sectors": planet_sector_read(planets),
        "score": analysis["score"],
        "net": analysis["net"],
        "sentiment": {"verdict": rec["verdict"], "strength": rec["strength"]},
        "recommendation": rec,
        "market_alert": calendar_alert,
        "yoga_alerts": yoga_alerts,
        "trade_setups": trade_setups_data,
    }
