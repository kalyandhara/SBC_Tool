"""Natal yoga engine - conjunction yogas with classical strength checks.

Gaja Kesari is the first implemented yoga, built exactly to the
classical spec:

- Primary: Jupiter in a Kendra (1/4/7/10) from the Moon - conjunction
  and opposition included.
- Strength factors: combustion (Jupiter within COMBUST_ORB of the
  Sun), debilitation (Jupiter in Capricorn / Moon in Scorpio) with
  Neecha Bhanga (dispositor of the debilitated planet in a Kendra
  from the Lagna or the Moon), malefic affliction (Saturn/Rahu/Ketu
  conjoining or casting full Vedic drishti on either planet; a node
  on Jupiter flags the Guru-Chandal defect), dusthana placement
  (Moon or Jupiter in 6/8/12 from the Lagna), sign strength
  (exaltation / own sign), and Dasha activation (Vimshottari
  Mahadasha/Antardasha of Jupiter or the Moon).

The pure evaluator takes a {planet: longitude} map, so tests can feed
synthetic charts; the wrapper assembles the chart from sbc.natal.
"""

from __future__ import annotations

import datetime as dt

from .nakshatra import RASHIS
from .planets import COMBUST_ORB

# Vimshottari Mahadasha lords and years, starting from Ashwini.
VIMSHOTTARI = [("Ketu", 7), ("Venus", 20), ("Sun", 6), ("Moon", 10),
               ("Mars", 7), ("Rahu", 18), ("Jupiter", 16), ("Saturn", 19),
               ("Mercury", 17)]
NAK_SPAN = 360.0 / 27.0
YEAR_DAYS = 365.25

KENDRA = {1, 4, 7, 10}
DUSTHANA = {6, 8, 12}
SIGNS = {"Aries": 0, "Taurus": 1, "Gemini": 2, "Cancer": 3, "Leo": 4,
         "Virgo": 5, "Libra": 6, "Scorpio": 7, "Sagittarius": 8,
         "Capricorn": 9, "Aquarius": 10, "Pisces": 11}
EXALTED = {"Jupiter": 3, "Moon": 1}          # Cancer / Taurus
OWN = {"Jupiter": {8, 11}, "Moon": {3}}      # Sag/Pisces / Cancer
DEBILITATED = {"Jupiter": 9, "Moon": 7}      # Capricorn / Scorpio
SIGN_LORDS = {0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon", 4: "Sun",
              5: "Mercury", 6: "Venus", 7: "Mars", 8: "Jupiter",
              9: "Saturn", 10: "Saturn", 11: "Jupiter"}


