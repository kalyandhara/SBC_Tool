import json
r=json.load(open('D:\\SBC_Tool\\backtest_report.json'))
lines=['# Backtest Report','',f"**Total:** {r['total']}  **Matches:** {r['matches']}  **Accuracy:** {r['accuracy']}%",'']
for e in r['results']:
    lines.append(f"## {e['anchor']} – {e['event']} ({e['category']})")
    lines.append(f"Reported: {e['reported_outcome']} | Result: {e['result']}")
    lines.append(f"Jupiter: {e['calculated']['sign']} {e['calculated']['degree']:.2f}° – {e['calculated']['nakshatra']} {e['calculated']['nakshatra_lord']}")
    lines.append(f"Heuristic: {e['heuristic']['level']} – {e['heuristic']['bias']}")
    lines.append(f"Reasons: {'; '.join(e['heuristic']['reasons'])}")
    lines.append(f"Sectors: {', '.join(e['heuristic']['sectors'])}")
    lines.append('')
open('D:\\SBC_Tool\\backtest_summary.md','w',encoding='utf-8').write('\n'.join(lines))
print('done')