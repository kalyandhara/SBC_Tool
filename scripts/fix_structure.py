with open('static/app.js', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Fix 1: Remove duplicate loadLunarForecast (second occurrence)
first_lunar = content.find('async function loadLunarForecast')
second_lunar = content.find('async function loadLunarForecast', first_lunar + 1)

if first_lunar != -1 and second_lunar != first_lunar:
    next_func = content.find('async function ', second_lunar + 1)
    if next_func != -1:
        content = content[:second_lunar] + content[next_func:]
        print('Removed duplicate loadLunarForecast at position', second_lunar)
    else:
        print('Could not find next function after second loadLunarForecast')
else:
    print('No duplicate loadLunarForecast found')

# Fix 2: Move renderTourismSignals out of loadFmcgSignals
idx_fmcg = content.find('async function loadFmcgSignals')
idx_tourism_func = content.find('async function loadTourismSignals')
idx_tourism = idx_tourism_func  # alias for the search range

# Find renderTourismSignals inside loadFmcgSignals
render_tourism_idx = content.find('function renderTourismSignals', idx_fmcg, idx_tourism)

if render_tourism_idx != -1 and idx_fmcg < render_tourism_idx < idx_tourism:
    print('Found renderTourismSignals inside loadFmcgSignals at', render_tourism_idx)
    
    # Find the function body
    brace_pos = content.find('{', render_tourism_idx)
    if brace_pos != -1:
        brace_count = 1
        pos = brace_pos + 1
        while pos < len(content) and brace_count > 0:
            if content[pos] == '{':
                brace_count += 1
            elif content[pos] == '}':
                brace_count -= 1
            pos += 1
        func_end = pos
        
        func_code = content[render_tourism_idx:func_end]
        print('Found renderTourismSignals from', render_tourism_idx, 'to', func_end)
        
        # Remove from inside loadFmcgSignals
        content = content[:render_tourism_idx] + content[func_end:]
        
        # Insert before loadTourismSignals
        insert_pos = idx_tourism
        content = content[:idx_tourism] + func_code + '\n\n' + content[idx_tourism:]
        print('Moved renderTourismSignals to top level before loadTourismSignals')
else:
    print('renderTourismSignals not found inside loadFmcgSignals or already moved')

# Write back
with open('static/app.js', 'w', encoding='utf-8') as f:
    f.write(content)
print('File written successfully')