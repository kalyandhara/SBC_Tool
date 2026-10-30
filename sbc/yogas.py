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
from .planets import DEBIL as DEBILITATED
from .planets import EXALT as EXALTED_FROM_PLANETS

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
EXALTED = dict(EXALTED_FROM_PLANETS)          # planets.py classical map
OWN = {"Sun": {4}, "Moon": {3}, "Mars": {0, 7}, "Mercury": {2, 5},
       "Jupiter": {8, 11}, "Venus": {1, 6}, "Saturn": {9, 10}}
DEBILITATED = dict(DEBILITATED)               # planets.py classical map
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


# ---------------------------------------------------------------------------
# Shared machinery for the two-planet conjunction yogas below.
# ---------------------------------------------------------------------------

COMBUSTIBLE = {"Moon": 12.0, "Mars": 17.0, "Mercury": 14.0,
               "Jupiter": 11.0, "Venus": 10.0, "Saturn": 15.0}
BENEFICS = ("Jupiter", "Venus", "Moon", "Mercury")


def _sign(longitude: float) -> int:
    return int(longitude % 360.0 // 30)


def _dignity(name: str, sign: int) -> str | None:
    if EXALTED.get(name) == sign:
        return "exalted"
    if sign in OWN.get(name, set()):
        return "own sign"
    if DEBILITATED.get(name) == sign:
        return "debilitated"
    return None


def _neecha_bhanga(name: str, sign: int, longitudes: dict[str, float],
                   lagna_sign: int | None,
                   moon_sign: int) -> tuple[bool, str]:
    """Cancellation: the dispositor of the debilitated planet in a
    Kendra from the Lagna or the Moon."""
    lord_name = SIGN_LORDS[sign]
    lord_lon = longitudes.get(lord_name)
    if lord_lon is None:
        return False, ""
    lord_sign = _sign(lord_lon)
    from_moon = (lord_sign - moon_sign) % 12 + 1
    from_lagna = ((lord_sign - lagna_sign) % 12 + 1
                  if lagna_sign is not None else None)
    if from_moon in KENDRA or (from_lagna is not None
                               and from_lagna in KENDRA):
        where = "Lagna" if (from_lagna is not None
                            and from_lagna in KENDRA) else "Moon"
        return True, (f"neecha bhanga: {lord_name} (dispositor of "
                      f"debilitated {name}) is in a Kendra from the "
                      f"{where}")
    return False, ""


def _afflictions(longitudes: dict[str, float],
                 victims: dict[str, int],
                 exclude: set[str]) -> list[str]:
    """Saturn/Rahu/Ketu conjunction or Saturn full drishti on victims.

    victims: {planet_name: sign}.  Malefics that are themselves part of
    the yoga pair are excluded from afflicting each other only when the
    caller says so.
    """
    found = []
    for victim_name, victim_sign in victims.items():
        for malefic in ("Saturn", "Rahu", "Ketu"):
            if malefic in exclude:
                continue
            m_lon = longitudes.get(malefic)
            if m_lon is None:
                continue
            m_sign = _sign(m_lon)
            if m_sign == victim_sign:
                found.append(f"{malefic} conjunct {victim_name}")
            elif malefic == "Saturn" and victim_sign in drishti_targets(
                    "Saturn", m_sign):
                found.append(
                    f"Saturn aspects {victim_name} "
                    f"({RASHIS[m_sign]} -> {RASHIS[victim_sign]})")
    return sorted(set(found))


def _benefic_drishti(longitudes: dict[str, float], victim_sign: int,
                     exclude: set[str]) -> list[str]:
    """Benefics (Venus/Moon/Jupiter not part of the pair) casting their
    7th-house aspect onto the victim's sign - a mitigating factor."""
    out = []
    for benefic in ("Venus", "Moon", "Jupiter"):
        if benefic in exclude:
            continue
        b_lon = longitudes.get(benefic)
        if b_lon is None:
            continue
        b_sign = _sign(b_lon)
        # Venus and the Moon cast a 7th-house aspect only; Jupiter
        # also aspects the 5th and 9th.
        targets = {(b_sign + 6) % 12}
        if benefic == "Jupiter":
            targets |= {(b_sign + 4) % 12, (b_sign + 8) % 12}
        if victim_sign in targets:
            out.append(f"{benefic} aspects the pair from "
                       f"{RASHIS[b_sign]}")
    return sorted(set(out))


def _dusthana_check(longitudes: dict[str, float], lagna_sign: int | None,
                    names: tuple[str, ...]) -> str | None:
    if lagna_sign is None:
        return None
    for name in names:
        h = (_sign(longitudes[name]) - lagna_sign) % 12 + 1
        if h in DUSTHANA:
            return name
    return None


def _dasha_state(dasha: dict | None, lords: tuple[str, ...]) -> str:
    if not dasha:
        return "unknown"
    active = {dasha["at"]["maha"], dasha["at"]["antar"]}
    return "active" if active & set(lords) else "dormant"


def _tier(score: float) -> str:
    if score >= 7.0:
        return "strong"
    if score >= 5.0:
        return "moderate"
    return "weak"


def _conjunction(longitudes: dict[str, float], a: str,
                 b: str) -> bool:
    return (_sign(longitudes[a]) == _sign(longitudes[b]))


def evaluate_conjunction_yoga(longitudes: dict[str, float],
                              yoga: str, pair: tuple[str, str],
                              lagna_sign: int | None = None,
                              dasha: dict | None = None,
                              spec: dict | None = None) -> dict:
    """Generic conjunction-yoga evaluator.

    spec keys:
      polarity        "auspicious" or "affliction"
      dasha_lords     lords whose period activates the yoga
      results         one-line classical interpretation
      waxing_matters  (Moon pairs) Moon bright/wane modifies the score
      benefic_drishti_mitigates  benefic aspects soften affliction yogas
    """
    spec = spec or {}
    polarity = spec.get("polarity", "auspicious")
    a, b = pair
    reasons: list[str] = []
    score = 5.0

    if not _conjunction(longitudes, a, b):
        sep_note = (f"{a} is in {RASHIS[_sign(longitudes[a])]}, {b} in "
                    f"{RASHIS[_sign(longitudes[b])]}")
        reasons.append(f"primary fails: {a} and {b} are not conjunct "
                       f"({sep_note})")
        return {"yoga": yoga, "present": False, "tier": "absent",
                "score": 0.0, "reasons": reasons,
                "checks": {"pair": [a, b], "dasha": None}}

    present = True
    reasons.append(f"primary: {a} and {b} are conjunct in "
                   f"{RASHIS[_sign(longitudes[a])]}")

    victims = {}
    for name in pair:
        sign = _sign(longitudes[name])
        victims[name] = sign
        dignity = _dignity(name, sign)
        if polarity == "auspicious":
            if dignity == "exalted":
                score += 2.0
                reasons.append(f"{name} is exalted ({RASHIS[sign]})")
            elif dignity == "own sign":
                score += 1.0
                reasons.append(f"{name} is in its own sign ({RASHIS[sign]})")
            elif dignity == "debilitated":
                score -= 2.0
                nb, nb_reason = _neecha_bhanga(
                    name, sign, longitudes, lagna_sign,
                    _sign(longitudes["Moon"]))
                if nb:
                    score += 1.0
                    reasons.append(f"{name} is debilitated "
                                   f"({RASHIS[sign]}); {nb_reason}")
                else:
                    nb_note = nb_reason or "no neecha bhanga detected"
                    reasons.append(f"{name} is debilitated "
                                   f"({RASHIS[sign]}); {nb_note}")
        elif polarity == "affliction":
            if dignity in ("exalted", "own sign"):
                score -= 1.5
                reasons.append(f"{name} is dignified ({dignity}, "
                               f"{RASHIS[sign]}) - the defect is softened")
            elif dignity == "debilitated":
                score += 1.0
                reasons.append(f"{name} is debilitated "
                               f"({RASHIS[sign]}) - the defect deepens")

    # combustion of a combustible pair member (not when the Sun itself
    # is in the pair - that case is measured directly below)
    if "Sun" not in pair:
        for name in pair:
            orb = COMBUSTIBLE.get(name)
            if orb is None:
                continue
            sep = _separation(longitudes[name], longitudes["Sun"])
            if sep <= orb:
                delta = -1.5 if polarity == "auspicious" else 0.5
                score += delta
                reasons.append(f"{name} is combust ({sep:.1f} deg from "
                               "the Sun)")

    afflictions = _afflictions(longitudes, victims,
                               exclude={a, b})
    if afflictions:
        delta = (-min(2.0, len(afflictions)) if polarity == "auspicious"
                 else min(1.0, 0.5 * len(afflictions)))
        score += delta
        reasons.append("malefic affliction: " + "; ".join(afflictions))
    elif polarity == "auspicious":
        reasons.append("no Saturn/Rahu/Ketu affliction on the pair")

    if spec.get("benefic_drishti_mitigates"):
        soft = _benefic_drishti(longitudes, victims[pair[0]],
                                exclude={a, b})
        if soft:
            score -= min(2.0, len(soft))
            reasons.append("mitigation: " + "; ".join(soft))

    if spec.get("waxing_matters"):
        elong = (longitudes["Moon"] - longitudes["Sun"]) % 360.0
        if elong < 180.0:
            score += 2.0 if polarity == "auspicious" else -0.5
            reasons.append("the Moon is bright (Shukla paksha)")
        else:
            score -= 1.0 if polarity == "auspicious" else 0.5
            reasons.append("the Moon is dark (Krishna paksha)")

    dust = _dusthana_check(longitudes, lagna_sign, pair)
    if dust:
        delta = -1.0 if polarity == "auspicious" else 0.5
        score += delta
        reasons.append(f"{dust} is in dusthana from the Lagna")
    elif lagna_sign is not None:
        reasons.append("neither planet is in dusthana from the Lagna")

    dasha_state = _dasha_state(dasha, spec.get("dasha_lords",
                                               (pair[0], pair[1])))
    if dasha_state == "active":
        score += 1.0
        reasons.append("dasha: a pair lord's period is running - the "
                       "yoga is activated")
    elif dasha_state == "dormant":
        reasons.append("dasha: dormant until a pair lord's period runs")
    if spec.get("results"):
        reasons.append("results: " + spec["results"])

    score = max(0.0, min(10.0, score))
    return {"yoga": yoga, "present": present, "tier": _tier(score),
            "score": round(score, 1), "reasons": reasons,
            "checks": {"pair": [a, b], "dasha": dasha_state}}


def evaluate_budha_aditya(longitudes: dict[str, float],
                          lagna_sign: int | None = None,
                          dasha: dict | None = None) -> dict:
    """Sun + Mercury (Nipuna Yoga): intellect, speech, administration."""
    deep = _conjunction(longitudes, "Sun", "Mercury") and \
        _separation(longitudes["Mercury"], longitudes["Sun"]) <= 3.0
    out = evaluate_conjunction_yoga(
        longitudes, "budha_aditya", ("Sun", "Mercury"), lagna_sign,
        dasha,
        {"polarity": "auspicious", "dasha_lords": ("Sun", "Mercury"),
         "results": "sharp intellect, way with words, success in "
                    "administration, writing and commerce"})
    if out["present"] and deep:
        out["score"] = round(max(0.0, out["score"] - 1.0), 1)
        out["tier"] = _tier(out["score"])
        out["reasons"].append("Mercury is deeply combust (within 3 deg) "
                              "- brilliance turns impulsive")
    return out


def evaluate_guru_chandal(longitudes: dict[str, float],
                          lagna_sign: int | None = None,
                          dasha: dict | None = None) -> dict:
    """Jupiter + Rahu/Ketu (Guru-Chandal): unorthodox brilliance with
    an ethical-risk edge; dignified or benefic-aspected Jupiter softens
    it toward occult/spiritual aptitude."""
    node = "Rahu" if _conjunction(longitudes, "Jupiter", "Rahu") else \
        ("Ketu" if _conjunction(longitudes, "Jupiter", "Ketu") else None)
    out = evaluate_conjunction_yoga(
        longitudes, "guru_chandal", ("Jupiter", node or "Rahu"),
        lagna_sign, dasha,
        {"polarity": "affliction", "dasha_lords": ("Jupiter", "Rahu"),
         "benefic_drishti_mitigates": True,
         "results": "unorthodox intelligence and worldly cunning; "
                    "mitigated, it becomes aptitude for astrology, "
                    "occult and unconventional wisdom; unmitigated, "
                    "ethical risk"})
    if out["present"] and node == "Ketu":
        out["reasons"].append("Ketu variant: moksha-oriented, detached "
                              "wisdom rather than worldly cunning")
    return out


def evaluate_chandra_mangal(longitudes: dict[str, float],
                            lagna_sign: int | None = None,
                            dasha: dict | None = None) -> dict:
    """Moon + Mars: earning capacity through bold effort (classically
    a wealth combination; with a dark Moon the earning turns impulsive
    or is squandered)."""
    return evaluate_conjunction_yoga(
        longitudes, "chandra_mangal", ("Moon", "Mars"), lagna_sign,
        dasha,
        {"polarity": "auspicious", "dasha_lords": ("Moon", "Mars"),
         "waxing_matters": True,
         "results": "wealth through courage, enterprise and practical "
                    "action; strong earning instinct"})


def evaluate_shrapit(longitudes: dict[str, float],
                     lagna_sign: int | None = None,
                     dasha: dict | None = None) -> dict:
    """Saturn + Rahu (Shrapit Yoga): the past-life-curse combination -
    recurring obstructions and sudden setbacks; dignity and benefic
    aspects soften it."""
    return evaluate_conjunction_yoga(
        longitudes, "shrapit", ("Saturn", "Rahu"), lagna_sign, dasha,
        {"polarity": "affliction", "dasha_lords": ("Saturn", "Rahu"),
         "benefic_drishti_mitigates": True,
         "results": "recurring obstructions, unexplained delays and "
                    "sudden reversals; softened, it gives relentless "
                    "persistence through hardship"})


def evaluate_punarphoo(longitudes: dict[str, float],
                       lagna_sign: int | None = None,
                       dasha: dict | None = None) -> dict:
    """Moon + Saturn (Punarphoo): obstacles and delays - classically
    in marriage and agreements; benefic aspects ease the friction."""
    return evaluate_conjunction_yoga(
        longitudes, "punarphoo", ("Moon", "Saturn"), lagna_sign, dasha,
        {"polarity": "affliction", "dasha_lords": ("Moon", "Saturn"),
         "waxing_matters": True, "benefic_drishti_mitigates": True,
         "results": "delays and second thoughts - classically in "
                    "marriage and contracts; progress comes slowly "
                    "and sticks once made"})


def evaluate_chandra_aditya(longitudes: dict[str, float],
                            lagna_sign: int | None = None,
                            dasha: dict | None = None) -> dict:
    """Sun + Moon (Amavasya-side conjunction): the closer the Moon to
    the Sun, the weaker the mind's light; separation restores strength."""
    out = evaluate_conjunction_yoga(
        longitudes, "chandra_aditya", ("Sun", "Moon"), lagna_sign, dasha,
        {"polarity": "auspicious", "dasha_lords": ("Sun", "Moon"),
         "results": "willpower fused with the mind - strong when the "
                    "Moon has room from the Sun; near-exact, an "
                    "Amavasya-like dimming of mood and confidence"})
    if out["present"]:
        sep = _separation(longitudes["Moon"], longitudes["Sun"])
        if sep <= 12.0:
            out["score"] = round(max(0.0, out["score"] - 2.0), 1)
            out["tier"] = _tier(out["score"])
            out["reasons"].append(
                f"near-Amavasya: the Moon is only {sep:.1f} deg from "
                "the Sun - paksha bala is very low")
        else:
            out["reasons"].append(
                f"the Moon is {sep:.1f} deg from the Sun - some paksha "
                "bala remains")
    return out


YOGAS = {
    "gaja_kesari": gaja_kesari,
    "budha_aditya": evaluate_budha_aditya,
    "guru_chandal": evaluate_guru_chandal,
    "chandra_mangal": evaluate_chandra_mangal,
    "shrapit": evaluate_shrapit,
    "punarphoo": evaluate_punarphoo,
    "chandra_aditya": evaluate_chandra_aditya,
}


def detect_all(anchor_or_date: str, time: str | None = None,
               tz: str | None = None, city: str | None = None,
               at_date: str | None = None) -> dict:
    """Run every registered yoga on one birth chart.

    Returns {yoga_name: verdict} with lagna/birth metadata attached,
    plus a convenience 'summary' listing present yogas by tier.
    """
    from . import natal  # noqa: PLC0415

    detail = natal.chart_detail(anchor_or_date, time, tz)
    longitudes = {p["name"]: p["longitude"] for p in detail}
    lag = natal.lagna_longitude(anchor_or_date, time, tz, city)
    lagna_sign = int(lag % 360.0 // 30)
    birth_date, _t, _z = natal._birth(anchor_or_date, time, tz)
    dasha = vimshottari(longitudes["Moon"], birth_date, at_date)

    out: dict = {}
    for name, fn in YOGAS.items():
        if name == "gaja_kesari":
            out[name] = fn(anchor_or_date, time, tz, city, at_date)
        else:
            out[name] = fn(longitudes, lagna_sign, dasha)
        out[name]["lagna"] = RASHIS[lagna_sign]
    out["summary"] = {
        "present": [n for n, v in out.items()
                    if isinstance(v, dict) and v.get("present")],
        "strong": [n for n, v in out.items()
                   if isinstance(v, dict) and v.get("tier") == "strong"],
    }
    return out
