with open('static/app.js', 'rb') as f:
    content = f.read()

# Fix pattern: }\r\n\r\n$("X-signals").classList.remove("hidden");\r\n  }\r\n}
# This pattern appears multiple times for different signal types
# We need to remove the duplicate closing braces after each render function

# Pattern: }\r\n\r\n$("X-signals").classList.remove("hidden");\r\n  }\r\n}
# This appears after each render function's catch block

patterns_to_fix = [
    b'}\r\n\r\n$("fmcg-signals").classList.remove("hidden");\r\n  }\r\n}',
    b'}\r\n\r\n$("tourism-signals").classList.remove("hidden");\r\n  }\r\n}',
    b'}\r\n\r\n$("chemical-signals").classList.remove("hidden");\r\n  }\r\n}',
    b'}\r\n\r\n$("alcohol-signals").classList.remove("hidden");\r\n  }\r\n}',
    b'}\r\n\r\n$("largecap-divergence").classList.remove("hidden");\r\n  }\r\n}',
    b'}\r\n\r\n$("fmcg-signals").classList.remove("hidden");\r\n  }\r\n}',
    b'}\r\n\r\n$("tourism-signals").classList.remove("hidden");\r\n  }\r\n}',
    b'}\r\n\r\n$("chemical-signals").classList.remove("hidden");\r\n  }\r\n}',
    b'}\r\n\r\n$("alcohol-signals").classList.remove("hidden");\r\n  }\r\n}',
    b'}\r\n\r\n$("largecap-divergence").classList.remove("hidden");\r\n  }\r\n}',
]

fixed_count = 0
for pattern in patterns_to_fix:
    idx = content.find(pattern)
    if idx >= 0:
        # Replace the duplicate with just the closing brace for the function
        replacement = b'}\r\n'
        content = content[:idx] + replacement + content[idx + len(pattern):]
        fixed_count += 1
        print(f"Fixed pattern at index {idx}")

# Also check for any remaining duplicate patterns
# Pattern: }\r\n\r\n$("X").classList.remove("hidden");\r\n  }\r\n}
# This should only appear once per function (the catch block closing)

print(f"Fixed {fixed_count} duplicate patterns")

with open('static/app.js', 'wb') as f:
    f.write(content)

print("Done!")
