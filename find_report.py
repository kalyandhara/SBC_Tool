import sys
try:
    with open(r'D:\SBC_Tool\static\app.js', 'r', encoding='utf-8') as f:
        content = f.read()
        # Find the renderKPIntradayReport function
        idx = content.find('function renderKPIntradayReport')
        if idx >= 0:
            lines = content.split('\n')
            # Print lines from idx to idx+120
            for i in range(idx, min(idx+120, len(lines))):
                print(f'{i}: {lines[i]}')
        else:
            print('Not found')
except Exception as e:
    print(f'Error: {e}')
PYEOF