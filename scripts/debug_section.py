with open('static/app.js', 'rb') as f:
    content = f.read()

# Find the exact broken section
idx = content.find(b'for (const [keyfunction renderTourismSignals(data) {')
print('Found at:', idx)

# Show context
print('BEFORE:')
print(content[idx-200:idx])
print('---')
print(content[idx:idx+300])
print('---')
print(content[idx+300:idx+600])