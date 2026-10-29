"""Validate the AstroZ gold-video transcript claims (2026-10-24).

Claims under test:
- Gold INR story: ~96,000 (Apr 2025 video) -> ~1,90,000 (Jan 2026) ->
  ~1,39,000 -> currently 1,50,000-1,60,000 (per 10 g).
- Cycle 1 (1971-1980): $35 -> $843/873 peak, -70% to $256 by 2000,
  +136% in 1979 alone (no repo data before 2000 - prose checks only).
- Cycle 2 (2000-2011): segment returns by Saturn sign (repo GC=F data
  starts 2000-08, so Taurus/Gemini legs are partial).
- Saturn sidereal ingresses: Taurus 2000-06-06; Aries windows
  1968-71 / 1998-2000 / 2027-06..10 and 2028-02..2030-04; Taurus
  2030-04-17..2032-05-31.
- 2036-08-27: Saturn in Magha nakshatra, "30 deg axis" with Jupiter.
- Jupiter-Saturn cycle: "conjoin every ~20 y, oppose every ~10 y";
  cycle 1 ran opposition (1971) -> conjunction (1980-81); the 2030-32
  Taurus window carries the next J-S opposition; bullish window to
  2041-01-29.

Ephemeris: repo pipeline (Swiss Ephemeris Moshier, sidereal Lahiri,
mean node, IST).  Example:
    python scripts/adhoc/validate_transcript_astroz_gold_video.py
"""

import datetime
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from sbc.planets import positioned_planets  # noqa: E402
from sbc.stations import between as stations_between  # noqa: E402
from sbc.transits import (  # noqa: E402
    conjunction_events,
    sign_ingresses,
    sign_periods,
)
from scripts.study_mars_node_conjunction import load_series  # noqa: E402

GRAMS_PER_OZ = 31.1035

# Video INR claims (per 10 g) mapped to the repo gold level at the same
# date.  USDINR comes from the repo series (data/usdinr_ohlc.csv).
INR_CLAIMS = [
    ("Apr 2025 video: ~96,000", "2025-04-25", "close_avg_apr2025", 96000),
    ("Jan 2026: 1,90,000", "2026-01-29", "high", 190000),
    ("Jun 2026: ~1,39,000", "2026-06-30", "low", 139000),
    ("Oct 2026: 1,50,000-1,60,000", "2026-10-23", "close", 155000),
]


def usdinr_rows():
    return load_series("usdinr", datetime.date(2024, 1, 1),
                       datetime.date.today())


def rate_on_or_after(fx, date_str):
    return next(r["close"] for r in fx if r["time"] >= date_str)


def inr_per_10g(usd_oz, fx):
    return usd_oz * fx * 10.0 / GRAMS_PER_OZ


def gold_facts(fx):
    rows = load_series("gold", datetime.date(2025, 1, 1),
                       datetime.date.today())
    if not rows:
        print("  no gold data in market.db")
        return
    print("== Gold (GC=F, USD/oz) vs transcript INR claims\n")
    apr = [r for r in rows if "2025-04-21" <= r["time"] <= "2025-04-30"]
    fx_apr = rate_on_or_after(fx, "2025-04-21")
    if apr:
        v = sum(r["close"] for r in apr) / len(apr)
        print(f"  2025-04-21..30 close avg: ${v:,.0f} "
              f"(~Rs {inr_per_10g(v, fx_apr):,.0f}/10g at actual FX "
              f"{fx_apr:.2f}; video: ~96,000)")
    peak = max(rows, key=lambda r: r["high"])
    fx_peak = rate_on_or_after(fx, peak["time"])
    print(f"  series peak: {peak['time']} high ${peak['high']:,.0f} "
          f"(~Rs {inr_per_10g(peak['high'], fx_peak):,.0f}/10g at FX "
          f"{fx_peak:.2f}; video: 1,90,000 in January)")
    after = [r for r in rows if r["time"] > peak["time"]]
    if after:
        trough = min(after, key=lambda r: r["low"])
        fx_tr = rate_on_or_after(fx, trough["time"])
        print(f"  post-peak trough: {trough['time']} low "
              f"${trough['low']:,.0f} "
              f"(~Rs {inr_per_10g(trough['low'], fx_tr):,.0f}/10g at FX "
              f"{fx_tr:.2f}; video: ~1,39,000)")
        print(f"  drawdown peak->trough: "
              f"{(trough['low'] / peak['high'] - 1) * 100:+.1f}%")
    last = rows[-1]
    fx_last = rate_on_or_after(fx, last["time"])
    print(f"  latest: {last['time']} close ${last['close']:,.0f} "
          f"(~Rs {inr_per_10g(last['close'], fx_last):,.0f}/10g at FX "
          f"{fx_last:.2f}; video: 1,50,000-1,60,000)")


