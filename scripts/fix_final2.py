import re

with open('static/app.js', 'rb') as f:
    content = f.read()

# Search for the pattern more broadly
for m in re.finditer(b'hidden");', content):
    context = content[m.start():m.end()+100]
    if b'val]' in context:
        print(f'Found at {m.start()}: {context[:150]}')

# Also search for the specific corrupted pattern
idx = content.find(b'signals.remove("hidden");\r\n\r\n, val]')
if idx >= 0:
    print('Found exact pattern at:', idx)
    print(repr(content[idx-50:idx+80]))
    content = content[:idx] + b'[key, ' + content[idx:]
    with open('static/app.js', 'wb') as f:
        f.write(content)
    print('Fixed!')
else:
    print('Not found with exact pattern')
