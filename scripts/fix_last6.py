import re

with open('static/app.js', 'rb') as f:
    content = f.read()

# Find the corrupted pattern at the end
idx = content.find(b'signals.remove("hidden");\r\n\r\n, val] of Object.entries(data.details))')
if idx >= 0:
    print('Found at:', idx)
    print(repr(content[idx-50:idx+80]))
    # Fix: add missing '[key, ' before 'val]'
    content = content[:idx] + b'[key, ' + content[idx:]
    with open('static/app.js', 'wb') as f:
        f.write(content)
    print('Fixed!')
else:
    print('Not found with exact pattern')
    
    # Search more broadly
    for m in re.finditer(b'hidden");\r\n\r\n, val]', content):
        print(f'Found at {m.start()}: {content[m.start()-50:m.end()+80]}')