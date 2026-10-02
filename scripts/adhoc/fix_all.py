with open('static/app.js', 'rb') as f:
    content = f.read()

# 1. Fix the broken for loop in renderChemicalSignals
idx = content.find(b'for (const [keyfunction renderTourismSignals(data) {')
if idx >= 0:
    content = content[:idx] + b'for (const [key, val] of Object.entries(data.details)) {' + content[idx + 47:]
    content = content[:idx] + b'}' + content[idx:]
    print('Fixed for loop header and added missing }')

# 2. Find and remove the misplaced renderTourismSignals function
func_start = content.find(b'function renderTourismSignals(data) {')
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

# 3. Insert renderTourismSignals before loadTourismSignals
insert_idx = content.find(b'async function loadTourismSignals')
if insert_idx != -1:
    # Recreate the function code
    func_code = b'function renderTourismSignals(data) {\n  const content = $(\"tourism-signals-content\");\n  content.innerHTML = \"\";\n\n  const summary = document.createElement(\"div\");\n  summary.className = \"tourism-summary\";\n  summary.innerHTML = `<strong>${data.summary}</strong>`;\n  content.appendChild(summary);\n\n  if (!data.is_bullish && !data.active_signals.length) {\n    const none = document.createElement(\"div\");\n    none.className = \"tourism-empty\";\n    none.textContent = \"No tourism/leisure bullish syntax active today.\";\n    content.appendChild(none);\n    return;\n  }\n\n  const badge = document.createElement(\"div\");\n  badge.className = \"tourism-badge \" + data.conviction.toLowerCase();\n  badge.textContent = data.conviction + (data.is_strong_bullish ? \" \u00b7 STRONG\" : data.is_bullish ? \" \u00b7 BULLISH\" : \" \u00b7 WATCH\");\n  content.appendChild(badge);\n\n  if (data.active_signals.length > 0) {\n    const signalsSection = document.createElement(\"div\");\n    signalsSection.className = \"tourism-section\";\n    signalsSection.innerHTML = \"<h4>Active Signals</h4>\";\n    for (const s of data.active_signals) {\n      const card = document.createElement(\"div\");\n      card.className = \"tourism-card\";\n      card.textContent = s;\n      signalsSection.appendChild(card);\n    }\n    content.appendChild(signalsSection);\n  }\n\n  if (data.price_levels) {\n    const pl = data.price_levels;\n    const priceSection = document.createElement(\"div\");\n    priceSection.className = \"tourism-section\";\n    priceSection.innerHTML = `<h4>Price Levels</h4>\n      <div class=\"tourism-price-row\"><strong>Current:</strong> ${pl.current_price}</div>\n      <div class=\"tourism-price-row\"><strong>Target:</strong> ${pl.target_high}</div>\n      <div class=\"tourism-price-row\"><strong>Support:</strong> ${pl.support_zone}</div>\n      <div class=\"tourism-price-row\"><strong>Stop Loss:</strong> ${pl.stop_loss}</div>\n      <div class=\"tourism-method\">${pl.method}</div>`;\n    content.appendChild(priceSection);\n  }\n\n  if (data.details) {\n    const detailSection = document.createElement(\"div\");\n    detailSection.className = \"tourism-section\";\n    detailSection.innerHTML = `<h4>Details <span class=\"tourism-toggle\">\u25bc</span></h4>`;\n    const detailList = document.createElement(\"div\");\n    detailList.className = \"tourism-detail-list\";\n    for (const [key, val] of Object.entries(data.details)) {\n      const card = document.createElement(\"div\");\n      card.className = \"tourism-card\";\n      card.textContent = `${key}: ${val}`;\n      detailList.appendChild(card);\n    }\n    detailSection.appendChild(detailList);\n    content.appendChild(detailSection);\n  }\n\n  $(\"tourism-signals\").classList.remove(\"hidden\");\n}'

    insert_idx = content.find(b'async function loadTourismSignals')
    if insert_idx != -1:
        content = content[:insert_idx] + func_code + b'\n\n' + content[insert_idx:]
        print('Inserted renderTourismSignals before loadTourismSignals')

# 3. Remove duplicate loadLunarForecast
first_lunar = content.find(b'async function loadLunarForecast')
second_lunar = content.find(b'async function loadLunarForecast', first_lunar + 1)
if first_lunar != -1 and second_lunar != first_lunar:
    next_func = content.find(b'async function ', second_lunar + 1)
    if next_func != -1:
        content = content[:second_lunar] + content[next_func:]
        print('Removed duplicate loadLunarForecast')

# 4. Check brace balance
open_braces = content.count(b'{')
close_braces = content.count(b'}')
print(f'Brace balance: {content.count(b"{") - content.count(b"}")}')

with open('static/app.js', 'wb') as f:
    f.write(content)

print('Done!')
