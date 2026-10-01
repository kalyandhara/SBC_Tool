"""KP Intraday Trend Change Prediction Engine.

Parses precomputed KP astrology data and generates structured intraday
trend change prediction reports for NIFTY/BANK NIFTY.
"""

import csv
import json
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from pathlib import Path
from typing import Any


class SignalGrade(Enum):
    PURE_SET_ALARM = "PURE-SET ALARM"
    TIER_1 = "TIER-1"
    TIER_2 = "TIER-2"
    REGIME_SHIFT = "REGIME SHIFT"
    COUNTER_REGIME = "COUNTER-REGIME"


class Direction(Enum):
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"


class HoraQuality(Enum):
    SLUGGISH = "Sluggish"
    NEUTRAL = "Neutral"
    FRUITFUL = "Fruitful"
    AGGRESSIVE = "Aggressive"
    VOLATILE = "Volatile"


@dataclass
class HoraSlot:
    start: time
    end: time
    lord: str
    quality: HoraQuality
    base_quality: str = ""
    aspects_received: str = ""
    interpretation: str = ""
    aspect_notes: str = ""

    def time_range_str(self) -> str:
        return f"{self.start.strftime('%H:%M')}–{self.end.strftime('%H:%M')}"


@dataclass
class RegimeShift:
    timestamp: time
    planet: str
    old_sublord: str
    new_sublord: str
    house_set_strength: float
    regime_label: str
    direction: Direction

    def time_str(self) -> str:
        return self.timestamp.strftime('%H:%M')


@dataclass
class TrendChangeSignal:
    timestamp: time
    grade: SignalGrade
    direction: Direction
    trigger: str
    asc_sub_house_set: str
    hora_lord: str
    score: float = 0.0
    notes: str = ""
    navamsa_d9: str = ""      # v15: "Gemini (friend VARGOTTAMA PUSHKARA) Mo:AI"
    nadi: str = ""            # v15.1: "Neer (1.05x)"

    def time_str(self) -> str:
        return self.timestamp.strftime('%H:%M')


@dataclass
class WindowScore:
    start: time
    end: time
    score: float
    direction: Direction
    signals: list[TrendChangeSignal] = field(default_factory=list)

    def time_range_str(self) -> str:
        return f"{self.start.strftime('%H:%M')}–{self.end.strftime('%H:%M')}"


@dataclass
class DayChartSignature:
    day_lord: str
    moon_sign: str
    moon_star: str
    opening_sublord: str
    moon_speed: float
    day_bias_score: float
    day_bias_label: str
    moon_affliction_gate: str
    hora_slots: list[HoraSlot]
    # v15 / v15.1 layers (filled by kp_layers.enrich_report; empty if it fails)
    rahu_windows: list[Any] = field(default_factory=list)
    rahu_windows_note: str = ""
    vargottama_note: str = ""
    navamsa: dict[str, Any] | None = None
    nadi: dict[str, Any] | None = None


@dataclass
class KPIntradayReport:
    trading_day: date
    instrument: str
    market: str
    ayanamsa: str
    source_file: str
    generated_at: datetime
    brand: str

    day_signature: DayChartSignature
    regime_shifts: list[RegimeShift]
    trend_changes: list[TrendChangeSignal]
    bullish_windows: list[WindowScore]
    bearish_windows: list[WindowScore]
    strongest_bullish: WindowScore | None
    strongest_bearish: WindowScore | None
    exhaustion_warnings: list[str]

    config: dict[str, Any] = field(default_factory=dict)
    data_quality: dict[str, Any] = field(default_factory=dict)


# NSE session bounds used by the cumulative path builder.
NSE_MARKET_OPEN = time(9, 15)
NSE_MARKET_CLOSE = time(15, 30)

# Composite scoring weights for the predictive intraday path.
HORA_QUALITY_SCORE = {
    "Sluggish": -0.5,
    "Neutral": 0.0,
    "Fruitful": 0.5,
    "Aggressive": 0.8,
    "Volatile": 0.0,
}
REGIME_SHIFT_DELTA = 1.5
WINDOW_VOTE_DELTA = 1.0

MALEFIC_HORAS = ("Mars", "Saturn", "Rahu", "Ketu")
BENEFIC_HORAS = ("Moon", "Jupiter")


def build_cumulative_path(
    report: KPIntradayReport, step_minutes: int = 60
) -> list[dict[str, Any]]:
    """Build a cumulative composite score path from a KP intraday report.

    Aggregates hora quality, regime shifts, and window scores into a
    cumulative composite score per interval (default hourly). Each point
    carries the hora lord, DL-hora / Dahan / Chand-Vat flags, and signal
    markers, ready for chart.js / lightweight-charts consumption.
    """
    if step_minutes <= 0:
        raise ValueError("step_minutes must be a positive number of minutes")

    ds = report.day_signature
    hora_slots = list(getattr(ds, "hora_slots", []) or [])
    hora_by_start = {hs.start: hs for hs in hora_slots}
    day_lord = ds.day_lord

    regime_by_time = {rs.timestamp: rs for rs in report.regime_shifts}
    signals_by_time: dict[time, list[TrendChangeSignal]] = {}
    for tc in report.trend_changes:
        signals_by_time.setdefault(tc.timestamp, []).append(tc)

    windows = list(report.bullish_windows) + list(report.bearish_windows)

    def _slot_at(t: time) -> HoraSlot | None:
        slot = hora_by_start.get(t)
        if slot is None:
            for hs in hora_slots:
                if hs.start <= t < hs.end:
                    return hs
        return slot

    series: list[dict[str, Any]] = []
    cumulative = 0.0
    current = datetime.combine(report.trading_day, NSE_MARKET_OPEN)
    end_dt = datetime.combine(report.trading_day, NSE_MARKET_CLOSE)

    while current <= end_dt:
        t = current.time()
        clock = t.strftime("%H:%M")

        slot = _slot_at(t)
        hora_quality = HORA_QUALITY_SCORE.get(slot.quality.value, 0.0) if slot else 0.0
        hora_lord = slot.lord if slot else None

        regime_delta = 0.0
        rs = regime_by_time.get(t)
        if rs is not None:
            if rs.direction == Direction.BULLISH:
                regime_delta = REGIME_SHIFT_DELTA
            elif rs.direction == Direction.BEARISH:
                regime_delta = -REGIME_SHIFT_DELTA

        window_delta = 0.0
        for w in windows:
            if w.start <= t < w.end:
                if w.direction == Direction.BULLISH:
                    window_delta += WINDOW_VOTE_DELTA
                elif w.direction == Direction.BEARISH:
                    window_delta -= WINDOW_VOTE_DELTA

        score = round(hora_quality + regime_delta + window_delta, 3)
        cumulative = round(cumulative + score, 3)

        dl_hora = bool(hora_lord) and hora_lord == day_lord and hora_quality > 0
        dahan = hora_lord in MALEFIC_HORAS and hora_quality < 0
        chand_vat = hora_lord in BENEFIC_HORAS and hora_quality >= 0

        markers = [{
            "grade": s.grade.value,
            "direction": s.direction.value,
            "score": s.score,
        } for s in signals_by_time.get(t, [])]

        series.append({
            "time": clock,
            "cumulative": cumulative,
            "score": score,
            "hora_lord": hora_lord,
            "hora_quality": hora_quality,
            "regime_delta": regime_delta,
            "window_delta": round(window_delta, 3),
            "dl_hora": bool(dl_hora),
            "dahan": bool(dahan),
            "chand_vat": bool(chand_vat),
            "markers": markers,
        })

        current += timedelta(minutes=step_minutes)

    return series


