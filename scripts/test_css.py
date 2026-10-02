import sys

sys.path.insert(0, r'D:\SBC_Tool')
from app import app

with app.test_client() as client:
    resp = client.get('/static/style.css?v=5')
    print('CSS Status:', resp.status_code)
    print('CSS Length:', len(resp.get_data()))
    css = resp.get_data(as_text=True)
    checks = ['weekly-commentary-panel', 'weekly-main-cycle', 'weekly-bias', 'moon-transit-table']
    for c in checks:
        found = c in css
        print(f'  {c}: {"FOUND" if found else "MISSING"}')
