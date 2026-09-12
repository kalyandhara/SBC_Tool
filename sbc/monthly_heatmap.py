"""Monthly sector projection heatmap (SBC vedha + planetary transit confluence).

Produces a SECTOR x DAY matrix of combined bullish/bearish net strength using
the same multi-layer confluence engine as the daily/weekly reports:

  - SBC nakshatra-vedha layer      (prediction.sector_read / vedha hits)
  - rashi + planet-rulership layer (prediction.sector_read, planet_sector_read)
  - planetary transit layer        (transit_alert, jupiter, lunar phase)
  - reversal-window layer          (reversal_alert windows)

The net per canonical NSE/Nifty sector is taken from the unified
`build_confluence_report` output, mapped through SECTOR_ALIASES so the rows
are the familiar Nifty sector buckets.

Alongside the heatmap, a lunar-timing strip is returned per day so the slow
confluence bias can be timed with lunar events (Purnima / Amavasya / Ekadashi /
Ashtami / Chaturdashi), Moon-nakshatra shifts, and Bhadra (Vishti) muhurt
windows.

Research aid only - not investment advice.
"""

import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import swisseph as swe

from .planets import positions, all_planets_with_natures
from .nakshatra import tithi_of, paksha_of
from .prediction import analyze, compute_vedhas, place_planets, sector_read, planet_sector_read
from .confluence import build_confluence_report, SECTOR_ALIASES, normalize_sectors
from .chakra import GRID
from .market_calendar import (
    _anchor_nakshatra, transit_alert,
    jupiter_market_analysis, lunar_phase_alert,
)
from .bhadra import bhadra_windows

# Canonical Nifty sector rows: display name -> confluence canonical keys that
# roll up into it (via SECTOR_ALIASES).  A sector maps to any canonical whose
# alias intersects these tags.
NIFTY_SECTOR_ROWS = [
    ("Nifty Large Caps", ["Nifty 50", "Large Caps", "Large Cap", "Speculative Spikes", "Gap Plays", "Crash Risk / Corrections", "Reversal Risk", "Momentum Amplifiers", "Intraday Momentum", "Exit Zones", "Water & Liquidity"]),
    ("Nifty Bank", ["Banking", "Banks", "Nifty Bank", "Bank Nifty", "PSU Banks", "Private Banks", "Finance & Banking", "Financial Services", "Banking & Management", "Insurance"]),
    ("Nifty IT", ["IT", "IT & Software", "Technology", "Semiconductors", "Consulting"]),
    ("Nifty Telecom/Cable", ["Telecom", "Cable & Media", "Communication Infrastructure", "Digital Infrastructure", "Cosmetics & Media", "Entertainment"]),
    ("Nifty Auto", ["Auto", "Auto & Mobility"]),
    ("Nifty Metal", ["Metals", "Metals & Mining", "Base Metals", "Copper & Red Metals", "Steel & Energy", "Industrial / Base-Metal Index", "Mining"]),
    ("Nifty Agri", ["Agriculture (state-run)", "Food & Agri"]),
    ("Nifty Renewable", ["Renewables"]),
    ("Nifty FMCG", ["FMCG", "Consumer Staples", "Consumer-FMCG", "Consumer", "Retail & E-com", "Trade & Exports"]),
    ("Nifty Pharma", ["Pharma", "Pharma & Alcohol", "Healthcare", "Healthcare IT"]),
    ("Nifty Energy", ["Energy", "Energy & Power", "Oil & Gas", "Petroleum & Crude", "Petroleum", "Coal & Railways"]),
    ("Nifty Realty", ["Real Estate", "Realty", "Realty & Housing"]),
    ("Nifty Infra", ["Infrastructure", "Cement & Infra", "Defense & Infra"]),
    ("Nifty PSU", ["PSU", "PSU & Utilities", "PSU & Sovereign", "Government-linked"]),
    ("Nifty Gold", ["Gold/MCX", "Gold", "Gold (store of wealth)", "MCX Gold", "Luxury & Silver", "Jewelry"]),
    ("Nifty Defense", ["Defense", "Defense & Aerospace"]),
    ("Nifty Shipping", ["Shipping", "Shipping & Fisheries", "Logistics"]),
    ("Nifty Travel", ["Travel & Aviation", "Airlines"]),
    ("Nifty Other", ["All sectors", "Education", "Startups"]),
]

