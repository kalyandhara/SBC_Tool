import sys

sys.path.insert(0, r'D:\SBC_Tool')
from app import app

with app.test_client() as client:
    resp = client.get('/')
    html = resp.get_data(as_text=True)
    panels = [
        'yoga-alerts',
        'futurecast-results',
        'bullish-timeline',
        'weekly-commentary-content',
        'bullion-vedha-content',
        'transit-vedha-content',
    ]
    for p in panels:
        found = f'id="{p}"' in html
        print(f'{p}: {"FOUND" if found else "MISSING"}')
