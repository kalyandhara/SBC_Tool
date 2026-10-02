import sys

sys.path.insert(0, '.')
from app import app

with app.test_client() as client:
    resp = client.get('/')
    print('Status:', resp.status_code)
    html = resp.data.decode()
    print('Grid div present:', 'id="grid"' in html)
    print('Rays SVG present:', 'id="rays"' in html)
    print('Grid panel present:', 'grid-panel' in html)
