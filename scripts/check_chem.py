with open('static/app.js', 'rb') as f:
    content = f.read()

idx = content.find(b'detailList.className = "chemical-detail-list";')
if idx >= 0:
    print('Found at:', idx)
    # Show context
    print(repr(content[idx-100:idx+300]))
else:
    print('Not found')