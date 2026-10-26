"""Validate the AstroZ Mercury-retrograde video transcript claims (2026-10-25).

Claims under test (video recorded the day after Mercury's station; the
repo pins Mercury R to 2026-10-24 13:29 IST, so the video day is
2026-10-25):
- "Mercury has gone retrograde as of yesterday"; Venus and Saturn were
  already retrograde; Venus is combust.
- "Today is Purnima. Tomorrow the Moon is in Aries (Ashwini) - recovery.
  Day after tomorrow Moon in Bharani - volatility."
- NIFTY topped 26,277 on 2024-09-27, fell since; Mercury+Venus went
  retrograde in Mar 2025 and "a recovery began" (Apr-May rally).
- Mercury retro stat card: 63 completed periods Oct 2006 - Jul 2026;
  trend reversed 31/63 (49.2%); after a downtrend 19/29 rebounded
  (65.5%); 41/63 positive (65.1%), average return +0.55%.
- Gold: after a downtrend gold rose 22/31 times (71%); in an uptrend it
  turned negative 11/32 times. Gold ~$4,000, silver ~$53 now.
- Crude: Brent hit ~$116; crude averaged over $80 this year.
- Attacks: Jun (2026) strike with Mars-Ketu, Feb (2026) with Mars-Rahu;
  next Mars-Ketu "November 12th".
- Fed: outcome Oct 28, presser Oct 29; Moon "between Rahu and Ketu and
  under Saturn's aspect" on Oct 28.
- Copper positive; expects a rise after Nov 12.

The retrograde-vs-market statistics themselves are graded by
scripts/study_retrograde_reversal.py (trend-reversal framing with
matched baselines); this script pins the ephemeris, prices and dates.

Ephemeris: repo pipeline (Swiss Ephemeris Moshier, sidereal Lahiri,
mean node, IST).  Example:
    python scripts/adhoc/validate_transcript_astroz_mercury_video.py
"""

import datetime
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from sbc.planets import COMBUST_ORB, positioned_planets  # noqa: E402
from sbc.stations import between as stations_between  # noqa: E402
from sbc.transits import conjunction_events  # noqa: E402
from scripts.study_mars_node_conjunction import load_series  # noqa: E402

VIDEO_DAY = datetime.date(2026, 10, 25)  # pinned below, verified in A.1


def stations_chunked(start, end, bodies):
    """stations.between is limited to 10-year ranges; chain calls."""
    out = []
    cur = start
    while cur < end:
        nxt = min(cur + datetime.timedelta(days=3650), end)
        out.extend(stations_between(cur, nxt, bodies=bodies))
        cur = nxt
    return out


def snap(date_str, label=""):
    planets, _ay, sun, moon, tithi = positioned_planets(date_str)
    p = {x["name"]: x for x in planets}
    print(f"  {date_str} {label}")
    print(f"    tithi {tithi} ({'Purnima' if tithi == 15 else ''})"
          f"  Moon {moon['sign']} {moon['nakshatra']} p{moon['pada']}")
    for name in ("Mercury", "Venus", "Saturn"):
        pl = p[name]
        sep = abs((pl["longitude"] - sun["longitude"] + 180) % 360 - 180)
        combust = (sep < COMBUST_ORB.get(name, 0)) if name != "Sun" else False
        print(f"    {name:<8} {pl['sign']:>11} {pl['degree']:5.2f}"
              f"  retro={pl['retrograde']!s:<5}"
              f"  Sun-sep {sep:5.1f} deg"
              f"{'  COMBUST' if combust else ''}")
    return p, sun, moon, tithi


def nifty_facts():
    rows = load_series("nifty", datetime.date(2007, 9, 1),
                       datetime.date.today())
    print("\n== NIFTY (^NSEI, repo CSV cache)\n")
    peak = max(rows, key=lambda r: r["high"])
    print(f"  series intraday high: {peak['time']} high {peak['high']:,.2f}"
          f"  (video: 26,277 on 2024-09-27)")
    last = rows[-1]
    print(f"  latest: {last['time']} close {last['close']:,.2f}"
          f"  -> {(last['close'] / peak['high'] - 1) * 100:+.1f}% off the"
          f" high (video: about -14%)")
    # Mar 2025 episode: Venus+Mercury stations and the bottom
    win = [r for r in rows if "2025-02-01" <= r["time"] <= "2025-06-30"]
    if win:
        trough = min(win, key=lambda r: r["close"])
        print(f"  Feb-Jun 2025 lowest close: {trough['time']} "
              f"{trough['close']:,.2f}")
        rec = next((r for r in win if r["time"] > trough["time"]
                    and r["close"] > trough["close"] * 1.05), None)
        if rec:
            print(f"  first close +5% off that low: {rec['time']} "
                  f"{rec['close']:,.2f}")
    return rows


