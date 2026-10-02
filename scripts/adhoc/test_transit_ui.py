import sys

sys.path.insert(0, r'D:\SBC_Tool')
from app import app

with app.test_client() as client:
    # Test main page
    resp = client.get('/')
    print('Main page:', resp.status_code)
    html = resp.get_data(as_text=True)
    print('Has transit-vedha panel:', 'transit-vedha' in html)
    print('Has transit-vedha-date:', 'transit-vedha-date' in html)
    print('Has transit-vedha-run:', 'transit-vedha-run' in html)
    print('Has transit-vedha-content:', 'transit-vedha-content' in html)
    print('Has transit-vedha-week:', 'transit-vedha-week' in html)
