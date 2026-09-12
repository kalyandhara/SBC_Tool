import sys
try:
    with open(r'D:\SBC_Tool\static\app.js', 'r', encoding='utf-8') as f:
        content = f.read()
        # Find the end of DOMContentLoaded section
        # Look for the "// Handle initial hash if present" line
        lines = content.split('\n')
        for i, line in enumerate(lines[3100:3120], start=3101):
            if 'Handle initial hash' in line:
                print(f'Found at line {i}: {line}')
                # Print lines i to i+20
                for j in range(i, min(i+20, len(lines))):
                    print(f'{j}: {lines[j-1]}')
                break
        else:
            print('Not found in that range')
            # Try searching for "initWorkspaceTabs"
            for i, line in enumerate(lines[3060:3110], start=3061):
                if 'initWorkspaceTabs' in line:
                    print(f'Found initWorkspaceTabs at line {i}: {line}')
                    break
except Exception as e:
    print(f'Error: {e}')
PYEOF