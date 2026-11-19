"""Context for the Today card. Rule items echo the stance inputs; context items
never change the stance. Classical rules, unvalidated: every item carries a badge."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sbc import ashtakavarga as AV
from sbc.engine import _julday, _utc_from_local
from sbc.nakshatra import RASHIS
from sbc.panchang_signals import panchang_signal
from sbc.planets import positions
from sbc.transit_natal import active_on

SPAN = 360.0 / 27.0
TARAS = ("Janma", "Sampat", "Vipat", "Kshema", "Pratyak", "Sadhana", "Naidhana", "Mitra", "Parama Mitra")
_TARA_DIR = {1: "neutral", 2: "up", 3: "down", 4: "up", 5: "down", 6: "up", 7: "down", 8: "up", 9: "up"}
_CHANDRA_UP = {1, 3, 6, 7, 10, 11}
SAV_HIGH, SAV_LOW = 28, 25
SESSION_START, SESSION_END = 9 * 60 + 15, 15 * 60 + 30


def _item(key: str, label: str, direction: str, detail: str, in_rule: bool = False) -> dict[str, Any]:
    return {"key": key, "label": label, "direction": direction, "in_rule": in_rule,
            "badge": "unvalidated" if in_rule else "experimental", "detail": detail}


def _star(lon: float) -> int:
    return int(lon % 360.0 // SPAN) % 27


def tarabala(natal_moon: float, moon: float) -> dict[str, Any]:
    count = (_star(moon) - _star(natal_moon)) % 27 + 1
    tara = (count - 1) % 9 + 1
    return _item("tarabala", "Tarabala", _TARA_DIR[tara], f"{TARAS[tara - 1]} (star {count} from natal Moon)")


def chandrabala(natal_moon: float, moon: float) -> dict[str, Any]:
    count = (int(moon % 360 // 30) - int(natal_moon % 360 // 30)) % 12 + 1
    return _item("chandrabala", "Chandrabala", "up" if count in _CHANDRA_UP else "down",
                 f"Moon {count} signs from natal Moon")


def chart_sav(natal: Mapping[str, float]) -> list[int]:
    signs = {p: int(natal[p] % 360 // 30) for p in AV.PLANETS}
    return AV.sav(AV.bav(signs, int(natal["Lagna"] % 360 // 30)))


def sav_item(sav_list: list[int], moon: float) -> dict[str, Any]:
    sign = int(moon % 360 // 30)
    value = sav_list[sign]
    direction = "up" if value >= SAV_HIGH else "down" if value <= SAV_LOW else "neutral"
    return _item("sav", "Ashtakavarga SAV", direction, f"Moon in {RASHIS[sign]}: {value} bindus")


def sky_at(day: str) -> list[dict]:
    planets, _ = positions(_julday(_utc_from_local(day, "09:15", "Asia/Kolkata")))
    return list(planets)


def rule_items(band: str, trend: str, vix: str) -> list[dict[str, Any]]:
    band_dir = ("up" if band in ("High Probability", "Exceptional Setup")
                else "down" if band in ("Very Defensive", "No Trading") else "neutral")
    return [_item("band", "Score band", band_dir, band, True),
            _item("trend", "Nifty trend (20/50-day)", {"Up": "up", "Down": "down"}.get(trend, "neutral"), trend, True),
            _item("vix", "India VIX regime", "down" if vix == "High" else "neutral", vix, True)]


def context_items(natal: Mapping[str, float], day: str, running: Mapping[str, str | None]) -> list[dict[str, Any]]:
    sky = sky_at(day)
    moon = next(p["longitude"] for p in sky if p["name"] == "Moon")
    contacts = active_on(dict(natal), day)
    text = ", ".join(f"{c['planet']} {c['aspect']} natal {c['natal']}" for c in contacts) or "none"
    panch = panchang_signal(sky)
    p_dir = "up" if panch["final_score"] > 0 else "down" if panch["final_score"] < 0 else "neutral"
    lords = " / ".join(x for x in (running.get("maha"), running.get("antar"), running.get("pratyantar")) if x)
    return [tarabala(natal["Moon"], moon), chandrabala(natal["Moon"], moon),
            sav_item(chart_sav(natal), moon),
            _item("contacts", "Transit contacts at 09:15", "neutral", text),
            _item("panchang", "Panchang trend", p_dir, panch["final_label"]),
            _item("dasha", "Running dasha", "neutral", lords or "unknown")]


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def time_windows(forecast: Mapping[str, Any]) -> dict[str, Any]:
    blocks: dict[int, list[float]] = {}
    for b in forecast["buckets"]:
        m = _minutes(b["time"])
        if SESSION_START <= m < SESSION_END:
            blocks.setdefault((m - SESSION_START) // 30, []).append(float(b["score"]))
    rows: list[dict[str, Any]] = [{"start": _clock(SESSION_START + 30 * k),
             "end": _clock(min(SESSION_START + 30 * (k + 1), SESSION_END)),
             "score": round(sum(v) / len(v), 3)} for k, v in sorted(blocks.items())]
    best = sorted(rows, key=lambda r: (-float(r["score"]), str(r["start"])))[:2]
    worst = sorted(rows, key=lambda r: (r["score"], r["start"]))[:1]
    return {"available": bool(rows), "best": best, "worst": worst,
            "status": forecast.get("status", "experimental"), "notice": forecast.get("experimental_notice", "")}
