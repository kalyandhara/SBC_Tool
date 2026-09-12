from sbc.backtest import run_backtest
result = run_backtest()
print('Accuracy:', result['accuracy'], '%')
print('Matches:', result['matches'], '/', result['total'])
for r in result['results']:
    print(' ', r['anchor'], '-', r['event'], ':', r['result'])