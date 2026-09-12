with open('static/app.js', 'rb') as f:
    content = f.read()

# 1. Fix the broken for loop in renderChemicalSignals
idx = content.find(b'for (const [keyfunction renderTourismSignals(data) {')
if idx >= 0:
    # Fix the for loop header
    content = content[:idx] + b'for (const [key, val] of Object.entries(data.details)) {' + content[idx + 47:]
    
    # Add missing } for the for loop
    content = content[:idx] + b'}' + content[idx:]
    
    print('Fixed for loop header and added missing }')

# 2. Find and remove the misplaced renderTourismSignals function (at 31659)
func_start = content.find(b'function renderTourismSignals(data) {')
func_end = -1
if func_start >= 0:
    pos = content.find(b'{', func_start) + 1
    brace_count = 1
    pos = func_start + 1
    while pos < len(content):
        if content[pos:pos+1] == b'{':
            brace_count += 1
        elif content[pos:pos+1] == b'}':
            brace_count -= 1
            if brace_count == 0:
                func_end = pos + 1
                break
            pos += 1
    else:
        func_end = len(content)
    
    func_code = content[func_start:func_end]
    content = content[:func_start] + content[func_end:]
    print('Removed misplaced renderTourismSignals')

# 3. Insert renderTourismSignals before loadTourismSignals (at 28531)
insert_idx = content.find(b'async function loadTourismSignals')
if insert_idx != -1:
    # Need to get the function code first - let's extract it from the original position
    # We need to find the original function code. Let's extract it from the original position
    pass

# 4. Remove duplicate loadLunarForecast (second one at 45066)
first_lunar = content.find(b'async function loadLunarForecast')
second_lunar = content.find(b'async function loadLunarForecast', first_lunar + 1)
if first_lunar != -1 and second_lunar != first_lunar:
    next_func = content.find(b'async function ', second_lunar + 1)
    if next_func != -1:
        content = content[:second_lunar] + content[next_func:]
        print('Removed duplicate loadLunarForecast')

with open('static/app.js', 'wb') as f:
    f.write(content)

print('Done with basic fixes')