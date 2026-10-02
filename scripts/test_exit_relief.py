from sbc.backtest import run_bullish_futurecast

result = run_bullish_futurecast(center_date='2032-06-02', years=2)
for c in result.get('clusters', []):
    triggers = c.get('triggers', [])
    if any('Saturn Taurus Exit' in t for t in triggers) or c.get('timeline') == 'current':
        print(f"  {c['timeline'].upper()}: {c['start']} to {c['end']} | score={c['score']} | {triggers}")
