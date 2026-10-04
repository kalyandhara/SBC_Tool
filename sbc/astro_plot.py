"""Astrological plotting engine - Swiss Ephemeris based time-series generator.

Generates planetary position time-series, events, and aspect timelines
for financial-chart-style visualization.
"""

import datetime
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import swisseph as swe

from .market_calendar import NAKSHATRA_LORDS
from .nakshatra import NAKSHATRAS_27, nakshatra_of, sign_of
from .planets import COMBUST_ORB, DEBIL, EXALT, NATURAL_NATURE

# =============================================================================
# CONFIGURATION
# =============================================================================

PLANETS_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
PLANET_COLORS = {
    "Sun": "#FFD700", "Moon": "#C0C0C0", "Mars": "#FF4444", "Mercury": "#00BFFF",
    "Jupiter": "#FF8C00", "Venus": "#00FF7F", "Saturn": "#808080", "Rahu": "#8B00FF", "Ketu": "#FF00FF",
}

# Aspect orbs (degrees)
ASPECT_ORBS = {
    "conjunction": 8,
    "opposition": 8,
    "trine": 8,
    "square": 8,
    "sextile": 6,
}

ASPECT_ANGLES = {
    "conjunction": 0,
    "sextile": 60,
    "square": 90,
    "trine": 120,
    "opposition": 180,
}

# House systems
HOUSE_SYSTEMS = {
    "whole_sign": "W",
    "placidus": "P",
    "equal": "E",
    "koch": "K",
    "regiomontanus": "R",
    "campanus": "C",
}

# Default location for market charts (Mumbai/NSE)
DEFAULT_LAT = 19.0760
DEFAULT_LON = 72.8777
DEFAULT_TZ = "Asia/Kolkata"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PlanetPoint:
    """Single time-point for a planet."""
    date: str
    datetime: str
    planet: str
    longitude: float
    speed: float
    sign: str
    sign_index: int
    degree: float
    nakshatra: str
    nakshatra_index: int
    pada: int
    house: int
    retrograde: bool
    combust: bool
    combustion_orb: float
    dignity: str  # "exalted", "debilitated", "own", "neutral"
    nature: str  # "benefic", "malefic"
    strength: float  # -3 to +3 scale


@dataclass
class AstroEvent:
    """Astrological event marker."""
    date: str
    datetime: str
    type: str  # "ingress", "retrograde_start", "retrograde_end", "station", "combustion_start", "combustion_end", "nakshatra_change", "eclipse", "aspect_exact", "tithi_change"
    planet: str
    secondary_planet: str | None = None
    description: str = ""
    severity: str = "moderate"  # "mild", "moderate", "strong", "extreme"
    value: float | None = None  # e.g., aspect angle, combustion orb


@dataclass
class AspectTimeline:
    """Active aspect between two planets."""
    planet1: str
    planet2: str
    aspect_type: str  # conjunction, opposition, trine, square, sextile
    exact_date: str
    start_date: str
    end_date: str
    applying: bool  # True = applying, False = separating
    orb_at_start: float
    orb_at_exact: float
    orb_at_end: float


@dataclass
class AstroPlotData:
    """Complete plot data for a date window."""
    center_date: str
    start_date: str
    end_date: str
    resolution: str  # "daily", "hourly"
    timezone: str
    latitude: float
    longitude: float
    house_system: str
    planet_tracks: dict[str, list[PlanetPoint]]
    events: list[AstroEvent]
    aspects: list[AspectTimeline]
    nakshatra_bands: list[dict]  # {start_deg, end_deg, nakshatra, color}
    house_bands: list[dict]  # {house, sign, start_deg, end_deg}
    combustion_zones: list[dict]  # {planet, start_date, end_date, orb}
    retrograde_periods: list[dict]  # {planet, start_date, end_date}
    eclipses: list[dict]


# =============================================================================
# CORE CALCULATIONS
# =============================================================================

def _julian_day(dt: datetime.datetime) -> float:
    """Convert datetime to Julian day."""
    h = dt.hour + dt.minute / 60.0 + dt.second / 3600.0 + dt.microsecond / 3_600_000_000.0
    return float(swe.julday(dt.year, dt.month, dt.day, h))


