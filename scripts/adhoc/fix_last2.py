import re

with open('static/app.js', 'rb') as f:
    content = f.read()

# Find the corrupted pattern at the end
idx = content.find(b'urism-signals").classList.remove("hidden");\r\n\r\n, val] of Object.entries(data.details))')
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

    # Try alternative search
    idx = content.find(b'hidden\");\r\n\r\n, val]')
    if idx >= 0:
        print('Found alternative at:', idx)
        print(repr(content[idx-50:idx+80]))
    else:
        print('Alternative not found either')

    # Search for the pattern more broadly
    for m in re.finditer(b', val] of Object.entries', content):
        print(f'Found at {m.start()}: {content[m.start()-50:m.end()+50]}')
