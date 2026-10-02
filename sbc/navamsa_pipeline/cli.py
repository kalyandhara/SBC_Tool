import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from navamsa_pipeline.db.writer import save_rows
from navamsa_pipeline.divisional.navamsa import navamsa_of
from navamsa_pipeline.ephemeris.ephemeris import Ephemeris
from navamsa_pipeline.export.exporter import export_csv
from navamsa_pipeline.kp_loader import find_kp_file, load_kp_for_day
from navamsa_pipeline.lagna import get_lagna
from navamsa_pipeline.panchanga import get_panchanga
from navamsa_pipeline.rules.engine import RuleEngine
from navamsa_pipeline.tiler.tiler import market_hours_times


def main():
    parser = argparse.ArgumentParser(description="Navamsa D-9 Pipeline CLI")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--granularity", default="1m", choices=["1m","5m","1h"])
    parser.add_argument("--ayanamsha", default="KP", choices=["KP","Lahiri"])
    parser.add_argument("--ephemeris", default="de440", choices=["de440","de441","swisseph"])
    parser.add_argument("--outdir", default="./outputs")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    start = datetime.strptime(args.start, "%Y-%m-%d").date()
    end = datetime.strptime(args.end, "%Y-%m-%d").date()

    epi = Ephemeris(backend=args.ephemeris, ayanamsha=args.ayanamsha)
    engine = RuleEngine()

    rows = []
    # Preload KP data per day
    kp_cache = {}
    prev_sublord = None
    prev_house_set = None
    prev_dt = None
    confirmation_streak = 0
    for dt in market_hours_times(start, end):
        day = dt.date()
        if day not in kp_cache:
            kp_path = find_kp_file(day)
            kp_cache[day] = load_kp_for_day(kp_path, day)
        kp_rows = kp_cache[day]
        # Find KP row for this timestamp approx match
        kp_row = None
        for r in kp_rows:
            try:
                ts = datetime.fromisoformat(r['timestamp'])
                if ts.date() == day and abs((ts - dt.replace(tzinfo=None)).total_seconds()) < 180:
                    kp_row = r
                    break
            except:
                continue

        pos, ayan = epi.get_positions(dt)
        moon_lon = pos.get("Moon", {}).get("longitude", 0)
        nav = navamsa_of(moon_lon)
        panch = get_panchanga(dt)
        lagna_lon = get_lagna(dt)

        # Build realistic context from KP row if available
        hora_quality = 1.0
        house_set_strength = 1.0
        moon_sub_score = 1.0
        asc_sub_score = 1.0
        hora_lord = ""
        house_set = ""
        sublord = ""
        if kp_row:
            try:
                house_set_strength = float(kp_row.get('house_set_strength', 1.0))
            except:
                pass
            hora_lord = kp_row.get('hora_lord', '')
            house_set = kp_row.get('house_set', '')
            sublord = kp_row.get('sublord', '')
            # Simple proxy scores
            moon_sub_score = 1.5 if kp_row.get('planet') == 'Moon' else 1.0
            asc_sub_score = 1.2

        # Sub-lord transition detection
        sublord_change = False
        house_set_change = False
        if prev_sublord is not None and sublord and prev_sublord != sublord:
            sublord_change = True
            house_set_strength = min(house_set_strength + 0.5, 2.0)
        if prev_house_set is not None and house_set and prev_house_set != house_set:
            house_set_change = True

        # Regime shift detection
        regime_shift = False
        if sublord_change and house_set_change:
            regime_shift = True
            house_set_strength = min(house_set_strength + 0.7, 2.5)

        prev_sublord = sublord
        prev_house_set = house_set
        prev_dt = dt

        # Pure-set alarm placeholder
        pure_set_alarm = False
        if sublord_change and house_set_strength >= 1.8:
            pure_set_alarm = True
            score_boost = 2.5 if regime_shift else 2.0
        else:
            score_boost = 1.5 if sublord_change else 0.0

        context = {
            "hora_quality": hora_quality,
            "house_set_strength": house_set_strength,
            "moon_sub_score": moon_sub_score,
            "asc_sub_score": asc_sub_score,
        }
        score = engine.score(context)
        score += score_boost
        grade = engine.classify(score)
        # Confirmation points tracking
        if grade != "NoTrade":
            confirmation_streak += 1
        else:
            confirmation_streak = 0
        confirmation_points = min(confirmation_streak, 15)
        rows.append({
            "timestamp": dt.isoformat(),
            "ayanamsa_offset": ayan,
            "moon_lon": moon_lon,
            "lagna_lon": lagna_lon,
            "navamsa_sign": nav.navamsa_sign,
            "navamsa_index": nav.navamsa_index,
            "vargottama": nav.vargottama_flag,
            "tithi": panch.get("tithi"),
            "nakshatra": panch.get("nakshatra"),
            "nakshatra_pada": panch.get("pada"),
            "yoga": panch.get("yoga"),
            "karana": panch.get("karana"),
            "hora_lord": hora_lord,
            "house_set": house_set,
            "sublord": sublord,
            "sublord_change": sublord_change,
            "regime_shift": regime_shift,
            "pure_set_alarm": pure_set_alarm,
            "confirmation_points": confirmation_points,
            "score": round(score,4),
            "grade": grade,
        })

    # Export
    fieldnames = ["timestamp","ayanamsa_offset","moon_lon","lagna_lon","navamsa_sign","navamsa_index","vargottama","tithi","nakshatra","nakshatra_pada","yoga","karana","hora_lord","house_set","sublord","sublord_change","regime_shift","pure_set_alarm","confirmation_points","score","grade"]
    export_csv(rows, outdir/"intraday_triggers.csv", fieldnames)
    # Monthly summary placeholder
    export_csv([], outdir/"navamsa_monthly.csv", ["month","avg_score"])
    # Save to DB
    save_rows(rows)
    print(f"Pipeline complete. {len(rows)} rows written to {outdir} and saved to DB")

if __name__ == "__main__":
    main()