def _get_planet_positions(julian_day: float) -> list[dict]:
    """Get all planet positions for a Julian day."""
    flags = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    swe.set_sid_mode(swe.SIDM_LAHIRI)

    out = []
    rahu = None
    for body, name in [
        (swe.SUN, "Sun"), (swe.MOON, "Moon"), (swe.MARS, "Mars"),
        (swe.MERCURY, "Mercury"), (swe.JUPITER, "Jupiter"),
        (swe.VENUS, "Venus"), (swe.SATURN, "Saturn"), (swe.MEAN_NODE, "Rahu"),
    ]:
        xx, _ = swe.calc_ut(julian_day, body, flags)
        lon = xx[0] % 360.0
        speed = xx[3]
        out.append({"name": name, "longitude": lon, "speed": speed})
        if name == "Rahu":
            rahu = out[-1]

    # Add Ketu
    if rahu:
        ketu_lon = (rahu["longitude"] + 180.0) % 360.0
        out.append({"name": "Ketu", "longitude": ketu_lon, "speed": rahu["speed"]})

    return out


def _calculate_houses(julian_day: float, lat: float, lon: float, system: str = "W") -> list[float]:
    """Calculate house cusps. Returns list of 12 cusp longitudes (0=Aries cusp)."""
    hsys = HOUSE_SYSTEMS.get(system, "W")
    cusps, ascmc = swe.houses(julian_day, lat, lon, hsys=hsys.encode())
    # cusps[0] is house 1 (Ascendant), cusps[11] is house 12
    return [c % 360.0 for c in cusps]


def _get_house(longitude: float, cusps: list[float]) -> int:
    """Determine which house a longitude falls in (1-12)."""
    # Normalize longitude
    lon = longitude % 360.0
    # Cusps: index 0 = house 1 cusp, index 1 = house 2 cusp, etc.
    # Planet is in house N if it's >= cusp[N-1] and < cusp[N] (with wrap)
    for i in range(12):
        cusp_start = cusps[i]
        cusp_end = cusps[(i + 1) % 12]
        if cusp_start <= cusp_end:
            if cusp_start <= lon < cusp_end:
                return i + 1
        else:  # Wraps around 0°
            if lon >= cusp_start or lon < cusp_end:
                return i + 1
    return 1


def _check_combustion(planet_lon: float, sun_lon: float, planet_name: str) -> tuple[bool, float]:
    """Check if planet is combust. Returns (is_combust, orb)."""
    orb_limit = COMBUST_ORB.get(planet_name)
    if orb_limit is None:
        return False, 0.0
    sep = abs((planet_lon - sun_lon + 180) % 360 - 180)
    return sep < orb_limit, sep


def _get_dignity(planet_name: str, sign_index: int) -> str:
    """Get planetary dignity."""
    if sign_index == EXALT.get(planet_name, -1):
        return "exalted"
    if sign_index == DEBIL.get(planet_name, -1):
        return "debilitated"
    # Own sign check
    own_signs = {
        "Sun": [4], "Moon": [3], "Mars": [0, 7], "Mercury": [2, 5],
        "Jupiter": [8, 11], "Venus": [1, 6], "Saturn": [9, 10],
        "Rahu": [1], "Ketu": [7],
    }
    if sign_index in own_signs.get(planet_name, []):
        return "own"
    return "neutral"


def _calculate_strength(planet: dict, dignity: str, retrograde: bool, combust: bool, combustion_orb: float) -> float:
    """Calculate strength score -3 to +3."""
    base = 0.0
    if dignity == "exalted":
        base = 2.0
    elif dignity == "debilitated":
        base = -2.0
    elif dignity == "own":
        base = 1.0

    if retrograde:
        base *= 1.5  # Retrograde amplifies
    if combust:
        base *= 0.5  # Combustion weakens

    # Nature modifier
    nature = NATURAL_NATURE.get(planet["name"], "neutral")
    if nature == "benefic":
        base = abs(base)
    elif nature == "malefic":
        base = -abs(base)

    return max(-3.0, min(3.0, base))


# =============================================================================
# EVENT DETECTION
# =============================================================================

