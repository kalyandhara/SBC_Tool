from sbc.backtest import run_backtest

result = run_backtest()
print('Backtest Accuracy:', result['accuracy'], '%')
print('Matches:', result['matches'], '/', result['total'])
for r in result['results']:
    print('  {} - {}: {}'.format(r['anchor'], r['event'], r['result']))
