with open('static/app.js', 'rb') as f:
    content = f.read()

# The file ends abruptly - missing closing }); for the DOMContentLoaded event listener
# Check the end of the file
if content.strip().endswith(b'});'):
    print("Already ends correctly")
else:
    # Add the missing closing
    if not content.endswith(b'\n'):
        content += b'\n'
    content += b'});\n'
    with open('static/app.js', 'wb') as f:
        f.write(content)
    print("Added missing closing });")

print("Done!")