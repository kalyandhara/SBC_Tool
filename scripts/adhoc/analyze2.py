with open('static/app.js', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Find all async function positions
import re
pattern = r'async function (\w+)\s*\('
matches = list(re.finditer(pattern, content))

print('All async functions:')
for m in matches:
    print(f'  {m.group(1)} at position {m.start()}')

# Check for duplicate loadLunarForecast
count_lunar = content.count('async function loadLunarForecast')
print(f'\nloadLunarForecast count: {count_lunar}')

# Check render functions
render_pattern = r'function render(\w+)\s*\('
render_matches = list(re.finditer(render_pattern, content))
print(f'\nRender functions:')
for m in render_matches:
    print(f'  render{m.group(1)} at position {m.start()}')

# Check brace balance
open_braces = content.count('{')
close_braces = content.count('}')
print(f'\nTotal braces: open={content.count("{")}, close={content.count("}")}, balance={content.count("{") - content.count("}")}')