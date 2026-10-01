"""v15 layers for the KP Intraday Trend Change Prediction Report.

The reference report (Astro Quant Research Lab, v15.1) carries four things the
rule engine in ``kp_intraday`` did not compute:

* **Rule A-13** — Rahu Moon-sub windows: the market-hours spans in which the
  Moon's sub-lord is Rahu. Gains inside them are at risk of full give-back.
* **Rule C-5** — Vargottama Moon: Moon in the same sign in D-1 and D-9,
  read as trend amplification (suppress counter-trend reversals).
* **Navamsa D-9 strength layer (v15)** — Rules N-3 / N-5 / N-6 plus the
  per-signal "Navamsa D-9" column (Ascendant's navamsa sign, the incoming
  sub-lord's dignity there, VARGOTTAMA / PUSHKARA flags, Moon element).
* **SBC Nadi classification (v15.1)** — the Sapta-Nadi of the Moon's
  nakshatra, used as a score multiplier and a market-character read.

Everything here is derived from Swiss Ephemeris positions via
``sbc.planets.positioned_planets`` (Lahiri) and Placidus cusps for Mumbai; the
KP ayanamsa differs from Lahiri by ~6 arc-minutes, which cannot move a navamsa
except within a few arc-minutes of a boundary.

All multipliers and score adjustments are calibration parameters. They mirror
the values printed in the reference report where it states them and are
otherwise conservative defaults; override them through ``KP_LAYER_CONFIG``.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import swisseph as swe

from .planets import positioned_planets

IST = ZoneInfo("Asia/Kolkata")
NSE_LAT, NSE_LON = 19.0656, 72.8646  # Exchange Plaza, BKC, Mumbai

RASHIS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
SIGN_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}
ELEMENT = {
    "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
    "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
    "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
    "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
}
ELEMENT_ABBR = {"Fire": "FI", "Earth": "EA", "Air": "AI", "Water": "WA"}

EXALTATION = {
    "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn", "Mercury": "Virgo",
    "Jupiter": "Cancer", "Venus": "Pisces", "Saturn": "Libra",
    "Rahu": "Taurus", "Ketu": "Scorpio",
}
DEBILITATION = {
    "Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer", "Mercury": "Pisces",
    "Jupiter": "Capricorn", "Venus": "Virgo", "Saturn": "Aries",
    "Rahu": "Scorpio", "Ketu": "Taurus",
}
OWN_SIGNS = {
    "Sun": {"Leo"}, "Moon": {"Cancer"}, "Mars": {"Aries", "Scorpio"},
    "Mercury": {"Gemini", "Virgo"}, "Jupiter": {"Sagittarius", "Pisces"},
    "Venus": {"Taurus", "Libra"}, "Saturn": {"Capricorn", "Aquarius"},
    "Rahu": {"Aquarius"}, "Ketu": {"Scorpio"},
}
# Naisargika (natural) friendships, planet -> (friends, enemies); rest neutral.
FRIENDS = {
    "Sun": ({"Moon", "Mars", "Jupiter"}, {"Venus", "Saturn"}),
    "Moon": ({"Sun", "Mercury"}, set()),
    "Mars": ({"Sun", "Moon", "Jupiter"}, {"Mercury"}),
    "Mercury": ({"Sun", "Venus"}, {"Moon"}),
    "Jupiter": ({"Sun", "Moon", "Mars"}, {"Mercury", "Venus"}),
    "Venus": ({"Mercury", "Saturn"}, {"Sun", "Moon"}),
    "Saturn": ({"Mercury", "Venus"}, {"Sun", "Moon", "Mars"}),
    "Rahu": ({"Mercury", "Venus", "Saturn"}, {"Sun", "Moon", "Mars"}),
    "Ketu": ({"Mars", "Venus", "Saturn"}, {"Sun", "Moon"}),
}
DIGNITY_FACTOR = {
    "exalted": 1.20, "own": 1.15, "friend": 1.05,
    "neutral": 1.00, "enemy": 0.85, "debilitated": 0.62,
}
# Pushkara navamsas by element of the D-1 sign (1-based navamsa index in sign).
PUSHKARA_NAVAMSA = {"Fire": {7, 9}, "Earth": {3, 5}, "Air": {6, 8}, "Water": {1, 3}}
# Pushkara bhaga: the single most auspicious degree of each sign.
PUSHKARA_BHAGA = {
    "Aries": 21, "Taurus": 14, "Gemini": 18, "Cancer": 8, "Leo": 19, "Virgo": 9,
    "Libra": 24, "Scorpio": 11, "Sagittarius": 23, "Capricorn": 14,
    "Aquarius": 19, "Pisces": 9,
}

# ---------------------------------------------------------------------------
# Sapta-Nadi chakra: the seven nadis of the Sarvatobhadra scheme, four
# nakshatras each (Abhijit included, so 28). Names follow the reference report
# ("Neer", "Vata", "Dahan"); classical spellings in the docstring.
# ---------------------------------------------------------------------------
SAPTA_NADI = {
    "Chanda": ["Krittika", "Vishakha", "Anuradha", "Bharani"],          # Prachanda
    "Vata":   ["Rohini", "Swati", "Jyeshtha", "Ashwini"],               # Vayu
    "Dahan":  ["Mrigashira", "Chitra", "Mula", "Revati"],               # Dahana
    "Saumya": ["Ardra", "Hasta", "P.Ashadha", "U.Bhadrapada"],
    "Neer":   ["Punarvasu", "U.Phalguni", "U.Ashadha", "P.Bhadrapada"],  # Neera
    "Jala":   ["Pushya", "P.Phalguni", "Abhijit", "Shatabhisha"],
    "Amrit":  ["Ashlesha", "Magha", "Shravana", "Dhanishta"],           # Amrita
}
NADI_OF_NAKSHATRA = {nak: nadi for nadi, naks in SAPTA_NADI.items() for nak in naks}

# Market character and conviction multiplier per nadi. The reference states
# Neer 1.05x ("constant, steady"), and describes Chanda/Vata as amplifiers and
# Dahan as the whipsaw dampener; the other values are conservative defaults.
NADI_PROFILE = {
    "Chanda": (1.15, "Fierce, impulsive — sharp one-directional thrusts; momentum entries, wider stops"),
    "Vata":   (1.20, "High velocity — expansion of range; fast two-sided action; breakout entries with quick exits"),
    "Dahan":  (0.60, "Whipsaw / false-break risk — cut conviction, fade extremes, avoid chasing"),
    "Saumya": (1.00, "Mild, orderly — moderate trends; standard position size"),
    "Neer":   (1.05, "Constant, steady — sustained directional moves; breakout-continuation strategies favoured"),
    "Jala":   (0.90, "Fluid, drifting — slow rotation; mean-reversion favoured over breakouts"),
    "Amrit":  (1.10, "Nourishing, resilient — dips get absorbed; buy-on-dip in a bullish regime"),
}

ELEMENT_CHARACTER = {
    "Fire":  "FIRE — impulsive, trending; momentum entries work, expect fast follow-through",
    "Earth": "EARTH — steady, grinding; trends persist, patience pays, avoid over-trading",
    "Air":   "AIR — choppy, two-sided action; no clear edge; smaller positions, wait for clarity",
    "Water": "WATER — fluid, emotional; sharp reversals; fade extremes, tight risk",
}

KP_LAYER_CONFIG = {
    "n5_kendra_trikona_bonus": 0.20,
    "n5_dusthana_penalty": -0.20,
    "n6_weak_penalty": -0.25,
    "n6_strong_bonus": 0.25,
    "vargottama_bonus": 0.10,
}

_NAK_ALIASES = {
    "ashvini": "Ashwini", "mrigasira": "Mrigashira", "mrigashirsha": "Mrigashira",
    "jyestha": "Jyeshtha", "jyeshta": "Jyeshtha", "shravan": "Shravana",
    "dhanishtha": "Dhanishta", "satabhisha": "Shatabhisha", "shatabhishak": "Shatabhisha",
    "aslesha": "Ashlesha", "moola": "Mula", "vishaka": "Vishakha",
}


def normalize_nakshatra(name: str) -> str:
    """Map KP-file spellings ("Purva Ashadha") onto the engine's ("P.Ashadha")."""
    if not name:
        return ""
    s = name.strip()
    low = s.lower()
    if low in _NAK_ALIASES:
        return _NAK_ALIASES[low]
    for prefix, short in (("purva ", "P."), ("poorva ", "P."), ("uttara ", "U."), ("uttar ", "U.")):
        if low.startswith(prefix):
            rest = s[len(prefix):].strip()
            rest = _NAK_ALIASES.get(rest.lower(), rest.capitalize())
            return short + rest
    return s[0].upper() + s[1:]


