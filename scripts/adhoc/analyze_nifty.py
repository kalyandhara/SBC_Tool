import sys
try:
    with open(r'D:\SBC_Tool\static\nifty-chart.js', 'r', encoding='utf-8') as f:
        content = f.read()
        # Search for chart-related terms
        terms = ['chart', 'canvas', 'plot', 'window', ' candle', 'overlay', 'signal']
        for term in terms:
            count = content.lower().count(term.lower())
            if count > 0:
                print(f'"{term}": {count} occurrences')
except Exception as e:
    print(f'Error: {e}')