# Confluence canonical keys that correspond to each Nifty row's tags.
def _row_to_canonical(tags):
    out = set()
    for tag in tags:
        canon = normalize_sectors([tag])
        out.update(canon)
    return out


def _julian_at_noon(date, tz_name="Asia/Kolkata"):
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("Asia/Kolkata")
    local = datetime.datetime.combine(date, datetime.time(12, 0), tzinfo=tz)
    utc = local.astimezone(datetime.timezone.utc)
    return swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute / 60.0)


def _day_planets(date, tz_name="Asia/Kolkata"):
    jul = _julian_at_noon(date, tz_name)
    planets, _ = positions(jul)
    sun = next(p for p in planets if p["name"] == "Sun")
    moon = next(p for p in planets if p["name"] == "Moon")
    tithi = tithi_of(sun["longitude"], moon["longitude"])
    planets = all_planets_with_natures(planets, tithi, sun["longitude"])
    return planets, tithi


def _day_sector_net(planets, tithi, anchor_nakshatra, row_canonical_cache):
    """Return combined confluence net per Nifty row for a single day."""
    vedha_map, _ = compute_vedhas(planets, school="classical")
    analysis = analyze(planets, vedha_map, anchor_nakshatra, school="classical")
    sr = sector_read(vedha_map, planets)
    psr = planet_sector_read(planets)
    transits = transit_alert(planets)
    lunar = lunar_phase_alert(tithi)
    jup = jupiter_market_analysis(planets)

    conf = build_confluence_report(
        analysis=analysis,
        sector_read=sr,
        planet_sector_read=psr,
        reversal_data={"windows": [], "upcoming_windows": []},
        transits=transits,
        jupiter_analysis=jup,
        lunar_phase=lunar,
    )

    sector_conf = conf.get("sector_confluence", {})

    # Assign each raw confluence key to exactly ONE Nifty row (first tag
    # match), so aliases are neither double-counted across rows nor summed
    # multiple times within a row.
    net_by_row = {name: 0.0 for name, _ in NIFTY_SECTOR_ROWS}
    for raw_key, data in sector_conf.items():
        raw_norm = normalize_sectors([raw_key])
        raw_canon = raw_norm[0] if raw_norm else raw_key
        net = data.get("net", 0.0)
        assigned = False
        for row_name, tags in NIFTY_SECTOR_ROWS:
            canon = row_canonical_cache[row_name]
            if raw_canon in canon or raw_key in tags:
                net_by_row[row_name] += net
                assigned = True
                break
        if not assigned:
            # Fall back to any row whose canonical set contains raw_canon.
            for row_name, tags in NIFTY_SECTOR_ROWS:
                if raw_canon in row_canonical_cache[row_name]:
                    net_by_row[row_name] += net
                    break

    for k in net_by_row:
        net_by_row[k] = round(net_by_row[k], 2)
    return net_by_row, conf.get("overall", {}).get("signal", "NEUTRAL")


def _lunar_events(date, planets, tithi, tz_name):
    """Return a list of lunar-timing event labels for a single day."""
    events = []
    if tithi == 15:
        events.append(("Purnima", "FULL MOON"))
    elif tithi == 30:
        events.append(("Amavasya", "NEW MOON"))
    elif tithi in (14, 16):
        events.append(("Purnima-window", "FULL MOON WINDOW"))
    elif tithi in (29, 1):
        events.append(("Amavasya-window", "NEW MOON WINDOW"))
    if tithi in (11, 26):
        events.append(("Ekadashi", "EKADASHI"))
    if tithi in (8, 23):
        events.append(("Ashtami", "ASHTAMI"))
    if tithi in (14, 29):
        events.append(("Chaturdashi", "CHATURDASHI"))
    moon = next(p for p in planets if p["name"] == "Moon")
    events.append(("Moon:" + moon["nakshatra"], "MOON NAKSHATRA"))
    return events


