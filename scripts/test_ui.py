import sys
sys.path.insert(0, r'D:\SBC_Tool')
from app import app

with app.test_client() as client:
    resp = client.get('/')
    html = resp.get_data(as_text=True)
    
    checks = [
        'weekly-commentary',
        'weekly-commentary-date',
        'weekly-commentary-run',
        'weekly-commentary-content',
    ]
    
    for c in checks:
        found = c in html
        print(f'  {c}: {"FOUND" if found else "MISSING"}')