def price_levels():
    print("\n== Metals / energy levels vs transcript\n")
    for asset, label, claim in (
            ("gold", "Gold GC=F", "around $4,000"),
            ("silver", "Silver SI=F", "around $53"),
            ("crude", "Crude WTI CL=F", "Brent ~$116 (WTI is the repo proxy)"),
    ):
        rows = load_series(asset, datetime.date(2000, 1, 1),
                           datetime.date.today())
        if not rows:
            print(f"  {label}: no data")
            continue
        last = rows[-1]
        y2026 = [r["close"] for r in rows if r["time"].startswith("2026")]
        hi90 = max(rows[-90:], key=lambda r: r["high"])
        avg_txt = (f"  2026 YTD close avg ${sum(y2026) / len(y2026):,.2f}"
                   if y2026 else "")
        print(f"  {label}: {last['time']} close ${last['close']:,.2f}"
              f"  (video: {claim})")
        print(f"    90-session high: {hi90['time']} ${hi90['high']:,.2f}"
              f"{avg_txt}")
    # copper via market.db research series (HG=F)
    from sbc import market_store
    hg = market_store.get_daily("HG", "2026-01-01")
    if hg:
        first, last = hg[0], hg[-1]
        chg = (last["close"] / first["close"] - 1) * 100
        print(f"  Copper HG=F: {last['date']} close ${last['close']:,.2f}"
              f"  2026 YTD {chg:+.1f}%  (video: 'hasn't fallen much, "
              f"recovered first, rises after Nov 12')")


def mercury_station_counts():
    print("\n== Mercury retrograde stations (video: 63 completed periods,"
          " Oct 2006 - Jul 2026)\n")
    starts = stations_chunked(datetime.date(2006, 10, 1),
                              datetime.date(2026, 8, 1), ("Mercury",))
    retro_starts = [s for s in starts if s["direction"] == "retrograde"]
    print(f"  Mercury stations retrograde {len(retro_starts)} times in "
          f"2006-10-01..2026-08-01 (video: 63)")
    nifty_first = "2007-09-17"  # first repo NIFTY bar
    coverable = [s for s in retro_starts if s["date"] >= nifty_first]
    print(f"  of those, {len(coverable)} fall inside repo NIFTY data "
          f"(data starts {nifty_first}) - the Oct 2006 episode is "
          f"pre-data")


def mars_node_checks():
    print("\n== Mars-Rahu / Mars-Ketu exact crossings 2025-06 .. 2026-12"
          " (attack-timing claims)\n")
    for a, b in (("Mars", "Rahu"), ("Mars", "Ketu")):
        for e in conjunction_events(a, b, datetime.date(2025, 6, 1),
                                    datetime.date(2026, 12, 31),
                                    step_hours=24):
            if e["kind"] != "conjunction":
                continue
            print(f"  {e['ist_date']}  Mars conj {b:<4} orb {e['orb']:.3f}")
    print("  (video: Jun 2026 attack with Mars-Ketu, Feb 2026 with"
          " Mars-Rahu, next Mars-Ketu 'Nov 12' - repo already pinned"
          " it to 2026-11-15, TODO A3)")


def fed_and_moon():
    print("\n== Fed dates (data/econ_events.json) and the Oct 28 moon"
          " claims\n")
    with open(os.path.join(_ROOT, "data", "econ_events.json"),
              encoding="utf-8") as fh:
        events = json.load(fh)
    items = events if isinstance(events, list) else events.get("events",
                                                               [])
    for ev in items:
        name = ev.get("name", "")
        if "FOMC" in name and str(ev.get("date", "")).startswith("2026-10"):
            print(f"  {ev.get('date')}  {name}  {ev.get('title', '')}")
    for day in ("2026-10-27", "2026-10-28", "2026-10-29"):
        planets, _ay, sun, moon, tithi = positioned_planets(day)
        p = {x["name"]: x for x in planets}
        rahu, sat = p["Rahu"], p["Saturn"]
        d_rahu = abs((moon["longitude"] - rahu["longitude"] + 180) % 360
                     - 180)
        d_ketu = 180.0 - d_rahu if d_rahu <= 180 else 360.0 - d_rahu
        off = (moon["sign_index"] - sat["sign_index"]) % 12
        vedic = {2: "3rd", 6: "7th", 9: "10th"}.get(off)
        print(f"  {day}: Moon {moon['sign']} {moon['nakshatra']}, "
              f"{d_rahu:.0f} deg from Rahu / {d_ketu:.0f} from Ketu, "
              f"Saturn {sat['sign']} -> Vedic aspect on Moon: "
              f"{vedic or 'none'}")


def main():
    print("=" * 74)
    print("A. PIN THE VIDEO DAY + PANCHANG CALLS")
    print("=" * 74)
    st = stations_between(datetime.date(2026, 10, 18),
                          datetime.date(2026, 10, 30), ("Mercury",))
    for s in st:
        print(f"  {s['time']}  {s['label']}")
    print("  video: 'Mercury has gone retrograde as of yesterday' -> "
          "video recorded 2026-10-25 if the station is 2026-10-24")
    for day, label in (("2026-10-24", "(Mercury station day)"),
                       ("2026-10-25", "(video day: 'today Purnima')"),
                       ("2026-10-26", "('tomorrow Moon in Aries/Ashwini')"),
                       ("2026-10-27", "('day after: Moon in Bharani')")):
        snap(day, label)

    print("\n" + "=" * 74)
    print("B. NIFTY FACTS")
    print("=" * 74)
    nifty_facts()
    mercury_station_counts()

    print("\n" + "=" * 74)
    print("C. METALS / ENERGY LEVELS")
    print("=" * 74)
    price_levels()

    print("\n" + "=" * 74)
    print("D. MARS-NODE CROSSINGS (attack-timing claims)")
    print("=" * 74)
    mars_node_checks()

    print("\n" + "=" * 74)
    print("E. FED + OCT 28 MOON CLAIMS")
    print("=" * 74)
    fed_and_moon()


if __name__ == "__main__":
    main()
