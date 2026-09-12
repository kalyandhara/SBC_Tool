import sys
sys.path.insert(0, r'D:\SBC_Tool')
from app import app

with app.test_client() as client:
    # Test transit vedha daily API
    resp = client.get('/api/transit_vedha?date=2026-08-24')
    print('Transit Vedha Daily API:', resp.status_code)
    import json
    data = json.loads(resp.data)
    print('Keys:', list(data.keys()))
    print('Signal count:', len(data.get('data', {}).get('signals', [])))
    
    print('\n---')
    
    # Test transit vedha weekly API
    resp = client.get('/api/transit_vedha_week?date=2026-08-24')
    print('\nTransit Vedha Weekly API:', resp.status_code)
    data = json.loads(resp.data)
    print('Keys:', list(data.keys()))
    print('Weekly summary:', data.get('weekly_summary', {}))
    print('Unique signals:', len(data.get('weekly_unique_signals', [])))