with open('static/app.js', 'rb') as f:
    content = f.read()

# Find the misplaced renderTourismSignals
idx = content.find(b'for (const [keyfunction renderTourismSignals(data) {')
if idx >= 0:
    # Find the start of the function
    func_start = content.rfind(b'function renderTourismSignals(data) {', 0, idx)
    if func_start == -1:
        func_start = content.rfind(b'function renderTourismSignals(data) {', 0, idx)
    
    if func_start != -1:
        # Find the end of this function
        brace_count = 0
        pos = func_start
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
        
        # Extract the function
        func_code = content[func_start:func_end]
        
        # Remove from current position
        content = content[:func_start] + content[func_end:]
        
        # Find the correct insertion point (before loadTourismSignals)
        insert_idx = content.find(b'async function loadTourismSignals')
        if insert_idx != -1:
            # Insert before loadTourismSignals with proper spacing
            new_content = content[:insert_idx] + func_code + b'\n\n' + content[insert_idx:]
            
            with open('static/app.js', 'wb') as f:
                f.write(new_content)
            print('Fixed!')
        else:
            print('Could not find loadTourismSignals')
    else:
        print('Could not find function start')
else:
    print('Misplaced function not found')