import sys

sys.path.insert(0, r'D:\SBC_Tool')
from app import app

with app.test_client() as client:
    resp = client.get('/api/weekly_commentary?date=2026-08-24')
    print('Status:', resp.status_code)
    import json
    data = json.loads(resp.data)
    print('Top keys:', list(data.keys()))
    if 'data' in data:
        print('Data keys:', list(data['data'].keys()))
        print('Has sector_outlook:', 'sector_outlook' in data['data'])
        if 'sector_outlook' in data['data']:
            print('Sector outlook count:', len(data['data']['sector_outlook']))
            for s in data['data']['sector_outlook'][:3]:
                print('  {}: {}'.format(s['sector'], s['trend_outlook']))
