import sys
sys.path.insert(0, r'D:\SBC_Tool')
from app import app

with app.test_client() as client:
    # Test bullion vedha daily
    resp = client.get('/api/bullion_vedha?date=2026-08-24')
    print('Bullion Vedha Daily Status:', resp.status_code)
    import json
    data = json.loads(resp.data)
    print('Keys:', list(data.keys()))
    print('Summary:', data.get('data', {}).get('summary', {}))
    print('Signal count:', len(data.get('data', {}).get('signals', [])))
    
    print('\n---')
    
    # Test bullion vedha weekly
    resp = client.get('/api/bullion_vedha_week?date=2026-08-24')
    print('\nBullion Vedha Weekly Status:', resp.status_code)
    data = json.loads(resp.data)
    print('Keys:', list(data.keys()))
    print('Weekly summary:', data.get('weekly_summary', {}))
    print('Unique signals:', len(data.get('weekly_unique_signals', [])))