def _detect_events(
    prev_points: dict[str, PlanetPoint],
    curr_points: dict[str, PlanetPoint],
    date_str: str,
    datetime_str: str,
) -> list[AstroEvent]:
    """Detect events between two time points."""
    events = []

    for planet_name in PLANETS_ORDER:
        if planet_name not in curr_points:
            continue
        curr = curr_points[planet_name]
        prev = prev_points.get(planet_name)

        if prev is None:
            continue

        # Retrograde start/end
        if prev.retrograde != curr.retrograde:
            if curr.retrograde:
                events.append(AstroEvent(
                    date=date_str, datetime=datetime_str,
                    type="retrograde_start", planet=planet_name,
                    description=f"{planet_name} turns retrograde at {curr.sign} {curr.degree:.1f}°",
                    severity="strong",
                ))
            else:
                events.append(AstroEvent(
                    date=date_str, datetime=datetime_str,
                    type="retrograde_end", planet=planet_name,
                    description=f"{planet_name} turns direct at {curr.sign} {curr.degree:.1f}°",
                    severity="strong",
                ))

        # Stationary (speed near 0)
        if abs(curr.speed) < 0.01 and abs(prev.speed) > 0.01:
            events.append(AstroEvent(
                date=date_str, datetime=datetime_str,
                type="station", planet=planet_name,
                description=f"{planet_name} stationary at {curr.sign} {curr.degree:.1f}°",
                severity="extreme",
            ))

        # Sign ingress
        if prev.sign_index != curr.sign_index:
            events.append(AstroEvent(
                date=date_str, datetime=datetime_str,
                type="ingress", planet=planet_name,
                description=f"{planet_name} enters {curr.sign} from {prev.sign}",
                severity="moderate",
            ))

        # Nakshatra change
        if prev.nakshatra != curr.nakshatra:
            events.append(AstroEvent(
                date=date_str, datetime=datetime_str,
                type="nakshatra_change", planet=planet_name,
                description=f"{planet_name} enters {curr.nakshatra} (pada {curr.pada}) from {prev.nakshatra}",
                severity="mild",
            ))

        # Combustion start/end
        if prev.combust != curr.combust:
            if curr.combust:
                events.append(AstroEvent(
                    date=date_str, datetime=datetime_str,
                    type="combustion_start", planet=planet_name,
                    description=f"{planet_name} combust (orb {curr.combustion_orb:.1f}°)",
                    severity="strong",
                ))
            else:
                events.append(AstroEvent(
                    date=date_str, datetime=datetime_str,
                    type="combustion_end", planet=planet_name,
                    description=f"{planet_name} emerges from combustion",
                    severity="moderate",
                ))

    return events


def _detect_aspects(
    prev_points: dict[str, PlanetPoint],
    curr_points: dict[str, PlanetPoint],
    date_str: str,
    datetime_str: str,
) -> list[AstroEvent]:
    """Detect exact aspects between planets."""
    events = []

    for i, p1_name in enumerate(PLANETS_ORDER):
        if p1_name not in curr_points:
            continue
        for p2_name in PLANETS_ORDER[i+1:]:
            if p2_name not in curr_points:
                continue

            p1_curr = curr_points[p1_name]
            p2_curr = curr_points[p2_name]
            p1_prev = prev_points.get(p1_name)
            p2_prev = prev_points.get(p2_name)

            if not p1_prev or not p2_prev:
                continue

            angle_curr = abs((p1_curr.longitude - p2_curr.longitude + 180) % 360 - 180)
            angle_prev = abs((p1_prev.longitude - p2_prev.longitude + 180) % 360 - 180)

            for aspect_name, aspect_angle in ASPECT_ANGLES.items():
                orb = ASPECT_ORBS[aspect_name]

                # Check if exact aspect formed (orb crossed threshold)
                curr_orb = abs(angle_curr - aspect_angle)
                prev_orb = abs(angle_prev - aspect_angle)

                if curr_orb <= orb and prev_orb > orb:
                    # Aspect became exact
                    applying = curr_orb < prev_orb
                    events.append(AstroEvent(
                        date=date_str, datetime=datetime_str,
                        type="aspect_exact", planet=p1_name, secondary_planet=p2_name,
                        description=f"{p1_name} {aspect_name} {p2_name} (orb {curr_orb:.1f}°) {'applying' if applying else 'separating'}",
                        severity="moderate" if aspect_name in ("conjunction", "opposition") else "mild",
                        value=angle_curr,
                    ))

    return events


