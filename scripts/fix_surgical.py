with open('static/app.js', 'rb') as f:
    content = f.read()

# The issue is at position 31644:
# "for (const [keyfunction renderTourismSignals(data) {"
# Should be: "for (const [key, val] of Object.entries(data.details)) {"
# And the function should be moved out

# Find the exact broken pattern
idx = content.find(b'for (const [keyfunction renderTourismSignals(data) {')
print('Found at:', idx)

# The broken part is exactly:
# "for (const [keyfunction renderTourismSignals(data) {"
# Should be: "for (const [key, val] of Object.entries(data.details)) {"
# Then the loop body, then "}"
# Then the function definition

# Let's do a precise surgical fix:
# 1. Replace the broken for loop header
# 2. Add the missing closing brace for the loop
# 3. Move the function to the correct location

idx = content.find(b'for (const [keyfunction renderTourismSignals(data) {')
if idx >= 0:
    # The broken pattern is exactly 47 bytes
    broken = b'for (const [keyfunction renderTourismSignals(data) {'
    fixed_header = b'for (const [key, val] of Object.entries(data.details)) {'
    
    # Replace the broken header
    content = content[:idx] + b'for (const [key, val] of Object.entries(data.details)) {' + content[idx + 47:]
    
    # Now we need to add the missing } for the for loop
    # The loop body ends where the function was inserted (at idx)
    # So we need to insert } at idx
    content = content[:idx] + b'}' + content[idx:]
    
    # Now remove the misplaced function
    func_start = content.find(b'function renderTourismSignals(data) {', idx)
    if func_start == -1:
        func_start = content.find(b'function renderTourismSignals(data) {', idx)
    
    if func_start != -1:
        # Find function end
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
        
        print(f'Function from {func_start} to {func_end}')
        func_code = content[func_start:func_end]
        
        # Remove the misplaced function
        content = content[:func_start] + content[func_end:]
        
        # Insert before loadTourismSignals
        insert_idx = content.find(b'async function loadTourismSignals')
        if insert_idx != -1:
            new_content = content[:insert_idx] + content[func_start:func_end] + b'\n\n' + content[insert_idx:]
            
            with open('static/app.js', 'wb') as f:
                f.write(content)
            print('Fixed!')
        else:
            print('Could not find loadTourismSignals')
else:
    print('Pattern not found')