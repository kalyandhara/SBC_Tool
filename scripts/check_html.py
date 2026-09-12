with open(r'D:\SBC_Tool\templates\index.html', 'r') as f:
    content = f.read()
import re

# Check nifty-chart-panel class
matches = re.findall(r'nifty-chart-panel[^>]*>', content)
for m in matches:
    print("nifty-chart-panel:", m)

# Check if it has 'hidden' class
if 'nifty-chart-panel' in content:
    # find the section
    idx = content.find('nifty-chart-panel')
    print("Context:", content[max(0,idx-100):idx+200])