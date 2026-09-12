import sys
sys.path.insert(0, r'D:\SBC_Tool')

# Test the API endpoint directly
from app import app

with app.test_client() as client:
    # Test weekly commentary API
    resp = client.get('/api/weekly_commentary?date=2026-08-24')
    print('Weekly Commentary API Status:', resp.status_code)
    import json
    data = json.loads(resp.data)
    print('Data keys:', list(data.get('data', {}).keys()))
    print('Has sector_outlook:', 'sector_outlook' in data.get('data', {}))
    print('Has general_strategy:', 'general_strategy' in data.get('data', {}))
    print('Has nifty_levels:', 'nifty_levels' in data.get('data', {}))
    
    if 'sector_outlook' in data.get('data', {}):
        print('Sector outlook count:', len(data['data']['sector_outlook']))
        for s in data['data']['sector_outlook'][:3]:
            print('  {}: {}'.format(s['sector'], s['trend_outlook']))
    
    print('\nGeneral Strategy length:', len(data['data'].get('general_strategy', '')))
    print('Nifty Levels length:', len(data['data'].get('nifty_levels', '')))