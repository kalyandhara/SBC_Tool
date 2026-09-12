import sys
sys.path.insert(0, r'D:\SBC_Tool')
from app import app

with app.test_client() as client:
    # Test futurecast API structure
    resp = client.get('/api/futurecast?date=2026-08-24')
    import json
    data = json.loads(resp.data)
    print('Futurecast keys:', list(data.keys()))
    print('timeline_windows:', len(data.get('timeline_windows', [])))
    print('windows:', len(data.get('windows', [])))
    print('range_start:', data.get('range_start'))
    print('range_end:', data.get('range_end'))
    print('method:', data.get('method')[:50] if data.get('method') else 'None')
    print('disclaimer:', data.get('disclaimer'))
    
    # Test bullish futurecast
    resp = client.get('/api/bullish_futurecast?date=2026-08-24')
    data = json.loads(resp.data)
    print('\nBullish Futurecast keys:', list(data.keys()))
    print('scan_window:', data.get('scan_window'))
    print('clusters:', len(data.get('clusters', [])))
    print('version:', data.get('version'))
    print('disclaimer:', data.get('disclaimer'))