def _build_aspect_timelines(
    planet_tracks: dict[str, list[PlanetPoint]],
) -> list[AspectTimeline]:
    """Build continuous aspect timelines from planet tracks."""
    # Get all dates
    aspect_timelines = []

    for i, p1_name in enumerate(PLANETS_ORDER):
        if p1_name not in planet_tracks:
            continue
        for p2_name in PLANETS_ORDER[i+1:]:
            if p2_name not in planet_tracks:
                continue

            track1 = planet_tracks[p1_name]
            track2 = planet_tracks[p2_name]

            for aspect_name, aspect_angle in ASPECT_ANGLES.items():
                orb = ASPECT_ORBS[aspect_name]

                active_start = None
                exact_date = None
                exact_orb: float = 999
                applying_phase = True

                for pt1, pt2 in zip(track1, track2):
                    angle = abs((pt1.longitude - pt2.longitude + 180) % 360 - 180)
                    curr_orb = abs(angle - aspect_angle)

                    if curr_orb <= orb:
                        if active_start is None:
                            active_start = pt1.date
                        if curr_orb < exact_orb:
                            exact_orb = curr_orb
                            exact_date = pt1.date
                            # Determine if applying or separating
                            if pt1.datetime != track1[0].datetime:  # Not first point
                                prev_idx = track1.index(pt1) - 1
                                if prev_idx >= 0:
                                    prev_angle = abs((track1[prev_idx].longitude - track2[prev_idx].longitude + 180) % 360 - 180)
                                    prev_orb = abs(prev_angle - aspect_angle)
                                    applying_phase = curr_orb < prev_orb
                    else:
                        if active_start is not None:
                            aspect_timelines.append(AspectTimeline(
                                planet1=p1_name,
                                planet2=p2_name,
                                aspect_type=aspect_name,
                                exact_date=exact_date or active_start,
                                start_date=active_start,
                                end_date=pt1.date,
                                applying=applying_phase,
                                orb_at_start=abs(abs((track1[0].longitude - track2[0].longitude + 180) % 360 - 180) - aspect_angle),
                                orb_at_exact=exact_orb,
                                orb_at_end=curr_orb,
                            ))
                            active_start = None
                            exact_orb = 999

                # Close if still active at end
                if active_start is not None:
                    aspect_timelines.append(AspectTimeline(
                        planet1=p1_name,
                        planet2=p2_name,
                        aspect_type=aspect_name,
                        exact_date=exact_date or active_start,
                        start_date=active_start,
                        end_date=track1[-1].date,
                        applying=applying_phase,
                        orb_at_start=abs(abs((track1[0].longitude - track2[0].longitude + 180) % 360 - 180) - aspect_angle),
                        orb_at_exact=exact_orb,
                        orb_at_end=abs((track1[-1].longitude - track2[-1].longitude + 180) % 360 - 180 - aspect_angle),
                    ))

    return aspect_timelines


def _detect_eclipses(planet_tracks: dict[str, list[PlanetPoint]]) -> list[dict]:
    """Detect solar/lunar eclipses."""
    eclipses: list = []

    if "Sun" not in planet_tracks or "Moon" not in planet_tracks:
        return eclipses

    sun_track = planet_tracks["Sun"]
    moon_track = planet_tracks["Moon"]
    rahu_track = planet_tracks.get("Rahu", [])
    ketu_track = planet_tracks.get("Ketu", [])

    # Build lookup for nodes
    rahu_lons = {pt.date: pt.longitude for pt in rahu_track}
    ketu_lons = {pt.date: pt.longitude for pt in ketu_track}

    for sun_pt, moon_pt in zip(sun_track, moon_track):
        # Solar eclipse: Sun-Moon conjunction near node
        sun_moon_angle = abs((sun_pt.longitude - moon_pt.longitude + 180) % 360 - 180)
        if sun_moon_angle < 18:  # New Moon within eclipse range
            rahu_lon = rahu_lons.get(sun_pt.date, 0)
            ketu_lon = ketu_lons.get(sun_pt.date, 0)
            sun_rahu = abs((sun_pt.longitude - rahu_lon + 180) % 360 - 180)
            sun_ketu = abs((sun_pt.longitude - ketu_lon + 180) % 360 - 180)

            if sun_rahu < 15 or sun_ketu < 15:
                eclipses.append({
                    "date": sun_pt.date,
                    "type": "solar",
                    "description": f"Solar eclipse: Sun-Moon {sun_moon_angle:.1f}°, node distance {min(sun_rahu, sun_ketu):.1f}°",
                    "severity": "extreme" if min(sun_rahu, sun_ketu) < 5 else "strong",
                })

        # Lunar eclipse: Sun-Moon opposition near node
        if sun_moon_angle > 162:  # Full Moon
            rahu_lon = rahu_lons.get(sun_pt.date, 0)
            ketu_lon = ketu_lons.get(sun_pt.date, 0)
            sun_rahu = abs((sun_pt.longitude - rahu_lon + 180) % 360 - 180)
            sun_ketu = abs((sun_pt.longitude - ketu_lon + 180) % 360 - 180)

            if sun_rahu < 15 or sun_ketu < 15:
                eclipses.append({
                    "date": sun_pt.date,
                    "type": "lunar",
                    "description": f"Lunar eclipse: Sun-Moon {sun_moon_angle:.1f}°, node distance {min(sun_rahu, sun_ketu):.1f}°",
                    "severity": "extreme" if min(sun_rahu, sun_ketu) < 5 else "strong",
                })

    return eclipses