def implied_premiums(rows, fx):
    """Implied INR-per-USD (and premium over actual FX) per claim."""
    print("\n== Implied basis: what FX each INR claim assumes\n")
    peak_time = max(rows, key=lambda r: r["high"])["time"]
    print("  | claim | gold level | actual FX | implied FX | premium |")
    for label, date_str, basis, inr in INR_CLAIMS:
        if basis == "close_avg_apr2025":
            sel = [r for r in rows if "2025-04-21" <= r["time"]
                   <= "2025-04-30"]
            usd = sum(r["close"] for r in sel) / len(sel)
        elif basis == "high":
            usd = max(r["high"] for r in rows if r["time"] <= date_str)
        elif basis == "low":
            usd = min(r["low"] for r in rows
                      if peak_time < r["time"] <= date_str)
        else:
            usd = max((r for r in rows if r["time"] <= date_str),
                      key=lambda r: r["time"])["close"]
        rate = rate_on_or_after(fx, date_str)
        implied = inr / 10.0 * GRAMS_PER_OZ / usd
        print(f"  | {label} | ${usd:,.0f} | {rate:.2f} "
              f"| {implied:.1f} | {implied / rate * 100 - 100:+.1f}% |")
    print("  Apr 2025 (+4.7%) fits an MCX/duty basis; Jan and Jun 2026 "
          "(~+15%) fit a retail basis consistently; the Oct 2026 claim "
          "(+27%) breaks even that basis - at his own ~15% premium the "
          "current level would be ~Rs 1.40-1.42L/10g, not 1.5-1.6L.")


def saturn_snap(date_str, label):
    planets, _ay, _sun, _moon, _tithi = positioned_planets(date_str)
    p = {x["name"]: x for x in planets}
    sa, ju = p["Saturn"], p["Jupiter"]
    sep = abs((sa["longitude"] - ju["longitude"] + 180) % 360 - 180)
    print(f"  {date_str} {label}")
    print(f"    Saturn   {sa['sign']:>11} {sa['degree']:5.2f} "
          f"{sa['nakshatra']:<13} p{sa['pada']}")
    print(f"    Jupiter  {ju['sign']:>11} {ju['degree']:5.2f} "
          f"{ju['nakshatra']:<13} p{ju['pada']}")
    print(f"    Saturn-Jupiter separation: {sep:.1f} deg")


def main():
    print("=" * 74)
    print("A. GOLD PRICE FACTS (repo market.db, real USDINR series)")
    print("=" * 74)
    fx = usdinr_rows()
    gold_rows = load_series("gold", datetime.date(2025, 1, 1),
                            datetime.date.today())
    gold_facts(fx)
    implied_premiums(gold_rows, fx)

    print("\n" + "=" * 74)
    print("B. SATURN SIDEREAL INGRESSES 1965-2045")
    print("=" * 74)
    for e in sign_ingresses("Saturn", datetime.date(1965, 1, 1),
                            datetime.date(2045, 12, 31)):
        print(f"   {e['ist_date']}  {e['from_label']} -> {e['label']}")

    print("\n== Snapshot claims")
    saturn_snap("2036-08-27",
                "(claim: Saturn in Magha, 30 deg from Jupiter)")
    saturn_snap("2041-01-29", "(claim: bullish window ends here)")
    saturn_snap("2030-10-25", "(mid of claimed 2030-32 Taurus window)")

    print("\n== Stations near 2041-01 (what is Jan 29, 2041?)")
    for r in stations_between(datetime.date(2040, 10, 1),
                              datetime.date(2041, 4, 30),
                              bodies=("Jupiter", "Saturn")):
        print(f"   {r['time']}  {r['label']}")

    print("\n" + "=" * 74)
    print("C. JUPITER-SATURN CONJUNCTIONS AND OPPOSITIONS 1965-2045")
    print("=" * 74)
    for e in conjunction_events("Jupiter", "Saturn",
                                datetime.date(1965, 1, 1),
                                datetime.date(2045, 12, 31),
                                step_hours=24):
        print(f"   {e['ist_date']}  {e['kind']:<12} orb {e['orb']:.3f}")

    print("\n" + "=" * 74)
    print("D. SATURN SIGN STAYS x GOLD (repo data 2000-08 onward)")
    print("=" * 74)
    rows = load_series("gold", datetime.date(2000, 8, 1),
                       datetime.date.today())
    periods = sign_periods("Saturn", datetime.date(2000, 8, 1),
                           datetime.date.today())
    print("\n| start | end | sign | gold % |")
    print("|-------|-----|------|--------|")
    for p in periods:
        i0 = next((i for i, r in enumerate(rows)
                   if r["time"] >= p["start"]), None)
        if i0 is None:
            continue
        i1 = i0
        for i, r in enumerate(rows):
            if r["time"] > p["end"]:
                break
            i1 = i
        if i1 <= i0:
            continue
        ret = (rows[i1]["close"] / rows[i0]["open"] - 1.0) * 100.0
        print(f"| {p['start']} | {p['end']} | {p['sign']:>11} "
              f"| {ret:+7.1f} |")


if __name__ == "__main__":
    main()