def monthly_heatmap(start_date=None, days=30, tz_name="Asia/Kolkata", anchor_key="nse"):
    """Compute the sector x day confluence heatmap + lunar timing strip.

    Returns:
        sectors: list of row names
        days: list of date strings
        matrix: {sector: {date: net}}
        lunar_events: {date: [event dicts]}
        bhadra: {date: [ {begin,end} ]}
        overall_by_day: {date: signal}
    """
    if start_date is None:
        start_date = datetime.date.today()
    elif isinstance(start_date, str):
        start_date = datetime.date.fromisoformat(start_date)

    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("Asia/Kolkata")

    anchor_nakshatra = _anchor_nakshatra(anchor_key)

    row_canonical_cache = {name: _row_to_canonical(tags) for name, tags in NIFTY_SECTOR_ROWS}

    days_list = [start_date + datetime.timedelta(days=i) for i in range(days)]
    day_strs = [d.isoformat() for d in days_list]

    matrix = {name: {} for name, _ in NIFTY_SECTOR_ROWS}
    overall_by_day = {}
    lunar_events = {}
    bhadra_map = {}

    for d in days_list:
        planets, tithi = _day_planets(d, tz_name)
        net_by_row, overall = _day_sector_net(planets, tithi, anchor_nakshatra, row_canonical_cache)
        ds = d.isoformat()
        for name in matrix:
            matrix[name][ds] = net_by_row.get(name, 0.0)
        overall_by_day[ds] = overall
        lunar_events[ds] = _lunar_events(d, planets, tithi, tz_name)

    # Bhadra windows across the span.
    first_month = datetime.datetime(start_date.year, start_date.month, 1, tzinfo=tz)
    end_date = start_date + datetime.timedelta(days=days)
    last_month = datetime.datetime(end_date.year, end_date.month, 1, tzinfo=tz)
    cursor = first_month
    seen = set()
    all_bwindows = []
    while cursor <= last_month:
        for w in bhadra_windows(cursor, tz):
            key = (w["begin"].isoformat(), w["end"].isoformat())
            if key not in seen:
                seen.add(key)
                all_bwindows.append(w)
        y, m = cursor.year, cursor.month + 1
        if m > 12:
            m = 1
            y += 1
        cursor = datetime.datetime(y, m, 1, tzinfo=tz)

    start_dt = datetime.datetime(start_date.year, start_date.month, start_date.day, tzinfo=tz)
    horizon_end = start_dt + datetime.timedelta(days=days + 1)
    for w in all_bwindows:
        b, e = w["begin"], w["end"]
        if e < start_dt or b >= horizon_end:
            continue
        bhadra_map.setdefault(b.date().isoformat(), []).append({
            "begin": b.strftime("%H:%M"),
            "end": e.strftime("%H:%M"),
            "begin_iso": b.isoformat(),
            "end_iso": e.isoformat(),
        })

    # Flatten lunar events into a per-day list of markers for the frontend.
    lunar_markers = []
    for ds in day_strs:
        for typ, label in lunar_events.get(ds, []):
            lunar_markers.append({"date": ds, "type": typ, "label": label})

    return {
        "start_date": day_strs[0],
        "end_date": day_strs[-1],
        "days": days,
        "dates": day_strs,
        "anchor": anchor_key,
        "sectors": [name for name, _ in NIFTY_SECTOR_ROWS],
        "matrix": matrix,
        "overall_by_day": overall_by_day,
        "lunar_markers": lunar_markers,
        "bhadra": bhadra_map,
        "disclaimer": "Research confluence projection; not financial advice.",
    }