# ---------------------------------------------------------------------------
# Navamsa
# ---------------------------------------------------------------------------

@dataclass
class Navamsa:
    d1_sign: str
    d9_sign: str
    index_in_sign: int          # 1..9
    deg_in_sign: float
    vargottama: bool
    pushkara_navamsa: bool
    pushkara_bhaga: bool

    @property
    def element(self) -> str:
        return ELEMENT[self.d9_sign]

    def flags(self) -> str:
        out = []
        if self.vargottama:
            out.append("VARGOTTAMA")
        if self.pushkara_bhaga:
            out.append("PUSHKARA-BHAGA")
        elif self.pushkara_navamsa:
            out.append("PUSHKARA")
        return " ".join(out)


def navamsa_of(longitude: float) -> Navamsa:
    """Navamsa (D-9) of a sidereal longitude."""
    lon = longitude % 360.0
    sign_idx = int(lon // 30)
    deg = lon - sign_idx * 30
    idx = int(deg // (30.0 / 9))            # 0..8
    d9_idx = (sign_idx * 9 + idx) % 12       # navamsas run continuously from Aries
    d1 = RASHIS[sign_idx]
    d9 = RASHIS[d9_idx]
    return Navamsa(
        d1_sign=d1, d9_sign=d9, index_in_sign=idx + 1, deg_in_sign=deg,
        vargottama=(d1 == d9),
        pushkara_navamsa=(idx + 1) in PUSHKARA_NAVAMSA[ELEMENT[d1]],
        pushkara_bhaga=abs(deg - PUSHKARA_BHAGA[d1]) <= 0.5,
    )


def dignity(planet: str, sign: str) -> str:
    """Dignity of *planet* placed in *sign*: exalted/own/friend/neutral/enemy/debilitated."""
    if EXALTATION.get(planet) == sign:
        return "exalted"
    if DEBILITATION.get(planet) == sign:
        return "debilitated"
    if sign in OWN_SIGNS.get(planet, ()):
        return "own"
    lord = SIGN_LORD[sign]
    friends, enemies = FRIENDS.get(planet, (set(), set()))
    if lord in friends:
        return "friend"
    if lord in enemies:
        return "enemy"
    return "neutral"


def strength_factor(planet: str, nav: Navamsa) -> float:
    f = DIGNITY_FACTOR[dignity(planet, nav.d9_sign)]
    if nav.vargottama:
        f += KP_LAYER_CONFIG["vargottama_bonus"]
    return round(f, 2)


def describe_placement(planet: str, nav: Navamsa) -> str:
    """'Gemini (friend VARGOTTAMA PUSHKARA)' — the reference's placement syntax."""
    d = dignity(planet, nav.d9_sign)
    fl = nav.flags()
    return f"{nav.d9_sign} ({d}{' ' + fl if fl else ''})"


# ---------------------------------------------------------------------------
# Ephemeris helpers
# ---------------------------------------------------------------------------

def _jd(trading_day: _dt.date, t: _dt.time) -> float:
    local = _dt.datetime.combine(trading_day, t, tzinfo=IST)
    u = local.astimezone(_dt.timezone.utc)
    return swe.julday(u.year, u.month, u.day, u.hour + u.minute / 60 + u.second / 3600)


def sidereal_ascendant(trading_day: _dt.date, t: _dt.time,
                       lat: float = NSE_LAT, lon: float = NSE_LON) -> float:
    """Sidereal (Lahiri) Placidus ascendant for Mumbai at a local time."""
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    _, ascmc = swe.houses_ex(_jd(trading_day, t), lat, lon, b"P", swe.FLG_SIDEREAL)
    return ascmc[0] % 360.0


def planets_at(trading_day: _dt.date, t: _dt.time) -> Dict[str, dict]:
    pl, _ay, _sun, _moon, _tithi = positioned_planets(
        trading_day.isoformat(), t.strftime("%H:%M"), "Asia/Kolkata")
    return {p["name"]: p for p in pl}


def _bisect_change(trading_day, t0, t1, key, minutes=5):
    """Find (to *minutes* resolution) when key(time) first differs from key(t0)."""
    v0 = key(t0)
    lo = _dt.datetime.combine(trading_day, t0)
    hi = _dt.datetime.combine(trading_day, t1)
    if key(t1) == v0:
        return None
    while (hi - lo) > _dt.timedelta(minutes=minutes):
        mid = lo + (hi - lo) / 2
        if key(mid.time()) == v0:
            lo = mid
        else:
            hi = mid
    return hi.time().replace(second=0, microsecond=0)


# ---------------------------------------------------------------------------
# Rule A-13: Rahu Moon-sub windows
# ---------------------------------------------------------------------------

def rahu_moon_sub_windows(day_rows: List[dict], close: str = "15:30") -> List[Tuple[str, str]]:
    """Contiguous market-hour spans in which the Moon's sub-lord is Rahu."""
    moon = sorted(
        (r for r in day_rows if r.get("planet") == "Moon" and r.get("timestamp")),
        key=lambda r: r["timestamp"],
    )
    windows: List[Tuple[str, str]] = []
    start = None
    for i, r in enumerate(moon):
        hhmm = r["timestamp"][11:16]
        if r.get("sublord") == "Rahu":
            if start is None:
                start = hhmm
        elif start is not None:
            windows.append((start, hhmm))
            start = None
    if start is not None:
        windows.append((start, close))
    return windows


def rahu_windows_text(windows: List[Tuple[str, str]]) -> str:
    if not windows:
        return "Rahu Moon-sub windows (Rule A-13): none during market hours."
    spans = ", ".join(f"{a} to {b}" for a, b in windows)
    return (f"Rahu Moon-sub windows (Rule A-13): {spans}.  Gains made inside these windows "
            "are at risk of full give-back after the sub ends — trade half size, "
            "breakout-only, and do not project Rahu-window momentum forward.")


# ---------------------------------------------------------------------------
# Layer assembly
# ---------------------------------------------------------------------------

@dataclass
class NavamsaLayer:
    placements: Dict[str, str]          # planet -> "Sign (dignity FLAGS)"
    moon_element: str                   # Fire/Earth/Air/Water
    n3_text: str
    n5_text: str
    n5_adjust: float
    n6_text: str
    n6_adjust: float
    lagna_d9_sign: str
    moon_vargottama: bool
    moon_navamsa_change: Optional[str]  # HH:MM if the Moon's navamsa changes in-session


@dataclass
class NadiLayer:
    nakshatra: str
    nadi: str
    multiplier: float
    character: str
    transition: Optional[str]           # "HH:MM -> <nakshatra> (<nadi>)" or None
    text: str


def build_navamsa_layer(trading_day: _dt.date, opening_sublord: str, moon_star: str,
                        open_t: _dt.time = _dt.time(9, 15),
                        close_t: _dt.time = _dt.time(15, 30)) -> NavamsaLayer:
    pl = planets_at(trading_day, open_t)
    asc_lon = sidereal_ascendant(trading_day, open_t)
    asc_nav = navamsa_of(asc_lon)
    lagna_lord = SIGN_LORD[asc_nav.d1_sign]

    placements: Dict[str, str] = {}
    key = ["Moon"]
    if opening_sublord and opening_sublord not in key:
        key.append(opening_sublord)
    for p in ("Sun", "Jupiter", "Saturn"):
        if p not in key:
            key.append(p)
    for name in key:
        if name in pl:
            nav = navamsa_of(pl[name]["longitude"])
            label = describe_placement(name, nav)
            placements["Asc Sub (%s)" % name if name == opening_sublord and name != "Moon" else name] = label

    moon_nav = navamsa_of(pl["Moon"]["longitude"])
    moon_el = moon_nav.element
    n3 = f"Moon Navamsa Element (Rule N-3): {ELEMENT_CHARACTER[moon_el]}."

    # N-5: Lagna lord's D-9 house counted from the D-9 lagna.
    ll_nav = navamsa_of(pl[lagna_lord]["longitude"]) if lagna_lord in pl else None
    if ll_nav:
        house = (RASHIS.index(ll_nav.d9_sign) - RASHIS.index(asc_nav.d9_sign)) % 12 + 1
        if house in (1, 4, 7, 10) or house in (5, 9):
            n5_adj = KP_LAYER_CONFIG["n5_kendra_trikona_bonus"]
            n5 = (f"Lagna Lord Navamsa (Rule N-5): {lagna_lord} in D-9 house {house} — "
                  f"kendra/trikona (trend sustains) (effect: {n5_adj:+.2f} on slot scores).")
        elif house in (6, 8, 12):
            n5_adj = KP_LAYER_CONFIG["n5_dusthana_penalty"]
            n5 = (f"Lagna Lord Navamsa (Rule N-5): {lagna_lord} in D-9 house {house} — "
                  f"dusthana (trend fails to sustain) (effect: {n5_adj:+.2f} on slot scores).")
        else:
            n5_adj = 0.0
            n5 = f"Lagna Lord Navamsa (Rule N-5): {lagna_lord} in D-9 house {house} — neutral (no adjustment)."
    else:
        n5_adj, n5 = 0.0, "Lagna Lord Navamsa (Rule N-5): not computed."

    # N-6: Moon star lord's own D-9 condition confirms or weakens the day bias.
    star_lord = _lord_of_nakshatra(normalize_nakshatra(moon_star))
    if star_lord and star_lord in pl:
        d = dignity(star_lord, navamsa_of(pl[star_lord]["longitude"]).d9_sign)
        if d in ("enemy", "debilitated"):
            n6_adj = KP_LAYER_CONFIG["n6_weak_penalty"]
            n6 = (f"Day Bias Navamsa Confirmation (Rule N-6): Moon Star Lord {star_lord} weak in D-9 "
                  f"({d}) — day bias WEAKENED ({n6_adj:+.2f} on day factor).")
        elif d in ("exalted", "own"):
            n6_adj = KP_LAYER_CONFIG["n6_strong_bonus"]
            n6 = (f"Day Bias Navamsa Confirmation (Rule N-6): Moon Star Lord {star_lord} strong in D-9 "
                  f"({d}) — day bias CONFIRMED ({n6_adj:+.2f} on day factor).")
        else:
            n6_adj = 0.0
            n6 = (f"Day Bias Navamsa Confirmation (Rule N-6): Moon Star Lord {star_lord} {d} in D-9 "
                  "— day bias unchanged.")
    else:
        n6_adj, n6 = 0.0, "Day Bias Navamsa Confirmation (Rule N-6): not computed."

    change = _bisect_change(
        trading_day, open_t, close_t,
        lambda t: navamsa_of(planets_at(trading_day, t)["Moon"]["longitude"]).d9_sign)

    return NavamsaLayer(
        placements=placements, moon_element=moon_el, n3_text=n3,
        n5_text=n5, n5_adjust=n5_adj, n6_text=n6, n6_adjust=n6_adj,
        lagna_d9_sign=asc_nav.d9_sign, moon_vargottama=moon_nav.vargottama,
        moon_navamsa_change=change.strftime("%H:%M") if change else None,
    )


def vargottama_text(layer: NavamsaLayer, open_t: _dt.time = _dt.time(9, 15)) -> str:
    if layer.moon_vargottama:
        until = f" until {layer.moon_navamsa_change}" if layer.moon_navamsa_change else ""
        # "%-H" is glibc-only and raises on Windows; format the hour manually.
        open_hm = f"{open_t.hour}:{open_t.minute:02d}"
        return (f"Vargottama Moon (Rule C-5): active from {open_hm}"
                f"{until} — trend amplification; suppress counter-trend reversals while active.")
    return "Vargottama Moon (Rule C-5): not active — no trend amplification from the Moon."


def build_nadi_layer(trading_day: _dt.date,
                     open_t: _dt.time = _dt.time(9, 15),
                     close_t: _dt.time = _dt.time(15, 30)) -> NadiLayer:
    def moon_nak(t):
        return planets_at(trading_day, t)["Moon"]["nakshatra"]
    nak = moon_nak(open_t)
    nadi = NADI_OF_NAKSHATRA.get(nak, "Saumya")
    mult, character = NADI_PROFILE[nadi]
    change = _bisect_change(trading_day, open_t, close_t, moon_nak)
    if change:
        nak2 = moon_nak(change)
        nadi2 = NADI_OF_NAKSHATRA.get(nak2, "Saumya")
        transition = f"{change.strftime('%H:%M')} -> {nak2} ({nadi2}, {NADI_PROFILE[nadi2][0]:.2f}x)"
        trans_text = f"Nakshatra transition at {transition} — re-read character after it."
    else:
        transition = None
        trans_text = "Nadi stable all session — no nakshatra transition during market hours."
    text = (f"Moon Nakshatra (opening): {nak}.   Nadi: {nadi}  (score multiplier: {mult:.2f}×)\n"
            f"Market character: {character}\n{trans_text}")
    return NadiLayer(nakshatra=nak, nadi=nadi, multiplier=mult, character=character,
                     transition=transition, text=text)


_NAK_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
_NAK_ORDER = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "P.Phalguni", "U.Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "P.Ashadha", "U.Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "P.Bhadrapada", "U.Bhadrapada", "Revati",
]


def _lord_of_nakshatra(nak: str) -> Optional[str]:
    if nak in _NAK_ORDER:
        return _NAK_LORDS[_NAK_ORDER.index(nak) % 9]
    # KP files sometimes carry the lord itself in the star column
    return nak if nak in _NAK_LORDS else None


def signal_navamsa_column(trading_day: _dt.date, t: _dt.time, incoming_sublord: str,
                          moon_element_abbr: str) -> str:
    """'Sagittarius (neutral PUSHKARA) Mo:AI' for one timing-table row."""
    try:
        nav = navamsa_of(sidereal_ascendant(trading_day, t))
    except Exception:
        return ""
    who = incoming_sublord if incoming_sublord in FRIENDS else SIGN_LORD[nav.d9_sign]
    return f"{describe_placement(who, nav)} Mo:{moon_element_abbr}"


def incoming_sublord_from_trigger(trigger: str) -> str:
    """'Asc sub change Saturn->Mercury; ...' -> 'Mercury' (first arrow in the trigger)."""
    if not trigger or "->" not in trigger:
        return ""
    head = trigger.split(";")[0]
    return head.split("->")[-1].strip().split()[0].strip(".,")


__all__ = [
    "SAPTA_NADI", "NADI_OF_NAKSHATRA", "NADI_PROFILE", "KP_LAYER_CONFIG",
    "Navamsa", "NavamsaLayer", "NadiLayer",
    "navamsa_of", "dignity", "strength_factor", "describe_placement",
    "normalize_nakshatra", "sidereal_ascendant", "planets_at",
    "rahu_moon_sub_windows", "rahu_windows_text",
    "build_navamsa_layer", "vargottama_text", "build_nadi_layer",
    "signal_navamsa_column", "incoming_sublord_from_trigger",
]
