import re

with open('D:/SBC_Tool/static/app.js', 'rb') as f:
    content = f.read()

# Find the location - content.appendChild(report; followed by the classList line
# We'll insert the chart rendering code right after content.appendChild(report);

# Find the exact byte offset
idx = content.find(b'content.appendChild(report);')
if idx >= 0:
    # Print context
    start = idx
    end = idx + 150
    print('Found at offset:', idx)
    print('Context (decoded):')
    try:
        print(content[start:end].decode('utf-8', errors='replace'))
    except:
        print('Decode error')
    
    # Insert the chart rendering code after 'content.appendChild(report);'
    # The line is: content.appendChild(report);\n  $("kp-intraday").classList.remove("hidden");\n}
    # We want to add: renderKPIntradayPriceChart(data); between the report append and the classList removal
    
    # Create the insertion string
    insertion = b'  content.appendChild(report);\n  // Render KP Intraday Price Chart with lightweight-charts.js\n  renderKPIntradayPriceChart(data);\n  $("kp-intraday").classList.remove("hidden");\n}'
    
    # Actually, let's insert AFTER content.appendChild(report); but BEFORE the next line
    # The next line starts right after, so we insert between them
    new_content = content[:idx + len(b'content.appendChild(report);')] + insertion + content[idx + len(b'content.appendChild(report);'):]
    
    with open('D:/SBC_Tool/static/app.js', 'wb') as f:
        f.write(new_content)
    print('Successfully added chart rendering code')
else:
    print('Pattern not found')