def vimshottari(moon_longitude: float, birth_date: str,
                at_date: str | None = None) -> dict:
    """Mahadasha/Antardasha timeline from the Moon's nakshatra.

    Returns {birth_maha, balance_years, mahadashas: [{lord, start, end,
    antardashas: [{lord, start, end}]}], at: {maha, antar, ends}}.
    """
    birth = dt.date.fromisoformat(birth_date)
    at = dt.date.fromisoformat(at_date) if at_date else dt.date.today()
    birth_dt = dt.datetime.combine(birth, dt.time())
    at_dt = dt.datetime.combine(at, dt.time())
    nak_idx = int(moon_longitude % 360.0 // NAK_SPAN)
    start_lord_idx = nak_idx % 9
    elapsed_frac = (moon_longitude % NAK_SPAN) / NAK_SPAN
    start_years = VIMSHOTTARI[start_lord_idx][1]
    # The birth falls `elapsed_frac` into the start lord's Mahadasha.
    maha_start = birth_dt - dt.timedelta(days=start_years * elapsed_frac
                                         * YEAR_DAYS)

    mahadashas = []
    idx = start_lord_idx
    cursor = maha_start
    for _ in range(9):  # one full 120-year cycle is more than any scan
        lord, years = VIMSHOTTARI[idx]
        end = cursor + dt.timedelta(days=years * YEAR_DAYS)
        # Antardashas: begin with the Mahadasha lord, proportional.
        antars = []
        acursor = cursor
        ant_idx = idx
        for _a in range(9):
            alord, ayears = VIMSHOTTARI[ant_idx]
            alen = dt.timedelta(days=years * ayears / 120.0 * YEAR_DAYS)
            antars.append({"lord": alord,
                           "start": acursor.isoformat(),
                           "end": (acursor + alen).isoformat()})
            acursor += alen
            ant_idx = (ant_idx + 1) % 9
        mahadashas.append({"lord": lord, "start": cursor.isoformat(),
                           "end": end.isoformat(), "antardashas": antars})
        cursor = end
        idx = (idx + 1) % 9
        if (cursor - maha_start).days > 120 * YEAR_DAYS:
            break

    at_maha = next((m for m in mahadashas
                    if dt.datetime.fromisoformat(m["start"]) <= at_dt
                    < dt.datetime.fromisoformat(m["end"])), None)
    at_antar = None
    if at_maha:
        at_antar = next((a for a in at_maha["antardashas"]
                         if dt.datetime.fromisoformat(a["start"]) <= at_dt
                         < dt.datetime.fromisoformat(a["end"])), None)
    balance = (dt.datetime.fromisoformat(mahadashas[0]["end"])
               - birth_dt).total_seconds() / 86400.0 / YEAR_DAYS
    return {"birth_maha": mahadashas[0]["lord"],
            "balance_years": round(balance, 2),
            "mahadashas": mahadashas,
            "at": {"date": at.isoformat(),
                   "maha": at_maha["lord"] if at_maha else None,
                   "antar": at_antar["lord"] if at_antar else None}}


def drishti_targets(planet: str, planet_sign: int) -> set[int]:
    """Signs receiving this planet's full Vedic aspect (whole-sign)."""
    houses = {7}
    if planet == "Mars":
        houses |= {4, 8}
    elif planet == "Jupiter":
        houses |= {5, 9}
    elif planet == "Saturn":
        houses |= {3, 10}
    return {(planet_sign + h - 1) % 12 for h in houses}


def _separation(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def evaluate_gaja_kesari(longitudes: dict[str, float],
                         lagna_sign: int | None = None,
                         dasha: dict | None = None) -> dict:
    """Pure evaluator: verdict for the Gaja Kesari yoga.

    `longitudes` needs at least Sun, Moon, Jupiter, Mars, Saturn, Rahu,
    Ketu.  `lagna_sign` (0-11) is optional - without it the dusthana
    check is skipped (no birth time).  `dasha` is the output of
    vimshottari(); when omitted the activation factor is "unknown".
    """
    reasons: list[str] = []
    score = 5.0

    moon = longitudes["Moon"]
    jup = longitudes["Jupiter"]
    moon_sign = int(moon % 360.0 // 30)
    jup_sign = int(jup % 360.0 // 30)
    jup_from_moon = (jup_sign - moon_sign) % 12 + 1

    if jup_from_moon in KENDRA:
        reasons.append(f"primary: Jupiter is in house {jup_from_moon} "
                       "from the Moon (Kendra)")
        if jup_from_moon == 1:
            reasons.append("conjunction form (same sign)")
        elif jup_from_moon == 7:
            reasons.append("opposition form (7th from the Moon)")
    else:
        reasons.append(f"primary fails: Jupiter is in house {jup_from_moon} "
                       "from the Moon, not a Kendra")
        return {"yoga": "gaja_kesari", "present": False, "tier": "absent",
                "score": 0.0, "reasons": reasons, "checks":
                {"kendra_from_moon": jup_from_moon, "combust": None,
                 "debilitated": None, "neecha_bhanga": None,
                 "afflictions": [], "dusthana": None, "dasha": None}}

    # combustion
    sep = _separation(jup, longitudes.get("Sun", 0.0))
    combust = sep <= COMBUST_ORB.get("Jupiter", 11.0)
    if combust:
        score -= 2.0
        reasons.append(f"Jupiter is combust ({sep:.1f} deg from the Sun) "
                       "- strength reduced")
    else:
        reasons.append("Jupiter is not combust")

    # debilitation + Neecha Bhanga
    jup_debil = jup_sign == DEBILITATED["Jupiter"]
    moon_debil = moon_sign == DEBILITATED["Moon"]
    nb = False
    if jup_debil or moon_debil:
        score -= 2.0
        victims = []
        if jup_debil:
            victims.append("Jupiter (Capricorn)")
        if moon_debil:
            victims.append("Moon (Scorpio)")
        reasons.append("debilitated: " + ", ".join(victims))
        # Neecha Bhanga: dispositor of the debilitated planet in a
        # Kendra from the Lagna or the Moon.
        dispos = []
        if jup_debil:
            dispos.append(("Jupiter", SIGN_LORDS[DEBILITATED["Jupiter"]]))
        if moon_debil:
            dispos.append(("Moon", SIGN_LORDS[DEBILITATED["Moon"]]))
        for victim, lord_name in dispos:
            lord_lon = longitudes.get(lord_name)
            if lord_lon is None:
                continue
            lord_sign = int(lord_lon % 360.0 // 30)
            from_moon = (lord_sign - moon_sign) % 12 + 1
            from_lagna = ((lord_sign - lagna_sign) % 12 + 1
                          if lagna_sign is not None else None)
            if from_moon in KENDRA or (from_lagna is not None
                                       and from_lagna in KENDRA):
                nb = True
                score += 1.0
                where = "Lagna" if from_lagna in KENDRA else "Moon"
                reasons.append(f"neecha bhanga: {lord_name} (dispositor of "
                               f"debilitated {victim}) is in a Kendra "
                               f"from the {where}")
        if not nb:
            reasons.append("no neecha bhanga detected")
    else:
        reasons.append("neither Jupiter nor Moon is debilitated")

    # malefic affliction: Saturn/Rahu/Ketu by conjunction or full drishti
    afflictions = []
    for victim_name, _victim_lon, victim_sign in (
            ("Moon", moon, moon_sign), ("Jupiter", jup, jup_sign)):
        for malefic in ("Saturn", "Rahu", "Ketu"):
            m_lon = longitudes.get(malefic)
            if m_lon is None:
                continue
            m_sign = int(m_lon % 360.0 // 30)
            if m_sign == victim_sign:
                afflictions.append(f"{malefic} conjunct {victim_name}")
            elif malefic == "Saturn" and victim_sign in drishti_targets(
                    "Saturn", m_sign):
                afflictions.append(
                    f"Saturn aspects {victim_name} "
                    f"({RASHIS[m_sign]} -> {RASHIS[victim_sign]})")
    unique_affl = sorted(set(afflictions))
    if unique_affl:
        score -= min(2.0, len(unique_affl))
        reasons.append("malefic affliction: " + "; ".join(unique_affl))
        if any(a.startswith("Rahu conjunct Jupiter")
               or a.startswith("Ketu conjunct Jupiter")
               for a in unique_affl):
            reasons.append("Guru-Chandal defect risk: a node sits on "
                           "Jupiter - intelligence may serve unethical "
                           "gains")
    else:
        reasons.append("no Saturn/Rahu/Ketu conjunction or drishti on "
                       "Moon or Jupiter")

    # dusthana from the Lagna (needs a birth time)
    dusthana = None
    if lagna_sign is not None:
        for name, lon in (("Moon", moon), ("Jupiter", jup)):
            h = (int(lon % 360.0 // 30) - lagna_sign) % 12 + 1
            if h in DUSTHANA:
                dusthana = name
                score -= 1.0
                reasons.append(f"{name} is in house {h} from the Lagna "
                               "(dusthana) - results come late or with "
                               "struggle")
        if dusthana is None:
            reasons.append("Moon and Jupiter are not in dusthana from "
                           "the Lagna")

    # sign strength
    if jup_sign in (EXALTED["Jupiter"],) or jup_sign in OWN["Jupiter"]:
        score += 1.0
        where = ("exalted" if jup_sign == EXALTED["Jupiter"]
                 else "own sign")
        reasons.append(f"Jupiter is {where} ({RASHIS[jup_sign]})")
    if moon_sign in (EXALTED["Moon"],) or moon_sign in OWN["Moon"]:
        score += 1.0
        where = ("exalted" if moon_sign == EXALTED["Moon"]
                 else "own sign")
        reasons.append(f"Moon is {where} ({RASHIS[moon_sign]})")

    # dasha activation
    dasha_state = "unknown"
    if dasha:
        active = {dasha["at"]["maha"], dasha["at"]["antar"]}
        if active & {"Jupiter", "Moon"}:
            dasha_state = "active"
            score += 1.0
            reasons.append(f"dasha: {dasha['at']['maha']}/"
                           f"{dasha['at']['antar']} activates the yoga")
        else:
            dasha_state = "dormant"
            reasons.append(f"dasha: {dasha['at']['maha']}/"
                           f"{dasha['at']['antar']} - the yoga stays "
                           "dormant until a Jupiter or Moon period")

    score = max(0.0, min(10.0, score))
    if score >= 7.0:
        tier = "strong"
    elif score >= 5.0:
        tier = "moderate"
    else:
        tier = "weak"
    return {"yoga": "gaja_kesari", "present": True, "tier": tier,
            "score": round(score, 1), "reasons": reasons,
            "checks": {"kendra_from_moon": jup_from_moon,
                       "combust": combust, "debilitated":
                       bool(jup_debil or moon_debil),
                       "neecha_bhanga": nb, "afflictions": unique_affl,
                       "dusthana": dusthana, "dasha": dasha_state}}


def gaja_kesari(anchor_or_date: str, time: str | None = None,
                tz: str | None = None, city: str | None = None,
                at_date: str | None = None) -> dict:
    """Full verdict for a birth moment (anchor key or date + city)."""
    from . import natal  # noqa: PLC0415

    detail = natal.chart_detail(anchor_or_date, time, tz)
    longitudes = {p["name"]: p["longitude"] for p in detail}
    lag = natal.lagna_longitude(anchor_or_date, time, tz, city)
    lagna_sign = int(lag % 360.0 // 30)
    birth_date, _t, _z = natal._birth(anchor_or_date, time, tz)
    dasha = vimshottari(longitudes["Moon"], birth_date, at_date)
    verdict = evaluate_gaja_kesari(longitudes, lagna_sign, dasha)
    verdict["lagna"] = RASHIS[lagna_sign]
    verdict["birth_date"] = birth_date
    return verdict


YOGAS = {"gaja_kesari": gaja_kesari}
