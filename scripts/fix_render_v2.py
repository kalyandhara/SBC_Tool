with open('static/app.js', 'rb') as f:
    content = f.read()

# Find the misplaced function
idx = content.find(b'for (const [keyfunction renderTourismSignals(data) {')
if idx >= 0:
    # Find the actual function start (should be right after "for (const [key")
    # The pattern is: for (const [key, val] of Object.entries(data.details)) {
    # Then the function starts
    
    # Find the actual function start
    func_start = content.rfind(b'function renderTourismSignals(data) {', 0, idx)
    print('Function start:', func_start)
    
    if func_start != -1:
        # Find the matching closing brace
        brace_count = 0
        pos = content.find(b'{', idx)
        if pos != -1:
            brace_count = 1
            pos = content.find(b'{', idx) + 1
            while pos < len(content) and brace_count > 0:
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
            
            # Remove from current position
            new_content = content[:func_start] + content[func_end:]
            
            # Find insertion point (before loadTourismSignals)
            insert_idx = new_content.find(b'async function loadTourismSignals')
            if insert_idx != -1:
                new_content = new_content[:insert_idx] + func_code + b'\n\n' + new_content[insert_idx:]
                
                with open('static/app.js', 'wb') as f:
                    f.write(new_content)
                print('Fixed!')
            else:
                print('Could not find loadTourismSignals')
        else:
            print('Could not find function start')
    else:
        print('Pattern not found')