import sys
sys.path.insert(0, r'D:\SBC_Tool')
import urllib.request

try:
    req = urllib.request.Request('http://127.0.0.1:8000/')
    resp = urllib.request.urlopen(req, timeout=5)
    print('Main Page Status:', resp.status)
    html = resp.read().decode()
    checks = ['weekly-commentary', 'weekly-commentary-date', 'weekly-commentary-run', 'weekly-commentary-content']
    for c in checks:
        found = c in html
        print(f'  {c}: {"FOUND" if found else "MISSING"}')
except Exception as e:
    print('Error:', e)