def report_to_dict(report: KPIntradayReport) -> dict[str, Any]:
    """Serialize a KPIntradayReport into the JSON shape the web UI expects.

    Enum fields become their string values; time objects become "HH:MM".
    """
    def _window(w: WindowScore | None) -> dict[str, Any] | None:
        if not w:
            return None
        return {
            "time_range": w.time_range_str(),
            "score": round(w.score, 2),
            "direction": w.direction.value,
        }

    ds = report.day_signature
    return {
        "trading_day": report.trading_day.isoformat(),
        "instrument": report.instrument,
        "market": report.market,
        "ayanamsa": report.ayanamsa,
        "brand": report.brand,
        "day_signature": {
            "day_lord": ds.day_lord,
            "moon_sign": ds.moon_sign,
            "moon_star": ds.moon_star,
            "opening_sublord": ds.opening_sublord,
            "moon_speed": ds.moon_speed,
            "day_bias_score": ds.day_bias_score,
            "day_bias_label": ds.day_bias_label,
            "moon_affliction_gate": ds.moon_affliction_gate,
            "hora_slots": [{
                "time_range": hs.time_range_str(),
                "lord": hs.lord,
                "quality": hs.quality.value,
                "base_quality": hs.base_quality,
                "aspects_received": hs.aspects_received,
                "interpretation": hs.interpretation,
                "aspect_notes": hs.aspect_notes,
            } for hs in ds.hora_slots],
        },
        "regime_shifts": [{
            "time": rs.time_str(),
            "planet": rs.planet,
            "old_sublord": rs.old_sublord,
            "new_sublord": rs.new_sublord,
            "house_set_strength": rs.house_set_strength,
            "regime_label": rs.regime_label,
            "direction": rs.direction.value,
        } for rs in report.regime_shifts],
        "trend_changes": [{
            "time": tc.time_str(),
            "grade": tc.grade.value,
            "direction": tc.direction.value,
            "trigger": tc.trigger,
            "asc_sub_house_set": tc.asc_sub_house_set,
            "hora_lord": tc.hora_lord,
            "score": tc.score,
            "notes": tc.notes,
        } for tc in report.trend_changes],
        "strongest_bullish": _window(report.strongest_bullish),
        "strongest_bearish": _window(report.strongest_bearish),
        "exhaustion_warnings": list(report.exhaustion_warnings),
        "source_file": report.source_file,
        "data_quality": report.data_quality,
    }


# Sidereal star order; each spans 13deg20', so it can only sit in the one or
# two signs that arc covers. Used to catch fabricated KP files.
_KP_STARS = [
    'Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra', 'Punarvasu',
    'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni', 'Hasta',
    'Chitra', 'Swati', 'Vishakha', 'Anuradha', 'Jyeshtha', 'Mula', 'Purva Ashadha',
    'Uttara Ashadha', 'Shravana', 'Dhanishta', 'Shatabhisha', 'Purva Bhadrapada',
    'Uttara Bhadrapada', 'Revati',
]
_KP_SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra',
             'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
