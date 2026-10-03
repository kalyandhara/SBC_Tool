"""The tool's existing astro rules, expressed as one daily NIFTY signal each.

Each rule is taken *as stated in the codebase*: its direction and threshold
come from the module that defines it, nothing is fitted here. That makes
the validation an honest out-of-sample test of the rule as published,
apart from whatever tuning the original author did on past data.

  directional  +1 bullish / -1 bearish / 0 no call, judged on excess return
  event        True / False, judged on whether the market moves more (|return|)

Two placebo rules (hash-of-date noise, one daily and one monthly) are
included as controls: a sound test should call them insignificant.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass

from sbc import backtest as bt
from sbc.kp_intraday import KPRuleEngine
from sbc.market_calendar import reversal_alert
from sbc.nakshatra import moon_nature
from sbc.planets import positioned_planets, positions

_kp_engine = KPRuleEngine()


@dataclass(frozen=True)
class Rule:
    name: str
    kind: str  # "directional" | "event"
    source: str
    description: str
    fn: Callable[[dict, Context], int | bool]


class Context:
    """Lazily computed inputs shared by the rules for one date."""

    def __init__(self, date: str):
        self.date = date
        self.noon_jd = bt._julian_at_noon(date)
        self._noon = None
        self._open = None
        self._windows = None

    @property
    def noon_planets(self) -> dict:
        """sbc.planets positions at noon IST: what the futurecast scorers use."""
        if self._noon is None:
            planets, _ = positions(self.noon_jd)
            self._noon = {p["name"]: p for p in planets}
        return self._noon

    @property
    def open_chart(self):
        """(planets with natures, tithi) at 09:15 IST, as build_response uses them."""
        if self._open is None:
            planets, _ay, _sun, _moon, tithi = positioned_planets(self.date, "09:15")
            self._open = (planets, tithi)
        return self._open


def _sign(x: float) -> int:
    return (x > 0) - (x < 0)


def _reversal_windows(ctx: Context) -> list[dict]:
    if ctx._windows is None:
        planets, tithi = ctx.open_chart
        alert = reversal_alert(ctx.date, planets, tithi)
        ctx._windows = alert.get("windows", []) if alert.get("active") else []
    return ctx._windows


def _reversal_bias(fp: dict, ctx: Context) -> int:
    score = 0
    for w in _reversal_windows(ctx):
        label = str(w.get("bias", "")).upper()
        if "BULLISH" in label:
            score += 1
        elif "BEARISH" in label:
            score -= 1
    return _sign(score)


def _near_eclipse(fp: dict, days: float = 7.0) -> bool:
    e = fp["eclipse"]
    return any(v is not None and v <= days for v in (e["days_since"], e["days_to"]))


def _hash_sign(text: str) -> int:
    return 1 if hashlib.sha256(text.encode()).digest()[0] % 2 else -1


RULES: list[Rule] = [
    Rule("sbc_classical", "directional", "sbc.prediction.analyze",
         "Sign of the NIFTY-anchor vedha net, classical school",
         lambda fp, ctx: _sign(fp["sbc"]["classical"]["net"])),
    Rule("sbc_allthree", "directional", "sbc.prediction.analyze",
         "Sign of the NIFTY-anchor vedha net, all-three-rays school",
         lambda fp, ctx: _sign(fp["sbc"]["allthree"]["net"])),
    Rule("kp_day_bias", "directional", "sbc.kp_intraday.KPRuleEngine.compute_day_bias",
         "Day lord + Moon star lord natures",
         lambda fp, ctx: _sign(_kp_engine.compute_day_bias(
             fp["panchang"]["weekday_lord"], fp["kp"]["moon_star_lord"])[0])),
    Rule("bullish_futurecast", "directional", "sbc.backtest._bullish_future_score",
         "Bullish trigger score >= 4 (futurecast threshold) -> bullish",
         lambda fp, ctx: 1 if bt._bullish_future_score(ctx.noon_jd)[0] >= 4 else 0),
    Rule("bearish_futurecast", "directional", "sbc.backtest._bearish_future_score",
         "Bearish trigger score >= 3 (futurecast threshold) -> bearish",
         lambda fp, ctx: -1 if bt._bearish_future_score(ctx.noon_jd)[0] >= 3 else 0),
    Rule("jupiter_crash_legacy", "directional", "sbc.backtest._future_score",
         "Legacy Jupiter crash score >= 4 -> bearish",
         lambda fp, ctx: -1 if bt._future_score(ctx.noon_jd)[0] >= 4 else 0),
    Rule("reversal_calendar_bias", "directional", "sbc.market_calendar.reversal_alert",
         "Net bias of active reversal windows (bullish labels minus bearish)",
         _reversal_bias),
    Rule("bradley_sign", "directional", "sbc.bradley.bradley_score",
         "Sign of the Bradley barometer",
         lambda fp, ctx: _sign(fp["bradley"])),
    Rule("moon_nature", "directional", "sbc.nakshatra.moon_nature",
         "Shubha Moon -> bullish, ashubha (Krishna Ekadashi..Shukla Chaturthi) -> bearish",
         lambda fp, ctx: 1 if moon_nature(fp["panchang"]["tithi"]) == "benefic" else -1),
    Rule("shukla_paksha", "directional", "sbc.nakshatra.paksha_of",
         "Waxing Moon -> bullish, waning -> bearish",
         lambda fp, ctx: 1 if fp["panchang"]["paksha"] == "Shukla" else -1),
    Rule("rikta_tithi", "directional", "sbc.nakshatra.GROUP_OF_TITHI",
         "Rikta tithi group -> bearish",
         lambda fp, ctx: -1 if fp["panchang"]["tithi_group"] == "Rikta" else 0),
    Rule("moon_sentiment_sign", "directional", "sbc.backtest._moon_sentiment_sign",
         "Moon in Taurus, Cancer or Pisces -> bullish",
         lambda fp, ctx: 1 if bt._moon_sentiment_sign(ctx.noon_planets["Moon"]) else 0),
    Rule("moon_gandanta", "directional", "sbc.backtest._moon_gandanta",
         "Moon at a gandanta junction -> bearish",
         lambda fp, ctx: -1 if bt._moon_gandanta(ctx.noon_planets["Moon"]["longitude"]) else 0),
    Rule("mercury_retrograde", "directional", "sbc.backtest._mercury_retrograde",
         "Mercury retrograde -> bearish",
         lambda fp, ctx: -1 if fp["planets"]["Mercury"]["retrograde"] else 0),
    Rule("eclipse_window", "directional", "sbc.backtest._eclipse_financial_axis (spirit)",
         "Within 7 days of a solar or lunar eclipse -> bearish",
         lambda fp, ctx: -1 if _near_eclipse(fp) else 0),
    Rule("vishti_volatility", "event", "sbc.bhadra",
         "Bhadra (Vishti karana) at the open -> bigger moves",
         lambda fp, ctx: bool(fp["panchang"]["vishti"])),
    Rule("reversal_window_volatility", "event", "sbc.market_calendar.reversal_alert",
         "Any active reversal window -> bigger moves",
         lambda fp, ctx: bool(_reversal_windows(ctx))),
    Rule("eclipse_volatility", "event", "sbc.fingerprint eclipse distance",
         "Within 7 days of an eclipse -> bigger moves",
         lambda fp, ctx: _near_eclipse(fp)),
    Rule("placebo_daily", "directional", "control",
         "Coin flip from a hash of the date (should show no edge)",
         lambda fp, ctx: _hash_sign(fp["date"])),
    Rule("placebo_monthly", "directional", "control",
         "Coin flip per calendar month (persistent noise; should show no edge)",
         lambda fp, ctx: _hash_sign(fp["date"][:7])),
]


def signals_for(fingerprints: list[dict]) -> dict[str, list]:
    """{rule name: [signal per fingerprint]} in the fingerprints' order."""
    out: dict[str, list] = {r.name: [] for r in RULES}
    for fp in fingerprints:
        ctx = Context(fp["date"])
        for rule in RULES:
            out[rule.name].append(rule.fn(fp, ctx))
    return out
