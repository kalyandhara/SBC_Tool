import sys

sys.path.insert(0, r'D:\SBC_Tool')
from app import app

with app.test_client() as client:
    # Test main page
    resp = client.get('/')
    print('Main page:', resp.status_code)
    html = resp.get_data(as_text=True)
    print('Has bullion-vedha panel:', 'bullion-vedha' in html)
    print('Has bullion-vedha-date:', 'bullion-vedha-date' in html)
    print('Has bullion-vedha-run:', 'bullion-vedha-run' in html)
    print('Has bullion-vedha-content:', 'bullion-vedha-content' in html)

    # Test API
    resp = client.get('/api/bullion_vedha?date=2026-08-24')
    print('\nBullion Vedha API:', resp.status_code)
    import json
    data = json.loads(resp.data)
    print('Keys:', list(data.keys()))
    print('Signal count:', len(data.get('data', {}).get('signals', [])))

    resp = client.get('/api/bullion_vedha_week?date=2026-08-24')
    print('\nBullion Vedha Week API:', resp.status_code)
    data = json.loads(resp.data)
    print('Keys:', list(data.keys()))
