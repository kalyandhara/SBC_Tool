"""Validate the AstroZ (Neesh Kumar) crash-cycle video transcript claims.

Claims under test (transcript, 2026-10-22):
- Oct 31, 2026: Jupiter enters Leo / Magha (Ketu's nakshatra), aligns with
  the Rahu-Ketu axis, forms Shatashtak (6/8) with Saturn; window lasts to
  ~Jan 25, 2027; "Jupiter goes retrograde on January 27th".
- Nov 12-13, 2026: Mars joins Ketu; Jupiter/Mars/Rahu/Ketu on one axis.
- June 2027: Saturn debilitated; Jupiter surrounded by malefics.
- 2033: Jupiter Shatashtak with Saturn, no malefic influence (bull call).
- Historical: Jupiter in Ketu nakshatras (Ashwini/Magha/Mula) afflicted at
  1966, 1973-74, 1979-80, 1987 (Dow) and 1992, 2000, 2008, 2020 (Nifty);
  counter-examples 1995/2003/2023 unafflicted.
- "Similar cycle to 1929" (no details given; snapshot printed for review).

Ephemeris: sbc pipeline (Swiss Ephemeris Moshier, sidereal Lahiri, mean
node, IST 09:15 snapshots).  Example:
    python scripts/adhoc/validate_transcript_astroz_crash_video.py
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
    nakshatra_ingresses,
    nakshatra_periods,
    sign_ingresses,
)

KETU_NAKS = {"Ashwini", "Magha", "Mula"}
NAK_LORDS = {
    "Ashwini": "Ketu", "Bharani": "Venus", "Krittika": "Sun",
    "Rohini": "Moon", "Mrigashira": "Mars", "Ardra": "Rahu",
    "Punarvasu": "Jupiter", "Pushya": "Saturn", "Ashlesha": "Mercury",
    "Magha": "Ketu", "P.Phalguni": "Venus", "U.Phalguni": "Sun",
    "Hasta": "Moon", "Chitra": "Mars", "Swati": "Rahu",
    "Vishakha": "Jupiter", "Anuradha": "Saturn", "Jyeshtha": "Mercury",
    "Mula": "Ketu", "P.Ashadha": "Venus", "U.Ashadha": "Sun",
    "Shravana": "Moon", "Dhanishta": "Mars", "Shatabhisha": "Rahu",
    "P.Bhadrapada": "Jupiter", "U.Bhadrapada": "Saturn",
    "Revati": "Mercury", "Abhijit": "Ketu",
}


def sep(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def snap(date_str):
    planets, _ay, _sun, _moon, _tithi = positioned_planets(date_str)
    return {p["name"]: p for p in planets}


def fmt(p):
    r = "R" if p["retrograde"] else "D"
    return (f"{p['sign']:>11} {p['degree']:5.2f} {p['nakshatra']:<13} "
            f"p{p['pada']} [{r}]")


def relationship(ju, sa):
    d = (ju["sign_index"] - sa["sign_index"]) % 12
    if d == 5:
        return "6th-from-Saturn (Saturn 8th from Ju) => Shashtashtaka 6/8"
    if d == 7:
        return "8th-from-Saturn (Saturn 6th from Ju) => Shashtashtaka 6/8"
    return f"{d + 1}th-from-Saturn"


def check_snapshot(date_str, label=""):
    s = snap(date_str)
    ju, sa = s["Jupiter"], s["Saturn"]
    print(f"\n--- {date_str}  {label}")
    for name in ("Jupiter", "Saturn", "Mars", "Sun", "Rahu", "Ketu"):
        print(f"  {name:<8} {fmt(s[name])}")
    print(f"  Jupiter nakshatra lord: {NAK_LORDS[ju['nakshatra']]}"
          f"{'  << KETU NAKSHATRA' if ju['nakshatra'] in KETU_NAKS else ''}")
    print(f"  Ju-Sat: {relationship(ju, sa)}")
    print(f"  Ju-Sat {sep(ju['longitude'], sa['longitude']):5.1f} deg | "
          f"Ju-Ra {sep(ju['longitude'], s['Rahu']['longitude']):5.1f} | "
          f"Ju-Ke {sep(ju['longitude'], s['Ketu']['longitude']):5.1f} | "
          f"Ju-Ma {sep(ju['longitude'], s['Mars']['longitude']):5.1f} | "
          f"Ju-Su {sep(ju['longitude'], s['Sun']['longitude']):5.1f}")
    return s


def scan_pairwise_jup_sat(a, b):
    """Days where Jupiter-Saturn are in mutual 6/8 (Shashtashtaka)."""
    print(f"\n== Shashtashtaka (6/8) Jupiter-Saturn windows {a}..{b}")
    cur = None
    d = datetime.date.fromisoformat(a)
    end = datetime.date.fromisoformat(b)
    while d <= end:
        s = snap(d.isoformat())
        dist = (s["Jupiter"]["sign_index"] - s["Saturn"]["sign_index"]) % 12
        state = dist in (5, 7)
        if state and cur is None:
            cur = d
        if not state and cur is not None:
            print(f"   {cur} .. {d - datetime.timedelta(days=1)}")
            cur = None
        d += datetime.timedelta(days=1)
    if cur is not None:
        print(f"   {cur} .. {end} (still open at scan end)")


def mars_node_conjunction(y, m_lo, m_hi, node="Ketu"):
    """Refine Mars-node minimum separation inside a month window (IST noon)."""
    import swisseph as swe
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    body = swe.MARS
    best = (999.0, None)
    d = datetime.date(y, m_lo, 1)
    while d <= datetime.date(y, m_hi, 28):
        jd = swe.julday(d.year, d.month, d.day, 6.5)  # 12:00 IST ~ 06:30 UT
        xx, _ = swe.calc_ut(jd, body, flags)
        rahu, _ = swe.calc_ut(jd, swe.MEAN_NODE, flags)
        ke = (rahu[0] + 180.0) % 360.0
        s = sep(xx[0], ke if node == "Ketu" else rahu[0])
        if s < best[0]:
            best = (s, d)
        d += datetime.timedelta(days=1)
    print(f"   Mars-{node} min separation {best[0]:.2f} deg on {best[1]}")


def nifty_drawdowns():
    from scripts.study_mars_node_conjunction import load_series
    print("\n== NIFTY drawdown checks (repo market.db, close & low based)")
    windows = [("2000 dot-com", "2000-02-11", "2003-04-25"),
               ("2008 Lehman", "2008-01-08", "2008-10-27"),
               ("2020 COVID", "2020-01-20", "2020-03-23")]
    for label, a, b in windows:
        try:
            rows = load_series(
                "nifty", datetime.date.fromisoformat(a),
                datetime.date.fromisoformat(b))
        except Exception as exc:  # noqa: BLE001
            print(f"   {label}: data unavailable ({exc})")
            continue
        if not rows:
            print(f"   {label}: no rows in range")
            continue
        peak, peak_i = rows[0]["close"], 0
        worst = 0.0
        for i, r in enumerate(rows):
            if r["close"] > peak:
                peak, peak_i = r["close"], i
            dd = (r["close"] / peak - 1.0) * 100.0
            worst = min(worst, dd)
        peak_row = rows[peak_i]
        trough_row = min(rows[peak_i:], key=lambda r: r["close"])
        low_dd = (trough_row["low"] / peak_row["high"] - 1.0) * 100.0
        print(f"   {label}: close {peak_row['time']} {peak:.0f} -> "
              f"{trough_row['time']} {trough_row['close']:.0f} = "
              f"{worst:.1f}% (intraday low {low_dd:.1f}%)")


def main():
    print("=" * 74)
    print("A. FORWARD CLAIMS")
    print("=" * 74)

    print("\n== Jupiter nakshatra ingresses 2026-09 .. 2027-12")
    for e in nakshatra_ingresses(
            "Jupiter", datetime.date(2026, 9, 1), datetime.date(2027, 12, 31)):
        print(f"   {e['ist_date']}  {e['label']}"
              + (f"  (from {e['from_label']})" if e.get("from_label") else ""))

    print("\n== Jupiter stations 2026-06 .. 2027-12 (claim: Rx Jan 27 2027)")
    for r in stations_between(datetime.date(2026, 6, 1),
                              datetime.date(2027, 12, 31),
                              bodies=("Jupiter",)):
        print(f"   {r['time']}  {r['label']}")

    print("\n== Saturn sign ingresses 2027-2028 (claim: debilitated Jun 2027)")
    for e in sign_ingresses("Saturn", datetime.date(2027, 1, 1),
                            datetime.date(2028, 12, 31)):
        print(f"   {e['ist_date']}  {e['from_label']} -> {e['label']}")

    print("\n== Rahu sign ingress Oct 2026 - Feb 2027 (node-axis claim)")
    for e in sign_ingresses("Rahu", datetime.date(2026, 10, 1),
                            datetime.date(2027, 2, 28)):
        print(f"   {e['ist_date']}  {e['from_label']} -> {e['label']}")

    scan_pairwise_jup_sat("2026-09-01", "2027-12-31")

    print("\n== Daily Jupiter-Ketu separation Oct 2026 - Feb 2027")
    d, end = datetime.date(2026, 10, 25), datetime.date(2027, 2, 10)
    best = (999.0, None)
    while d <= end:
        s = snap(d.isoformat())
        x = sep(s["Jupiter"]["longitude"], s["Ketu"]["longitude"])
        if x < best[0]:
            best = (x, d)
        if d in (datetime.date(2026, 10, 31), datetime.date(2026, 11, 15),
                 datetime.date(2026, 12, 6), datetime.date(2027, 1, 10),
                 datetime.date(2027, 1, 24), datetime.date(2027, 1, 27)):
            print(f"   {d}: Ju-Ke {x:5.1f} deg (Jupiter in "
                  f"{s['Jupiter']['nakshatra']})")
        d += datetime.timedelta(days=1)
    print(f"   min Jupiter-Ketu separation: {best[0]:.1f} deg on {best[1]}")

    print("\n== Mars-Ketu conjunction Nov 2026 (claim: Nov 12-13)")
    mars_node_conjunction(2026, 11, 11, "Ketu")
    check_snapshot("2026-11-15", "Mars-Ketu exact; node-axis check")

    print("\n== Stations Jan-Mar 2027 (what actually happens near Jan 27?)")
    for r in stations_between(datetime.date(2027, 1, 1),
                              datetime.date(2027, 3, 1)):
        print(f"   {r['time']}  {r['label']}")

    print("\n== June-Aug 2027 snapshots (claim: Saturn debilitated, "
          "Jupiter surrounded by malefics)")
    for dstr, lab in (("2027-06-25", "Jupiter re-enters Magha"),
                      ("2027-07-25", ""), ("2027-08-25", "")):
        check_snapshot(dstr, lab)

    print("\n== 2033 check (claim: Ju-Sat Shashtashtaka, no malefics, "
          "bull market)")
    scan_pairwise_jup_sat("2032-06-01", "2034-06-30")
    s2033 = snap("2033-06-30")
    print(f"   2033-06-30: Jupiter {s2033['Jupiter']['sign']} "
          f"{s2033['Jupiter']['degree']:.1f} "
          f"{s2033['Jupiter']['nakshatra']} | Saturn "
          f"{s2033['Saturn']['sign']} {s2033['Saturn']['degree']:.1f} "
          f"{s2033['Saturn']['nakshatra']}")

    print("\n== 1929 snapshots (claim: cycle similar to 1929)")
    check_snapshot("1929-09-03", "Dow all-time high before crash")
    check_snapshot("1929-10-29", "Black Tuesday")

    print("\n" + "=" * 74)
    print("B. HISTORICAL CRASH CLAIMS (Jupiter in Ketu nakshatra + affliction)")
    print("=" * 74)
    events = [
        ("1966-02-09", "1966 Dow peak (1001)"),
        ("1966-10-07", "1966 Dow low (-26%)"),
        ("1973-01-11", "1973 Dow peak (1051)"),
        ("1974-12-06", "1974 Dow low (-45%)"),
        ("1980-02-13", "1980 Dow high (904)"),
        ("1980-04-21", "1980 Dow low (759, -16%)"),
        ("1987-10-19", "Black Monday (-22.6%)"),
        ("1992-04-23", "Sensex peak / scam breaks"),
        ("1993-04-30", "Sensex low area (-57%)"),
        ("2000-02-11", "Nifty dot-com peak"),
        ("2003-04-25", "Nifty final trough (-50%)"),
        ("2008-01-08", "Nifty 2008 peak (6357)"),
        ("2008-10-27", "Nifty 2008 low (2253, -64%)"),
        ("2020-01-20", "Nifty 2020 peak (12430)"),
        ("2020-03-23", "Nifty 2020 COVID low (7594, -39%)"),
        ("1995-09-30", "counter-example 1995"),
        ("2003-08-15", "counter-example 2003 (Magha stay)"),
        ("2023-05-15", "counter-example 2023 (Ashwini stay)"),
        ("2023-12-15", "counter-example 2023 (Ashwini stay 2)"),
        ("2015-08-24", "China devaluation crash day"),
        ("2011-12-20", "Nifty 2011 low (4531)"),
    ]
    for dstr, lab in events:
        check_snapshot(dstr, lab)

    print("\n== Jupiter nakshatra stays 1995-1996 (1995 counter-example)")
    for p in nakshatra_periods("Jupiter", datetime.date(1995, 1, 1),
                               datetime.date(1996, 12, 31)):
        print(f"   {p['start']} .. {p['end']}  {p['nakshatra']}")

    print("\n" + "=" * 74)
    print("C. MARKET DATA")
    print("=" * 74)
    nifty_drawdowns()


if __name__ == "__main__":
    main()
