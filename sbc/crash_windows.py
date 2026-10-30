"""Indicative market-crash windows from planetary combinations.

Scores each calendar day in a range by adding the weights of the combinations active that day.
Weights and lifts come from the fixed historical crash-day study (26 crash days, 1929-2025):
weight = (lift - 1) * n / (n + 5). They are in-sample and none passed a multiple-testing
correction, so the output is a research prompt, not a signal.

Positions: 11:30 IST, sidereal Lahiri, mean nodes. The Venus-in-11th tests use the Mumbai
09:15 IST opening-bell chart with whole-sign houses.
"""
from __future__ import annotations

import datetime as dt

import swisseph as swe

ELEVATED = 1.85  # about the top 10% of all days since 1925
HIGH = 2.36      # about the top 3%
JOIN_GAP_DAYS = 4
MUMBAI = (18.9750, 72.8258)
SIGNS = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]
SIGN_NAMES = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
              "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
FIRE, WATER = {0, 4, 8}, {3, 7, 11}

# key: (label, type, lift, weight, meaning, seen in)
COMBOS = {
    "venus11_water": ("Venus in 11th house in a water sign (Mumbai open)", "Trigger", 2.80, 0.90,
                      "Venus in the house of gains, in a water sign.", ""),
    "sat_ura": ("Saturn–Uranus hard aspect", "Slow backdrop", 2.11, 0.74,
                "Restriction against disruption; strongest slow-cycle signal.", ""),
    "jup_sat": ("Jupiter–Saturn hard aspect", "Slow backdrop", 2.09, 0.73,
                "Expansion against contraction; the business-cycle pair.", ""),
    "jup_fire": ("Jupiter in a fire sign", "Slow backdrop", 1.82, 0.58,
                 "Expansive Jupiter in fiery signs; associated with speculative excess before the fall.",
                 "1987, 1992, 2000, 2004, 2008 (x3), 2011, 2015, 2016, 2020 (x2)"),
    "venus11": ("Venus in 11th house (Mumbai open)", "Trigger", 1.73, 0.52,
                "Venus in the house of gains; appeared in 46% of crash days vs 27% expected.",
                "1929, 1990, 1992, 1998, 2000, 2001, 2008, 2011, 2015, 2018, 2024, 2025"),
    "kaal_sarp": ("Kaal Sarp (all 7 planets one side of Rahu–Ketu)", "Trigger", 2.03, 0.46,
                  "All planets hemmed between the nodes.", ""),
    "sat_cap": ("Saturn in Capricorn", "Slow backdrop", 1.81, 0.41, "Saturn in its own earthy sign.", ""),
    "sun_lib": ("Sun debilitated in Libra", "Seasonal", 1.88, 0.39,
                "Weak Sun (authority, confidence). Falls every mid-Oct to mid-Nov, so it overlaps the \"October effect\".",
                "1929, 1987, 1997, 2008"),
    "sun_sat_68": ("Sun–Saturn in 6/8 (shadashtak)", "Trigger", 1.50, 0.27,
                   "Sun and Saturn in mutually hostile 6/8 positions.", "1990, 1997, 2008, 2010, 2016, 2024"),
    "venus_water": ("Venus in a water sign", "Trigger", 1.40, 0.26, "Venus in Cancer, Scorpio or Pisces.", ""),
    "merc_rx": ("Mercury retrograde", "Trigger", 1.41, 0.24,
                "Errors, miscommunication and technical breakdowns (2010 Flash Crash, 2024 carry unwind).",
                "1962, 1987, 2008, 2010, 2011, 2024, 2025"),
    "mars_can": ("Mars debilitated in Cancer", "Trigger", 1.52, 0.23,
                 "Weak, emotional Mars; seen in fast, liquidity-driven panics.", "1998, 2010, 2015, 2025"),
    "sat_plu": ("Saturn–Pluto hard aspect", "Slow backdrop", 1.29, 0.16, "Structural pressure.", ""),
    "mars_sat": ("Mars–Saturn hard aspect", "Trigger", 1.27, 0.15, "Force against restriction.", ""),
    "guru_chandal": ("Guru-Chandal (Jupiter with Rahu/Ketu)", "Trigger", 1.27, 0.14,
                     "Jupiter (finance, wisdom) afflicted by the nodes; confirming factor.",
                     "1990, 2001, 2016, 2020 (x2)"),
}
HARD_ORB = {"sat_ura": 8.0, "jup_sat": 8.0, "sat_plu": 8.0, "mars_sat": 6.0}

