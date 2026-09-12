import sys
try:
    with open(r'D:\SBC_Tool\static\app.js', 'r', encoding='utf-8') as f:
        content = f.read()
        # Search for chart-related terms
        terms = ['chart', 'canvas', 'lightweight', 'nifty', 'highcharts', 'chartjs']
        for term in terms:
            count = content.lower().count(term.lower())
            if count > 0:
                print(f'"{term}": {count} occurrences')
except Exception as e:
    print(f'Error: {e}')