# =============================================================================
# MAIN GENERATOR
# =============================================================================

def generate_astro_plot(
    center_date: str | None = None,
    window_days: int = 30,
    resolution: str = "daily",
    timezone: str = DEFAULT_TZ,
    latitude: float = DEFAULT_LAT,
    longitude: float = DEFAULT_LON,
    house_system: str = "whole_sign",
) -> AstroPlotData:
    """Generate complete astrological plot data for a date window."""

    if center_date is None:
        center_date = datetime.date.today().isoformat()

    center = datetime.date.fromisoformat(center_date)
    half_window = window_days // 2
    start_date = center - datetime.timedelta(days=half_window)
    end_date = center + datetime.timedelta(days=half_window)

    # Timezone handling
    try:
        tz = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo(DEFAULT_TZ)

    # Generate time points
    time_points = []
    if resolution == "daily":
        current = start_date
        while current <= end_date:
            dt = datetime.datetime.combine(current, datetime.time(9, 15), tzinfo=tz)  # Market open
            time_points.append((current.isoformat(), dt.isoformat(), dt))
            current += datetime.timedelta(days=1)
    elif resolution == "hourly":
        # 9:15 to 15:30 market hours
        current = datetime.datetime.combine(start_date, datetime.time(9, 15), tzinfo=tz)
        end_dt = datetime.datetime.combine(end_date, datetime.time(15, 30), tzinfo=tz)
        while current <= end_dt:
            time_points.append((current.date().isoformat(), current.isoformat(), current))
            current += datetime.timedelta(hours=1)
    else:
        raise ValueError("Resolution must be 'daily' or 'hourly'")

    # Calculate all planet positions
    planet_tracks: dict[str, list] = {p: [] for p in PLANETS_ORDER}
    all_events = []
    prev_points: dict = {}

    for date_str, datetime_str, dt in time_points:
        jul = _julian_day(dt.astimezone(datetime.UTC).replace(tzinfo=None))

        # Planet positions
        raw_planets = _get_planet_positions(jul)

        # Houses
        cusps = _calculate_houses(jul, latitude, longitude, HOUSE_SYSTEMS.get(house_system, "W"))

        # Sun longitude for combustion
        sun_lon = next(p["longitude"] for p in raw_planets if p["name"] == "Sun")

        # Build current points
        curr_points = {}
        for rp in raw_planets:
            name = rp["name"]
            lon = rp["longitude"]
            speed = rp["speed"]
            sign, sign_idx = sign_of(lon)
            degree = lon % 30.0
            nakshatra, pada = nakshatra_of(lon)
            nak_idx = NAKSHATRAS_27.index(nakshatra) if nakshatra in NAKSHATRAS_27 else 0
            house = _get_house(lon, cusps)
            retrograde = speed < 0
            combust, comb_orb = _check_combustion(lon, sun_lon, name)
            dignity = _get_dignity(name, sign_idx)
            nature = NATURAL_NATURE.get(name, "neutral")
            strength = _calculate_strength(rp, dignity, retrograde, combust, comb_orb)

            point = PlanetPoint(
                date=date_str,
                datetime=datetime_str,
                planet=name,
                longitude=lon,
                speed=speed,
                sign=sign,
                sign_index=sign_idx,
                degree=degree,
                nakshatra=nakshatra,
                nakshatra_index=nak_idx,
                pada=pada,
                house=house,
                retrograde=retrograde,
                combust=combust,
                combustion_orb=comb_orb,
                dignity=dignity,
                nature=nature,
                strength=strength,
            )
            curr_points[name] = point
            planet_tracks[name].append(point)

        # Detect events
        if prev_points:
            all_events.extend(_detect_events(prev_points, curr_points, date_str, datetime_str))
            all_events.extend(_detect_aspects(prev_points, curr_points, date_str, datetime_str))

        prev_points = curr_points

    # Build aspect timelines
    aspects = _build_aspect_timelines(planet_tracks)

    # Detect eclipses
    eclipses = _detect_eclipses(planet_tracks)
    for eclipse in eclipses:
        all_events.append(AstroEvent(
            date=eclipse["date"],
            datetime=eclipse["date"] + "T09:15:00",
            type="eclipse",
            planet="Sun",
            secondary_planet="Moon",
            description=eclipse["description"],
            severity=eclipse["severity"],
        ))

    # Build nakshatra bands (for background shading)
    nakshatra_bands = []
    for i, nak in enumerate(NAKSHATRAS_27):
        start_deg = i * (360.0 / 27.0)
        end_deg = start_deg + (360.0 / 27.0)
        # Color by lord
        lord = NAKSHATRA_LORDS.get(nak, "Unknown")
        lord_colors = {
            "Ketu": "#8B00FF", "Venus": "#00FF7F", "Sun": "#FFD700",
            "Moon": "#C0C0C0", "Mars": "#FF4444", "Rahu": "#8B00FF",
            "Jupiter": "#FF8C00", "Saturn": "#808080", "Mercury": "#00BFFF",
        }
        nakshatra_bands.append({
            "nakshatra": nak,
            "start_deg": start_deg,
            "end_deg": end_deg,
            "lord": lord,
            "color": lord_colors.get(lord, "#888888"),
            "index": i,
        })

    # Build house bands (for background)
    # Use center date houses
    center_jul = _julian_day(
        datetime.datetime.combine(center, datetime.time(9, 15), tzinfo=tz).astimezone(datetime.UTC).replace(tzinfo=None)
    )
    center_cusps = _calculate_houses(center_jul, latitude, longitude, HOUSE_SYSTEMS.get(house_system, "W"))
    house_bands = []
    for i in range(12):
        cusp_start = center_cusps[i]
        cusp_end = center_cusps[(i + 1) % 12]
        sign, _ = sign_of(cusp_start)
        house_bands.append({
            "house": i + 1,
            "sign": sign,
            "start_deg": cusp_start,
            "end_deg": cusp_end,
        })

    # Build combustion zones
    combustion_zones = []
    for planet_name in PLANETS_ORDER:
        if planet_name not in planet_tracks:
            continue
        track = planet_tracks[planet_name]
        zone_start = None
        for pt in track:
            if pt.combust and zone_start is None:
                zone_start = pt.date
            elif not pt.combust and zone_start is not None:
                combustion_zones.append({
                    "planet": planet_name,
                    "start_date": zone_start,
                    "end_date": pt.date,
                    "max_orb": max(p.combustion_orb for p in track if p.date >= zone_start and p.date <= pt.date),
                })
                zone_start = None
        if zone_start is not None:
            combustion_zones.append({
                "planet": planet_name,
                "start_date": zone_start,
                "end_date": track[-1].date,
                "max_orb": max(p.combustion_orb for p in track if p.date >= zone_start),
            })

    # Build retrograde periods
    retrograde_periods = []
    for planet_name in PLANETS_ORDER:
        if planet_name not in planet_tracks:
            continue
        track = planet_tracks[planet_name]
        period_start = None
        for pt in track:
            if pt.retrograde and period_start is None:
                period_start = pt.date
            elif not pt.retrograde and period_start is not None:
                retrograde_periods.append({
                    "planet": planet_name,
                    "start_date": period_start,
                    "end_date": pt.date,
                    "start_deg": next(p.degree for p in track if p.date == period_start),
                    "end_deg": pt.degree,
                })
                period_start = None
        if period_start is not None:
            retrograde_periods.append({
                "planet": planet_name,
                "start_date": period_start,
                "end_date": track[-1].date,
                "start_deg": next(p.degree for p in track if p.date == period_start),
                "end_deg": track[-1].degree,
            })

    return AstroPlotData(
        center_date=center_date,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        resolution=resolution,
        timezone=timezone,
        latitude=latitude,
        longitude=longitude,
        house_system=house_system,
        planet_tracks=planet_tracks,
        events=all_events,
        aspects=aspects,
        nakshatra_bands=nakshatra_bands,
        house_bands=house_bands,
        combustion_zones=combustion_zones,
        retrograde_periods=retrograde_periods,
        eclipses=eclipses,
    )