_P = {"Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS, "Mars": swe.MARS,
      "Jupiter": swe.JUPITER, "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Pluto": swe.PLUTO,
      "Rahu": swe.MEAN_NODE}
_FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED


def _jd(day: dt.date, hh: int, mm: int) -> float:
    ist = dt.datetime(day.year, day.month, day.day, hh, mm) - dt.timedelta(hours=5, minutes=30)
    return swe.julday(ist.year, ist.month, ist.day, ist.hour + ist.minute / 60.0)


def _fmt(lon: float) -> str:
    return f"{SIGNS[int(lon // 30)]} {int(lon % 30)}°"


def _hard(a: float, b: float, orb: float) -> bool:
    d = abs((a - b + 180) % 360 - 180)
    return min(d, abs(d - 90), abs(d - 180)) <= orb


def day_state(day: dt.date) -> dict:
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd = _jd(day, 11, 30)
    pos, spd = {}, {}
    for name, pid in _P.items():
        xx, _ = swe.calc_ut(jd, pid, _FLAGS)
        pos[name], spd[name] = xx[0] % 360, xx[3]
    pos["Ketu"] = (pos["Rahu"] + 180) % 360
    sign = {k: int(v // 30) for k, v in pos.items()}

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    jd_open = _jd(day, 9, 15)
    _, ascmc = swe.houses_ex(jd_open, MUMBAI[0], MUMBAI[1], b"W", swe.FLG_SIDEREAL)
    lagna = int((ascmc[0] % 360) // 30)
    venus_open, _ = swe.calc_ut(jd_open, swe.VENUS, _FLAGS)
    venus_sign_open = int((venus_open[0] % 360) // 30)
    venus_house = (venus_sign_open - lagna) % 12 + 1

    rahu = pos["Rahu"]
    rel = [((pos[p] - rahu) % 360) for p in ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")]
    kaal_sarp = all(r < 180 for r in rel) or all(r > 180 for r in rel)

    v11 = f"Lagna {SIGN_NAMES[lagna]} at 09:15 IST, Venus {_fmt(venus_open[0] % 360)} in {venus_house}th"
    active = {
        "venus11_water": (venus_house == 11 and venus_sign_open in WATER, v11),
        "sat_ura": (_hard(pos["Saturn"], pos["Uranus"], HARD_ORB["sat_ura"]),
                    f"Saturn {_fmt(pos['Saturn'])} / Uranus {_fmt(pos['Uranus'])}"),
        "jup_sat": (_hard(pos["Jupiter"], pos["Saturn"], HARD_ORB["jup_sat"]),
                    f"Jupiter {_fmt(pos['Jupiter'])} / Saturn {_fmt(pos['Saturn'])}"),
        "jup_fire": (sign["Jupiter"] in FIRE, f"Jupiter {_fmt(pos['Jupiter'])}"),
        "venus11": (venus_house == 11, v11),
        "kaal_sarp": (kaal_sarp, f"Rahu {_fmt(rahu)}"),
        "sat_cap": (sign["Saturn"] == 9, f"Saturn {_fmt(pos['Saturn'])}"),
        "sun_lib": (sign["Sun"] == 6, f"Sun {_fmt(pos['Sun'])}"),
        "sun_sat_68": ((sign["Saturn"] - sign["Sun"]) % 12 in (5, 7),
                       f"Sun {_fmt(pos['Sun'])} / Saturn {_fmt(pos['Saturn'])}"),
        "venus_water": (sign["Venus"] in WATER, f"Venus {_fmt(pos['Venus'])}"),
        "merc_rx": (spd["Mercury"] < 0, f"Mercury retrograde at {_fmt(pos['Mercury'])}"),
        "mars_can": (sign["Mars"] == 3, f"Mars {_fmt(pos['Mars'])}"),
        "sat_plu": (_hard(pos["Saturn"], pos["Pluto"], HARD_ORB["sat_plu"]),
                    f"Saturn {_fmt(pos['Saturn'])} / Pluto {_fmt(pos['Pluto'])}"),
        "mars_sat": (_hard(pos["Mars"], pos["Saturn"], HARD_ORB["mars_sat"]),
                     f"Mars {_fmt(pos['Mars'])} / Saturn {_fmt(pos['Saturn'])}"),
        "guru_chandal": (sign["Jupiter"] in (sign["Rahu"], sign["Ketu"]),
                         f"Jupiter {_fmt(pos['Jupiter'])} with {'Rahu' if sign['Jupiter'] == sign['Rahu'] else 'Ketu'}"),
    }
    on = {k: p for k, (a, p) in active.items() if a}
    raw = sum(COMBOS[k][3] for k in on)
    # Compare before rounding, with a small tolerance below each cut so float noise doesn't flag a day.
    level = "HIGH" if raw >= HIGH - 1e-9 else "ELEVATED" if raw > ELEVATED + 1e-9 else ""
    score = round(raw, 2)
    return {"date": day.isoformat(), "score": score, "level": level, "active": on}


def _runs(days: list[str]) -> list[list[str]]:
    out: list[list[str]] = []
    for d in days:
        if out and (dt.date.fromisoformat(d) - dt.date.fromisoformat(out[-1][-1])).days <= 1:
            out[-1].append(d)
        else:
            out.append([d])
    return [[r[0], r[-1]] for r in out]


def _eclipses(start: dt.date, end: dt.date) -> list[dict]:
    out = []
    jd0, jd1 = _jd(start, 0, 0), _jd(end, 23, 59)
    for kind, fn in (("Solar", swe.sol_eclipse_when_glob), ("Lunar", swe.lun_eclipse_when)):
        jd = jd0
        while True:
            try:
                tret = fn(jd, swe.FLG_SWIEPH)[1]
            except Exception:  # noqa: BLE001 - ephemeris edge; eclipses are reference only
                break
            if tret[0] > jd1:
                break
            y, m, d, _ = swe.revjul(tret[0] + 5.5 / 24)
            out.append({"date": dt.date(y, m, d).isoformat(), "kind": kind})
            jd = tret[0] + 20
    return sorted(out, key=lambda e: e["date"])


def build(start: dt.date, end: dt.date) -> dict:
    days = [day_state(start + dt.timedelta(n)) for n in range((end - start).days + 1)]
    by_date = {d["date"]: d for d in days}
    flagged = [d["date"] for d in days if d["level"]]

    # Join flagged days less than JOIN_GAP_DAYS apart into periods.
    groups: list[list[str]] = []
    for d in flagged:
        if groups and (dt.date.fromisoformat(d) - dt.date.fromisoformat(groups[-1][-1])).days < JOIN_GAP_DAYS:
            groups[-1].append(d)
        else:
            groups.append([d])

    periods = []
    for g in groups:
        span = [by_date[(dt.date.fromisoformat(g[0]) + dt.timedelta(n)).isoformat()]
                for n in range((dt.date.fromisoformat(g[-1]) - dt.date.fromisoformat(g[0])).days + 1)]
        peak = max(span, key=lambda d: d["score"])
        reasons = []
        for k in sorted(peak["active"], key=lambda k: -COMBOS[k][3]):
            on_days = [d["date"] for d in days if k in d["active"]]
            # Active dates near the period: the runs that touch it.
            runs = [r for r in _runs(on_days) if r[1] >= g[0] and r[0] <= g[-1]]
            label, typ, lift, weight, meaning, seen = COMBOS[k]
            reasons.append({"key": k, "label": label, "type": typ, "lift": lift, "weight": weight,
                            "position": peak["active"][k], "meaning": meaning, "seen": seen, "runs": runs})
        periods.append({
            "start": g[0], "end": g[-1], "days": len(span),
            "level": "HIGH" if any(d["level"] == "HIGH" for d in span) else "ELEVATED",
            "high_runs": _runs([d["date"] for d in span if d["level"] == "HIGH"]),
            "peak_score": peak["score"], "peak_date": peak["date"], "reasons": reasons,
        })

    calendar = []
    for k, (label, typ, lift, weight, _m, _s) in sorted(COMBOS.items(), key=lambda kv: -kv[1][3]):
        calendar.append({"key": k, "label": label, "type": typ, "lift": lift, "weight": weight,
                         "runs": _runs([d["date"] for d in days if k in d["active"]])})

    slow_strong = [c for c in calendar if c["key"] in ("sat_ura", "jup_sat") and c["runs"]]
    return {
        "start": start.isoformat(), "end": end.isoformat(),
        "generated": dt.date.today().isoformat(),
        "days_scanned": len(days),
        "n_high": sum(p["level"] == "HIGH" for p in periods),
        "n_elevated": sum(p["level"] == "ELEVATED" for p in periods),
        "days_covered": sum(p["days"] for p in periods),
        "strong_slow_active": [c["label"] for c in slow_strong],
        "thresholds": {"elevated": ELEVATED, "high": HIGH, "join_gap_days": JOIN_GAP_DAYS},
        "periods": sorted(periods, key=lambda p: -p["peak_score"]),
        "calendar": calendar,
        "eclipses": _eclipses(start, end),
        "series": [{"date": d["date"], "score": d["score"], "level": d["level"]} for d in days],
    }
