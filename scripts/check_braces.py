with open('static/app.js', 'rb') as f:
    content = f.read()

print('Length:', len(content))
print('Last 100 bytes:', content[-100:])
print('Ends with newline:', content.endswith(b'\n'))
print('Ends with }); :', content.endswith(b'});'))

open_braces = content.count(b'{')
close_braces = content.count(b'}')
print('Total open braces:', open_braces)
print('Total close braces:', close_braces)
print('Balance:', open_braces - close_braces)