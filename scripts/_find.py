c=open(r'D:\SBC_Tool\static\app.js', encoding='utf-8').read()
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import re
m=re.search(r'async function run\(\) \{.*?^\}', c, re.M|re.S)
if m:
    # find closing brace of function - need more robust
    start=m.start()
    # find matching brace
    depth=0
    pos=start
    for i,ch in enumerate(c[start:]):
        if ch=='{': depth+=1
        elif ch=='}':
            depth-=1
            if depth==0:
                end=start+i+1
                break
    print(c[start:end])