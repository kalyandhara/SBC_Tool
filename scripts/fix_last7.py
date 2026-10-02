with open('static/app.js', 'rb') as f:
    content = f.read()

idx = content.find(b'signals.remove("hidden");\r\n\r\n, val] of Object.entries(data.details))')
if idx >= 0:
    print('Found at:', idx)
    print(repr(content[idx-50:idx+80]))
    content = content[:idx] + b'[key, ' + content[idx:]
    with open('static/app.js', 'wb') as f:
        f.write(content)
    print('Fixed!')
else:
    print('Not found')
