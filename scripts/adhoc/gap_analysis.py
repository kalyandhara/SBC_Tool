import datetime
from sbc.monthly_heatmap import monthly_heatmap, NIFTY_SECTOR_ROWS, _row_to_canonical
from sbc.confluence import build_confluence_report, normalize_sectors
from sbc.monthly_heatmap import _day_planets, _anchor_nakshatra, _day_sector_net
from collections import Counter

# Collect raw sector keys over a month
start_date = datetime.date(2025,9,1)
days = 30
anchor_nakshatra = _anchor_nakshatra('nse')
row_canonical_cache = {name: _row_to_canonical(tags) for name, tags in NIFTY_SECTOR_ROWS}

unmapped_keys = Counter()
mapped_counts = Counter()

for i in range(days):
    d = start_date + datetime.timedelta(days=i)
    planets, tithi = _day_planets(d)
    # Build confluence for day
    from sbc.prediction import analyze, compute_vedhas, sector_read, planet_sector_read
    from sbc.market_calendar import transit_alert, jupiter_market_analysis, lunar_phase_alert
    vedha_map,_ = compute_vedhas(planets, school='classical')
    analysis = analyze(planets, vedha_map, anchor_nakshatra, school='classical')
    sr = sector_read(vedha_map, planets)
    psr = planet_sector_read(planets)
    transits = transit_alert(planets)
    lunar = lunar_phase_alert(tithi)
    jup = jupiter_market_analysis(planets)
    conf = build_confluence_report(
        analysis=analysis,
        sector_read=sr,
        planet_sector_read=psr,
        reversal_data={"windows": [], "upcoming_windows": []},
        transits=transits,
        jupiter_analysis=jup,
        lunar_phase=lunar,
    )
    sector_conf = conf.get("sector_confluence", {})
    for raw_key in sector_conf.keys():
        raw_norm = normalize_sectors([raw_key])
        raw_canon = raw_norm[0] if raw_norm else raw_key
        assigned = False
        for row_name in NIFTY_SECTOR_ROWS:
            canon_set = row_canonical_cache[row_name[0]]
            if raw_canon in canon_set or raw_key in row_name[1]:
                assigned = True
                mapped_counts[row_name[0]] += 1
                break
        if not assigned:
            # fallback check
            for row_name in NIFTY_SECTOR_ROWS:
                if raw_canon in row_canonical_cache[row_name[0]]:
                    assigned = True
                    mapped_counts[row_name[0]] += 1
                    break
        if not assigned:
            unmapped_keys[raw_key] += 1

print("Mapped sector row hit counts:")
for k,v in mapped_counts.most_common():
    print(k, v)

print("\nUnmapped raw sector keys:")
for k,v in unmapped_keys.most_common():
    print(k, v)
