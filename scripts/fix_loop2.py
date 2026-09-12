with open('static/app.js', 'rb') as f:
    content = f.read()

idx = content.find(b'for (const [keyfunction renderTourismSignals(data) {')
if idx >= 0:
    # Find the for loop start
    loop_start = content.rfind(b'for (const [key', 0, idx)
    print('Loop start:', loop_start)
    
    # Find the function start
    func_start = content.find(b'function renderTourismSignals(data) {', idx)
    if func_start == -1:
        func_start = content.find(b'function renderTourismSignals(data) {', idx)
    
    print('Function start:', func_start)
    
    # Find the function end
    if func_start != -1:
        brace_count = 0
        pos = content.find(b'{', func_start) + 1
        brace_count = 1
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
        
        # Extract function
        func_code = content[func_start:func_end]
        
        # Find the for loop end (should be before the function)
        loop_end = content.rfind(b'}', 0, func_start)
        print('Loop end:', loop_end)
        
        # Fix the for loop - add missing {
        # The loop should end with: for (const [key, val] of Object.entries(data.details)) {
        # Then the loop body, then }
        # But the function was inserted before the closing }
        
        # Remove the misplaced function
        new_content = content[:func_start] + content[func_end:]
        
        # Fix the for loop - it should end with } before the next function
        # The loop body should end before the function
        # The loop currently ends at func_start, but it's missing the closing }
        # Add the missing } before the function was inserted
        loop_end = func_start
        # Find the last } before the function that closes the for loop
        loop_end = new_content.rfind(b'}', 0, func_start)
        
        # Remove the misplaced function
        new_content = content[:func_start] + content[func_end:]
        
        # Insert function before loadTourismSignals
        insert_idx = new_content.find(b'async function loadTourismSignals')
        if insert_idx != -1:
            new_content = new_content[:insert_idx] + func_code + b'\n\n' + new_content[insert_idx:]
            
            with open('static/app.js', 'wb') as f:
                f.write(new_content)
            print('Fixed!')
        else:
            print('Could not find loadTourismSignals')
    else:
        print('Function start not found')
else:
    print('Pattern not found')