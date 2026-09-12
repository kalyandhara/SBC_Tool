import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
c = open(r'D:\SBC_Tool\static\app.js', encoding='utf-8', errors='replace').read()
needle = 'const grid = $("grid")'
i = c.find(needle)
print(c[i-200:i+1800])