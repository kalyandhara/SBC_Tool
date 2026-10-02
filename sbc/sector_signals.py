"""Sector & commodity vedha signal scanner (backtest-informed).

Encodes the plantation-commodity, fertilizer-sector and food-inflation vedha
scenarios backtested in backtest_plantation.py / backtest_fertilizer.py /
backtest_foodinflation.py (2021-08 .. 2026-08 daily data) and exposes the
pairs active on a given date plus those firing within the next few weeks.

Pair legend "X -> Y" = planet X casts an SBC vedha ray onto the chakra cell
occupied by planet Y.  Stats are historical: avg forward close-to-close
return and win rate at the stated horizon, n = number of historical signals.
A pair may appear under several themes when it moves different markets
(e.g. Rahu -> Moon drives both tea spikes and FMCG margin pressure).
"""

import datetime

from .backtest import _julian_at_noon
from .chakra import NAKSHATRA_CELL
from .planets import positions
from .prediction import compute_vedhas

DISCLAIMER = ("Historical backtest stats 2021-08..2026-08; small samples on some pairs. "
              "Research aid only - not investment advice.")

SCAN_AHEAD_DAYS = 21


def _s(pair, group, sector, instruments, note, findings):
    return {
        "pair": pair,
        "group": group,
        "sector": sector,
        "instruments": instruments,
        "note": note,
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# Scenario catalogue (one entry per pair x market theme)
# ---------------------------------------------------------------------------
SCENARIOS = [
    # ================= Plantation commodities ==============================
    _s(("Mercury", "Venus"), "Strong Bullish", "Plantation",
       ["Coffee (KC=F)"],
       "Best coffee signal found: export-demand vedha. Tea does not confirm.",
       [{"target": "Coffee KC=F", "h": 7, "avg": 4.13, "win": 76.9, "n": 39},
        {"target": "Coffee KC=F", "h": 3, "avg": 1.49, "win": 69.2, "n": 39}]),
    _s(("Venus", "Moon"), "Strong Bullish", "Plantation",
       ["Coffee (KC=F)"],
       "Positive on coffee at all horizons.",
       [{"target": "Coffee KC=F", "h": 7, "avg": 0.78, "win": 52.4, "n": 42}]),
    _s(("Jupiter", "Venus"), "Strong Bullish", "Plantation",
       ["Coffee (KC=F)"],
       "Modest coffee edge; fails on tea proxy (-1.7% / 32% win at 7d).",
       [{"target": "Coffee KC=F", "h": 7, "avg": 0.55, "win": 62.1, "n": 29}]),
    _s(("Moon", "Venus"), "Strong Bullish", "Plantation",
       ["Coffee (KC=F)", "Tea (McLeodRussel proxy)"],
       "Slow starter on both; builds into day 5-7.",
       [{"target": "Coffee KC=F", "h": 7, "avg": 1.12, "win": 57.4, "n": 47},
        {"target": "Tea proxy", "h": 7, "avg": 3.45, "win": 50.0, "n": 48}]),
    _s(("Rahu", "Venus"), "Reversal Spike", "Plantation",
       ["Coffee (KC=F)", "Tea (McLeodRussel proxy)"],
       "Violent bullish spikes on tea; steady gains on coffee.",
       [{"target": "Coffee KC=F", "h": 7, "avg": 2.45, "win": 68.8, "n": 32},
        {"target": "Tea proxy", "h": 7, "avg": 10.67, "win": 68.8, "n": 32}]),
    _s(("Rahu", "Moon"), "Reversal Spike", "Plantation",
       ["Coffee (KC=F)", "Tea (McLeodRussel proxy)"],
       "Short sharp rallies, strongest by day 3-5.",
       [{"target": "Coffee KC=F", "h": 5, "avg": 1.93, "win": 68.4, "n": 38},
        {"target": "Tea proxy", "h": 3, "avg": 2.75, "win": 65.0, "n": 40}]),
    _s(("Saturn", "Moon"), "Reversal Spike", "Plantation",
       ["Tea (McLeodRussel proxy)"],
       "Weather-stress reversal: coffee flat, tea recovers fast.",
       [{"target": "Coffee KC=F", "h": 7, "avg": 0.54, "win": 52.1, "n": 48},
        {"target": "Tea proxy", "h": 3, "avg": 2.39, "win": 64.6, "n": 48}]),
    _s(("Saturn", "Venus"), "Bearish (coffee) / Spike (tea)", "Plantation",
       ["Coffee (KC=F)", "Tea (McLeodRussel proxy)"],
       "Commodity-split: avoid coffee longs; tea spikes hard after dip.",
       [{"target": "Coffee KC=F", "h": 7, "avg": -1.73, "win": 28.6, "n": 14},
        {"target": "Tea proxy", "h": 3, "avg": 5.58, "win": 84.6, "n": 13}]),

    # ================= Fertilizer sector ===================================
    _s(("Jupiter", "Sun"), "Strong Bullish", "Fertilizer",
       ["Fertilizer basket", "PSU fert (RCF, NFL)", "Deepak Fert"],
       "Best fertilizer-sector signal: subsidy-clarity rally, window 5-12d.",
       [{"target": "Fert basket", "h": 10, "avg": 2.90, "win": 62.2, "n": 37},
        {"target": "Fert basket", "h": 3, "avg": 0.79, "win": 64.9, "n": 37}]),
    _s(("Mercury", "Jupiter"), "Strong Bullish", "Fertilizer",
       ["Fertilizer basket"],
       "Trade-flow improvement read; mild positive edge.",
       [{"target": "Fert basket", "h": 10, "avg": 1.15, "win": 61.7, "n": 47}]),
    _s(("Moon", "Jupiter"), "Strong Bullish", "Fertilizer",
       ["Fertilizer basket", "Chambal Fert"],
       "Monsoon-demand read; builds late (day 5-10).",
       [{"target": "Fert basket", "h": 10, "avg": 1.30, "win": 52.5, "n": 40}]),
    _s(("Sun", "Jupiter"), "Strong Bullish", "Fertilizer",
       ["Fertilizer basket"],
       "Weak early; only meaningful by day 10.",
       [{"target": "Fert basket", "h": 10, "avg": 1.05, "win": 51.1, "n": 45}]),
    _s(("Jupiter", "Moon"), "Strong Bullish", "Fertilizer",
       ["Fertilizer basket"],
       "Marginal edge only.",
       [{"target": "Fert basket", "h": 10, "avg": 0.86, "win": 51.2, "n": 43}]),
    _s(("Saturn", "Sun"), "Dip-then-Rally", "Fertilizer",
       ["PSU fert (RCF, NFL)"],
       "Textbook reversal: down day 1-3, PSU names rip by day 7-10. "
       "Inverse for GNFC/Deepak - stay out.",
       [{"target": "RCF", "h": 10, "avg": 5.87, "win": 74.6, "n": 67},
        {"target": "NFL", "h": 10, "avg": 5.20, "win": 68.7, "n": 67},
        {"target": "GNFC", "h": 10, "avg": -2.41, "win": 55.2, "n": 67},
        {"target": "Fert basket", "h": 10, "avg": 1.67, "win": 69.2, "n": 26}]),
    _s(("Rahu", "Sun"), "Dip-then-Rally", "Fertilizer",
       ["PSU fert (RCF, NFL)"],
       "Speculative shock; PSU recovery works, basket stays flat-negative.",
       [{"target": "NFL", "h": 10, "avg": 5.20, "win": 68.7, "n": 67},
        {"target": "RCF", "h": 10, "avg": 5.87, "win": 74.6, "n": 67}]),
    _s(("Moon", "Sun"), "Weak/Moderate", "Fertilizer",
       ["Coromandel"],
       "Failed at basket level; Coromandel-only fit (7d +0.79%/62%).",
       [{"target": "Coromandel", "h": 7, "avg": 0.79, "win": 62.0, "n": 129}]),
    _s(("Mercury", "Moon"), "Weak/Moderate", "Fertilizer",
       [], "Failed at sector level in backtest - informational only.", []),
    _s(("Mercury", "Sun"), "Weak/Moderate", "Fertilizer",
       [], "Failed at sector level in backtest - informational only.", []),

    # ================= Food inflation ======================================
    # Backtest surprise: malefic 'strong inflation' vedhas preceded FOOD PRICE
    # DECLINES in global ag futures (contrarian), while genuine delayed spikes
    # came from Rahu->Sun / Rahu->Mercury. FMCG margins were hit by the
    # sudden-spike set; agri-chem got a brief day-3 bounce.
    _s(("Saturn", "Sun"), "Food Deflation Signal", "Food Inflation",
       ["Food basket (SB/ZW/ZC/ZR)"],
       "Hypothesis REFUTED as inflation trigger: food futures FELL after this "
       "vedha - 20d avg -3.44% with 0 wins in 29 signals. Rare contrarian "
       "short/disinflation marker.",
       [{"target": "Food basket", "h": 20, "avg": -3.44, "win": 0.0, "n": 29},
        {"target": "Food basket", "h": 10, "avg": -2.06, "win": 13.8, "n": 29}]),
    _s(("Saturn", "Moon"), "Deflationary (food) / FMCG watch", "Food Inflation",
       ["Food basket", "FMCG basket"],
       "Monsoon-stress read did NOT lift food futures: 5-7d negative. "
       "FMCG roughly flat - treat as supply-glut, not inflation.",
       [{"target": "Food basket", "h": 5, "avg": -0.39, "win": 35.4, "n": 48},
        {"target": "Food basket", "h": 7, "avg": -0.25, "win": 35.4, "n": 48}]),
    _s(("Mars", "Moon"), "Deflationary (food) / FMCG drag", "Food Inflation",
       ["Food basket", "FMCG basket"],
       "Heat/drought hypothesis inverted for futures (7d -0.65%/34%), but "
       "part of the sudden-spike set that dents FMCG margins.",
       [{"target": "Food basket", "h": 7, "avg": -0.65, "win": 34.3, "n": 35},
        {"target": "FMCG basket", "h": 7, "avg": -0.56, "win": 39.5, "n": 76}]),
    _s(("Mars", "Jupiter"), "Deflationary (food)", "Food Inflation",
       ["Food basket"],
       "Agri-stress read inverted: grain basket sold off through day 10.",
       [{"target": "Food basket", "h": 10, "avg": -1.11, "win": 30.0, "n": 40},
        {"target": "Food basket", "h": 20, "avg": -2.25, "win": 37.5, "n": 40}]),
    _s(("Rahu", "Moon"), "FMCG Drag / Spike Set", "Food Inflation",
       ["FMCG basket", "Agri-chem basket"],
       "Sudden-spike member: FMCG basket bleeds across horizons; "
       "agri-chem pops briefly by day 3; food futures flat.",
       [{"target": "FMCG basket", "h": 7, "avg": -0.56, "win": 39.5, "n": 76},
        {"target": "Agri-chem basket", "h": 3, "avg": 0.48, "win": 59.2, "n": 76}]),
    _s(("Rahu", "Mercury"), "Delayed Food Spike", "Food Inflation",
       ["Food basket"],
       "Trade-disruption read works with a lag: grains grind higher into day 20.",
       [{"target": "Food basket", "h": 20, "avg": 0.88, "win": 60.9, "n": 46}]),
    _s(("Rahu", "Sun"), "Genuine Inflation Spike", "Food Inflation",
       ["Food basket", "FMCG basket"],
       "The real deal: policy-confusion vedha precedes a delayed 20-day food "
       "rally (75% win) while FMCG margins compress. Best true inflation trigger.",
       [{"target": "Food basket", "h": 20, "avg": 1.48, "win": 75.0, "n": 40},
        {"target": "FMCG basket", "h": 5, "avg": -0.32, "win": 42.1, "n": 76}]),
    _s(("Moon", "Mars"), "Moderate (partial confirm)", "Food Inflation",
       ["Food basket"],
       "Only moderate-set member with a positive food read (day 7).",
       [{"target": "Food basket", "h": 7, "avg": 0.29, "win": 61.1, "n": 36}]),
    _s(("Moon", "Saturn"), "Weak/Moderate", "Food Inflation",
       [],
       "Failed to move food futures consistently - informational only.",
       []),
    _s(("Sun", "Saturn"), "Weak/Moderate", "Food Inflation",
       [],
       "Failed: food basket fell at 20d (-1.11%/28%). Informational only.",
       []),

    # ================= Metals / Copper =====================================
    # Mars vedha thesis largely CONFIRMED on COMEX copper; miner equities
    # (Hindustan Copper) amplify the trade-driven pairs dramatically.
    _s(("Mars", "Mercury"), "Strong Bullish", "Copper",
       ["Copper HG=F", "Hindustan Copper"],
       "#1 copper trigger confirmed: metal-demand vedha hits 80% win by day 5 "
       "on futures; miner equity even stronger.",
       [{"target": "Copper HG=F", "h": 5, "avg": 1.39, "win": 80.8, "n": 26},
        {"target": "Copper HG=F", "h": 10, "avg": 1.04, "win": 73.1, "n": 26},
        {"target": "HindCopper", "h": 7, "avg": 4.05, "win": 84.0, "n": 25}]),
    _s(("Mercury", "Mars"), "Strong Bullish", "Copper",
       ["Copper HG=F"],
       "Reverse direction also works: steady build to 76% win by day 10.",
       [{"target": "Copper HG=F", "h": 7, "avg": 1.72, "win": 68.0, "n": 25},
        {"target": "Copper HG=F", "h": 10, "avg": 1.80, "win": 76.0, "n": 25}]),
    _s(("Mars", "Saturn"), "Strong Bullish (long cycle)", "Copper",
       ["Copper HG=F"],
       "Heavy-industry read confirmed spectacularly: 20-day window went "
       "positive 69 times out of 69 (avg +5.17%).",
       [{"target": "Copper HG=F", "h": 10, "avg": 1.94, "win": 69.6, "n": 69},
        {"target": "Copper HG=F", "h": 20, "avg": 5.17, "win": 100.0, "n": 69}]),
    _s(("Saturn", "Mars"), "Strong Bullish", "Copper",
       ["Copper HG=F", "Freeport (FCX)"],
       "Manufacturing boost confirmed on both futures and global miner.",
       [{"target": "Copper HG=F", "h": 5, "avg": 0.80, "win": 72.2, "n": 18},
        {"target": "FCX", "h": 5, "avg": 3.20, "win": 83.3, "n": 18},
        {"target": "FCX", "h": 20, "avg": 6.71, "win": 77.8, "n": 18}]),
    _s(("Mercury", "Sun"), "Strong Bullish (delayed)", "Copper",
       ["Copper HG=F"],
       "Trade-expansion vedha compounds: 75.6% win at 10d, 77.8% at 20d.",
       [{"target": "Copper HG=F", "h": 10, "avg": 1.70, "win": 75.6, "n": 45},
        {"target": "Copper HG=F", "h": 20, "avg": 2.43, "win": 77.8, "n": 45}]),
    _s(("Sun", "Mercury"), "Weak/Moderate", "Copper",
       ["Copper HG=F"],
       "Only meaningful from day 10 onward; skip short windows.",
       [{"target": "Copper HG=F", "h": 10, "avg": 1.04, "win": 62.3, "n": 53}]),
    _s(("Jupiter", "Sun"), "Growth Rally (miners)", "Copper",
       ["Hindustan Copper"],
       "Economic-growth vedha is THE Hindustan Copper signal: avg +18.8% in "
       "20 days, 81% win. Futures barely move - it is an equity story.",
       [{"target": "HindCopper", "h": 10, "avg": 8.93, "win": 64.9, "n": 37},
        {"target": "HindCopper", "h": 20, "avg": 18.80, "win": 81.1, "n": 37}]),
    _s(("Rahu", "Mercury"), "Miner Spike (futures flat)", "Copper",
       ["Hindustan Copper"],
       "Trade-chaos vedha does nothing to LME copper but rockets the Indian "
       "miner: 77% win at day 10.",
       [{"target": "HindCopper", "h": 10, "avg": 7.72, "win": 77.1, "n": 48},
        {"target": "HindCopper", "h": 5, "avg": 5.40, "win": 70.8, "n": 48}]),
    _s(("Rahu", "Sun"), "Confirmed Spike", "Copper",
       ["Copper HG=F"],
       "Power-sector volatility vedha delivers genuine futures spikes, "
       "peaking day 5-7 and again at 20d.",
       [{"target": "Copper HG=F", "h": 5, "avg": 1.36, "win": 62.5, "n": 40},
        {"target": "Copper HG=F", "h": 20, "avg": 2.59, "win": 67.5, "n": 40}]),
    _s(("Rahu", "Mars"), "INVERTED - avoid longs", "Copper",
       ["Copper HG=F", "FCX"],
       "Hypothesis refuted: mining-disruption vedha precedes copper DIPS "
       "(day 3-5 win rate only 20%), not spikes. Treat as bearish/caution.",
       [{"target": "Copper HG=F", "h": 5, "avg": -1.36, "win": 20.0, "n": 15},
        {"target": "FCX", "h": 5, "avg": -3.69, "win": 6.7, "n": 15}]),
    _s(("Mars", "Sun"), "INVERTED - avoid longs", "Copper",
       ["Copper HG=F"],
       "Refuted (tiny sample n=7): industrial-demand surge read actually "
       "preceded sharp copper declines at 10-20d.",
       [{"target": "Copper HG=F", "h": 10, "avg": -2.96, "win": 0.0, "n": 7}]),

    # Moon-target short-term demand pairs (hypothesis section 6)
    _s(("Mars", "Moon"), "Day-1 Demand Pop", "Copper",
       ["Copper HG=F"],
       "Inventory-cycle read confirmed but VERY short-lived: real edge is "
       "day 1 only (61% win); fades to baseline by day 3.",
       [{"target": "Copper HG=F", "h": 1, "avg": 0.52, "win": 61.1, "n": 36}]),
    _s(("Mercury", "Moon"), "Day-1 Trade Pop", "Copper",
       ["Copper HG=F"],
       "Trade-activity read gives a day-1 bounce (62% win) that decays "
       "quickly - scalp horizon, not a swing hold.",
       [{"target": "Copper HG=F", "h": 1, "avg": 0.63, "win": 62.0, "n": 50}]),
    _s(("Sun", "Moon"), "INVERTED - avoid longs", "Copper",
       ["Copper HG=F"],
       "Refuted: industrial-consumption read on the Moon preceded small "
       "copper dips across all horizons.",
       [{"target": "Copper HG=F", "h": 1, "avg": -0.28, "win": 45.7, "n": 46},
        {"target": "Copper HG=F", "h": 5, "avg": -0.24, "win": 47.8, "n": 46}]),
]


SPAN_SCAN_BACK = 270
SPAN_SCAN_FWD = 270


_ACTIVE_PAIRS_CACHE: dict = {}


def _active_pairs(date_str, _cache=_ACTIVE_PAIRS_CACHE):
    """Set of (source -> target) planet pairs whose vedha ray hits target's cell."""
    if date_str in _cache:
        return _cache[date_str]
    planets, _ = positions(_julian_at_noon(date_str))
    vedha_map, _ = compute_vedhas(planets, school="classical")
    cell_of = {p["name"]: NAKSHATRA_CELL.get(p["nakshatra"]) for p in planets}
    active = set()
    for src, hits in vedha_map.items():
        hit_cells = {(h["row"], h["col"]) for h in hits}
        for tgt, tcell in cell_of.items():
            if tgt != src and tcell and tcell in hit_cells:
                active.add((src, tgt))
    _cache[date_str] = active
    return active


def _pair_window(pair, center):
    """Contiguous active window of a pair around the center date.

    A vedha persists while the ray geometry holds - hours for Moon pairs,
    weeks-to-months for slow-graha pairs. Walk outward until the pair
    deactivates (bounded by SPAN_SCAN_*).
    """
    lo = center
    for _ in range(SPAN_SCAN_BACK):
        prev = lo - datetime.timedelta(days=1)
        if pair in _active_pairs(prev.isoformat()):
            lo = prev
        else:
            break
    hi = center
    for _ in range(SPAN_SCAN_FWD):
        nxt = hi + datetime.timedelta(days=1)
        if pair in _active_pairs(nxt.isoformat()):
            hi = nxt
        else:
            break
    return lo, hi


def scan_sector_vedhas(date_str):
    """Active scenario signals (with vedha time spans) + upcoming firing windows."""
    date = datetime.date.fromisoformat(date_str)

    today_active = _active_pairs(date_str)
    signals = []
    window_cache = {}
    for spec in SCENARIOS:
        if spec["pair"] not in today_active:
            continue
        if spec["pair"] not in window_cache:
            lo, hi = _pair_window(spec["pair"], date)
            window_cache[spec["pair"]] = (lo, hi)
        lo, hi = window_cache[spec["pair"]]
        signals.append({
            "pair": f"{spec['pair'][0]} -> {spec['pair'][1]}",
            "source": spec["pair"][0],
            "target": spec["pair"][1],
            "group": spec["group"],
            "sector": spec["sector"],
            "instruments": spec["instruments"],
            "note": spec["note"],
            "findings": spec["findings"],
            "span_start": lo.isoformat(),
            "span_end": hi.isoformat(),
            "span_days": (hi - lo).days + 1,
            "span_day": (date - lo).days + 1,
        })

    # Upcoming: merge consecutive firing dates into per-pair windows
    fired = {}
    for offset in range(1, SCAN_AHEAD_DAYS + 1):
        ds = date + datetime.timedelta(days=offset)
        for pair in _active_pairs(ds.isoformat()):
            fired.setdefault(pair, []).append(ds)

    upcoming = []
    seen = set()
    for pair, days in sorted(fired.items(), key=lambda kv: kv[1][0]):
        # merge consecutive calendar runs
        runs = []
        run_start = run_end = days[0]
        for d in days[1:]:
            if d == run_end + datetime.timedelta(days=1):
                run_end = d
            else:
                runs.append((run_start, run_end))
                run_start = run_end = d
        runs.append((run_start, run_end))
        themes = [s for s in SCENARIOS if s["pair"] == pair]
        for run_start, run_end in runs:
            key = (run_start, run_end, pair)
            if key in seen:
                continue
            seen.add(key)
            for spec in themes:
                # skip windows already live today - those are in signals[]
                if run_start <= date:
                    continue
                upcoming.append({
                    "start": run_start.isoformat(),
                    "end": run_end.isoformat(),
                    "days_ahead": (run_start - date).days,
                    "window_days": (run_end - run_start).days + 1,
                    "pair": f"{pair[0]} -> {pair[1]}",
                    "group": spec["group"],
                    "sector": spec["sector"],
                })
    upcoming.sort(key=lambda u: u["days_ahead"])

    return {
        "date": date_str,
        "scan_end": (date + datetime.timedelta(days=SCAN_AHEAD_DAYS)).isoformat(),
        "signals": signals,
        "upcoming": upcoming,
        "method": "Swiss Ephemeris Lahiri noon-IST positions; classical-school SBC vedha rays.",
        "disclaimer": DISCLAIMER,
    }