_STAR_SIGNS = {
    star: {_KP_SIGNS[int(i * 40 / 3 // 30)], _KP_SIGNS[int((i * 40 / 3 + 40 / 3 - 1e-9) // 30)]}
    for i, star in enumerate(_KP_STARS)
}
# Real ephemeris output has zero mismatches; allow a little for hand edits.
SYNTHETIC_THRESHOLD_PCT = 5.0


def assess_kp_data(rows: list[dict]) -> dict[str, Any]:
    """Check every planet row's star against its sign.

    A star can only fall in the sign(s) its 13deg20' arc covers. Random sample
    files (generate_sample_kp_csv) break this on ~89% of rows, so a high
    mismatch rate means the file is not ephemeris data and any report built
    from it is noise.
    """
    checked = bad = 0
    for r in rows:
        allowed = _STAR_SIGNS.get((r.get('star') or '').strip())
        if allowed is None:
            continue
        checked += 1
        if (r.get('sign') or '').strip() not in allowed:
            bad += 1
    pct = round(100.0 * bad / checked, 1) if checked else 0.0
    synthetic = checked > 0 and pct > SYNTHETIC_THRESHOLD_PCT
    return {
        "rows_checked": checked,
        "impossible_rows": bad,
        "impossible_pct": pct,
        "synthetic": synthetic,
        "message": (
            f"{pct}% of rows place a nakshatra in a sign it cannot occupy: this "
            "KP file is not real ephemeris data. Signals below are random."
            if synthetic else ""
        ),
    }


class KPDataParser:
    """Parse KP precomputed CSV data into structured objects."""

    REQUIRED_COLUMNS = [
        'timestamp', 'planet', 'sign', 'star', 'sublord', 'sub_sublord',
        'house_set', 'house_set_strength', 'moon_longitude', 'moon_speed',
        'asc_sign', 'asc_star', 'asc_sublord', 'asc_sub_sublord',
        'hora_lord', 'day_lord', 'aspects'
    ]

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    def parse_csv(self, filepath: Path) -> list[dict]:
        """Parse KP data CSV file."""
        rows = []
        with open(filepath, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        return rows

    def parse_day_data(self, rows: list[dict], target_date: date) -> dict[str, Any]:
        """Extract and structure data for a specific trading day."""
        day_rows = [r for r in rows if self._parse_date(r.get('timestamp', '')) == target_date]
        if not day_rows and rows:
            dates_in_file = sorted(list(set(self._parse_date(r.get('timestamp', '')) for r in rows if self._parse_date(r.get('timestamp', '')))))
            if dates_in_file:
                nearest_date = min(dates_in_file, key=lambda d: abs((d - target_date).days))
                day_rows = [r for r in rows if self._parse_date(r.get('timestamp', '')) == nearest_date]
        if not day_rows:
            raise ValueError(f"No data found for {target_date}")

        first = day_rows[0]
        day_lord = first.get('day_lord', '')

        moon_rows = [r for r in day_rows if r.get('planet') == 'Moon']
        moon_sign = moon_rows[0].get('sign', '') if moon_rows else ''
        moon_star = moon_rows[0].get('star', '') if moon_rows else ''
        moon_speed = float(moon_rows[0].get('moon_speed', 0)) if moon_rows else 0.0

        asc_rows = [r for r in day_rows if r.get('planet') == 'Ascendant']
        opening_sublord = asc_rows[0].get('sublord', '') if asc_rows else ''

        hora_rows = [r for r in day_rows if r.get('hora_lord')]
        hora_slots = []
        for hr in hora_rows:
            ts = self._parse_time(hr.get('timestamp', ''))
            if ts:
                hora_slots.append({
                    'time': ts,
                    'lord': hr.get('hora_lord', ''),
                    'aspects': hr.get('aspects', '')
                })

        return {
            'day_lord': day_lord,
            'moon_sign': moon_sign,
            'moon_star': moon_star,
            'opening_sublord': opening_sublord,
            'moon_speed': moon_speed,
            'hora_slots': hora_slots,
            'all_rows': day_rows
        }

    def _parse_date(self, ts_str: str) -> date | None:
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00')).date()
        except:
            return None

    def _parse_time(self, ts_str: str) -> time | None:
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00')).time()
        except:
            return None


class KPRuleEngine:
    """KP Astrology rule engine for intraday predictions."""

    RULE_WEIGHTS = {
        'hora_weight': 0.3,
        'house_set_weight': 0.4,
        'moon_sub_weight': 0.2,
        'asc_sub_weight': 0.1,
    }

    SIGNAL_THRESHOLDS = {
        'tier1_min_score': 5.0,
        'tier2_min_score': 3.0,
        'pure_set_min_score': 7.0,
        'regime_shift_min_strength': 1.5,
    }

    HORA_QUALITY_MAP = {
        'Sun': {'base': HoraQuality.AGGRESSIVE, 'nature': 'malefic'},
        'Moon': {'base': HoraQuality.FRUITFUL, 'nature': 'benefic'},
        'Mars': {'base': HoraQuality.AGGRESSIVE, 'nature': 'malefic'},
        'Mercury': {'base': HoraQuality.NEUTRAL, 'nature': 'neutral'},
        'Jupiter': {'base': HoraQuality.FRUITFUL, 'nature': 'benefic'},
        'Venus': {'base': HoraQuality.FRUITFUL, 'nature': 'benefic'},
        'Saturn': {'base': HoraQuality.SLUGGISH, 'nature': 'malefic'},
        'Rahu': {'base': HoraQuality.VOLATILE, 'nature': 'malefic'},
        'Ketu': {'base': HoraQuality.VOLATILE, 'nature': 'malefic'},
    }

    PLANET_NATURE = {
        'Sun': 'malefic', 'Moon': 'benefic', 'Mars': 'malefic',
        'Mercury': 'neutral', 'Jupiter': 'benefic', 'Venus': 'benefic',
        'Saturn': 'malefic', 'Rahu': 'malefic', 'Ketu': 'malefic'
    }

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.weights = {**self.RULE_WEIGHTS, **self.config.get('weights', {})}
        self.thresholds = {**self.SIGNAL_THRESHOLDS, **self.config.get('thresholds', {})}

    def compute_day_bias(self, day_lord: str, moon_star_lord: str) -> tuple[float, str]:
        """Compute day-level bias from Day Lord + Moon Star Lord."""
        dl_nature = self.PLANET_NATURE.get(day_lord, 'neutral')
        ms_nature = self.PLANET_NATURE.get(moon_star_lord, 'neutral')

        score = 0.0
        if dl_nature == 'benefic':
            score += 1.0
        elif dl_nature == 'malefic':
            score -= 1.0
        if ms_nature == 'benefic':
            score += 1.0
        elif ms_nature == 'malefic':
            score -= 1.0

        if score > 0.5:
            label = "bullish"
        elif score < -0.5:
            label = "bearish"
        else:
            label = "neutral"

        return score, f"Day-level bias (Day Lord + Moon Star Lord): {score:+.2f} -> {label}."

    def evaluate_moon_affliction_gate(self, moon_sign: str, moon_star: str, aspects: str) -> str:
        """Rule A-14: Moon Affliction Gate."""
        afflicted = False
        reasons = []

        malefic_aspects = ['Saturn', 'Mars', 'Rahu', 'Ketu']
        for ma in malefic_aspects:
            if ma in aspects:
                afflicted = True
                reasons.append(f"{ma} aspect")

        if moon_sign in ['Scorpio', 'Capricorn']:
            afflicted = True
            reasons.append(f"Moon in {moon_sign}")

        if afflicted:
            return f"Moon Affliction Gate (Rule A-14): FAILED ({'; '.join(reasons)})."
        return "Moon Affliction Gate (Rule A-14): PASSED."

    def evaluate_hora_quality(self, hora_lord: str, aspects: str) -> tuple[HoraQuality, str, str, str, str]:
        """Evaluate hora quality modified by aspects."""
        base_info = self.HORA_QUALITY_MAP.get(hora_lord, {'base': HoraQuality.NEUTRAL, 'nature': 'neutral'})
        base_quality = base_info['base'].value
        quality = base_info['base']
        notes = []

        benefic_aspects = ['Jupiter', 'Venus', 'Mercury']
        malefic_aspects = ['Saturn', 'Mars', 'Rahu', 'Ketu']

        aspects_received_list = []
        if aspects:
            for p in aspects.split(','):
                p_clean = p.strip()
                if p_clean and p_clean not in aspects_received_list:
                    aspects_received_list.append(p_clean)

        for ba in benefic_aspects:
            if ba in aspects:
                if ba == 'Jupiter':
                    notes.append("Jupiter aspect -> supported / expansive")
                elif ba == 'Venus':
                    notes.append("Venus aspect -> orderly / supportive")
                elif ba == 'Mercury':
                    notes.append("Mercury aspect -> active / adaptive")
                if quality == HoraQuality.SLUGGISH:
                    quality = HoraQuality.NEUTRAL
                elif quality == HoraQuality.NEUTRAL:
                    quality = HoraQuality.FRUITFUL

        for ma in malefic_aspects:
            if ma in aspects:
                if ma == 'Saturn':
                    notes.append("Saturn aspect -> delay / pressure")
                elif ma == 'Mars':
                    notes.append("Mars aspect -> volatility / aggression")
                elif ma in ['Rahu', 'Ketu']:
                    notes.append(f"{ma} aspect -> distortion / unpredictability")
                if quality == HoraQuality.FRUITFUL:
                    quality = HoraQuality.NEUTRAL
                elif quality == HoraQuality.NEUTRAL:
                    quality = HoraQuality.SLUGGISH

        aspects_received_str = ", ".join(aspects_received_list) if aspects_received_list else "None"
        interpretation_str = "; ".join(notes) if notes else f"Base {base_quality} rhythm maintained"
        aspect_notes_str = f"Lord receives: {aspects_received_str} ({interpretation_str})"
        return quality, base_quality, aspects_received_str, interpretation_str, aspect_notes_str

    def detect_regime_shifts(self, day_rows: list[dict]) -> list[RegimeShift]:
        """Detect Moon sub-lord and Ascendant sub-lord changes (Rule A-11/A-12)."""
        shifts = []

        moon_rows = [r for r in day_rows if r.get('planet') == 'Moon']
        asc_rows = [r for r in day_rows if r.get('planet') == 'Ascendant']

        for i in range(1, len(moon_rows)):
            prev = moon_rows[i-1]
            curr = moon_rows[i]
            if prev.get('sublord') != curr.get('sublord'):
                ts = self._parse_time(curr.get('timestamp', ''))
                old_sub = prev.get('sublord', '')
                new_sub = curr.get('sublord', '')
                hs_strength = float(curr.get('house_set_strength', 0))

                regime = self._classify_regime(new_sub, hs_strength)
                direction = Direction.BULLISH if 'buy' in regime.lower() else Direction.BEARISH if 'sell' in regime.lower() else Direction.NEUTRAL

                shifts.append(RegimeShift(
                    timestamp=ts,
                    planet='Moon',
                    old_sublord=old_sub,
                    new_sublord=new_sub,
                    house_set_strength=hs_strength,
                    regime_label=regime,
                    direction=direction
                ))

        for i in range(1, len(asc_rows)):
            prev = asc_rows[i-1]
            curr = asc_rows[i]
            if prev.get('sublord') != curr.get('sublord'):
                ts = self._parse_time(curr.get('timestamp', ''))
                old_sub = prev.get('sublord', '')
                new_sub = curr.get('sublord', '')
                hs_strength = float(curr.get('house_set_strength', 0))

                regime = self._classify_regime(new_sub, hs_strength)
                direction = Direction.BULLISH if 'buy' in regime.lower() else Direction.BEARISH if 'sell' in regime.lower() else Direction.NEUTRAL

                shifts.append(RegimeShift(
                    timestamp=ts,
                    planet='Ascendant',
                    old_sublord=old_sub,
                    new_sublord=new_sub,
                    house_set_strength=hs_strength,
                    regime_label=regime,
                    direction=direction
                ))

        shifts.sort(key=lambda x: x.timestamp)
        return shifts

    def _classify_regime(self, sublord: str, hs_strength: float) -> str:
        nature = self.PLANET_NATURE.get(sublord, 'neutral')
        if nature == 'benefic' and hs_strength > 1.0:
            return "buy-on-dip"
        elif nature == 'malefic' and hs_strength > 1.0:
            return "sell-on-rise"
        elif nature == 'benefic':
            return "cautious buy-on-dip"
        elif nature == 'malefic':
            return "cautious sell-on-rise"
        return "neutral/range"

    def detect_trend_changes(self, day_rows: list[dict], regime_shifts: list[RegimeShift]) -> list[TrendChangeSignal]:
        """Detect all trend change signals: pure-set alarms, regime shifts, tier-1, tier-2."""
        signals = []

        asc_rows = [r for r in day_rows if r.get('planet') == 'Ascendant']

        for i in range(1, len(asc_rows)):
            prev = asc_rows[i-1]
            curr = asc_rows[i]

            ts = self._parse_time(curr.get('timestamp', ''))
            if not ts:
                continue

            old_sub = prev.get('sublord', '')
            new_sub = curr.get('sublord', '')
            hs = curr.get('house_set', '')
            hs_strength = float(curr.get('house_set_strength', 0))

            hora_lord = curr.get('hora_lord', '')
            aspects = curr.get('aspects', '')

            if old_sub != new_sub:
                trigger = f"Asc sub change {old_sub}->{new_sub}"
                grade = self._grade_signal(hs_strength, True, aspects)
                direction = self._direction_from_sublord(new_sub, hs_strength)
                score = self._score_signal(hs_strength, aspects, hora_lord, True)

                signals.append(TrendChangeSignal(
                    timestamp=ts,
                    grade=grade,
                    direction=direction,
                    trigger=trigger,
                    asc_sub_house_set=hs,
                    hora_lord=hora_lord,
                    score=score
                ))

        for rs in regime_shifts:
            if rs.planet == 'Moon':
                ts = rs.timestamp
                trigger = f"Moon sub change {rs.old_sublord}->{rs.new_sublord}"
                if rs.planet == 'Ascendant':
                    trigger += f"; Asc sub change {rs.old_sublord}->{rs.new_sublord}"

                grade = SignalGrade.REGIME_SHIFT
                direction = rs.direction
                score = rs.house_set_strength * 2

                signals.append(TrendChangeSignal(
                    timestamp=ts,
                    grade=grade,
                    direction=direction,
                    trigger=trigger,
                    asc_sub_house_set=str(int(rs.house_set_strength)),
                    hora_lord=self._get_hora_at_time(day_rows, ts),
                    score=score
                ))

        pure_set_signals = self._detect_pure_set_alarms(day_rows, regime_shifts)
        signals.extend(pure_set_signals)

        signals.sort(key=lambda x: x.timestamp)
        return signals

    def _detect_pure_set_alarms(self, day_rows: list[dict], regime_shifts: list[RegimeShift]) -> list[TrendChangeSignal]:
        """Detect pure-set alarms (counter-regime)."""
        signals = []
        asc_rows = [r for r in day_rows if r.get('planet') == 'Ascendant']

        regime_times = {rs.timestamp: rs.direction for rs in regime_shifts if rs.planet == 'Moon'}

        for i in range(1, len(asc_rows)):
            prev = asc_rows[i-1]
            curr = asc_rows[i]

            ts = self._parse_time(curr.get('timestamp', ''))
            if not ts:
                continue

            old_sub = prev.get('sublord', '')
            new_sub = curr.get('sublord', '')
            hs = curr.get('house_set', '')
            hs_strength = float(curr.get('house_set_strength', 0))

            if old_sub == new_sub:
                continue

            current_regime = Direction.NEUTRAL
            for rt, rd in regime_times.items():
                if rt <= ts:
                    current_regime = rd

            signal_direction = self._direction_from_sublord(new_sub, hs_strength)

            if current_regime != Direction.NEUTRAL and signal_direction != current_regime:
                grade = SignalGrade.COUNTER_REGIME
                trigger = f"Asc sub change {old_sub}->{new_sub} (counter-regime)"
                score = self._score_signal(hs_strength, curr.get('aspects', ''), curr.get('hora_lord', ''), False) * 0.7

                signals.append(TrendChangeSignal(
                    timestamp=ts,
                    grade=grade,
                    direction=signal_direction,
                    trigger=trigger,
                    asc_sub_house_set=hs,
                    hora_lord=curr.get('hora_lord', ''),
                    score=score,
                    notes="Counter-regime: reduced conviction, requires price confirmation"
                ))
            elif hs_strength >= self.thresholds['pure_set_min_score']:
                grade = SignalGrade.PURE_SET_ALARM
                trigger = f"Asc sub change {old_sub}->{new_sub}"
                direction = self._direction_from_sublord(new_sub, hs_strength)
                score = self._score_signal(hs_strength, curr.get('aspects', ''), curr.get('hora_lord', ''), True)

                signals.append(TrendChangeSignal(
                    timestamp=ts,
                    grade=grade,
                    direction=direction,
                    trigger=trigger,
                    asc_sub_house_set=hs,
                    hora_lord=curr.get('hora_lord', ''),
                    score=score
                ))

        return signals

    def _grade_signal(self, hs_strength: float, is_regime_aligned: bool, aspects: str) -> SignalGrade:
        if hs_strength >= self.thresholds['pure_set_min_score']:
            return SignalGrade.PURE_SET_ALARM
        elif hs_strength >= self.thresholds['tier1_min_score'] and is_regime_aligned:
            return SignalGrade.TIER_1
        elif hs_strength >= self.thresholds['tier2_min_score']:
            return SignalGrade.TIER_2
        return SignalGrade.TIER_2

    def _direction_from_sublord(self, sublord: str, hs_strength: float) -> Direction:
        nature = self.PLANET_NATURE.get(sublord, 'neutral')
        if nature == 'benefic' and hs_strength > 0:
            return Direction.BULLISH
        elif nature == 'malefic' and hs_strength > 0:
            return Direction.BEARISH
        return Direction.NEUTRAL

    def _score_signal(self, hs_strength: float, aspects: str, hora_lord: str, regime_aligned: bool) -> float:
        score = hs_strength * self.weights['house_set_weight']

        hora_quality, _, _, _, _ = self.evaluate_hora_quality(hora_lord, aspects)
        hora_score = {'Sluggish': -1, 'Neutral': 0, 'Fruitful': 1, 'Aggressive': 1.5, 'Volatile': 0.5}.get(hora_quality.value, 0)
        score += hora_score * self.weights['hora_weight']

        if regime_aligned:
            score += 1.0

        return round(score, 2)

    def _get_hora_at_time(self, day_rows: list[dict], ts: time) -> str:
        for r in day_rows:
            rt = self._parse_time(r.get('timestamp', ''))
            if rt and rt == ts and r.get('hora_lord'):
                return r.get('hora_lord', '')
        return ''

    def score_windows(self, signals: list[TrendChangeSignal], day_rows: list[dict]) -> tuple[list[WindowScore], list[WindowScore]]:
        """Score candidate windows from signals."""
        bullish_windows = []
        bearish_windows = []

        window_signals = {}
        for s in signals:
            if s.grade in [SignalGrade.PURE_SET_ALARM, SignalGrade.TIER_1, SignalGrade.REGIME_SHIFT]:
                window_start = self._window_start(s.timestamp)
                key = window_start
                if key not in window_signals:
                    window_signals[key] = []
                window_signals[key].append(s)

        for ws, sigs in window_signals.items():
            window_end = (datetime.combine(date.today(), ws) + timedelta(minutes=15)).time()
            bullish_score = sum(s.score for s in sigs if s.direction == Direction.BULLISH)
            bearish_score = sum(s.score for s in sigs if s.direction == Direction.BEARISH)

            if bullish_score > 0:
                bullish_windows.append(WindowScore(
                    start=ws, end=window_end, score=bullish_score,
                    direction=Direction.BULLISH, signals=[s for s in sigs if s.direction == Direction.BULLISH]
                ))
            if bearish_score > 0:
                bearish_windows.append(WindowScore(
                    start=ws, end=window_end, score=abs(bearish_score),
                    direction=Direction.BEARISH, signals=[s for s in sigs if s.direction == Direction.BEARISH]
                ))

        bullish_windows.sort(key=lambda x: x.score, reverse=True)
        bearish_windows.sort(key=lambda x: x.score, reverse=True)

        return bullish_windows, bearish_windows

    def _window_start(self, ts: time) -> time:
        minute = ts.minute
        window_minute = (minute // 15) * 15
        return time(ts.hour, window_minute)

    def identify_exhaustion_warnings(self, bullish_windows: list[WindowScore], bearish_windows: list[WindowScore]) -> list[str]:
        """Identify mixed-house reversal risks."""
        warnings = []

        if bullish_windows and bearish_windows:
            top_bull = bullish_windows[0]
            top_bear = bearish_windows[0]

            if abs(top_bull.score - top_bear.score) < 2.0:
                warnings.append("Mixed-house reversal risk: bullish and bearish windows have similar strength.")

            for w in bullish_windows[:3]:
                houses = set()
                for s in w.signals:
                    hs = s.asc_sub_house_set
                    for h in hs.split(','):
                        houses.add(h.strip())
                if len(houses) >= 3:
                    warnings.append(f"Exhaustion warning at {w.time_range_str()}: mixed houses {', '.join(sorted(houses))} -> reversal risk.")

        return warnings

    def _parse_time(self, ts_str: str) -> time | None:
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00')).time()
        except:
            return None


class KPReportGenerator:
    """Generate formatted KP Intraday Prediction Reports matching the exact Astro Quant Research Initiative template."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.brand = self.config.get('brand', 'Astro Quant Research Initiative | Trading Bramha Consulting')

    def generate_html(self, report: KPIntradayReport) -> str:
        """Generate HTML report."""
        html = []
        html.append(self._render_header(report))
        html.append(self._render_section1(report))
        html.append(self._render_section2(report))
        html.append(self._render_section3(report))
        html.append(self._render_section4(report))
        html.append(self._render_section5(report))
        html.append(self._render_section6(report))
        return '\n'.join(html)

    def _render_header(self, report: KPIntradayReport) -> str:
        lines = []
        lines.append('<div class="kp-report">')
        lines.append('<div class="kp-title-block">')
        lines.append('<h1 class="kp-title">KP INTRADAY TREND CHANGE PREDICTION REPORT</h1>')
        lines.append(f'<div class="kp-meta-line"><strong>Trading Day:</strong> {report.trading_day.isoformat()}</div>')
        lines.append(f'<div class="kp-meta-line"><strong>{report.instrument}</strong> &bull; {report.market} &bull; {report.ayanamsa}</div>')
        lines.append("<div class=\"kp-brand\">" + report.brand + "</div>")
        lines.append('</div>')
        lines.append('<hr class="kp-divider">')
        return '\n'.join(lines)

    def _render_section1(self, report: KPIntradayReport) -> str:
        ds = report.day_signature
        lines = []
        lines.append('<section class="kp-section">')
        lines.append('<h2>SECTION 1 &mdash; DAY CHART SIGNATURE</h2>')

        lines.append('<table class="kp-table kp-signature-table">')
        lines.append('<tr><th>Parameter</th><th>Value</th></tr>')
        lines.append(f'<tr><td>Day Lord</td><td><strong>{ds.day_lord}</strong></td></tr>')
        lines.append(f'<tr><td>Moon Sign, Star, Opening Sub</td><td><strong>{ds.moon_sign}, {ds.moon_star}, {ds.opening_sublord} sub</strong></td></tr>')
        lines.append(f'<tr><td>Moon Speed</td><td><strong>{ds.moon_speed:.4f}&deg;/day</strong></td></tr>')
        lines.append(f'<tr><td>Day-Level Bias</td><td><strong>{ds.day_bias_label}</strong></td></tr>')
        lines.append(f'<tr><td>Moon Affliction Gate (Rule A-14)</td><td><strong>{ds.moon_affliction_gate}</strong></td></tr>')
        if getattr(ds, 'rahu_windows_note', ''):
            lines.append(f'<tr><td>Rahu Moon-sub windows (Rule A-13)</td><td>{ds.rahu_windows_note}</td></tr>')
        if getattr(ds, 'vargottama_note', ''):
            lines.append(f'<tr><td>Vargottama Moon (Rule C-5)</td><td>{ds.vargottama_note}</td></tr>')
        lines.append('</table>')

        lines.append('<h3>Hora Timeline Table</h3>')
        lines.append('<table class="kp-table kp-hora-table">')
        lines.append('<thead><tr><th>Time Range</th><th>Hora Lord</th><th>Base Quality</th><th>Aspects Received</th><th>Interpretation</th></tr></thead>')
        lines.append('<tbody>')
        for hs in ds.hora_slots:
            base_q = getattr(hs, 'base_quality', hs.quality.value)
            asp_rec = getattr(hs, 'aspects_received', 'None')
            interp = getattr(hs, 'interpretation', hs.aspect_notes)
            lines.append(f'<tr><td>{hs.time_range_str()}</td><td><strong>{hs.lord}</strong></td><td class="hora-{base_q.lower()}">{base_q}</td><td>{asp_rec}</td><td>{interp}</td></tr>')
        lines.append('</tbody>')
        lines.append('</table>')

        lines.append('<p class="kp-rule-note"><strong>Rule Note:</strong> Base hora quality is modified by aspects (weight 0.3). Benefic aspects (Jupiter, Venus, Mercury) upgrade quality; malefic aspects (Saturn, Mars, Rahu, Ketu) downgrade it. Do not treat hora as standalone signal.</p>')

        nav = getattr(ds, 'navamsa', None)
        if nav and 'error' not in nav:
            lines.append('<h3>1b. Navamsa (D-9) Strength Layer (v15)</h3>')
            lines.append('<table class="kp-table kp-signature-table">')
            for k, v in nav.get('placements', {}).items():
                lines.append(f'<tr><td>{k}</td><td><strong>{v}</strong></td></tr>')
            lines.append('</table>')
            for k in ('n3_text', 'n5_text', 'n6_text'):
                if nav.get(k):
                    lines.append(f'<p class="kp-rule-note">{nav[k]}</p>')
        nadi = getattr(ds, 'nadi', None)
        if nadi:
            lines.append('<h3>1c. SBC Nadi Classification (v15.1)</h3>')
            for ln in (nadi.get('text') or '').split('\n'):
                lines.append(f'<p class="kp-rule-note">{ln}</p>')
        lines.append('</section>')
        return '\n'.join(lines)

    def _render_section2(self, report: KPIntradayReport) -> str:
        lines = []
        lines.append('<section class="kp-section">')
        lines.append('<h2>SECTION 2 &mdash; MASTER REGIME SHIFTS (Moon Sub-Lord, Rule A-11/A-12)</h2>')

        if not report.regime_shifts:
            lines.append('<p>No regime shifts detected for this session.</p>')
        else:
            for rs in report.regime_shifts:
                lines.append('<div class="kp-regime-shift">')
                lines.append(f'<div class="regime-time"><strong>{rs.time_str()}</strong></div>')
                lines.append('<div class="regime-detail">')
                lines.append(f'<span>{rs.planet} sub change: <strong>{rs.old_sublord} &rarr; {rs.new_sublord}</strong></span> &bull; ')
                lines.append(f'<span>House-set strength: <strong>{rs.house_set_strength:+.1f}</strong></span> &bull; ')
                lines.append(f'<span>Post-shift regime: <strong class="regime-tag {rs.direction.value.lower()}">{rs.regime_label}</strong></span>')
                lines.append('</div>')
                lines.append('</div>')
        lines.append('</section>')
        return '\n'.join(lines)

    def _render_section3(self, report: KPIntradayReport) -> str:
        lines = []
        lines.append('<section class="kp-section">')
        lines.append('<h2>SECTION 3 &mdash; PREDICTIVE INTRADAY PATH</h2>')
        lines.append('<div class="kp-path-box">')
        lines.append('<p>Orange markers = Tier-1 / regime-shift timestamps. Path is directional shape, not price target. Windows are candidates until price confirms.</p>')
        lines.append('</div>')
        lines.append('</section>')
        return '\n'.join(lines)

    def _render_section4(self, report: KPIntradayReport) -> str:
        lines = []
        lines.append('<section class="kp-section">')
        lines.append('<h2>SECTION 4 &mdash; TREND CHANGE TIMING TABLE</h2>')

        if not report.trend_changes:
            lines.append('<p>No trend change signals detected.</p>')
        else:
            lines.append('<table class="kp-table kp-signals-table">')
            lines.append('<thead><tr><th>Time</th><th>Grade</th><th>Direction</th><th>Trigger (Rule A-8/A-11)</th><th>Asc Sub House-Set</th><th>Hora</th><th>Navamsa D-9</th><th>Nadi</th></tr></thead>')
            lines.append('<tbody>')
            for tc in report.trend_changes:
                grade_class = tc.grade.value.replace('-', '').replace(' ', '').lower()
                lines.append(f'<tr class="grade-{grade_class}">')
                lines.append(f'<td>{tc.time_str()}</td>')
                lines.append(f'<td><span class="badge {grade_class}">{tc.grade.value}</span></td>')
                lines.append(f'<td class="dir-{tc.direction.value.lower()}">{tc.direction.value}</td>')
                lines.append(f'<td>{tc.trigger}</td>')
                lines.append(f'<td>{tc.asc_sub_house_set}</td>')
                lines.append(f'<td>{tc.hora_lord}</td>')
                lines.append(f'<td>{getattr(tc, "navamsa_d9", "")}</td>')
                lines.append(f'<td>{getattr(tc, "nadi", "")}</td>')
                lines.append('</tr>')
            lines.append('</tbody>')
            lines.append('</table>')

        lines.append('<h3>Counter-Regime Pure-Set Alarms (v12)</h3>')
        counter_regime = [s for s in report.trend_changes if s.grade == SignalGrade.COUNTER_REGIME]
        lines.append('<div class="kp-counter-regime-box">')
        lines.append('<p><strong>Counter-regime pure-set alarms (v12):</strong> The following pure-set alarms fire against the active Moon sub-lord regime. Treat as early reversal warnings &mdash; trade ONLY on price confirmation with reduced position size (max 50% normal).</p>')
        if counter_regime:
            for cr in counter_regime:
                lines.append(f'<div class="kp-counter-regime">{cr.time_str()} | {cr.grade.value} | {cr.direction.value} | {cr.trigger} | {cr.asc_sub_house_set} | {cr.hora_lord}</div>')
        else:
            lines.append('<p class="kp-empty">No counter-regime pure-set alarms detected for this session.</p>')
        lines.append('</div>')

        lines.append('</section>')
        return '\n'.join(lines)

    def _render_section5(self, report: KPIntradayReport) -> str:
        lines = []
        lines.append('<section class="kp-section">')
        lines.append('<h2>SECTION 5 &mdash; INTRADAY TRADING VIEW</h2>')

        lines.append('<div class="kp-windows-grid">')
        if report.strongest_bullish:
            lines.append(f'<div class="kp-window bullish"><span class="window-title">Strongest Bullish Candidate Window</span><strong class="window-time">{report.strongest_bullish.time_range_str()}</strong><span class="window-score">Peak Score: +{report.strongest_bullish.score:.2f}</span></div>')
        else:
            lines.append('<div class="kp-window neutral"><span class="window-title">Strongest Bullish Candidate Window</span><strong>None active</strong></div>')

        if report.strongest_bearish:
            lines.append(f'<div class="kp-window bearish"><span class="window-title">Strongest Bearish Candidate Window</span><strong class="window-time">{report.strongest_bearish.time_range_str()}</strong><span class="window-score">Deepest Score: -{report.strongest_bearish.score:.2f}</span></div>')
        else:
            lines.append('<div class="kp-window neutral"><span class="window-title">Strongest Bearish Candidate Window</span><strong>None active</strong></div>')
        lines.append('</div>')

        if report.exhaustion_warnings:
            lines.append('<div class="kp-warning-box">')
            lines.append('<h4>Score Exhaustion Warnings</h4>')
            for w in report.exhaustion_warnings:
                lines.append(f'<div class="kp-warning">⚠ {w}</div>')
            lines.append('</div>')

        lines.append('<h3>Intraday Trading Playbook</h3>')
        lines.append('<ol class="kp-playbook">')
        lines.append('<li><strong>Trade only Tier-1 flips</strong> in the direction of the active Moon sub-lord regime.</li>')
        lines.append('<li><strong>Longs valid</strong> when regime is "buy-on-dip" and a Tier-1 bullish flip occurs. Enter on pullback to VWAP/CPR support with 5-candle confirmation (&ge;15 pts).</li>')
        lines.append('<li><strong>Shorts valid</strong> when regime is "sell-on-rise" and a Tier-1 bearish flip occurs. Enter on rally to VWAP/CPR resistance with 5-candle confirmation (&ge;15 pts).</li>')
        lines.append('<li><strong>Reversal candidate exception (v14):</strong> Counter-regime pure-set alarms may be traded only with price confirmation (first 5 five-minute candles &ge; 15 points in new direction, plus VWAP reclaim/loss or CPR break). Position size reduced to 50%.</li>')
        lines.append('<li><strong>Max 3 Tier-1 trades per session (Rule D-3).</strong> No adding to losers.</li>')
        lines.append('</ol>')

        lines.append('<h3>Bank Nifty Calibration Notes</h3>')
        lines.append('<div class="kp-calibration-notes">')
        lines.append('<p>Timing tolerance: &plusmn;3&ndash;5 minutes vs NIFTY. Response strength: 1.2&ndash;1.5&times; NIFTY magnitude on Tier-1 flips. Rahu-sub windows: wider SL (2&times; ATR), avoid first 15 min of Rahu sub-lord. Moon sub-lord transitions in Rahu star: expect false starts, wait for candle close confirmation.</p>')
        lines.append('</div>')

        lines.append('</section>')
        return '\n'.join(lines)

    def _render_section6(self, report: KPIntradayReport) -> str:
        lines = []
        lines.append('<section class="kp-section kp-disclaimer">')
        lines.append('<h2>SECTION 6 &mdash; DISCLAIMER</h2>')
        lines.append('<p><strong>Educational research output combining KP astrology with systematic trading discipline.</strong> It does not constitute investment advice, solicitation, or recommendation to buy or sell any securities or derivatives. Derivatives trading involves substantial risk of loss and is not suitable for all investors. Validate all signals with independent backtesting, position sizing, and risk management before live deployment. The author and publisher assume no liability for trading decisions based on this report.</p>')
        lines.append('</section>')
        lines.append('</div>')
        return '\n'.join(lines)


def generate_kp_intraday_report(
    csv_path: Path,
    trading_day: date,
    instrument: str = "NIFTY",
    config: dict | None = None
) -> KPIntradayReport:
    """Main entry point to generate a KP Intraday report."""
    cfg = config or {}

    parser = KPDataParser(cfg)
    engine = KPRuleEngine(cfg)
    generator = KPReportGenerator(cfg)

    rows = parser.parse_csv(csv_path)
    data_quality = assess_kp_data(rows)
    day_data = parser.parse_day_data(rows, trading_day)

    day_bias_score, day_bias_label = engine.compute_day_bias(
        day_data['day_lord'],
        day_data['moon_star']
    )

    moon_affliction = engine.evaluate_moon_affliction_gate(
        day_data['moon_sign'],
        day_data['moon_star'],
        day_data['all_rows'][0].get('aspects', '') if day_data['all_rows'] else ''
    )

    hora_slots = []
    for hs in day_data['hora_slots']:
        quality, base_q, asp_rec, interp, notes = engine.evaluate_hora_quality(hs['lord'], hs['aspects'])
        hora_slots.append(HoraSlot(
            start=hs['time'],
            end=(datetime.combine(date.today(), hs['time']) + timedelta(minutes=60)).time(),
            lord=hs['lord'],
            quality=quality,
            base_quality=base_q,
            aspects_received=asp_rec,
            interpretation=interp,
            aspect_notes=notes
        ))

    day_signature = DayChartSignature(
        day_lord=day_data['day_lord'],
        moon_sign=day_data['moon_sign'],
        moon_star=day_data['moon_star'],
        opening_sublord=day_data['opening_sublord'],
        moon_speed=day_data['moon_speed'],
        day_bias_score=day_bias_score,
        day_bias_label=day_bias_label,
        moon_affliction_gate=moon_affliction,
        hora_slots=hora_slots
    )

    regime_shifts = engine.detect_regime_shifts(day_data['all_rows'])
    trend_changes = engine.detect_trend_changes(day_data['all_rows'], regime_shifts)
    bullish_windows, bearish_windows = engine.score_windows(trend_changes, day_data['all_rows'])
    exhaustion_warnings = engine.identify_exhaustion_warnings(bullish_windows, bearish_windows)

    strongest_bullish = bullish_windows[0] if bullish_windows else None
    strongest_bearish = bearish_windows[0] if bearish_windows else None

    report = KPIntradayReport(
        trading_day=trading_day,
        instrument=instrument,
        market="NSE Mumbai",
        ayanamsa="KP Ayanamsha",
        source_file=csv_path.name,
        generated_at=datetime.now(),
        brand=generator.brand,
        day_signature=day_signature,
        regime_shifts=regime_shifts,
        trend_changes=trend_changes,
        bullish_windows=bullish_windows,
        bearish_windows=bearish_windows,
        strongest_bullish=strongest_bullish,
        strongest_bearish=strongest_bearish,
        exhaustion_warnings=exhaustion_warnings,
        config=cfg,
        data_quality=data_quality
    )

    enrich_report_v15(report, day_data['all_rows'])
    return report


def enrich_report_v15(report: KPIntradayReport, day_rows: list[dict]) -> None:
    """Attach the v15 layers (A-13, C-5, Navamsa D-9, Nadi) to a built report.

    Never raises: a failure leaves the v14 report intact with a note, so the
    document can still be produced.
    """
    from . import kp_layers as L
    ds = report.day_signature
    try:
        wins = L.rahu_moon_sub_windows(day_rows)
        ds.rahu_windows = wins
        ds.rahu_windows_note = L.rahu_windows_text(wins)
    except Exception as exc:  # pragma: no cover - defensive
        ds.rahu_windows_note = f"Rahu Moon-sub windows (Rule A-13): not computed ({exc})."

    try:
        nav = L.build_navamsa_layer(report.trading_day, ds.opening_sublord, ds.moon_star)
        ds.navamsa = {
            "placements": nav.placements,
            "moon_element": nav.moon_element,
            "n3_text": nav.n3_text,
            "n5_text": nav.n5_text, "n5_adjust": nav.n5_adjust,
            "n6_text": nav.n6_text, "n6_adjust": nav.n6_adjust,
            "lagna_d9_sign": nav.lagna_d9_sign,
            "moon_vargottama": nav.moon_vargottama,
            "moon_navamsa_change": nav.moon_navamsa_change,
        }
        ds.vargottama_note = L.vargottama_text(nav)
        # per-row column: Ascendant navamsa + incoming sub-lord dignity + Moon element
        el_open = L.ELEMENT_ABBR[nav.moon_element]
        change = nav.moon_navamsa_change
        el_late = None
        if change:
            try:
                t_change = time(int(change[:2]), int(change[3:5]))
                el_late = L.ELEMENT_ABBR[L.navamsa_of(
                    L.planets_at(report.trading_day, t_change)["Moon"]["longitude"]).element]
            except Exception:
                el_late = None
        for tc in report.trend_changes:
            el = el_open
            if change and el_late and tc.time_str() >= change:
                el = el_late
            tc.navamsa_d9 = L.signal_navamsa_column(
                report.trading_day, tc.timestamp,
                L.incoming_sublord_from_trigger(tc.trigger), el)
    except Exception as exc:  # pragma: no cover - defensive
        ds.vargottama_note = f"Vargottama Moon (Rule C-5): not computed ({exc})."
        ds.navamsa = {"error": str(exc)}

    try:
        nd = L.build_nadi_layer(report.trading_day)
        ds.nadi = {
            "nakshatra": nd.nakshatra, "nadi": nd.nadi, "multiplier": nd.multiplier,
            "character": nd.character, "transition": nd.transition, "text": nd.text,
        }
        label = f"{nd.nadi} ({nd.multiplier:.2f}x)"
        late_label = None
        if nd.transition:
            hhmm = nd.transition[:5]
            nadi2 = nd.transition.split("(")[1].split(",")[0]
            late_label = f"{nadi2} ({L.NADI_PROFILE[nadi2][0]:.2f}x)"
        for tc in report.trend_changes:
            tc.nadi = late_label if (nd.transition and late_label and tc.time_str() >= hhmm) else label
    except Exception as exc:  # pragma: no cover - defensive
        ds.nadi = {"error": str(exc), "text": f"SBC Nadi Classification (v15.1): not computed ({exc})."}


def generate_sample_kp_csv(output_path: Path, start_date, days: int = 31):
    """Generate sample KP data CSV for testing."""
    import random
    from datetime import date, datetime

    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    elif isinstance(start_date, datetime):
        start_date = start_date.date()

    planets = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu', 'Ascendant']
    signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
    stars = ['Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra', 'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni', 'Hasta', 'Chitra', 'Swati', 'Vishakha', 'Anuradha', 'Jyeshtha', 'Mula', 'Purva Ashadha', 'Uttara Ashadha', 'Shravana', 'Dhanishta', 'Shatabhisha', 'Purva Bhadrapada', 'Uttara Bhadrapada', 'Revati']

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(KPDataParser.REQUIRED_COLUMNS)

        for d in range(days):
            current_date = start_date + timedelta(days=d)
            if current_date.weekday() >= 5:
                continue

            day_lord = random.choice(planets[:7])
            moon_speed = round(13.0 + random.uniform(-1.5, 1.5), 4)

            for minute in range(9*60+15, 15*60+30, 5):
                ts = datetime.combine(current_date, time(0, 0)) + timedelta(minutes=minute)
                ts_str = ts.isoformat()

                for p in planets:
                    if p == 'Ascendant' or p == 'Moon':
                        sign = random.choice(signs)
                        star = random.choice(stars)
                        sublord = random.choice(planets[:7])
                        sub_sublord = random.choice(planets[:7])
                        house_set = f"{random.randint(1,12)},{random.randint(1,12)}"
                        hs_strength = round(random.uniform(-3, 5), 1)
                    else:
                        sign = random.choice(signs)
                        star = random.choice(stars)
                        sublord = random.choice(planets[:7])
                        sub_sublord = random.choice(planets[:7])
                        house_set = f"{random.randint(1,12)},{random.randint(1,12)}"
                        hs_strength = round(random.uniform(-3, 5), 1)

                    hora_lord = random.choice(planets[:7]) if minute % 60 == 15 else ''
                    aspects = ', '.join(random.sample(planets[:7], random.randint(0, 3)))

                    writer.writerow([
                        ts_str, p, sign, star, sublord, sub_sublord,
                        house_set, hs_strength, '', moon_speed,
                        sign, star, sublord, sub_sublord,
                        hora_lord, day_lord, aspects
                    ])

    print(f"Sample KP data generated: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate KP Intraday Report")
    parser.add_argument("--csv", type=Path, required=True, help="Path to KP data CSV")
    parser.add_argument("--date", type=str, required=True, help="Trading day (YYYY-MM-DD)")
    parser.add_argument("--instrument", type=str, default="NIFTY", choices=["NIFTY", "BANK NIFTY"])
    parser.add_argument("--output", type=Path, help="Output HTML file")
    parser.add_argument("--generate-sample", action="store_true", help="Generate sample CSV")
    parser.add_argument("--sample-days", type=int, default=31, help="Days of sample data")

    args = parser.parse_args()

    if args.generate_sample:
        start = date.fromisoformat(args.date)
        generate_sample_kp_csv(args.csv, start, args.sample_days)
    else:
        trading_day = date.fromisoformat(args.date)
        report = generate_kp_intraday_report(args.csv, trading_day, args.instrument)

        if args.output:
            html = KPReportGenerator().generate_html(report)
            args.output.write_text(html, encoding='utf-8')
            print(f"Report written to {args.output}")
        else:
            print(json.dumps({
                'day': report.trading_day.isoformat(),
                'instrument': report.instrument,
                'signals': len(report.trend_changes),
                'regime_shifts': len(report.regime_shifts),
                'bullish_windows': len(report.bullish_windows),
                'bearish_windows': len(report.bearish_windows)
            }, indent=2))
