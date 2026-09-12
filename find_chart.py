import sys
try:
    with open(r'D:\SBC_Tool\static\app.js', 'r', encoding='utf-8') as f:
        content = f.read()
        # Find sections related to KP Intraday or charts
        # Look for "kp-intraday" or "chart" sections
        idx = 0
        while True:
            idx = content.find('kp-intraday', idx)
            if idx == -1:
                break
            # Print context around it
            start = max(0, idx-100)
            end = min(len(content), idx+200)
            print(f'Found kp-intraday at {idx}:')
            print(content[start:end])
            print('---')
            idx += 1
except Exception as e:
    print(f'Error: {e}')