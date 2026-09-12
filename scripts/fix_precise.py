with open('static/app.js', 'rb') as f:
    content = f.read()

idx = content.find(b'for (const [keyfunction renderTourismSignals(data) {')
if idx >= 0:
    print('Found at:', idx)
    
    # The broken pattern is: "for (const [keyfunction renderTourismSignals(data) {"
    # It should be: "for (const [key, val] of Object.entries(data.details)) {"
    
    # Find the start of the for loop
    loop_start = content.rfind(b'for (const [key', 0, idx)
    print('Loop start:', loop_start)
    
    # Find where the function starts (misplaced)
    func_start = content.find(b'function renderTourismSignals(data) {', idx)
    print('Function start:', func_start)
    
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
    
    # The for loop is missing its opening { and closing }
    # The loop should be:
    # for (const [key, val] of Object.entries(data.details)) {
    #   // loop body (the chemical detail list code)
    # }
    
    # The function was inserted at idx, which is where the loop body should continue
    # So the loop body ends at idx, and we need to add } there
    
    # Step 1: Fix the for loop header
    broken = b'for (const [keyfunction renderTourismSignals(data) {'
    fixed_header = b'for (const [key, val] of Object.entries(data.details)) {'
    
    # Replace the broken header
    content = content[:idx] + b'for (const [key, val] of Object.entries(data.details)) {' + content[idx + 47:]
    
    # Add the missing } for the for loop at idx (where function was inserted)
    content = content[:idx] + b'}' + content[idx:]
    
    # Now remove the misplaced function
    func_start = content.find(b'function renderTourismSignals(data) {', idx)
    if func_start == -1:
        func_start = content.find(b'function renderTourismSignals(data) {', idx)
    
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
    
    # Remove misplaced function
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