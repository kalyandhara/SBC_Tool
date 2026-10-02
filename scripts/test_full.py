import sys

sys.path.insert(0, r'D:\SBC_Tool')
import json
import urllib.request

try:
    # Test prediction API which should also load weekly commentary
    req = urllib.request.Request('http://127.0.0.1:8000/api/prediction?date=2026-08-24&time=09:15&tz=Asia/Kolkata&anchor=nse&school=classical')
    resp = urllib.request.urlopen(req, timeout=10)
    print('Prediction API Status:', resp.status)
    data = json.loads(resp.read().decode())
    print('Keys:', list(data.keys()))
except Exception as e:
    print('Error:', e)

try:
    # Test weekly commentary API
    req = urllib.request.Request('http://127.0.0.1:8000/api/weekly_commentary?date=2026-08-24')
    resp = urllib.request.urlopen(req, timeout=10)
    print('\nWeekly Commentary API Status:', resp.status)
    data = json.loads(resp.read().decode())
    print('Data keys:', list(data.get('data', {}).keys()))
    print('Has sector_outlook:', 'sector_outlook' in data.get('data', {}))
    if 'sector_outlook' in data.get('data', {}):
        print('Sector outlook count:', len(data['data']['sector_outlook']))
        for s in data['data']['sector_outlook'][:5]:
            print('  {}: {} | {}'.format(s['sector'], s['trend_outlook'], s['astrological_influence'][:60]))
except Exception as e:
    print('Error:', e)