def serialize_plot_data(plot_data: AstroPlotData) -> dict:
    """Serialize AstroPlotData for JSON response."""
    return {
        "center_date": plot_data.center_date,
        "start_date": plot_data.start_date,
        "end_date": plot_data.end_date,
        "resolution": plot_data.resolution,
        "timezone": plot_data.timezone,
        "latitude": plot_data.latitude,
        "longitude": plot_data.longitude,
        "house_system": plot_data.house_system,
        "planet_tracks": {
            planet: [
                {
                    "date": pt.date,
                    "datetime": pt.datetime,
                    "planet": pt.planet,
                    "longitude": round(pt.longitude, 4),
                    "speed": round(pt.speed, 4),
                    "sign": pt.sign,
                    "sign_index": pt.sign_index,
                    "degree": round(pt.degree, 2),
                    "nakshatra": pt.nakshatra,
                    "nakshatra_index": pt.nakshatra_index,
                    "pada": pt.pada,
                    "house": pt.house,
                    "retrograde": pt.retrograde,
                    "combust": pt.combust,
                    "combustion_orb": round(pt.combustion_orb, 2),
                    "dignity": pt.dignity,
                    "nature": pt.nature,
                    "strength": round(pt.strength, 2),
                }
                for pt in track
            ]
            for planet, track in plot_data.planet_tracks.items()
        },
        "events": [
            {
                "date": e.date,
                "datetime": e.datetime,
                "type": e.type,
                "planet": e.planet,
                "secondary_planet": e.secondary_planet,
                "description": e.description,
                "severity": e.severity,
                "value": e.value,
            }
            for e in plot_data.events
        ],
        "aspects": [
            {
                "planet1": a.planet1,
                "planet2": a.planet2,
                "aspect_type": a.aspect_type,
                "exact_date": a.exact_date,
                "start_date": a.start_date,
                "end_date": a.end_date,
                "applying": a.applying,
                "orb_at_start": round(a.orb_at_start, 2),
                "orb_at_exact": round(a.orb_at_exact, 2),
                "orb_at_end": round(a.orb_at_end, 2),
            }
            for a in plot_data.aspects
        ],
        "nakshatra_bands": plot_data.nakshatra_bands,
        "house_bands": plot_data.house_bands,
        "combustion_zones": plot_data.combustion_zones,
        "retrograde_periods": plot_data.retrograde_periods,
        "eclipses": plot_data.eclipses,
        "planet_colors": PLANET_COLORS,
        "planets_order": PLANETS_ORDER,
    }


if __name__ == "__main__":
    # Test
    data = generate_astro_plot("2026-08-21", window_days=30, resolution="daily")
    serialized = serialize_plot_data(data)
    print(f"Center: {serialized['center_date']}")
    print(f"Window: {serialized['start_date']} to {serialized['end_date']}")
    print(f"Planets: {list(serialized['planet_tracks'].keys())}")
    print(f"Points per planet: {len(serialized['planet_tracks']['Sun'])}")
    print(f"Events: {len(serialized['events'])}")
    print(f"Aspects: {len(serialized['aspects'])}")
    print(f"Eclipses: {len(serialized['eclipses'])}")
    print(f"Combustion zones: {len(serialized['combustion_zones'])}")
    print(f"Retrograde periods: {len(serialized['retrograde_periods'])}")

    # Show sample events
    for e in serialized['events'][:10]:
        print(f"  {e['date']} {e['type']}: {e['description']} [{e['severity']}]")
