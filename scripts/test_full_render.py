import sys
sys.path.insert(0, r'D:\SBC_Tool')
from app import app

with app.test_client() as client:
    # Test the full prediction flow
    resp = client.get('/api/prediction?date=2026-08-24&time=09:15&tz=Asia/Kolkata&anchor=nse&school=classical')
    print('Prediction API:', resp.status_code)
    import json
    data = json.loads(resp.data)
    
    # Verify all data needed for rendering
    checks = {
        'yoga_alerts': len(data.get('yoga_alerts', [])),
        'market_alert': 'windows' in data.get('market_alert', {}),
        'planets': len(data.get('planets', [])),
        'grid': len(data.get('grid', [])),
        'sectors': len(data.get('sectors', [])),
        'planet_sectors': len(data.get('planet_sectors', [])),
        'recommendation': 'verdict' in data.get('recommendation', {}),
        'point_hits': len(data.get('point_hits', [])),
        'per_point': len(data.get('per_point', [])),
    }
    
    for k, v in checks.items():
        status = 'OK' if v else 'MISSING'
        print(f'{k}: {status} ({v})')