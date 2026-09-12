with open('static/app.js', 'rb') as f:
    content = f.read()

idx = content.find(b'details)) {dils)) {')
if idx >= 0:
    print('Found at:', idx)
    # Replace the broken part
    # From 'details)) {dils)) {' to 'details)) {'
    broken = b'details)) {dils)) {'
    fixed = b'details)) {'
    content = content[:idx] + fixed + content[idx + len(broken):]
    
    with open('static/app.js', 'wb') as f:
        f.write(content)
    print('Fixed!')
else:
    print('Not found')